# import the functions from collector.py 
from src.collector import get_station_details, get_journeys, get_weather

# define start- and end-point
start = "München"
end = "Berlin"


print(f"{start} -> {end}")
start_details = get_station_details(start)
end_details = get_station_details(end)

# check if we have station details for the requested stations and if so: store them as details 
if start_details:
    start_id, start_lat, start_lon = start_details
    print(f"Station {start} (ID: {start_id})")
    print(f"Koordinaten: {start_lat}, {start_lon}")

if end_details:
    end_id, end_lat, end_lon = end_details
    print(f"Station {end} (ID: {end_id})")
    print(f"Koordinaten: {end_lat}, {end_lon}")

    # get the weather details
    print("Wetterdaten:")
    start_weather = get_weather(start_lat, start_lon)
    end_weather = get_weather(end_lat, end_lon)

    # If we have weather details: show it to the user
    if start_weather:
        print(f"Wetter vor Ort: {start_weather['temperature']}°C")
        print(f"Niederschlag: {start_weather['precipitation']}mm")
        print(f"Wind: {start_weather['wind_speed']}km/h")

    if end_weather:
        print(f"Wetter vor Ort: {end_weather['temperature']}°C")
        print(f"Niederschlag: {end_weather['precipitation']}mm")
        print(f"Wind: {end_weather['wind_speed']}km/h")

    # get the trains and store them 
    print(f"Züge nach {end}:")
    df = get_journeys(start_id, end_id)

    # If our Data Frame is not empty, show the user a peek of it 
    if not df.empty:
        print(f"\n Aktuelle Verbindungen von {start} nach {end}")
        print(df[["train_line", "departure_time", "planned_arrival_time", "actual_arrival_time", "current_delay"]].head(20))

    # If there is no trip in our Data Frame
    else: 
        print(f"Aktuell keine Verbindungen von {start} nach {end}")

# If we don't have station detais 
else:
    print("Keine Station mit diesem Namen gefunden")