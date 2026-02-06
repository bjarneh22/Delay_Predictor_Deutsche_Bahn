# %% SETUP & PATHS
import pandas as pd
import sqlite3
from pathlib import Path
import holidays

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "TBA_project_backup" / "train_delay.db"

# %% LOAD DATA
# establish SQL connection to database and load into dataframe
con = sqlite3.connect(DATA_DIR)
df_raw = pd.read_sql_query("SELECT * from train_delay", con)
con.close()

# %% DATA INSPECTION
df_raw.info()
df_raw.head(5)
print(df_raw["delay_in_min"].describe())
# df_raw["train_type"].value_counts()

# %% ASSIGN CORRECT DATA TYPES

# preserve copy of data in df_raw
df = df_raw

# time columns
time_cols = [
    "departure_planned",
    "arrival_planned",
    "departure_actual",
    "arrival_actual"]
df[time_cols] = df[time_cols].apply(pd.to_datetime, errors='coerce')

# categorical variables
categorical_cols = [
    "start_station_name",
    "end_station_name",
    "train_name",
    "train_type"
]
df[categorical_cols] = df[categorical_cols].astype("category")

df.info()
df.head()

# %% DATA WRANGLING - RIDE RELATED


### FIRST FEATURES 
features_ride = (
    df_raw
    .groupby("train_name") # EXCHANGE BY UNIQUE IDENTIFIER
    .agg(     
        # route
        station_start=("start_station_name", "first"), # CHANGE TO CURRENT
        station_dest=("start_station_name", "last"),
        stops_total=("start_station_name", "count"),
        
        # time
        time_start_planned=("departure_planned", "first"),
        time_dest_planned=("arrival_planned", "last"),
    )
    .reset_index())

### TRAVEL TIME
features_ride["travel_time"] = (
    features_ride["time_dest_planned"]
    - features_ride["time_start_planned"]
).dt.total_seconds() / 60

### CALENDAR 
features_ride = features_ride.assign(
    weekday=lambda d: d["time_start_planned"].dt.weekday.astype("category"),  
    weekend=lambda d: (d["weekday"].isin([5, 6])).astype("category"),
    month=lambda d: d["time_start_planned"].dt.month.astype("category")
)

### SEASON
# function that assigns season to month
def season(month):
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"
    
features_ride["season"] = features_ride["month"].apply(season).astype("category")

### FEAST
# get holidays
de_holidays = holidays.Germany()

'''
features_ride["feast"] = (
    features_ride["time_start_planned"]
    .dt.date
    .apply(lambda d: int(d in de_holidays))
    .astype(int)
)
'''

features_ride["feast"] = (
    features_ride["time_start_planned"]
    .dt.date
    .apply(lambda d: 1 if pd.notnull(d) and d in de_holidays else 0)
)


features_ride.info()


# %% DATA WRANGLING - STATION RELATED


# %% DATA WRANGLING - SEQUENCE RELATED



# %% MISCELLANEOUS
# check data
df_filtered = df[(df["train_name"] == "ICE 920")]
df_filtered

