
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


def create_features(df):

    # create copy: do not overwrite input df
    df = df.copy()

    # check that all date variables have the correct format
    datetime_cols = ["departure_planned", "arrival_planned", "departure_real", "arrival_real"]
    for col in datetime_cols:
        df[col] = pd.to_datetime(df[col])

    # arrange dataset again to guarantee correct feature creation
    df = df.sort_values(by=["ride_id", "departure_planned"])


    ### RIDE RELATED 

    # prepare grouping
    grouped = df.groupby("ride_id")

    # number of stops
    df["stops_total"] = grouped["station_current"].transform("count")

    # time departure and arrival
    df["departure_planned_start"] = grouped["departure_planned"].transform("first")
    df["arrival_planned_dest"] = grouped["arrival_planned"].transform("last")

    # travel time
    df["travel_time"] = (df["arrival_planned_dest"] - df["departure_planned_start"]).dt.total_seconds() / 60

    # weekday and month
    df["weekday"] = df["departure_planned_start"].dt.weekday
    df["month"] = df["departure_planned_start"].dt.month

    # feast
    de_holidays = holidays.Germany()
    df["feast"] = df["departure_planned_start"].dt.date.apply(lambda x: x in de_holidays)


    ### STATION RELATED

    # hour
    df["hour"] = np.where(
        df["departure_real"].notna(), 
        df["departure_real"].dt.hour, 
        df["arrival_real"].dt.hour)
    
    # dwell-time planned
    df["dwell_time_planned"] = (df["departure_planned"] - df["arrival_planned"]).dt.total_seconds() / 60
    df["dwell_time_planned"] = df["dwell_time_planned"].fillna(0) # for start and destination stations


    ### SEQUENCE RELATED

    # station role: start, mid, end
    conditions = [
        (df["station_current"] == df["station_start"]), # Bedingung für 'start'
        (df["station_current"] == df["station_dest"])   # Bedingung für 'end'
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