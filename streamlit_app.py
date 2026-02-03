import streamlit as st 
import pandas as pd 
import time 
import sys 
import os 

# src Verzeichnis zum Pfad hinzufügen
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try: 
    from src.bjarne_api.collector_for_app import Fetcher
except ImportError as e:
    st.error(f"Fehler beim Importieren des Moduls: {e}")
    st.info("Stelle sicher, dass 'app.py' im Hauptverzeichnis liegt und der Ordner 'src/bjarne_api' existiert.")
    st.stop()
    
st.set_page_config(
    page_title="Bahn Delay Predictor",
    page_icon="🚆",
    layout="centered"
)

def mock_predict_delay(features):
    """
    Gibt Dummy-Wahrscheinlichkeiten zurück, damit probs nicht None ist.
    """
    time.sleep(0.5) # Ladezeit simulieren
    
    # Beispielwerte (später durch Jakob's Modell ersetzen)
    return [0.75, 0.20, 0.05]
    
st.title("🚆 Bahn Delay Predictor")
st.markdown("""
            Willkommen zum Bahn Delay Predictor! Diese Anwendung sagt die Verspätung von Zugfahrten vorher. Sie ist das Projekt von Bjarne, Eduard und Jakob für das Modul "Python for Data Science"
            """)

with st.container(border=True):
    col1, col2 = st.columns(2)
    
    with col1:
        start_station = st.text_input("Startbahnhof", value="Berlin Hbf")
    with col2:
        end_station = st.text_input("Zielbahnhof", value="Munchen Hbf")
        
    ticket_price = st.number_input("Ticketpreis (€)", min_value=0.0, value=50.0, step=1.0)
    
    analyze_button = st.button("Verspätung vorhersagen 🚆")
    
if analyze_button:
    if not start_station or not end_station:
        st.warning("Bitte geben Sie sowohl den Start- als auch den Zielbahnhof ein.")
    else:
        status = st.status("Verbinde mit DB API...", expanded=True)
        
        try: 
            fetcher = Fetcher()
            status.write("Verbindung suchen...")
            
            feature_row, error_msg = fetcher.find_connection(start_station, end_station)
            
            if error_msg:
                status.update(label="Fehler bei der Verbindung zur DB API", state="error", expanded=True)
                st.error(f"Fehler beim Abrufen der Zugdaten: {error_msg}")
                st.stop()
                
            elif feature_row is not None:
                status.write(f"**Zug:** {feature_row['train_name']} ({feature_row['train_type']})")
                status.write(f"**Aktueller Standort:** {feature_row['current_station']}")
                
                status.update(label="Zugverbindung gefunden", state="complete", expanded=False)
                
                probs = mock_predict_delay(feature_row)
                
                st.divider()
                st.subheader(f"Verspätungsvorhersage für {feature_row['train_name']} von {start_station} nach {end_station}")
                
                m1, m2 , m3 = st.columns(3)
                m1.metric("Pünktlich / <60min", f"{probs[0]:.2%}")
                m2.metric("60-120min Verspätung", f"{probs[1]:.2%}")
                m3.metric(">120min Verspätung", f"{probs[2]:.2%}")
                
                chart_data = {
                    "Pünktlich / <60min": probs[0],
                    "60-120min Verspätung": probs[1],
                    ">120min Verspätung": probs[2]}
                
                st.bar_chart(chart_data)
                
                st.divider()
                st.subheader("Voraussichtliche Erstattung:")
                
                refund_25 = ticket_price * 0.25
                refund_50 = ticket_price * 0.50
                
                c1, c2 = st.columns(2)
                
                with c1: 
                    st.info(f"**Falls > 60min Verspätung:** \n Du bekommst **{refund_25:.2f}€** erstattet. \n (25% von {ticket_price:.2f}€)")
                
                with c2:
                    st.info(f"**Falls > 120min Verspätung:** \n Du bekommst **{refund_50:.2f}€** erstattet. \n (50% von {ticket_price:.2f}€)")
                
        except Exception as e: 
            status.update(label="Fehler bei der Verbindung zur DB API", state="error", expanded=True)
            st.error(f"Es gab einen Fehler bei der Verbindung zur DB API: {e}")
            