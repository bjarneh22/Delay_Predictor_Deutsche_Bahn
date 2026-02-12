import streamlit as st 
import pandas as pd 
import time 
import sys 
import os 

### !!! CHECK IF REQUIREMENTS.TXT LOADED 

# Import Fetcher Klasse 
try: 
    from src.bjarne_api.collector_new import Fetcher
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    try:
        from src.bjarne_api.collector_new import Fetcher
    except ImportError as e:
        st.error(f"Import Fehler: {e}")
        st.stop()
        
# Import txt info file für modelle

# import historical_delay_lookups
    
# Import Modell 
# BITTE models.py MIT DEM MODELL ERSTELLEN!!! 
try:
    from.src.jakob_analysis.functions import * 
except ImportError: 
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    try:
        from.src.jakob_analysis.functions import * 
    except ImportError as e:
        st.error(f"Fehler beim Import: {e}")
        st.stop()

st.set_page_config(page_title="Bahn Delay Predictor", page_icon="🚆")

# Streamlit Layout   
st.title("🚆 Bahn Delay Predictor")

# Eingabefelder für Bahnhöfe und Ticketpres 
with st.container(border=True):
    c1 = st.columns(1)
    start_station = c1.selectbox("Startbahnhof", "Berlin Hbf")
    
# Ergebnisse im Session State speichern
if "connections" not in st.session_state:
    st.session_state.connections = None

# --- Hier kommt der final_df her----
    with st.spinner("Suche verfügbare Züge..."):
        fetcher = Fetcher()
        df_departures, err = fetcher.stations_details(start_station)
        df_trip = fetcher.trip_details()
        final_df = fetcher.create_dataframe()
        
        if err:
            st.error(err)
            st.session_state.connections = None
        else:
            st.session_state.connections = final_df
            
    # ---- Filtern nach den IC/ICE (1) ----
    
    
    # ---- get possible destinations (2) --- 

    # ---- Selectbox mit output von davor (3) --- 

    # end_station als
    end_station = None # Hier output von vorherigem Schritt (3) und eigener Container
    
    #--- If search button: get_connections von start_station nach end_station (4)--- 
    
    ticket_price = st.number_input("Preis (€)", value=50.0) # HIerfür eigenene Container
    
    search_btn = st.button("Verbindungen suchen", type="primary")
    
    if search_btn:
        # --- DATA WRANGLING FÜR ML INPUT ---
        #----- select possible connections mit get_connections ---
        # --- erstelle df für die select box
        
    
# gefundene Verbindungen anzeigen und auswählen
if st.session_state.connections is not None and not st.session_state.connections.empty:
    df = st.session_state.connections
    
    st.divider()
    st.subheader("Wähle deine Verbindung:")
    
    # --- SELECT BOX FÜR SPEZIFISCHE VERBINDUNG
    '''
    Hier anpassen für den data_frame, der von (4) returned wird
    
    df['label'] = df.apply(lambda x: f"{x['train_name']} (Plan: {x['departure_time']}) | Aktuell: +{x['current_delay']} min", axis=1)
    '''
    
    selected_label = st.selectbox("Gefundene Züge:", df['label'])
    
    #  ausgewählten Zug extrahieren
    row = df[df['label'] == selected_label].iloc[0]
    
    
    # ---- select        
        # ---- create features mit create_features function (basierend auf train_name)
        # --- select correct rows (station_current == start_station)
        #--- choose features function ---
        
        # --- PREDICTION ---
    
    


if st.session_state.connections is not None and not st.session_state.connections.empty:
    # Risiko berechnen 
    if st.button("Risiko für diesen Zug berechnen"):
        
        st.info(f"Analysiere **{row['train_name']}**...")
        probs = mock_predict_delay(row)
        
        # Verspätungswahrscheinlichkeiten anzeigen
        c1, c2, c3 = st.columns(3)
        c1.metric("Pünktlich", f"{probs[0]:.0%}")
        c2.metric(">60min Verspätung", f"{probs[1]:.0%}", delta_color="inverse")
        c3.metric(">120min Verspätung", f"{probs[2]:.0%}", delta_color="inverse")
        
        # Erstattungsrechner
        st.caption("Mögliche Erstattung:")
        refund_col1, refund_col2 = st.columns(2)
        refund_col1.write(f"Ab 60 min: **{ticket_price*0.25:.2f} €**")
        refund_col2.write(f"Ab 120 min: **{ticket_price*0.50:.2f} €**")
        
#----- BUTTON: EXPORT TXT-File
# --- Info: prediction und infos vom model ---