# import the self created function from own module 
from src.collector import get_station_details, get_departures, get_weather

start = "München"
end = "Berlin"

print(f"{start} -> {end}")
details = get_station_details(start)

# check if we have a station id for the requested station
if details:
    station_id, lat, lon = details
    print(f"Station {start} (ID: {station_id})")
    print(f"Koordinaten: {lat}, {lon}")

    # get the weather data
    print("Wetterdaten:")
    weather = get_weather(lat, lon)

    if weather:
        print(f"Wetter vor Ort: {weather['temperature']}°C")
        print(f"Niederschlag: {weather['precipitation']}mm")
        print(f"Wind: {weather['wind_speed']}km/h")

    # get the trains
    print(f"Züge nach {end}:")
    df = get_departures(station_id, destination=end)

    if not df.empty:
        print("\n Aktuelle Verbindungen nach {end}")
        print(df[["train_line", "direction", "delay_minutes"]].head(20))

    else: 
        print(f"Aktuell keine Verbindungen von {start} nach {end}")

else:
    print("Keine Station mit diesem Namen gefunden")

