# import the relevant packages for the API Call
import requests
import pandas as pd

# get the station id 
def get_station_id(station_name): 

    # store the url for the API 
    source_url = "https://v6.db.transport.rest"
    url = f"{source_url}/stations"

    # Define the parameters
    parameters = {
        "query": station_name,
        "limit": 100
    }

    # Call the data from the source
    try:
        response = requests.get(url, params=parameters)
        data = response.json()

        # Read the data from the source
        if data:
            first_element = list(data.values())[0]
            return first_element["id"]
        else: 
            return None
            
    except Exception as e:
        print(f"Fehler: {e}")
        return None

# get the information about the delay
def get_departures(station_id, duration=60, destination=None):
    # get the departures for a train with a given station id
    source_url = "https://v6.db.transport.rest"
    url = f"{source_url}/stops/{station_id}/departures"

    parameters = {
        "duration": duration,
        "results": 100
    }

    long_distance_trains = ["ICE", "IC", "EC", "ECE", "RJ", "RJX", "FLX", "NJ"]

    try:
        response = requests.get(url, params=parameters)
        data = response.json()
        departures = data.get("departures", [])

        cleaned_data = []

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

            train_data={
                "station_id": station_id,
                "train_line": line_info.get("name"),
                "direction": entry.get("direction"),
                "planned_time": entry.get("plannedWhen"),
                "actual_time": entry.get("when"),
                "delay_minutes": entry.get("delay", 0)/60 if entry.get("delay") else 0
            }

            cleaned_data.append(train_data)

        df = pd.DataFrame(cleaned_data)
        return df
    
    except Exception as e:
        print(f"Fehler: {e}")
        return None
