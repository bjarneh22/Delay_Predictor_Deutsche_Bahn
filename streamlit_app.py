
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
import plotly.graph_objects as go


# import custom functions (Jakob)
try:
    # Versuche den direkten Import
    from src.jakob_analysis.functions import get_possible_destinations, get_connections, create_features_api
except ImportError: 
    # Falls das fehlschlägt (z.B. wegen der Ordnerstruktur), füge den Pfad hinzu
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    try:
        from src.jakob_analysis.functions import get_possible_destinations, get_connections, create_features_api
    except ImportError as e:
        st.error(f"Fehler beim Import der Analyse-Funktionen: {e}")
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
        file_path_q95 = BASE_DIR / "src" / "jakob_analysis" / "pipeline_hgb_q95.pkl" # CHANGE NAME

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
    "pred_q95": None # prediction
    }
for key, value in defaults.items():
    # if key in session state: do not change session state
    if key not in st.session_state:
        st.session_state[key] = value





### UI START ###


st.set_page_config(page_title="Bahn Delay Predictor", page_icon="🚆")

# streamlit layout   
st.title("Bahn Delay Predictor")


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
    
    with st.spinner(f"Suche nach Verbindungen ab {st.session_state.start_station}..."):
        fetcher = Fetcher()
        
        #  get station id 
        s_id = fetcher.get_station_id(st.session_state.start_station)
        
        departures = []
        
        if s_id:
            # load departures for the station 
            try:
                departures = fetcher.stations_details(s_id)
            except Exception as e:
                st.error(f"Fehler beim Abrufen der Abfahrten: {e}")
                st.stop()

            all_trips = []
            if departures:
                progress_bar = st.progress(0)
                # filter out departures without tripId 
                valid_deps = [d for d in departures if d.get("tripId")]
                # restrict to max 5 trips to avoid API overload 
                num_deps = min(len(valid_deps), 5) 
                
                for i in range(num_deps):
                    dep = valid_deps[i]
                    tid = dep.get("tripId")
                    
                    if isinstance(tid, str):
                        t_data = fetcher.trip_details(tid)
                        
                        if t_data is not None:
                            df_t = fetcher.create_dataframe(t_data, ride_id=i)
                            if not df_t.empty:
                                all_trips.append(df_t)
                    
                    # Pause for API stability
                    time.sleep(0.3) 
                    progress_bar.progress((i + 1) / num_deps)
                
                if all_trips:
                    final_df = pd.concat(all_trips, ignore_index=True)
                    
                    # Filter for long-distance trains 
                    df_filtered = final_df[final_df["train_type"].isin(["ICE", "IC"])]
                
                    if not df_filtered.empty:
                        # extract possible destinations 
                        df_destinations = get_possible_destinations(df_filtered, st.session_state.start_station)

                        # save results in session state
                        st.session_state.df_filtered = df_filtered
                        st.session_state.df_destinations = df_destinations
                        st.success(f"Verbindungen für {len(all_trips)} Züge erfolgreich geladen.")
                    else:
                        st.warning("Keine ICE/IC Verbindungen in diesem Zeitraum gefunden.")
                else:
                    st.error("Keine Reisedaten verfügbar. Bitte versuche es erneut.")
            else:
                st.warning(f"Aktuell keine Abfahrten für '{st.session_state.start_station}' gefunden.")
        else:
            st.error(f"Bahnhof '{st.session_state.start_station}' wurde nicht erkannt.")

### 3 SELECT DESTINATION + GET CONNECTIONS 
if st.session_state.df_destinations:
        
    # create selectbox for destination selection
    with st.container(border=True):
        end_station = st.selectbox(
            "Destination station", 
            options=[""] + st.session_state.df_destinations, 
            index=0
        )
    
    # create button to search for connections
    if st.button("Search connections", type="secondary"):

        if not end_station:
            st.warning("Please select a destination station.")
        else: 
            # get connections for selected destination
            df_connections = get_connections(
                st.session_state.df_filtered, 
                st.session_state.start_station, 
                end_station
            )
            
            # ensure that connections are found before saving to session state
            if df_connections is not None and not df_connections.empty:
                # Ergebnisse speichern
                st.session_state.connections = df_connections
                st.session_state.end_station = end_station
                st.session_state.run_prediction = False
                st.rerun() 
            else:
                st.warning("No connections found for the selected destination.")

### 4 DISPLAY AND SELECT CONNECTION
if st.session_state.connections is not None:
    
    # get data from session state
    df = st.session_state.connections

    # layout
    st.divider()
    st.subheader("Available connections:")

    # get arrivales at end station
    arrivals = df[df["station_current"] == st.session_state.end_station].set_index("train_name")["arrival_planned"].to_dict()


    df["print"] = df.apply(
    lambda x: (
        f" {x['train_name']} | "
        f"Dep: {pd.to_datetime(x['departure_planned']).strftime('%H:%M') if pd.notnull(x['departure_planned']) else '??:??'} → "
        f"Arr: {pd.to_datetime(arrivals.get(x['train_name'])).strftime('%H:%M') if pd.notnull(arrivals.get(x['train_name'])) else '??:??'} | "
        f"Current Delay: +{x['current_delay']} min"), 
    axis=1)

    # filter only relevant rows
    filtered_options = df["print"][df["station_current"] == start_station].tolist()

    if not filtered_options:
        st.warning("No connections found for the starting station.")
    else: 
        selected_connection = st.selectbox("Trains:", filtered_options)
        # get chosen train and save in session state
        train_name = df[df["print"] == selected_connection]["train_name"].iloc[0]
        df_selected = df[df["train_name"] == train_name]
        
        if  selected_connection:
            train_name = df[df["print"] == selected_connection]["train_name"].iloc[0]
            df_selected = df[df["train_name"] == train_name]
            
            # save results in session state
            st.session_state.train_selected = train_name
            st.session_state.df_selected = df_selected

    with st.container(border=True):
        st.session_state.ticket_price = st.number_input("Price (€)", value=st.session_state.ticket_price)

        if st.button("Calculate prediction", type="secondary"):
            st.session_state.run_prediction = True


### 5 DATA WRANGLING FOR MODEL 
if st.session_state.run_prediction:

    # get data from session state
    df = st.session_state.df_selected
    
    # rename columns 
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
    
 