import requests
import pandas as pd
import urllib.parse
from typing import Optional, Dict, Any, List

def get_weather(lat: Any, lon: Any) -> Dict[str, Any]:
    """
    Liefert Wetterdaten zurück.
    Aktuell als Platzhalter, damit der Code nicht abstürzt.
    """
    # Hier könntest du später die echte Logik einfügen, wenn du sie brauchst.
    # Für jetzt reichen Dummy-Werte, damit die App läuft.
    return {
        "temperature": 15.0, 
        "precipitation": 0.0, 
        "wind_speed": 10.0
    }
# -----------------------------

class Fetcher:
    BASE_URL = "https://v6.db.transport.rest"

    # Initialisiere die Klasse
    def __init__(self):
        self.session = requests.Session()

    # Stations ID abrufen 
    def get_station_id(self, station_name: str) -> Optional[str]:
        url = f"{self.BASE_URL}/locations"
        parameters = {"query": station_name, "type": "station", "results": 1}

        try:
            response = self.session.get(url, params=parameters)
            response.raise_for_status()
            data = response.json()
            if data:
                return data[0]["id"]
        except Exception as e:
            print(f"Fehler beim Abrufen der Stations-ID: {e}")
            return None

    # Rufe die Abfahrtsdetails einer Station ab 
    def stations_details(self, station_id: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/stops/{station_id}/departures"
        
        # Abfrageparameter definieren
        parameters = {
            "results": 150,       
            "duration": 120,       
            "suburban": "false",  
            "subway": "false",    
            "tram": "false",      
            "bus": "false",       
            "regional": "false",  
            "ferry": "false",
            "taxi": "false"
        }

        try:
            response = self.session.get(url, params=parameters)
            response.raise_for_status()
            data = response.json()
            
            # Falls keine Abfahrten vorhanden, gebe leere Liste aus
            if data and "departures" in data:
                return data["departures"]
            return []
            
        except Exception as e:
            print(f"Fehler beim Abrufen der Stationsdetails: {e}")
            return []

    # Rufe Details einer Reise ab 
    def trip_details(self, trip_id: str) -> Optional[Dict[str, Any]]:
        encoded_trip_id = urllib.parse.quote(trip_id, safe='')
        url = f"{self.BASE_URL}/trips/{encoded_trip_id}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            print(f"Fehler beim Abrufen der Reisedetails: {e}")
            return None

    # Erstelle Dataframe aus Reisedaten
    def create_dataframe(self, trip_data: Dict[str, Any], ride_id: int) -> pd.DataFrame:
        if not trip_data:
            return pd.DataFrame()
        
        trip = trip_data.get("trip", trip_data)
        stopovers = trip.get("stopovers", [])

        if not stopovers:
            return pd.DataFrame()

        train_name = trip.get("line", {}).get("name", "NA")
        train_type = trip.get("line", {}).get("productName", "NA")
        
        # Start und Ziel basierend auf erster/letzter Station der Route
        station_start = stopovers[0]["stop"]["name"]
        station_end = stopovers[-1]["stop"]["name"]
        
        # Wetterdaten für Start- und Zielstation abrufen
        first_stop = stopovers[0]["stop"]
        last_stop = stopovers[-1]["stop"]
        
        lat_start = first_stop.get("location", {}).get("latitude")
        lon_start = first_stop.get("location", {}).get("longitude")
        
        lat_end = last_stop.get("location", {}).get("latitude")
        lon_end = last_stop.get("location", {}).get("longitude")
        
        weather_start = get_weather(lat_start, lon_start) if lat_start and lon_start else None
        weather_end = get_weather(lat_end, lon_end) if lat_end and lon_end else None
        
        if weather_start is None: weather_start = {}
        if weather_end is None: weather_end = {}
        
        # Anzahl Stopps berechnen 
        num_stops = len(stopovers)

        content_rows = []

        for i, stop in enumerate(stopovers):
            # Verspätung berechnen
            delay = stop.get("arrivalDelay")
            if delay is None:
                delay = stop.get("departureDelay")
            
            delay_minutes = int(delay / 60) if delay is not None else 0
            
            stop_data = {
                "ride_id": ride_id,
                "train_name": train_name,
                "train_type": train_type,
                "station_start": station_start,
                "station_dest": station_end,
                "current_station": stop["stop"]["name"],
                "planned_arrival": stop.get("plannedArrival"),
                "actual_arrival": stop.get("arrival"),
                "planned_departure": stop.get("plannedDeparture"),
                "actual_departure": stop.get("departure"),
                "current_delay": delay_minutes,
                "start_temp": weather_start.get("temperature"),
                "start_precip": weather_start.get("precipitation"),
                "start_wind_speed": weather_start.get("wind_speed"),
                "end_temp": weather_end.get("temperature"),
                "end_precip": weather_end.get("precipitation"),
                "end_wind_speed": weather_end.get("wind_speed"),
                "stops_total": num_stops,
                "stop_index": i, 
                "stops_remaining": num_stops - i - 1
            }
            content_rows.append(stop_data)

        return pd.DataFrame(content_rows)

    def find_connection(self, start_station: str, end_station: str):
        print(f"Suche Verbindung von {start_station} nach {end_station}...")
        
        start_id = self.get_station_id(start_station)
        end_id = self.get_station_id(end_station)
        
        if not start_id or not end_id:
            return None, "Konnte einen Bahnhof nicht finden."
        
        departures = self.stations_details(start_id)
        if not departures:
            return None, "keine Abfahrten am Startbahnhof gefunden."
        
        for i, departure in enumerate(departures[:10], start=1):
            if "tripId" in departure:
                trip_id = departure.get("tripId")
                if not trip_id:
                    continue
                
                trip_details = self.trip_details(trip_id)
                if not trip_details:
                    continue
                
                stops = trip_details.get("trip", {}).get("stopovers", [])
                stop_names = [s["stop"]["name"] for s in stops]
                
                target_station = any(end_station.lower() in s.lower() for s in stop_names)
                
                if target_station:
                    df = self.create_dataframe(trip_details, ride_id=i)
                    
                    if df.empty: 
                        continue
                    
                    # Finde die Zeile für den Einstiegspunkt
                    entry_row = df[df["current_station"].str.contains(start_station, case=False, na=False)]
                    
                    if not entry_row.empty:
                        return entry_row.iloc[0] , None
                    
                    return df.iloc[0], None
                
        return None, "Keine direkte Verbindung in den nächsten 10 Abfahrten gefunden."
                    

# Ausführung im Hauptprogramm 
if __name__ == "__main__":
    fetcher = Fetcher()
    station_name = "Berlin Hbf" 
    
    print(f"Suche Station ID für {station_name}...")
    station_id = fetcher.get_station_id(station_name)
    
    if station_id:
        print(f"Station ID gefunden: {station_id}. Suche Fernverkehrsabfahrten (nächste 60min)...")
        departures = fetcher.stations_details(station_id)
        
        if departures:
            print(f"{len(departures)} Abfahrten gefunden. Lade Details...")
            
            all_trips_dfs = []
            
            
            for i, departure in enumerate(departures, start=1):
                if "tripId" in departure:
                    trip_id = departure["tripId"]
                    line_name = departure.get("line", {}).get("name", "Unbekannt")
                    
                    print(f"Lade Trip {i}/{len(departures)}: {line_name}")
                    
                    trip_data = fetcher.trip_details(trip_id)
                    
                    df_trip = pd.DataFrame()
                    
                    if trip_data is not None:
                        df_trip = fetcher.create_dataframe(trip_data, ride_id=i)
                    
                    if not df_trip.empty:
                        all_trips_dfs.append(df_trip)
                        
                    else: 
                        print(f"Details für Trip {line_name} konnten nicht verarbeitete werden")
            
            # Zusammenfügen aller DataFrames
            if all_trips_dfs:
                final_df = pd.concat(all_trips_dfs, ignore_index=True)
                print("\n--- FERTIG ---")
                print(final_df)
                print(f"\nGesamtanzahl Haltepunkte analysiert: {len(final_df)}")
                print(f"Anzahl Züge: {final_df['ride_id'].nunique()}")
            else:
                print("Konnte keine Trip-Details verarbeiten.")
        else:
            print("Keine passenden Abfahrten im Zeitraum gefunden.")
    else:
        print("Station nicht gefunden.")