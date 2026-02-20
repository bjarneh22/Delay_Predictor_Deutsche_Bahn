### !!! CHECK IF REQUIREMENTS.TXT LOADED 

### IMPORTS ###

# libraries
import streamlit as st 
import streamlit.components.v1 as components # NEU: Für Chart.js HTML Einbindung
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
    st.session_state.mock_mode = st.checkbox("Enable Mock Mode (Testing)", value=False)
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

    with st.spinner("Searching for possible connections..."):
        if st.session_state.mock_mode:
            final_df = pd.read_csv(BASE_DIR / "data" / "mock_api_data.csv")
            time.sleep(1.5)
        else:
            fetcher = Fetcher()
            df_departures, err = fetcher.stations_details(st.session_state.start_station)
            df_trip = fetcher.trip_details()
            final_df = fetcher.create_dataframe()

        df_filtered = final_df[final_df["train_type"].isin(["ICE", "IC"])]
        df_destinations = get_possible_destinations(df_filtered, st.session_state.start_station)

        st.session_state.df_filtered = df_filtered
        st.session_state.df_destinations = df_destinations


### 3 SELECT DESTINATION + GET CONNECTIONS 
if st.session_state.start_station:

    if st.session_state.df_destinations is None:
        pass  # still loading

    elif len(st.session_state.df_destinations) == 0:
        st.info("Sadly there is no possible destination for you to go to. Please select a different start station.")

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
                df_connections = get_connections(st.session_state.df_filtered, st.session_state.start_station, end_station)
                
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
    st.subheader("Prediction")

    # Metrics Layout
    col1, col2, col3 = st.columns(3)
    col1.metric("Ø Expected", f"{st.session_state.pred_mean:.1f} min")
    col2.metric("Best Case (5%)", f"{st.session_state.pred_q05:.1f} min")
    col3.metric("Worst Case (95%)", f"{st.session_state.pred_q95:.1f} min", delta_color="inverse")

    # --- REINES PYTHON INTERAKTIVES CHART (PLOTLY) ---
    fig = go.Figure(data=[
        go.Bar(
            x=['Best Case (5%)', 'Ø Expected', 'Worst Case (95%)'],
            y=[st.session_state.pred_q05, st.session_state.pred_mean, st.session_state.pred_q95],
            marker_color=['#4BC0C0', '#FFCE56', '#FF6384'], # Grün, Gelb, Rot
            text=[f"{st.session_state.pred_q05:.1f} min", f"{st.session_state.pred_mean:.1f} min", f"{st.session_state.pred_q95:.1f} min"],
            textposition='auto' # Zeigt die Werte direkt im Balken an
        )
    ])

    fig.update_layout(
        yaxis_title='Predicted Delay in Minutes',
        plot_bgcolor='rgba(0,0,0,0)', # Transparenter Hintergrund passt sich Streamlit an
        margin=dict(l=0, r=0, t=30, b=0)
    )

    # Diagramm in Streamlit anzeigen
    st.plotly_chart(fig, use_container_width=True)
    # -------------------------------------------------

    # TICKET PRICE RESULTS
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

    st.divider()
    st.subheader("💾 Export Results")

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

    st.download_button(
        label="Download Report (TXT)",
        data=export_text,
        file_name=f"delay_prediction_{st.session_state.train_selected}.txt",
        mime="text/plain"
    )