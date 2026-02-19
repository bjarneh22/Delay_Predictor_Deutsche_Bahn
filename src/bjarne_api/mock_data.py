import pandas as pd
from datetime import datetime, timedelta

def generate_mock_data():
    # Beispiel-Stationen aus deinen historischen Daten (Berlin, Hamburg, München)
    stations = ["Berlin Hbf", "Hamburg Hbf", "München Hbf", "Frankfurt(Main)Hbf", "Köln Hbf"]
    
    mock_rows = []
    
    # Wir erstellen 3 Beispiel-Trips
    trips = [
        {"id": 1, "name": "ICE 501", "type": "ICE", "route": ["Berlin Hbf", "Leipzig Hbf", "München Hbf"]},
        {"id": 2, "name": "ICE 202", "type": "ICE", "route": ["Hamburg Hbf", "Hannover Hbf", "Frankfurt(Main)Hbf"]},
        {"id": 3, "name": "IC 2311", "type": "IC", "route": ["Berlin Hbf", "Wolfsburg Hbf", "Hamburg Hbf"]}
    ]

    now = datetime.now()

    for trip in trips:
        route = trip["route"]
        num_stops = len(route)
        
        for i, stop in enumerate(route):
            planned_dep = now + timedelta(hours=i)
            # Simuliere eine Verspätung von 5 Minuten
            delay = 5 
            
            row = {
                "ride_id": trip["id"],
                "train_name": trip["name"],
                "train_type": trip["type"],
                "station_start": route[0],
                "station_dest": route[-1],
                "station_current": stop,
                "arrival_planned": (planned_dep - timedelta(minutes=10)).isoformat(),
                "arrival_real": (planned_dep - timedelta(minutes=10) + timedelta(minutes=delay)).isoformat(),
                "departure_planned": planned_dep.isoformat(),
                "departure_real": (planned_dep + timedelta(minutes=delay)).isoformat(),
                "current_delay": delay,
                "temp": 12.5,
                "precip": 0.0,
                "wind_speed": 15.0,
                "stops_total": num_stops,
                "stop_index": i, 
                "stops_remaining": num_stops - i - 1
            }
            mock_rows.append(row)

    df = pd.DataFrame(mock_rows)
    df.to_csv("data/mock_api_data.csv", index=False)
    print("Mock-Daten erfolgreich in 'data/mock_api_data.csv' gespeichert.")

if __name__ == "__main__":
    import os
    if not os.path.exists('data'): os.makedirs('data')
    generate_mock_data()