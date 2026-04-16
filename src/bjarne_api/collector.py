'''
This module contains the functions and classes to collect data for the project.

Standalone functions:
- get_station_details: station ID und Koordinaten für einen Stationsnamen abrufen
- get_journeys: Verbindungen zwischen Start- und Zielstation mit ML-Features abrufen
- get_weather: aktuelle Wetterdaten für einen Standort abrufen
- get_historical_weather: historische Wetterdaten für einen Standort und ein Datum abrufen

Fetcher class:
- get_station_id: Stations-ID für einen Stationsnamen abrufen
- stations_details: Abfahrtsdetails einer Station abrufen
- trip_details: Details einer Reise abrufen
- create_dataframe: DataFrame mit relevanten Features aus Reisedaten erstellen
- find_connection: Mögliche Verbindungen zwischen zwei Stationen finden

Author: Member 2 (Student ID: 25268915)
'''

import requests
from requests.exceptions import HTTPError
import pandas as pd
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any, List


# --- Standalone Funktionen ---

def get_station_details(station_name):
    """Station-ID und Koordinaten (lat, lon) für einen Stationsnamen abrufen."""
    source_url = "https://v6.db.transport.rest"
    url = f"{source_url}/stations"

    parameters = {
        "query": station_name,
        "limit": 1
    }

    try:
        response = requests.get(url, params=parameters)
        data = response.json()

        if data:
            first_station = list(data.values())[0]
            station_id = first_station.get("id")
            location = first_station.get("location", {})
            lat = location.get("latitude")
            lon = location.get("longitude")

            if station_id and lat and lon:
                return station_id, lat, lon
        else:
            return None

    except Exception as e:
        print(f"Fehler: {e}")
        return None


def get_journeys(start_id, end_id, departure_time=None, duration=60):
    """Verbindungen zwischen Start- und Zielstation mit relevanten Features abrufen."""
    url = "https://v6.db.transport.rest/journeys"

    parameters = {
        "from": start_id,
        "to": end_id,
        "results": 10,
        "duration": duration,
        "departure_time": departure_time
    }

    long_distance_trains = ["ICE", "IC", "EC", "ECE", "RJ", "RJX", "FLX", "NJ"]

    try:
        response = requests.get(url, params=parameters)
        data = response.json()

        journey_list = data.get("journeys", [])
        cleaned_data = []

        def get_datetime_object(date_time_str):
            if not date_time_str:
                return None
            try:
                return datetime.fromisoformat(date_time_str)
            except ValueError:
                return None

        for journey in journey_list:
            legs = journey.get("legs", [])
            if not legs:
                continue

            first_leg = legs[0]
            last_leg = legs[-1]

            line_info = first_leg.get("line", [])
            train_type = line_info.get("productName", "")
            train_name = line_info.get("name", "Unknown")

            if train_type not in long_distance_trains:
                continue

            planned_arrival = last_leg.get("plannedArrival")
            actual_arrival = last_leg.get("arrival")

            d_plan = get_datetime_object(planned_arrival)
            d_actual = get_datetime_object(actual_arrival)

            if d_plan is not None and d_actual is not None:
                delay_minutes = (d_actual - d_plan).total_seconds() / 60
            else:
                delay_minutes = 0.0

            journey_data = {
                "train_line": train_name,
                "departure_time": datetime.fromisoformat(first_leg.get("plannedDeparture")),
                "planned_arrival_time": d_plan,
                "actual_arrival_time": d_actual,
                "current_delay": delay_minutes
            }

            cleaned_data.append(journey_data)

        return pd.DataFrame(cleaned_data)

    except Exception as e:
        print(f"Fehler bei Journeys: {e}")
        return pd.DataFrame()


def get_weather(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """Aktuelle Wetterdaten (Temperatur, Niederschlag, Windgeschwindigkeit) abrufen."""
    url = "https://api.open-meteo.com/v1/forecast"

    parameters = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,precipitation,wind_speed_10m"
    }

    try:
        response = requests.get(url, params=parameters)
        data = response.json()

        current = data.get("current", {})

        weather_info = {
            "temperature": current.get("temperature_2m"),
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed_10m")
        }

        return weather_info

    except Exception as e:
        print(f"Fehler beim Wetter: {e}")
        return None


def get_historical_weather(lat, lon, date):
    """Historische Wetterdaten für einen Standort und ein Datum abrufen."""
    url = "https://archive-api.open-meteo.com/v1/archive"

    parameters = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date,
        "end_date": date,
        "hourly": "temperature_2m,precipitation,wind_speed_10m",
        "timezone": "Europe/Berlin"
    }

    try:
        response = requests.get(url, params=parameters)
        response.raise_for_status()
        data = response.json()

        hourly = data.get("hourly", {})
        if not hourly or "temperature_2m" not in hourly:
            return {
                "temp_avg": None,
                "precipitation_sum": None,
                "wind_speed_max": None,
                "weather_status": "No data"
            }

        temperatures = hourly.get("temperature_2m", [])
        precipitations = hourly.get("precipitation", [])
        wind_speeds = hourly.get("wind_speed_10m", [])

        return {
            "temp_avg": round(sum(temperatures) / len(temperatures), 2) if temperatures else None,
            "precipitation_sum": round(sum(precipitations), 2) if precipitations else None,
            "wind_speed_max": round(max(wind_speeds), 2) if wind_speeds else None,
            "weather_status": "ok"
        }

    except Exception as e:
        print(f"Fehler beim Abrufen der historischen Wetterdaten: {e}")
        return {
            "temp_avg": None,
            "precipitation_sum": None,
            "wind_speed_max": None,
            "weather_status": "Error"
        }


# --- Fetcher Klasse ---

class Fetcher:
    BASE_URL = "https://v6.db.transport.rest"

    def __init__(self):
        self.session = requests.Session()

    def get_station_id(self, station_name: str) -> Optional[str]:
        """Stations-ID für einen Stationsnamen abrufen."""
        url = f"{self.BASE_URL}/locations"
        parameters = {"query": station_name, "type": "station", "results": 1}

        try:
            response = self.session.get(url, params=parameters)
            response.raise_for_status()
            data = response.json()
            if data:
                return data[0]["id"]
            else:
                print(f"Die eingegebene Station {station_name} existiert nicht")

        except HTTPError as http_err:
            print(f"Fehler bei der Suche nach {station_name} - {http_err}. Gibt es den eingegebenen Bahnhof wirklich?")

        except Exception as e:
            print(f"Fehler beim Abrufen der Stations-ID: {e}")
            return None

    def stations_details(self, station_id: str) -> List[Dict[str, Any]]:
        """Abfahrtsdetails (Fernverkehr) für eine Station abrufen."""
        url = f"{self.BASE_URL}/stops/{station_id}/departures"

        parameters = {
            "results": 30,
            "duration": 60,
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

            if data and "departures" in data and len(data["departures"]) > 0:
                return data["departures"]
            else:
                print(f"Für den Bahnhof {station_id} gibt es aktuell keine Abfahrten")
                return []

        except Exception as e:
            print(f"Fehler beim Abrufen der Stationsdetails: {e}")
            return []

    def trip_details(self, trip_id: str) -> Optional[Dict[str, Any]]:
        """Details einer Reise anhand der Trip-ID abrufen."""
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

    def create_dataframe(self, trip_data: Dict[str, Any], ride_id: int) -> pd.DataFrame:
        """DataFrame mit relevanten Features aus Reisedaten erstellen."""
        if not trip_data:
            return pd.DataFrame()

        trip = trip_data.get("trip", trip_data)
        stopovers = trip.get("stopovers", [])

        if not stopovers:
            return pd.DataFrame()

        station_start = stopovers[0]["stop"]["name"]
        station_end = stopovers[-1]["stop"]["name"]

        train_name = trip.get("line", {}).get("name", "NA")
        train_type = trip.get("line", {}).get("productName", "NA")

        num_stops = len(stopovers)
        content_rows = []

        for i, stop in enumerate(stopovers):
            lat = stop.get("stop", {}).get("location", {}).get("latitude")
            lon = stop.get("stop", {}).get("location", {}).get("longitude")

            weather = {}
            if lat and lon:
                weather = get_weather(lat, lon) or {}

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
                "station_current": stop["stop"]["name"],
                "arrival_planned": stop.get("plannedArrival"),
                "arrival_real": stop.get("arrival"),
                "departure_planned": stop.get("plannedDeparture"),
                "departure_real": stop.get("departure"),
                "current_delay": delay_minutes,
                "temp": weather.get("temperature"),
                "precip": weather.get("precipitation"),
                "wind_speed": weather.get("wind_speed"),
                "stops_total": num_stops,
                "stop_index": i,
                "stops_remaining": num_stops - i - 1
            }
            content_rows.append(stop_data)

        return pd.DataFrame(content_rows)

    def find_connection(self, start_station: str, end_station: str):
        """Mögliche direkte Verbindungen zwischen zwei Stationen finden."""
        print(f"Suche Verbindung von {start_station} nach {end_station}...")

        start_id = self.get_station_id(start_station)
        end_id = self.get_station_id(end_station)

        if not start_id or not end_id:
            return pd.DataFrame(), "Bahnhof nicht gefunden."

        departures = self.stations_details(start_id)
        if not departures:
            return pd.DataFrame(), "Keine Abfahrten am Startbahnhof gefunden."

        connections = []

        for i, departure in enumerate(departures[:15], start=1):
            if "tripId" in departure:
                trip_id = departure.get("tripId")
                if not trip_id:
                    continue

                trip_details = self.trip_details(trip_id)
                if not trip_details:
                    continue

                stops = trip_details.get("trip", {}).get("stopovers", [])
                stop_names = [s["stop"]["name"] for s in stops]

                if any(end_station.lower() in s.lower() for s in stop_names):
                    df = self.create_dataframe(trip_details, ride_id=i)

                    if df.empty:
                        continue

                    entry_row = df[df["station_current"].str.contains(start_station, case=False, na=False)]

                    if not entry_row.empty:
                        connections.append(entry_row.iloc[0])

            if not connections:
                return pd.DataFrame(), "Keine direkte Verbindung gefunden."

        return pd.DataFrame(connections), None


# --- Ausführung im Hauptprogramm ---

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
