import streamlit as st 
import pandas as pd 
import time 
import sys 
import os 

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
    
st.set_page_config(page_title="Bahn Delay Predictor", page_icon="🚆")

#---- Hier muss Jakobs Modell rein --- 
def mock_predict_delay(features):
    time.sleep(0.4)
    base_risk = features.get('current_delay', 0) * 0.05
    p_ok = max(0.05, 0.8 - base_risk)
    return [p_ok, (1-p_ok)*0.7, (1-p_ok)*0.3]

# Streamlit Layout   
st.title("🚆 Bahn Delay Predictor")

# Eingabefelder für Bahnhöfe und Ticketpres 
with st.container(border=True):
    c1, c2 = st.columns(2)
    start_station = c1.text_input("Startbahnhof", "Berlin Hbf")
    end_station = c2.text_input("Zielbahnhof", "München Hbf")
    ticket_price = st.number_input("Preis (€)", value=50.0)
    search_btn = st.button("Verbindungen suchen", type="primary")
    
# Ergebnisse im Session State speichern
if "connections" not in st.session_state:
    st.session_state.connections = None

# Verbindungen suchen mit Button 
if search_btn:
    with st.spinner("Suche verfügbare Züge..."):
        fetcher = Fetcher()
        df_connections, err = fetcher.find_connection(start_station, end_station)
        
        if err:
            st.error(err)
            st.session_state.connections = None
        else:
            st.session_state.connections = df_connections

# gefundene Verbindungen anzeigen
if st.session_state.connections is not None and not st.session_state.connections.empty:
    df = st.session_state.connections
    
    st.divider()
    st.subheader("Wähle deine Verbindung:")
    
    df['label'] = df.apply(lambda x: f"{x['train_name']} (Plan: {x['departure_time']}) | Aktuell: +{x['current_delay']} min", axis=1)
    
    selected_label = st.selectbox("Gefundene Züge:", df['label'])
    
    #  ausgewählten Zug extrahieren
    row = df[df['label'] == selected_label].iloc[0]
    
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