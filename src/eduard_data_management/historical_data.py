from pathlib import Path
import os
import requests
import duckdb
import pandas as pd


# set the url to the path that has the .parquet files for the huggingface dataset
url = "https://huggingface.co/api/datasets/piebro/deutsche-bahn-data/parquet/default/train"

# set directories so that python knows where to read data from and where to place the db
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PARQUET_DIR = os.path.join(DATA_DIR, "parquet")

parquet_folder = Path(PARQUET_DIR)
parquet_folder.mkdir(exist_ok=True)

# this function can lead to errors because of too many calls of the url.
# If it doesn't work just restart the code or wait for a few minutes  (may take some reruns).
response = requests.get(url)

response.raise_for_status()
parquet_urls = response.json()

# only downloads the parquet files that aren't already downloaded (in total 822 files)
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


# only filter for ICE, IC, EC and ECE because they have the most consistent data naming
allowed_types = ["ICE","IC","EC","ECE"] #right now "NJ", "RJ", "RJX" and "FLX" are left out for easier handling

# connect to db
con = duckdb.connect("train.duckdb")

# create the train_delay table in train.duckdb
con.execute("""
CREATE OR REPLACE TABLE train_delay AS

-- create a temporary table

WITH ordered AS (
    SELECT eva,
        station_name,              
        final_destination_station,
        train_name,
        train_type,
        departure_planned_time,
        departure_change_time,
        arrival_planned_time,
        arrival_change_time,
        delay_in_min,
        is_canceled,
        
        -- previous planned departure for the same train
        
        LAG(departure_planned_time)
            OVER (PARTITION BY train_name ORDER BY departure_planned_time)
            AS prev_time
    FROM read_parquet(?, union_by_name = TRUE)
    WHERE train_type = ANY(?)
),
per_train_journeys AS (
    SELECT *,
    
           -- increment journey id when a new run starts
           
           SUM(
               CASE
                   WHEN prev_time IS NULL THEN 1
                   
                   -- long gap indicates a new operational journey
                   
                   WHEN departure_planned_time - prev_time > INTERVAL '6 HOURS' THEN 1
                   ELSE 0
               END
           ) OVER (
               PARTITION BY train_name
               ORDER BY departure_planned_time
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) AS journey_id_train 
    FROM ordered
)
SELECT *,

       -- global journey id across all trains
       
       DENSE_RANK() OVER (
           ORDER BY train_name, journey_id_train
       ) AS journey_id
FROM per_train_journeys
""", [local_files_str, allowed_types])

# mit Einschränkungen der Zugarten: 3567509 Zeilen
# ohne Einschränkungen der Zugarten: 3783460 Zeilen

# with select you can pick which variables you want to see
# with order you can pick by which the db gets ordered
# the limit is the amount of shown entries
first_rows = con.execute("""
SELECT station_name, final_destination_station, departure_planned_time, journey_id
FROM train_delay
ORDER BY journey_id
LIMIT 500
""").df()

# to make sure every entry is seen
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
pd.set_option('display.max_colwidth', None)

print(first_rows)

