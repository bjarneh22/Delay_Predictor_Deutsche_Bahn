# import the relevant packages for the API Call
import requests
import pandas as pd


def get_station_id(station_name): 

    # store the url for the API 
    source_url = "https://v6.db.transport.rest"
    url = f"{source_url}/stations"

    # Define the parameters
    parameters = {
        "query": station_name,
        "limit": 1
    }

    # Call the data from the source
    try:
        response = requests.get(url, params=parameters)
        data = response.json()

        # Read the data from the source
        result1 = data.get("0")

        if result1:
            return result1["id"]
        else:
            return None
        
    except Exception as e:
        print(f"Fehler: {e}")
        return None
        