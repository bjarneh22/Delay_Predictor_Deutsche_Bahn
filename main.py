# import the functions from collector.py 
from src.collector import get_station_details, get_departures, get_weather

# define start- and end-point
start = "München"
end = "Berlin"


print(f"{start} -> {end}")
details = get_station_details(start)

# check if we have a station details for the requested station and if so: store it as details 
if details:
    station_id, lat, lon = details
    print(f"Station {start} (ID: {station_id})")
    print(f"Koordinaten: {lat}, {lon}")

    # get the weather details
    print("Wetterdaten:")
    weather = get_weather(lat, lon)

    # If we have weather details: show it to the user
    if weather:
        print(f"Wetter vor Ort: {weather['temperature']}°C")
        print(f"Niederschlag: {weather['precipitation']}mm")
        print(f"Wind: {weather['wind_speed']}km/h")

    # get the trains and store them 
    print(f"Züge nach {end}:")
    df = get_departures(station_id, destination=end)

    # If our Data Frame is not empty, show the user a peek of it 
    if not df.empty:
        print("\n Aktuelle Verbindungen nach {end}")
        print(df[["train_line", "direction", "delay_minutes"]].head(20))

    # If there is no trip in our Data Frame
    else: 
        print(f"Aktuell keine Verbindungen von {start} nach {end}")

# If we don't have station detais 
else:
    print("Keine Station mit diesem Namen gefunden")

