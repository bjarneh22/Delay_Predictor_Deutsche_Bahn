#########################
# LIBRARIES
#########################


import pandas as pd
import numpy as np
import holidays
from sklearn.preprocessing import FunctionTransformer


#########################
# FILTERING
#########################

### FILTER FUNCTION FOR ICE/IC TRAINS ONLY ###
def filter_train_type(df):
    output_df = df[df["train_type"].str.contains("ICE|IC", case=False, na=False)].copy()
    return output_df


#########################
# FEATURES
#########################


def historic_delay_features(df):

    # make correct date format
    df["date"] = df["departure_real"].dt.floor("D")

    # time-frames
    min_lookback = pd.Timedelta("60D") # gap between current day and time_frame
    lookback = pd.Timedelta("60D") # length of time_frame

    # create list for historic features
    hist_features = []

    # extract names of stations in list
    stations_list = df["station_current"].unique()

    # loop over stations
    for station in stations_list:

        # get information for station (df and corresponding days)
        df_station = df[df["station_current"] == station].sort_values("departure_real")

        # only select stations that are not NA
        df_station = df_station[df_station["date"].notna()]
        if df_station.empty:
            continue

        dates = pd.date_range(df_station["date"].min(), df_station["date"].max())

        # loop over days
        for day in dates:

            window_start = day - min_lookback - lookback
            window_end = day - min_lookback

            time_frame = (df_station["departure_real"] < window_end) & \
                       (df_station["departure_real"] >= window_start)
            
            if df_station.loc[time_frame, "delay"].empty:
                hist_avg = 0
                hist_q90 = 0
                hist_count = 0
            else:
                hist_avg = df_station.loc[time_frame, "delay"].mean()
                hist_q90 = df_station.loc[time_frame, "delay"].quantile(0.9)
                hist_count = df_station.loc[time_frame, "delay"].count()
                


            hist_features.append({
                "station_current": station,
                "date": day,
                "hist_delay_avg": hist_avg,
                "hist_delay_q90": hist_q90,
                "hist_delay_count": hist_count
                })
        
    hist_df = pd.DataFrame(hist_features)
    return hist_df


def create_features(df, api, historical_features):


    ### PREPARATION

    # define transformer
    def sin_transformer(period):
        return FunctionTransformer(lambda x: np.sin(x / period * 2 * np.pi))

    def cos_transformer(period):
        return FunctionTransformer(lambda x: np.cos(x / period * 2 * np.pi))

    # create copy: do not overwrite input df
    df = df.copy()

    # check that all date variables have the correct format
    datetime_cols = ["departure_planned", "arrival_planned", "departure_real", "arrival_real"]
    for col in datetime_cols:
        df[col] = pd.to_datetime(df[col])

    # arrange dataset again to guarantee correct feature creation
    df = df.sort_values(by=["ride_id", "departure_planned"])



    ### RIDE RELATED ###

    # prepare grouping
    grouped = df.groupby("ride_id")

    # number of stops
    df["stops_total"] = grouped["station_current"].transform("count")

    # time departure and arrival (WILL BE DELETED LATER)
    df["departure_planned_start"] = grouped["departure_planned"].transform("first")
    df["arrival_planned_dest"] = grouped["arrival_planned"].transform("last")

    # travel time
    df["travel_time"] = (df["arrival_planned_dest"] - df["departure_planned_start"]).dt.total_seconds() / 60

    # weekday
    df["weekday"] = df["departure_planned_start"].dt.weekday
    # FROM: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html
    df["weekday_sin"] = np.sin(2 * np.pi * df["weekday"] / 7)
    df["weekday_cos"] = np.cos(2 * np.pi * df["weekday"] / 7)
    df["weekend"] = (df["weekday"] >= 5).astype(int)

    # month
    df["month"] = df["departure_planned_start"].dt.month
    # FROM: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html
    df["month_sin"] = np.sin(2 * np.pi * (df["month"] - 1) / 12)
    df["month_cos"] = np.cos(2 * np.pi * (df["month"] - 1) / 12)

    # feast
    de_holidays = holidays.Germany()
    df["feast"] = df["departure_planned_start"].dt.date.apply(lambda x: x in de_holidays)



    ### STATION RELATED

    # hour
    df["hour"] = np.where(
        df["departure_real"].notna(), 
        df["departure_real"].dt.hour, 
        df["arrival_real"].dt.hour)
    
    # FROM: https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    
    # dwell-time planned
    df["dwell_time_planned"] = (df["departure_planned"] - df["arrival_planned"]).dt.total_seconds() / 60
    df["dwell_time_planned"] = df["dwell_time_planned"].fillna(0) # for start and destination stations



    ### SEQUENCE RELATED

    # station role: start, mid, end
    conditions = [
        (df["station_current"] == df["station_start"]),
        (df["station_current"] == df["station_dest"])
        ]
    choices = ["start", "end"]
    df["station_role"] = np.select(conditions, choices, default = "mid") 

    # stops index in journey
    df["stop_index"] = grouped.cumcount() + 1 
    
    # time since start planned
    df["time_since_start_planned"] = (
        df["arrival_planned"] - df["departure_planned_start"]).dt.total_seconds() / 60
    df["time_since_start_planned"] = df["time_since_start_planned"].fillna(0) # for start stations

    # share ride time
    df["share_ride_time"] = (df["time_since_start_planned"] / df["travel_time"])



    ### WEATHER

    # precipitation
    df["precipitation_any"] = (df["precipitation"] > 0).astype(int)
    df["precipitation_log"] = np.log1p(df["precipitation"])



    ### HISTORICAL

    # check if function is applied for historical data or api data
    if api == False:

        # merge by station_current and date
        df = df.merge(
            historical_features,
            on = ["station_current", "date"],
            how = "left"
            )
    else: 

        # if api data: merge only by station_current 
        # (in lookup file only one row per station)
        df = df.merge(
            historical_features,
            on = ["station_current"],
            how = "left"
        )    
    


    ### FINAL TRANSFORMATIONS AND SELECTION

    # transform time departure and arrival (datetime to hour)
    df["departure_planned_start"] = df["departure_planned_start"].dt.hour
    df["departure_rush_morning"] = df["departure_planned_start"].between(6, 9).astype(int)
    df["departure_rush_evening"] = df["departure_planned_start"].between(15, 18).astype(int)
    

    df = df.drop(columns = ["weekday", "month", "hour", 
                            "precipitation", 
                            "departure_planned_start", "arrival_planned_dest",
                            "date"])


    return df


#########################
# CLEAN API DATA
#########################

### FUNCTION TO FIND POSSIBLE DESTINATIONS FROM A GIVEN STATION ###
def get_possible_destinations(df, station_name):
    possible_destinations = []

    for ride_id, train_group in df.groupby("ride_id"):
        
        # find row where current_station is station_name
        start_row = train_group[train_group["station_current"] == station_name]
        
        # If the train actually stops at our station:
        if not start_row.empty:
            station_time = start_row["departure_real"].iloc[0]
            
            # get stations where actual_arrival is greater than station_time
            later_stops = train_group[train_group["arrival_real"] > station_time]
            
            # get station names and add to possible_destinations
            stations_names = later_stops["station_current"].tolist()
            possible_destinations.extend(stations_names)
            
    # use set() to remove duplicates
    return sorted(list(set(possible_destinations)))



### FUNCTION TO GET CONNECTION BETWEEN TWO STATIONS ###
def get_connections(df, station_start, station_dest):
    
    suited_rides = []

    for ride_id, train_group in df.groupby("ride_id"):
        start_row = train_group[train_group["station_current"] == station_start]
        
        if not start_row.empty:
            station_start_time = start_row["departure_real"].iloc[0]
            
            # get stations coming after station_start_time
            later_stops = train_group[train_group["arrival_real"] > station_start_time]
            
            # check: is station_dest in later_stops?
            if station_dest in later_stops["station_current"].values:
                # add ride_id to suited_rides
                suited_rides.append(train_group)

    # combine all suited_rides into one df
    if suited_rides:
        df_trip = pd.concat(suited_rides, ignore_index=True)
        return df_trip
    else:
        print(f"No current connections found.")
        return None
    


#########################
# ML-MODEL
#########################

### FUNCTION THAT SPLITS FEATURES AND TARGET
def choose_features_target(df):

    cols_exclude = ["ride_id", "delay", "departure_real",
                    "arrival_real", "departure_planned", "arrival_planned"]
    
    feature_cols = [col for col in df.columns if col not in cols_exclude]
    X = df[feature_cols]
    y = df["delay"]

    return X, y