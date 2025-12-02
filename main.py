# import the functions from collector.py 
from src.collector import get_station_details, get_departures, get_weather, get_journeys, parse_datetime

# define start- and end-point
start = "Muenchen"
end = "Goettingen"


print(f"{start} -> {end}")
details_start = get_station_details(start)
details_end = get_station_details(end)

# check if we have a station details for the requested station and if so: store it as details 
if details_start and details_end:
    start_id, start_lat, start_lon = details_start
    end_id, end_lat, end_lon = details_end
    print(f"Station {start} (ID: {start_id}) -> {end} (ID: {end_id})")
    print(f"Koordinaten Start: {start_lat}, {start_lon}\n Koordinaten Ende: {end_lat}, {end_lon}")


    # get the weather details
    print("Wetterdaten Start:")
    weather_start = get_weather(start_lat, start_lon)
    weather_end = get_weather(end_lat, end_lon)

    # If we have weather details: show it to the user
    if weather_start and weather_end:
        #print the weather data for the starting point
        print(f"Wetter in {start}: {weather_start['temperature']}°C")
        print(f"Niederschlag {start}: {weather_start['precipitation']}mm")
        print(f"Wind {start}: {weather_start['wind_speed']}km/h")

        # print the weather data for the end point
        print(f"Wetter in {end}: {weather_end['temperature']}°C")
        print(f"Niederschlag {end}: {weather_end['precipitation']}mm")
        print(f"Wind {end}: {weather_end['wind_speed']}km/h")


    # get the trains and store them 
    print(f"Züge nach {end}:")
    df = get_journeys(start_id, end_id, departure_time= "2025-12-24 09" ,duration = 10000)


    # If our Data Frame is not empty, show the user a peek of it 
    if not df.empty:
        print(f"\n Aktuelle Verbindungen von {start} nach {end}")
        print(df[["train_line", "departure_time", "arrival_time", "delay_minutes"]].head(20))

    # If there is no trip in our Data Frame
    else: 
        print(f"Aktuell keine Verbindungen von {start} nach {end}")

# If we don't have station detais 
else:
    print("Keine Station mit diesem Namen gefunden")