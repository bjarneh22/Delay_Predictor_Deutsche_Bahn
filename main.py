# import the functions from collector.py
from src.collector import get_station_details, get_journeys, get_weather

# import the functions for data insertion(DI)
import sqlite3
from db.insert_data import add_station, add_weather, add_journeys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# DI: current time in CET
#TO-DO: Take a look into this function to see how we can properly format the current time
now = datetime.now(ZoneInfo("Europe/Berlin")).isoformat()

# define start- and end-point
start = "Muenchen"
end = "Berlin"


print(f"{start} -> {end}")

# DI: connect to our DB
conn = sqlite3.connect("train_delay.db")
conn.execute("PRAGMA foreign_keys = ON;")

start_details = get_station_details(start)
end_details = get_station_details(end)

# check if we have station details for the requested stations and if so: store them as details 
if start_details:
    start_id, start_lat, start_lon = start_details
    print(f"Station {start} (ID: {start_id})")
    print(f"Koordinaten: {start_lat}, {start_lon}")

# DI: add the start station
    add_station(conn, (start_id, start, start_lat, start_lon))

if end_details:
    end_id, end_lat, end_lon = end_details
    print(f"Station {end} (ID: {end_id})")
    print(f"Koordinaten: {end_lat}, {end_lon}")

# DI: add the end station
    add_station(conn, (end_id, end, end_lat, end_lon))

    # get the weather details
    print("Wetterdaten:")
    start_weather = get_weather(start_lat, start_lon)
    end_weather = get_weather(end_lat, end_lon)

    # If we have weather details: show it to the user
    if start_weather:
        print(f"Wetter vor Ort: {start_weather['temperature']}°C")
        print(f"Niederschlag: {start_weather['precipitation']}mm")
        print(f"Wind: {start_weather['wind_speed']}km/h")

    # DI: add weather details
        add_weather(conn, (start_id, start_weather['temperature'],
                           start_weather['precipitation'], start_weather['wind_speed'], now))

    if end_weather:
        print(f"Wetter vor Ort: {end_weather['temperature']}°C")
        print(f"Niederschlag: {end_weather['precipitation']}mm")
        print(f"Wind: {end_weather['wind_speed']}km/h")

    # DI: add weather details
        add_weather(conn, (end_id, end_weather['temperature'],
                           end_weather['precipitation'], end_weather['wind_speed'], now))

    # get the trains and store them 
    print(f"Züge nach {end}:")
    df = get_journeys(start_id, end_id)



    # If our Data Frame is not empty, show the user a peek of it 
    if not df.empty:
        print(f"\n Aktuelle Verbindungen von {start} nach {end}")
        print(df[["train_line", "departure_time", "planned_arrival_time", "actual_arrival_time", "current_delay"]].head(20))

    # DI: add all the journeys into the table
    for _, row in df.iterrows():
        journey_tuple = (
            row["train_line"],
            start_id,
            end_id,
            row["departure_time"].isoformat(),
            row["planned_arrival_time"].isoformat() if row["planned_arrival_time"] else None,
            row["actual_arrival_time"].isoformat() if row["actual_arrival_time"] else None,
            row["current_delay"],
            now
        )
        add_journeys(conn, journey_tuple)

    # If there is no trip in our Data Frame
    else: 
        print(f"Aktuell keine Verbindungen von {start} nach {end}")

# If we don't have station detais 
else:
    print("Keine Station mit diesem Namen gefunden")