# import the self created function from own module 
from src.collector import get_station_id, get_departures

start = "München"
end = "Berlin"

print(f"{start} -> {end}")
station_id = get_station_id(start)

# check if we have a station id for the requested station
if station_id:
    df = get_departures(station_id, destination=end)

    if not df.empty:
        print("\n Aktuelle Verbindungen nach {end}")
        print(df[["train_line", "direction", "delay_minutes"]].head(20))

    else: 
        print(f"Aktuell keine Verbindungen von {start} nach {end}")

else:
    print("Keine Station mit diesem Namen gefunden")

