# import the relevant packages for the API Call
import requests
import pandas as pd
import json


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

        # --- DEBUGGING START ---
        '''
        print(f"\n--- DEBUG: Rohe API-Antwort für '{station_name}' ---")
        print(f"Datentyp: {type(data)}") # (Notebook 01: type())
        # Wir nutzen json.dumps für "Pretty Printing" mit Einrückung (indent=2)
        print(json.dumps(data, indent=2)) 
        print("----------------------------------------------------\n")
        '''
        # --- DEBUGGING ENDE ---

        # Read the data from the source
        if data:
            first_element = list(data.values())[0]
            return first_element["id"]
        else: 
            return None
        
    except Exception as e:
        print(f"Fehler: {e}")
        return None
