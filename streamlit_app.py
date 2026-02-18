
### !!! CHECK IF REQUIREMENTS.TXT LOADED 


### IMPORTS ###

# libraries
import streamlit as st 
import pandas as pd 
from pathlib import Path
import time 
import sys 
import os 
import joblib


# import custom functions (Jakob)
try:
    from src.jakob_analysis.functions import * 
except ImportError: 
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    try:
        from src.jakob_analysis.functions import * 
    except ImportError as e:
        st.error(f"Fehler beim Import: {e}")
        st.stop()
    
# import fetcher class (Bjarne)
try: 
    from src.bjarne_api.collector_new import Fetcher
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    try:
        from src.bjarne_api.collector_new import Fetcher
    except ImportError as e:
        st.error(f"Import Fehler: {e}")
        st.stop()

# base dir
BASE_DIR = Path(__file__).resolve().parent   

if "historical_features_list" not in st.session_state:
    try: 
        file_path_station = BASE_DIR / "data" / "hist_delay_station_lookup.parquet"
        file_path_train = BASE_DIR / "data" / "hist_delay_train_lookup.parquet"
    
        df_station = pd.read_parquet(file_path_station)
        df_train = pd.read_parquet(file_path_train)

        st.session_state.historical_features_list = [
            df_station,
            df_train
        ]

    except FileNotFoundError as e:
        st.error(f"Files not found: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Error loading parquet files: {e}")
        st.stop()


# load models (pkl-files)
if "models_loaded" not in st.session_state:
    try:
        file_path_mean = BASE_DIR / "src" / "jakob_analysis" / "pipeline_hgb_mean.pkl"
        file_path_q05 = BASE_DIR / "src" / "jakob_analysis" / "pipeline_hgb_q05.pkl"
        file_path_q95 = BASE_DIR / "src" / "jakob_analysis" / "pipeline_hgb_95.pkl"

        st.session_state.pipe_mean = joblib.load(file_path_mean)
        st.session_state.pipe_q05 = joblib.load(file_path_q05)
        st.session_state.pipe_q95 = joblib.load(file_path_q95)

        st.session_state.models_loaded = True

    except FileNotFoundError as e:
        st.error(f"Files not found: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Error loading models: {e}")
        st.stop()


# import list of train_stations (unique stations in historical data)
if "stations_list" not in st.session_state:
    try: 
        # CHANGE LINE (DO NOT TAKE STATIONS FROM LOOKUP)
        st.session_state.stations_list = sorted(df_station["station_current"].unique())
    except FileNotFoundError as e:
        st.error(f"Files not found: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Error loading models: {e}")
        st.stop()


# import txt info file for the models
# HAS TO BE ADDED



### INIT SESSION STATE ###

defaults = {
    "start_station": None, # select start
    "df_filtered": None, # filter imported api data
    "df_destinations": None, # get possible destinations
    "end_station": None, # select end station
    "connections": None, # find possible connections
    "train_selected": None, # select train
    "df_selected": None, # raw data of selected train
    "df_final": None, # data after data wrangling
    "ticket_price": 50.0, # select price
    "run_prediction": False, # run prediction
    "pred_mean": None, # prediction
    "pred_q05": None, # prediction
    "pred_q95": None # prediction
    }
for key, value in defaults.items():
    # if key in session state: do not change session state
    if key not in st.session_state:
        st.session_state[key] = value





### UI START ###


st.set_page_config(page_title="Bahn Delay Predictor", page_icon="🚆")

# streamlit layout   
st.title("🚆 Bahn Delay Predictor")


### 1 SELECT START STATION
with st.container(border=True):
    start_station = st.selectbox("Start station", options = [""] + st.session_state.stations_list, index = 0)
    
if start_station and start_station != st.session_state.start_station:
    # reset states if start_station_changed
    st.session_state.start_station = start_station
    st.session_state.connections = None
    st.session_state.df_destinations = None
    st.session_state.run_prediction = False


### 2 LOAD DATA IF START_STATION SELECTED
if st.session_state.start_station and st.session_state.df_destinations is None:

    with st.spinner("Searching for possible connections..."):

        # get api data
        fetcher = Fetcher()
        df_departures, err = fetcher.stations_details(st.session_state.start_station)
        df_trip = fetcher.trip_details()
        final_df = fetcher.create_dataframe()

        # filter: only keep ICE and IC trains
        df_filtered = final_df[final_df["train_type"].isin(["ICE", "IC"])]
    
        # get possible destinations 
        df_destinations = get_possible_destinations(df_filtered, st.session_state.start_station)

        # save results in session state
        st.session_state.df_filtered = df_filtered
        st.session_state.df_destinations = df_destinations


### 3 SELECT DESTINATION + GET CONNECTIONS 
if st.session_state.df_destinations:
        
        # select destination station: select from possible stations 
        with st.container(border=True):
            end_station = st.selectbox("Destination station", options = [""] + st.session_state.df_destinations, index = 0)
    
        # search for connections 
        if st.button("Search connections:"):

            if not end_station:
                st.warning("Please select a destination station.")
            else: 
                df_connections = get_connections(st.session_state.df_filtered, st.session_state.start_station, end_station)
                
                if df_connections.empty:
                    st.warning("No connections found.")
                else:
                    # save results in session state
                    st.session_state.connections = df_connections
                    st.session_state.end_station = end_station
                    st.session_state.run_prediction = False


### 4 DISPLAY AND SELECT CONNECTIONS
if st.session_state.connections is not None:
    
    # get data from session state
    df = st.session_state.connections

    # layout
    st.divider()
    st.subheader("Available connections:")

    # st.dataframe(df[["train_name", "departure_real"]])
    df["print"] = df.apply(lambda x: f"{x['train_name']} (Planned: {x['departure_planned']}) | Actual Delay: +{x['current_delay']} min", axis=1)
    selected_connection = st.selectbox("Trains:", df["print"])
    
    # get chosen train and save in session state
    train_name = df[df["print"] == selected_connection]["train_name"].iloc[0]
    df_selected = df[df["train_name"] == train_name]

    # save results in session state
    st.session_state.train_selected = train_name
    st.session_state.df_selected = df_selected

    with st.container(border=True):
        st.session_state.ticket_price = st.number_input("Price (€)", value=st.session_state.ticket_price)

        if st.button("Calculate prediction!", type="primary"):
            st.session_state.run_prediction = True


### 5 DATA WRANGLING FOR MODEL 
if st.session_state.run_prediction:

    # get data from session state
    df = st.session_state.df_selected
    
    # rename columns (for matching with lookup)
    df = df.rename({"precip": "precipitation", "temp": "temperature"}, axis=1)
    # drop columns
    df = df.drop(columns = ["current_delay", "stops_total", "stop_index", "stops_remaining"])

    # create features
    df_features = create_features(df, api = True, historical_features = st.session_state.historical_features_list)
    df_final = df_features[df_features["station_current"] == st.session_state.start_station] # only one row

    st.session_state.df_final = df_final


### 6 PREDICTION
if st.session_state.run_prediction and st.session_state.df_final is not None:

    with st.spinner("Calculating predictions..."):
        # define features
        def choose_features_target(df): # ADJUST THIS FUNCTION
            cols_exclude = [
                "ride_id", "delay", "departure_real", "arrival_real", 
                "departure_planned", "arrival_planned", "train_name", 
                "station_current", "station_start", "station_dest", 
                "hist_delay_train_q90", "hist_delay_station_q90", 
                "stops_total", "stop_index", "share_ride_time", "print"]
            feature_cols = [col for col in df.columns if col not in cols_exclude]
            return df[feature_cols]
        X = choose_features_target(st.session_state.df_final)

        # prediction
        st.session_state.pred_mean = st.session_state.pipe_mean.predict(X)[0]
        st.session_state.pred_q05 = st.session_state.pipe_q05.predict(X)[0]
        st.session_state.pred_q95 = st.session_state.pipe_q95.predict(X)[0]


### 7 DISPLAY THE RESULTS
if st.session_state.pred_mean is not None:

    # layout
    st.divider()
    st.subheader("Results & Analysis")

    # display results prediction
    col1, col2, col3 = st.columns(3)
    col1.metric("Ø Expected", f"{st.session_state.pred_mean:.1f} min")
    col2.metric("Best Case (5%)", f"{st.session_state.pred_q05:.1f} min")
    col3.metric("Worst Case (95%)", f"{st.session_state.pred_q95:.1f} min", delta_color="inverse")

    # display results for ticket price
    # HAS TO BE ADDED


### 8 ALLOW TO EXPORT THE RESULTS
if st.session_state.pred_mean is not None:

    # layout
    st.divider()
    st.subheader("💾 Export Results")

    # text for export
    export_text = f"""BAHN DELAY PREDICTION REPORT
    --------------------------------
    Connection: {st.session_state.start_station} -> {st.session_state.end_station}
    Train: {st.session_state.train_selected}
    Ticket Price: {st.session_state.ticket_price:.2f}€

    PREDICTION RESULTS:
    - Average Expected Delay: {st.session_state.pred_mean:.1f} min
    - Best Case (5% Quantile): {st.session_state.pred_q05:.1f} min
    - Worst Case (95% Quantile): {st.session_state.pred_q95:.1f} min

    Generated on: {time.strftime("%Y-%m-%d %H:%M:%S")}"""

    # download buttomn
    st.download_button(
        label="Download results as TXT",
        data=export_text,
        file_name=f"delay_prediction_{st.session_state.end_station}.txt",
        mime="text/plain"
    )
    
 