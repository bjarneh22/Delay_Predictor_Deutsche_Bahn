
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
        file_path_q95 = BASE_DIR / "src" / "jakob_analysis" / "pipeline_hgb_q95.pkl" 

        st.session_state.pipe_mean = joblib.load(file_path_mean)
        st.session_state.pipe_q05 = joblib.load(file_path_q05)
        st.session_state.pipe_q95 = joblib.load(file_path_q95)

        # get model information
        hgb_step = st.session_state.pipe_mean.named_steps['histgradientboostingregressor']
        
        # store as formatted string for export (TXT)
        st.session_state.model_info_text = (
            f"Model Type: HistGradientBoostingRegressor\n"
            f"- Learning Rate: {hgb_step.learning_rate}\n"
            f"- Max Iterations: {hgb_step.max_iter}\n"
            f"- Max Leaf Nodes: {hgb_step.max_leaf_nodes}\n"
            f"- Min Samples Leaf: {hgb_step.min_samples_leaf}")

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
    "pred_q95": None, # prediction
    "eff_price": None, # output
    "category": None, # output
    "reasoning": None, # output
    "price_at_calculation": None # check to prevent errors in txt-export
    }
for key, value in defaults.items():
    # if key in session state: do not change session state
    if key not in st.session_state:
        st.session_state[key] = value





### UI START ###


st.set_page_config(page_title="Bahn Delay Predictor", page_icon="🚆")

# streamlit layout   
st.title("🚆 Bahn Delay Predictor")


# 0 MOCK VERSION SELECTER
with st.sidebar:
    st.header("Settings")
    st.session_state.mock_mode = st.toggle("Enable Mock Mode (Testing)", value=False)
    if st.session_state.mock_mode:
        st.info("Mock Mode active: Using dummy data instead of API.")


### 1 SELECT START STATION
with st.container(border=True):
    start_station = st.selectbox("Start station", options = [""] + st.session_state.stations_list, index = 0)
    
# reset everything if start_station changed
if start_station != st.session_state.start_station:

    # set new start station
    st.session_state.start_station = start_station

    # waterfall reset
    st.session_state.df_destinations = None
    st.session_state.end_station = None
    st.session_state.connections = None
    st.session_state.train_selected = None
    st.session_state.df_selected = None
    st.session_state.df_final = None
    st.session_state.run_prediction = False
    st.session_state.pred_mean = None
    st.session_state.pred_q05 = None
    st.session_state.pred_q95 = None
    st.session_state.eff_price = None
    st.session_state.category = None
    st.session_state.reasoning = None
    st.session_state.ticket_price = 50.0
    st.session_state.price_at_calculation = None


### 2 LOAD DATA IF START_STATION SELECTED
if st.session_state.start_station and st.session_state.df_destinations is None:

    with st.spinner("Searching for possible connections..."):

        # MOCK MODE 
        if st.session_state.mock_mode:

            final_df = pd.read_csv(BASE_DIR / "data" / "mock_api_data.csv")
            # st.session_state.df_destinations = sorted(st.session_state.departures["station_dest"].unique())
            time.sleep(1.5)
        
        # API MODE
        else:
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

            # reset session state when end_station changed
            if end_station != st.session_state.end_station:
                st.session_state.connections = None
                st.session_state.end_station = None
                st.session_state.pred_mean = None
                st.session_state.pred_q05 = None
                st.session_state.pred_q95 = None
                st.session_state.run_prediction = False
                st.session_state.train_selected = None
                st.session_state.ticket_price = 50.0
                st.session_state.price_at_calculation = None
    
        # search for connections 
        if st.button("Search connections"):

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


### 4 DISPLAY AND SELECT CONNECTION
if st.session_state.connections is not None:
    
    # get data from session state
    df = st.session_state.connections

    # layout
    st.divider()
    st.subheader("Available connections:")

    # get arrivales at end station
    arrivals = df[df["station_current"] == st.session_state.end_station].set_index("train_name")["arrival_planned"].to_dict()

    # create output version ("print")
    df["print"] = df.apply(
    lambda x: (
        f"🚆 {x['train_name']} | "
        f"Dep: {pd.to_datetime(x['departure_planned']).strftime('%H:%M') if pd.notnull(x['departure_planned']) else '??:??'} → "
        f"Arr: {pd.to_datetime(arrivals.get(x['train_name'])).strftime('%H:%M') if pd.notnull(arrivals.get(x['train_name'])) else '??:??'} | "
        f"Current Delay: +{x['current_delay']} min"), 
    axis=1)

    # filter only relevant rows
    filtered_options = df["print"][df["station_current"] == start_station].tolist()

    if not filtered_options:
        st.warning("No connections found for the starting station.")
    else: 
        selected_connection = st.selectbox("Trains:", filtered_options, index=None, 
                                           placeholder="Select a connection...",
                                           key=f"train_selector_{st.session_state.end_station}")
        
        # only run when selection was made
        if selected_connection:

            # check: is the selected connection new?
            new_train_name = df[df["print"] == selected_connection]["train_name"].iloc[0]
            if new_train_name != st.session_state.train_selected:

                # get chosen train and save in session state and save in session state
                st.session_state.train_selected = new_train_name
                st.session_state.df_selected = df[df["train_name"] == new_train_name]

                # reset rest of session state
                st.session_state.run_prediction = False
                st.session_state.pred_mean = None
                st.session_state.pred_q05 = None
                st.session_state.pred_q95 = None
                st.session_state.df_final = None
            
        
        # show buttons and price input after selection
            if "train_selected" in st.session_state and st.session_state.train_selected:

                with st.container(border=True):
                    new_price = st.number_input("Price (€)", value=st.session_state.ticket_price)
        
                    # check if new price and old price (after hitting calculation-button) are identical
                    # if not: reset session state
                    if new_price != st.session_state.get("price_at_calculation"):
                        st.session_state.run_prediction = False
                        st.session_state.pred_mean = None # section 7/8 disappear

                    st.session_state.ticket_price = new_price

                if st.button("Calculate prediction!", type="primary"):
                    st.session_state.run_prediction = True
                    # save the price after pressing calculate predicition (later check for txt-output)
                    st.session_state.price_at_calculation = st.session_state.ticket_price


### 5 DATA WRANGLING FOR MODEL 
if st.session_state.run_prediction:

    # get data from session state
    df = st.session_state.df_selected
    
    # rename columns (for matching with lookup)
    df = df.rename({"precip": "precipitation", "temp": "temperature"}, axis=1)
    # drop columns
    df = df.drop(columns = ["current_delay", "stops_total", "stop_index", "stops_remaining"])

    # create features
    df_features = create_features_api(df, historical_features = st.session_state.historical_features_list)
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
    st.subheader("Prediction")

    # PREDICTION RESULTS
    col1, col2, col3 = st.columns(3)
    col1.metric("Ø Expected", f"{st.session_state.pred_mean:.1f} min")
    col2.metric("Best Case (5%)", f"{st.session_state.pred_q05:.1f} min")
    col3.metric("Worst Case (95%)", f"{st.session_state.pred_q95:.1f} min", delta_color="inverse")


    # TICKET PRICE RESULTS

    # setup
    price = st.session_state.ticket_price
    avg_delay = st.session_state.pred_mean

    # worst-case helper
    if st.session_state.pred_q95 >= 120:
        worst_note = f"However, in the **worst case (95%)**, your delay could exceed 120 min, leading to a **50% refund ({price * 0.5:.2f} €)**."
    elif st.session_state.pred_q95 >= 60:
        worst_note = f"However, in the **worst case (95%)**, you could reach the 60 min threshold, resulting in a **25% refund ({price * 0.75:.2f} €)**."
    else:
        worst_note = "Even in the worst case, you are unlikely to reach the 60 min refund threshold."
    
    # category and effective price
    if avg_delay < 60:
        st.session_state.eff_price = price
        st.session_state.category = "Delay < 60 min (0% refund)"
        st.session_state.reasoning = f"Since your predicted average is **{avg_delay:.1f} min**, you will likely pay the full price. {worst_note}"
    elif 60 <= avg_delay < 120:
        st.session_state.eff_price = price * 0.75
        st.session_state.category = "Delay 60-119 min (25% refund)"
        st.session_state.reasoning = f"Since your predicted average is **{avg_delay:.1f} min**, you fall into the 25% refund category. {worst_note}"
    else:
        st.session_state.eff_price = price * 0.5
        st.session_state.category = "Delay ≥ 120 min (50% refund)"
        st.session_state.reasoning = f"With an average prediction of **{avg_delay:.1f} min**, you are likely to get 50% back! {worst_note}"

    # display results
    st.divider()
    st.subheader("Predicted Effective Price")
    st.title(f"{st.session_state.eff_price:.2f} €")
    st.info(st.session_state.reasoning)



### 8 EXPORT THE RESULTS
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

PRICE ANALYSIS:
- Predicted Effective Price: {st.session_state.eff_price:.2f}€
- Refund Category: {st.session_state.category}
- Summary: {st.session_state.reasoning.replace('**', '')}

MODEL CONFIGURATION:
{st.session_state.get('model_info_text', 'No model info available.')}

Generated on: {time.strftime("%Y-%m-%d %H:%M:%S")}"""

    # download button
    st.download_button(
        label="Download Report (TXT)",
        data=export_text,
        file_name=f"delay_prediction_{st.session_state.train_selected}.txt",
        mime="text/plain"
    )
    
 