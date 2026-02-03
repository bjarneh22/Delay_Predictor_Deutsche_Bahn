import requests
import pandas as pd
import urllib.parse
from typing import Optional, Dict, Any, List

# Interne Wetter-Funktion (kein Import!)
def get_weather(lat: Any, lon: Any) -> Dict[str, Any]:
    return {"temperature": 15.0, "precipitation": 0.0, "wind_speed": 10.0}

class Fetcher:
    BASE_URL = "https://v6.db.transport.rest"

    def __init__(self):
        self.session = requests.Session()

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
            print(f"Fehler Stations-ID: {e}")
            return None

    def stations_details(self, station_id: str) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/stops/{station_id}/departures"
        parameters = {
            "results": 150, "duration": 120, "suburban": "false", "subway": "false",
            "tram": "false", "bus": "false", "regional": "false", "ferry": "false", "taxi": "false"
        }
        try:
            response = self.session.get(url, params=parameters)
            if response.status_code != 200: return []
            data = response.json()
            return data.get("departures", [])
        except Exception:
            return []

    def trip_details(self, trip_id: str) -> Optional[Dict[str, Any]]:
        encoded_trip_id = urllib.parse.quote(trip_id, safe='')
        url = f"{self.BASE_URL}/trips/{encoded_trip_id}"
        try:
            response = self.session.get(url)
            if response.status_code != 200: return None
            return response.json()
        except Exception:
            return None

    def create_dataframe(self, trip_data: Dict[str, Any], ride_id: int) -> pd.DataFrame:
        if not trip_data: return pd.DataFrame()
        trip = trip_data.get("trip", trip_data)
        stopovers = trip.get("stopovers", [])
        if not stopovers: return pd.DataFrame()

        train_name = trip.get("line", {}).get("name", "NA")
        train_type = trip.get("line", {}).get("productName", "NA")
        
        # Wetterdaten (Dummy)
        weather = get_weather(0, 0)

        num_stops = len(stopovers)
        content_rows = []

        for i, stop in enumerate(stopovers):
            delay = stop.get("arrivalDelay") or stop.get("departureDelay")
            delay_minutes = int(delay / 60) if delay is not None else 0
            
            content_rows.append({
                "ride_id": ride_id,
                "train_name": train_name,
                "train_type": train_type,
                "current_station": stop["stop"]["name"],
                "current_delay": delay_minutes,
                "stops_remaining": num_stops - i - 1,
                # Füge hier bei Bedarf weitere Felder hinzu
            })

        return pd.DataFrame(content_rows)

    def find_connection(self, start_station: str, end_station: str):
        print(f"Suche {start_station} -> {end_station}...")
        start_id = self.get_station_id(start_station)
        end_id = self.get_station_id(end_station)
        
        if not start_id or not end_id:
            return None, "Bahnhof nicht gefunden."
        
        departures = self.stations_details(start_id)
        if not departures:
            return None, "Keine Abfahrten."
        
        for i, departure in enumerate(departures[:10], start=1):
            trip_id = departure.get("tripId")
            if not trip_id: continue
            
            trip = self.trip_details(trip_id)
            if not trip: continue
            
            stops = trip.get("trip", {}).get("stopovers", [])
            stop_names = [s["stop"]["name"] for s in stops]
            
            if any(end_station.lower() in s.lower() for s in stop_names):
                df = self.create_dataframe(trip, ride_id=i)
                if df.empty: continue
                
                # Finde Einstieg
                entry = df[df["current_station"].str.contains(start_station, case=False, na=False)]
                if not entry.empty:
                    return entry.iloc[0], None
                return df.iloc[0], None
                
        return None, "Keine direkte Verbindung gefunden."
