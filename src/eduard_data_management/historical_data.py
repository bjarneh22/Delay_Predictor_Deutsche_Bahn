'''
This module downloads, cleans, and processes Deutsche Bahn train data 
from the Hugging Face dataset, and stores it in a DuckDB database.

Main steps performed in this script:

1. Downloads parquet files from the Hugging Face dataset if not already present locally.
2. Filters the data for train types ICE, IC, and EC.
3. Creates a temporary DuckDB table with cleaned and typed columns.
4. Adds an event_time column for ordering events.
5. Flags start and end of rides based on planned arrival and departure times.
6. Creates lag-based views to identify new rides and assigns preliminary ride IDs.
7. Validates rides to keep only complete rides (with exactly one start and one end flag).
8. Renumbers rides consecutively and stores the final ride information in a DuckDB table 'train_delay'.

This module does not define functions or classes.

Author: Member 3
'''

from pathlib import Path
import os
import requests
import duckdb
import pandas as pd


# Set the url to the path that has the .parquet files for the huggingface dataset
url = "https://huggingface.co/api/datasets/piebro/deutsche-bahn-data/parquet/default/train"

# set directories so that python knows where to read data from and where to place the db
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PARQUET_DIR = os.path.join(DATA_DIR, "parquet")

parquet_folder = Path(PARQUET_DIR)
parquet_folder.mkdir(exist_ok=True)

# This function can lead to errors because of too many calls of the url.
# If it doesn't work just restart the code or wait for a few minutes  (may take some reruns).
response = requests.get(url)

response.raise_for_status()
parquet_urls = response.json()

# Only downloads the parquet files that aren't already downloaded (in total 857 files)
for url in parquet_urls:
    filename = parquet_folder / url.split("/")[-1]
    if not filename.exists():
        print(f"Downloading {filename}...")
        r = requests.get(url)
        r.raise_for_status()
        with open(filename, "wb") as f:
            f.write(r.content)


local_files = list(parquet_folder.glob("*.parquet"))
local_files_str = [str(f) for f in local_files]


# Only filter for ICE, IC and EC because they have the most consistent data naming
allowed_types = ["ICE","IC","EC"] #right now "NJ", "RJ", "RJX", "ECE" and "FLX" are left out for easier handling

# Connect to DuckDB
con = duckdb.connect("data/train.duckdb")


# This will be the view with all our data present inside, from this point onwards we modify and filter
# We directly set the datatype of each column and restrict the data only to our allowed_types
con.execute("""
CREATE OR REPLACE TEMP TABLE raw_clean AS
SELECT
    station_name::VARCHAR AS station_current,
    final_destination_station::VARCHAR AS station_dest,
    train_name::VARCHAR AS train_name,
    train_type::VARCHAR AS train_type,
    departure_planned_time::TIMESTAMP AS departure_planned,
    arrival_planned_time::TIMESTAMP AS arrival_planned,
    departure_change_time::TIMESTAMP AS departure_real,
    arrival_change_time::TIMESTAMP AS arrival_real,
    delay_in_min::INT AS delay,
    is_canceled::BOOL AS canceled
FROM read_parquet(?, union_by_name = TRUE)
WHERE train_type = ANY(?)
""", [local_files_str, allowed_types])


# Add a column event_time so that we can order by it (without departure_planned and arrival_planned are NaT sometimes)
con.execute("""
CREATE OR REPLACE TEMP VIEW ordered AS
SELECT *,
    COALESCE(departure_planned, arrival_planned) AS event_time
FROM raw_clean
""")

# Here we take a look if start and end rows are correctly flagged (i.e. start if arrival_planned is NaT and same for departure_planned)
con.execute("""
CREATE OR REPLACE VIEW ride_flags AS
SELECT *,
    CASE
        WHEN arrival_planned IS NULL AND departure_planned IS NOT NULL THEN 1
        ELSE 0
    END AS start_flag,
    CASE
        WHEN departure_planned IS NULL
         AND arrival_planned IS NOT NULL
         AND station_current = station_dest THEN 1
        ELSE 0
    END AS end_flag
FROM ordered
""")

# Create a view for the lags (entries before each row) and use time to mark new rides
con.execute("""
CREATE OR REPLACE TEMP VIEW ride_with_lag AS
SELECT *,
    LAG(event_time) OVER (ORDER BY train_name, event_time) AS prev_event_time,
    LAG(train_name) OVER (ORDER BY train_name, event_time) AS prev_train
FROM ride_flags
""")

# If a row has a start_flag, a different train name or a time gap of more than 2 hours preceeding the row has to belong to a new ride
con.execute("""
CREATE OR REPLACE TEMP VIEW ride_starts AS
SELECT *,
    CASE
        WHEN start_flag = 1 THEN 1
        WHEN prev_train IS DISTINCT FROM train_name THEN 1
        WHEN prev_event_time IS NOT NULL
             AND event_time - prev_event_time > INTERVAL '2 HOURS'
        THEN 1
        ELSE 0
    END AS new_ride_flag
FROM ride_with_lag;
""")

# Use the new_ride_flag to get ride_ids (unfiltered)
con.execute("""
CREATE OR REPLACE TEMP VIEW preliminary_rides AS
SELECT *,
    SUM(new_ride_flag) OVER (
    ORDER BY train_name, event_time
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
) AS ride_id_prelim
FROM ride_starts
""")

# The column start_flag and end_flag should each sum up to 1 if the ride is complete
con.execute("""
CREATE OR REPLACE TEMP VIEW ride_validation AS
SELECT
    ride_id_prelim,
    SUM(start_flag) AS n_starts,
    SUM(end_flag)   AS n_ends
FROM preliminary_rides
GROUP BY ride_id_prelim
""")

# Join ride_validation and preliminary_rides to check for completeness
con.execute("""
CREATE OR REPLACE TEMP VIEW complete_rides AS
SELECT r.*
FROM preliminary_rides r
JOIN ride_validation v
  ON r.ride_id_prelim = v.ride_id_prelim
WHERE v.n_starts = 1
  AND v.n_ends   = 1

""")

# With all the incomplete data omitted, we renumber the database in order to have a consequent numbering schema from 1 to ... 
con.execute("""
CREATE OR REPLACE TEMP VIEW final_rides AS
SELECT *,
    DENSE_RANK() OVER (ORDER BY ride_id_prelim) AS ride_id
FROM complete_rides
""")

# Materialize the database
con.execute("""
CREATE OR REPLACE TABLE train_delay AS
SELECT
    ride_id,
    train_name,
    train_type,
    REPLACE(station_current, 'Berlin Hauptbahnhof', 'Berlin Hbf') AS station_current,
    REPLACE(station_dest, 'Berlin Hauptbahnhof', 'Berlin Hbf') AS station_dest,
    canceled,
    arrival_planned,
    arrival_real,
    departure_planned,
    departure_real,
    event_time,
    delay
FROM final_rides
ORDER BY ride_id, event_time
""")
con.close()