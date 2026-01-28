# import the relevant packages for the API Call
import requests
import pandas as pd
from datetime import datetime

# get the station id 
def get_station_details(station_name): 
    # store the url for the API 
    source_url = "https://v6.db.transport.rest"
    url = f"{source_url}/stations"

    # Define the parameters for the call 
    parameters = {
        "query": station_name,
        "limit": 1
    }

    # Call the data from the source with try-catch
    try:
        response = requests.get(url, params=parameters)
        data = response.json()

        # Read the data from the source
        if data:
            first_station = list(data.values())[0]

            # store the relevant features of the station (id and location)
            station_id = first_station.get("id")
            location = first_station.get("location", {})
            
            # store the latitude and longitude from the station separately
            lat = location.get("latitude")
            lon = location.get("longitude")
            
            # only if all values are present return the details of the station
            if station_id and lat and lon:
                return station_id, lat, lon

        # if data is empty return nothing
        else: 
            return None

    # if exception occurs during try
    except Exception as e:
        print(f"Fehler: {e}")
        return None
    

# get information about a journey
def get_journeys(start_id, end_id, departure_time=None, duration=60):

    # store the url for the API 
    url = "https://v6.db.transport.rest/journeys"

    # Define the parameters for the call
    parameters = {
        "from" : start_id, 
        "to" : end_id,
        "results" : 10,
        "duration" : duration,
        "departure_time" : departure_time
    }

    # Define which types of trains are long distance
    long_distance_trains = ["ICE", "IC", "EC", "ECE", "RJ", "RJX", "FLX", "NJ"]

    # Call the data from the source
    try:
        response = requests.get(url, params=parameters)
        data = response.json()

        # Store the journeys as list
        journey_list = data.get("journeys", [])

        cleaned_data = []

        def get_datetime_object(date_time_str):
            if not date_time_str:
                return None
            try:
                return datetime.fromisoformat(date_time_str)
            except ValueError:
                return None

        # Iterate through all the journeys and store matching ones in cleaned_data
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
        
            # compute the delay
            planned_arrival = last_leg.get("plannedArrival")
            actual_arrival = last_leg.get("arrival")

            # compute the delay
            planned_arrival = last_leg.get("plannedArrival")
            actual_arrival = last_leg.get("arrival")

            delay_minutes = 0.0 # Standardwert als Float
            d_plan = get_datetime_object(planned_arrival)
            d_actual = get_datetime_object(actual_arrival)

            # Nur rechnen, wenn beide Werte tatsächliche datetime-Objekte sind
            if d_plan is not None and d_actual is not None:
                delay_minutes = (d_actual - d_plan).total_seconds() / 60
            else:
                delay_minutes = 0.0

            journey_data = {
                "train_line" : train_name,
                "departure_time" : datetime.fromisoformat(first_leg.get("plannedDeparture")),
                "planned_arrival_time" : d_plan,
                "actual_arrival_time" : d_actual, 
                "current_delay" : delay_minutes
            }

            # Store the journey in cleaned_data
            cleaned_data.append(journey_data)
        
        return pd.DataFrame(cleaned_data)
    
    except Exception as e:
        print(f"Fehler bei Journeys: {e}")
        return pd.DataFrame()

# get weather information for a station 
def get_weather(lat, lon):

    # Store the url for the API 
    url = "https://api.open-meteo.com/v1/forecast"

    # Define the parameters for the call 
    parameters = {
        "latitude" : lat,
        "longitude" : lon,
        "current" : "temperature_2m,precipitation,wind_speed_10m"
    }

    # call the data from the source
    try: 
        response = requests.get(url, params=parameters)
        data = response.json()

        # get the current weather data for the latitude and longitude of a specific train 
        current = data.get("current", {})

        # store the weather info 
        weather_info = {
            "temperature" : current.get("temperature_2m"),
            "precipitation" : current.get("precipitation"),
            "wind_speed" : current.get("wind_speed_10m")
        }

        return weather_info
    
    except Exception as e:
        print(f"Fehler beim Wetter: {e}")
        return None

# Hier die neue Funktion für historische Wetterdaten @Eddi
def get_historical_weather(lat, lon, date):
    
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
                "weather_staus": "No data"
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
        

'''
# get the information about a trip
def get_departures(station_id, duration=60, destination=None):

    # store the url for the API 
    source_url = "https://v6.db.transport.rest"
    url = f"{source_url}/stops/{station_id}/departures"

    # Define the parameters for the call 
    parameters = {
        "duration": duration,
        "results": 2000,
        'bus': 'false',
        'suburban': 'false',
        'subway': 'false',
        'regional': 'false'
    }

    # Define which types of trains are long distance
    long_distance_trains = ["ICE", "IC", "EC", "ECE", "RJ", "RJX", "FLX", "NJ"]

    # Call the data from the source with try-catch 
    try:
        response = requests.get(url, params=parameters)
        data = response.json()
        departures = data.get("departures", [])

        cleaned_data = []

        # iterate through the departures and filter for those who match the criteria 
        for entry in departures:
            line_info = entry.get("line", [])
            trip_type = line_info.get("productName") 
            direction = entry.get("direction") or ""

            # Filter for long distance trains only
            if trip_type not in long_distance_trains:
                continue 

            # Filter for specific destination
            if destination:
                if destination.lower() not in direction.lower():
                    continue
            
            # Store the data of the trains that fulfil the requirements in a dictionary
            train_data={
                "station_id": station_id,
                "train_line": line_info.get("name"),
                "direction": entry.get("direction"),
                "planned_time": entry.get("plannedWhen"),
                "actual_time": entry.get("when"),
                "delay_minutes": entry.get("delay", 0)/60 if entry.get("delay") else 0
            }

            # Store the resulting train_data in the cleaned list
            cleaned_data.append(train_data)

        # Convert the clean list into a pandas Data Frame 
        df = pd.DataFrame(cleaned_data)
        return df
    
    # If exception occurs during try
    except Exception as e:
        print(f"Fehler: {e}")
        return None
'''
