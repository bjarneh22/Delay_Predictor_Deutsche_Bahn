### !!! CHECK IF REQUIREMENTS.TXT LOADED 

### IMPORTS ###

# libraries
import streamlit as st 
import streamlit.components.v1 as components
import pandas as pd 
from pathlib import Path
import time 
import sys 
import os 
import joblib
import plotly.graph_objects as go

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
    "start_station": None, 
    "df_filtered": None, 
    "df_destinations": None, 
    "end_station": None, 
    "connections": None, 
    "train_selected": None, 
    "df_selected": None, 
    "df_final": None, 
    "ticket_price": 50.0, 
    "run_prediction": False, 
    "pred_mean": None, 
    "pred_q05": None, 
    "pred_q95": None, 
    "eff_price": None, 
    "category": None, 
    "reasoning": None, 
    "price_at_calculation": None 
    }
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


### UI START ###

st.set_page_config(page_title="Bahn Delay Predictor", page_icon="🚆")
st.title("🚆 Bahn Delay Predictor")


### SIDEBAR ###

with st.sidebar:
    st.header("Bahn Delay Predictor Settings")

    # help toggle
    show_help = st.checkbox("Show Help / Instructions")
    if show_help:
        st.markdown("""
                    ### How to Use 🚆

                    1. **Select your departure station** from the dropdown menu.
                    2. **Choose one of the available destination stations**.
                    3. **Pick a train connection** from the list of available options.
                    4. **Enter the ticket price** you paid for your journey.
                    5. Click **"Calculate Prediction!"**.
                    6. View the **predicted delay**, including best-case and worst-case scenarios, as well as the **predicted effective price**.
                    7. Optionally, download a **delay prediction report** as a `.txt` file by clicking **"Download Report (TXT)"** under **Export Results**.

                    """)

        st.info("💡 Tip: Enable Mock Mode below for testing without connecting to the API.")
        st.warning("""
                    - If no destinations appear, the app will show the message *"Sadly there is no possible destination for you to go to. Please select a different start station."*.
                    - Make sure all required data files are available in the `data/` folder.
                    """)

    st.markdown("---")  # separator

    # mock mode toggle
    st.subheader("Testing / Mock Mode")

    # Initialize previous value once
    if "mock_mode_previous" not in st.session_state:
        st.session_state.mock_mode_previous = False

    # Checkbox
    mock_mode = st.checkbox(
        "Enable Mock Mode (Testing)",
        value=st.session_state.get("mock_mode", False)
    )

    # Detect change
    if mock_mode != st.session_state.mock_mode_previous:

        # Save new value first
        st.session_state.mock_mode = mock_mode

        # Reset dynamic state
        for key, value in defaults.items():
            st.session_state[key] = value

        # Update tracker
        st.session_state.mock_mode_previous = mock_mode

        st.rerun()

    # Keep state in sync
    st.session_state.mock_mode = mock_mode

    if st.session_state.mock_mode:
        st.info("Mock Mode active: Using dummy data instead of API.")


### 1 SELECT START STATION
with st.container(border=True):
    start_station = st.selectbox("Start station", options = [""] + st.session_state.stations_list, index = 0)
    
if start_station != st.session_state.start_station:
    st.session_state.start_station = start_station
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

    with st.spinner(f"Searching for connections from {st.session_state.start_station}..."):

        # mock mode
        if st.session_state.mock_mode:
            try:
                final_df = pd.read_csv(BASE_DIR / "data" / "mock_api_data.csv")

                # filter only for valid rides
                valid_rides = final_df[
                    (final_df["station_current"] == st.session_state.start_station) & 
                    (final_df["station_dest"] != st.session_state.start_station)
                ]["ride_id"].unique()

                final_df = final_df[
                    final_df["ride_id"].isin(valid_rides)
                ]

                time.sleep(1.2)  # simulate API delay
            except Exception as e:
                st.error(f"Error loading mock data: {e}")
                st.stop()
            

        # api mode
        else:
            fetcher = Fetcher()

            # Get station ID
            s_id = fetcher.get_station_id(st.session_state.start_station)

            if not s_id:
                st.error(f"Station '{st.session_state.start_station}' not recognized.")
                st.stop()

            try:
                departures = fetcher.stations_details(s_id)
            except Exception as e:
                st.error(f"Error retrieving departures: {e}")
                st.stop()

            if not departures:
                st.warning(
                    f"No departures currently found for '{st.session_state.start_station}'."
                )
                st.stop()

            # initialise list for trips
            all_trips = []
            valid_deps = [d for d in departures if d.get("tripId")]
            num_deps = min(len(valid_deps), 5)  # API protection

            progress_bar = st.progress(0)

            for i in range(num_deps):
                dep = valid_deps[i]
                trip_id = dep.get("tripId")

                if isinstance(trip_id, str):
                    trip_data = fetcher.trip_details(trip_id)

                    if trip_data is not None:
                        df_trip = fetcher.create_dataframe(trip_data, ride_id=i)
                        if not df_trip.empty:
                            all_trips.append(df_trip)

                time.sleep(0.3)  # API rate safety
                progress_bar.progress((i + 1) / num_deps)

            if not all_trips:
                st.error("No valid trip data available.")
                st.stop()

            final_df = pd.concat(all_trips, ignore_index=True)

        # shared post processing

        df_filtered = final_df[
            final_df["train_type"].isin(["ICE", "IC"])
        ]

        if df_filtered.empty:
            st.warning("No ICE/IC connections found in this timeframe.")
            st.stop()

        df_destinations = get_possible_destinations(
            df_filtered,
            st.session_state.start_station
        )

        # Save to session state
        st.session_state.df_filtered = df_filtered
        st.session_state.df_destinations = df_destinations
        
        st.success(
            f"Connections successfully loaded ({len(st.session_state.df_filtered['ride_id'].unique())} trains)."
        )


### 3 SELECT DESTINATION + GET CONNECTIONS 
if st.session_state.start_station:

    if st.session_state.df_destinations is None:
        pass  # still loading

    elif len(st.session_state.df_destinations) == 0:
        st.info(
            f"No valid ICE/IC destinations found for '{st.session_state.start_station}'. "
            "Please select a different start station."
        )

    else:
        
        with st.container(border=True):
            end_station = st.selectbox("Destination station", options = [""] + st.session_state.df_destinations, index = 0)

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
    
        if st.button("Search connections"):
            if not end_station:
                st.warning("Please select a destination station.")
            else: 
                df_connections = get_connections(st.session_state.df_filtered, 
                                                 st.session_state.start_station, 
                                                 end_station)
                
                if df_connections.empty:
                    st.warning("No connections found.")
                else:
                    st.session_state.connections = df_connections
                    st.session_state.end_station = end_station
                    st.session_state.run_prediction = False


### 4 DISPLAY AND SELECT CONNECTION
if st.session_state.connections is not None:
    
    df = st.session_state.connections
    st.divider()
    st.subheader("Available connections:")

    arrivals = df[df["station_current"] == st.session_state.end_station].set_index("train_name")["arrival_planned"].to_dict()

    df["print"] = df.apply(
    lambda x: (
        f"🚆 {x['train_name']} | "
        f"Dep: {pd.to_datetime(x['departure_planned']).strftime('%H:%M') if pd.notnull(x['departure_planned']) else '??:??'} → "
        f"Arr: {pd.to_datetime(arrivals.get(x['train_name'])).strftime('%H:%M') if pd.notnull(arrivals.get(x['train_name'])) else '??:??'} | "
        f"Current Delay: +{x['current_delay']} min"), 
    axis=1)

    filtered_options = df["print"][df["station_current"] == start_station].tolist()

    if not filtered_options:
        st.warning("No connections found for the starting station.")
    else: 
        selected_connection = st.selectbox("Trains:", filtered_options, index=None, 
                                           placeholder="Select a connection...",
                                           key=f"train_selector_{st.session_state.end_station}")
        
        if selected_connection:
            new_train_name = df[df["print"] == selected_connection]["train_name"].iloc[0]
            if new_train_name != st.session_state.train_selected:
                st.session_state.train_selected = new_train_name
                st.session_state.df_selected = df[df["train_name"] == new_train_name]
                st.session_state.run_prediction = False
                st.session_state.pred_mean = None
                st.session_state.pred_q05 = None
                st.session_state.pred_q95 = None
                st.session_state.df_final = None
            
            if "train_selected" in st.session_state and st.session_state.train_selected:
                with st.container(border=True):
                    new_price = st.number_input("Price (€)", value=st.session_state.ticket_price)
        
                    if new_price != st.session_state.get("price_at_calculation"):
                        st.session_state.run_prediction = False
                        st.session_state.pred_mean = None 

                    st.session_state.ticket_price = new_price

                if st.button("Calculate prediction!", type="primary"):
                    st.session_state.run_prediction = True
                    st.session_state.price_at_calculation = st.session_state.ticket_price


### 5 DATA WRANGLING FOR MODEL 
if st.session_state.run_prediction:
    df = st.session_state.df_selected
    df = df.rename({"precip": "precipitation", "temp": "temperature"}, axis=1)
    df = df.drop(columns = ["current_delay", "stops_total", "stop_index", "stops_remaining"])

    df_features = create_features_api(df, historical_features = st.session_state.historical_features_list)
    df_final = df_features[df_features["station_current"] == st.session_state.start_station]

    st.session_state.df_final = df_final


### 6 PREDICTION
if st.session_state.run_prediction and st.session_state.df_final is not None:
    with st.spinner("Calculating predictions..."):
        X = choose_features_target(st.session_state.df_final)

        st.session_state.pred_mean = st.session_state.pipe_mean.predict(X)[0]
        st.session_state.pred_q05 = st.session_state.pipe_q05.predict(X)[0]
        st.session_state.pred_q95 = st.session_state.pipe_q95.predict(X)[0]


### 7 DISPLAY THE RESULTS
if st.session_state.pred_mean is not None:

    st.divider()
    st.subheader("Results & Route Analysis")

    # display predictions in metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Ø Expected", f"{st.session_state.pred_mean:.1f} min")
    col2.metric("Best Case (5%)", f"{st.session_state.pred_q05:.1f} min")
    col3.metric("Worst Case (95%)", f"{st.session_state.pred_q95:.1f} min", delta_color="inverse")

    avg_delay = st.session_state.pred_mean
    price = st.session_state.ticket_price
    
    # define the refund info based on the average delay 
    if avg_delay >= 120:
        refund_factor, category = 0.5, "Delay ≥ 120 min (50% refund)"
        reasoning = f"With **{avg_delay:.1f} min** average delay, you'll likely get **50%** back."
    elif avg_delay >= 60:
        refund_factor, category = 0.25, "Delay ≥ 60 min (25% refund)"
        reasoning = f"With **{avg_delay:.1f} min** average delay, you'll likely get **25%** back."
    else:
        refund_factor, category = 0.0, "No refund expected (< 60 min)"
        reasoning = "The predicted delay is below the 60-minute threshold for refunds."

    # calculate effective price after refund
    eff_price = price * (1 - refund_factor)
    st.session_state.eff_price = eff_price
    st.session_state.category = category

    # create an informative box with interactive chart 
    with st.container(border=True):
        st.markdown(f"### Route Progression: {st.session_state.train_selected}")
        
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.write("Predicted Effective Price:")
            st.title(f"{eff_price:.2f} €")
            st.info(reasoning)

        with c2:
            df_plot = st.session_state.df_selected.copy()
            
            # create line-chart
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df_plot["station_current"],
                y=df_plot["current_delay"],
                mode='lines+markers',
                name='Current Delay',
                line=dict(color='RoyalBlue', width=3),
                marker=dict(size=8),
                hovertemplate="<b>%{x}</b><br>Delay: %{y} min<extra></extra>"
            ))

            # lines for refund thresholds 
            fig.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="60 min Threshold")
            fig.add_hline(y=120, line_dash="dash", line_color="red", annotation_text="120 min Threshold")

            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=30, b=10),
                xaxis_title="Stations",
                yaxis_title="Delay (minutes)",
                hovermode="x unified",
                xaxis=dict(tickangle=-45)
            )
            
            st.plotly_chart(fig, use_container_width=True)


### 8 EXPORT THE RESULTS
if st.session_state.pred_mean is not None:

    # layout
    st.divider()
    st.subheader("Export Results")

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
