# import the self created function from own module 
from src.collector import get_station_id

station_name = "Goettingen"

print(f"Suche nach Stationen: {station_name}")

station_id = get_station_id(station_name)

# check if we have a station id for the requested station
if station_id:
    print("The Station ID for {station_name} is: {station_id}")
else: 
    print("No station found")