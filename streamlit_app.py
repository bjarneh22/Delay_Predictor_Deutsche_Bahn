import streamlit as st 
import pandas as pd 
import time 
import sys 
import os 

try: 
    from src.bjarne_api.collector_for_app import Fetcher
except ImportError as e:
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    try:
        from src.bjarne_api.collector_for_app import Fetcher
    except ImportError as e2:
        st.error(f"Kritischer Import-Fehler: {e}")
        st.stop()
    
st.set_page_config(page_title="Bahn Delay Predictor", page_icon="🚆")

# --- Hier muss Jakobs Modell rein --- 
def mock_predict_delay(features):
    time.sleep(0.5)
    return [0.75, 0.20, 0.05]
    
st.title("🚆 Bahn Delay Predictor")
st.markdown("""
Dies ist das Projekt von Bjarne, Eduard und Jakob für das Modul "Python for Data Science". Mit diesem Tool können Bahnreisende die Wahrscheinlichkeit für Verspätungen und Ausfälle ihrer Zugverbindung abschätzen.
""")

with st.container(border=True):
    c1, c2 = st.columns(2)
    start_station = c1.text_input("Startbahnhof", "Berlin Hbf")
    end_station = c2.text_input("Zielbahnhof", "München Hbf")
    ticket_price = st.number_input("Preis (€)", value=50.0)
    analyze_btn = st.button("Verbindung suchen", type="primary")
    
if analyze_btn:
    status = st.status("Verbinde mit DB...", expanded=True)
    try: 
        fetcher = Fetcher()
        status.write("Suche Zug...")
        
        row, err = fetcher.find_connection(start_station, end_station)
        
        if err:
            status.update(label="Fehler", state="error")
            st.error(err)
        elif row is not None:
            status.update(label="Gefunden!", state="complete", expanded=False)
            
            # Ergebnisse anzeigen
            st.success(f"Zug: {row['train_name']} ({row['train_type']})")
            
            probs = mock_predict_delay(row)
            col1, col2, col3 = st.columns(3)
            col1.metric("Pünktlich", f"{probs[0]:.0%}")
            col2.metric("Verspätet", f"{probs[1]:.0%}")
            col3.metric("Ausfall", f"{probs[2]:.0%}")
            
            # Erstattung
            refund = ticket_price * 0.25 if probs[1] > 0.5 else 0
            st.info(f"Mögliche Erstattung bei >60min: {ticket_price*0.25:.2f}€")
            st.info(f"Geschätzte Erstattung bei >120min: {ticket_price*0.5:.2f}€")
            
    except Exception as e: 
        st.error(f"Fehler: {e}")