import requests
import folium
from polyline import decode
import csv
import datetime
from geopy.geocoders import Nominatim

def get_coordinates(location):
    geolocator = Nominatim(user_agent="osrm_locator")
    try:
        location_info = geolocator.geocode(location)
        if location_info:
            return (location_info.latitude, location_info.longitude)
        else:
            return None
    except Exception as e:
        return None

def get_weather_data(api_key, lat, lon):
    base_url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'imperial'}  # Use 'imperial' for Fahrenheit

    response = requests.get(base_url, params=params)
    data = response.json()

    if response.status_code == 200:
        temp_fahrenheit = data['main']['temp']
        conditions = data['weather'][0]['description']
        return {'temp_F': temp_fahrenheit, 'conditions': conditions}
    else:
        print(f"Error fetching weather data: {response.status_code}")
        return None

def get_traffic_info(api_key, start_coord, end_coord):
    base_url = 'https://maps.googleapis.com/maps/api/directions/json'
    params = {
        'origin': f"{start_coord[0]},{start_coord[1]}",
        'destination': f"{end_coord[0]},{end_coord[1]}",
        'key': api_key,
        'mode': 'driving',
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if response.status_code == 200 and 'routes' in data and data['routes']:
        route = data['routes'][0]

        if 'legs' in route and route['legs'] and 'duration' in route['legs'][0]:
            duration_in_traffic_seconds = route['legs'][0]['duration']['value']
            duration_in_traffic = str(datetime.timedelta(seconds=duration_in_traffic_seconds))
            return duration_in_traffic
    else:
        print(f"Error fetching traffic data: {response.status_code}")
        return None

def get_color_for_condition(condition):
    if 'clear sky' in condition.lower():
        return 'green'
    elif 'mist' in condition.lower():
        return 'blue'
    elif 'shower rain' in condition.lower():
        return 'blue'
    elif 'thunderstorm' in condition.lower():
        return 'blue'
    elif 'snow' in condition.lower():
        return 'white'
    else:
        return 'red'

def get_symbol_for_condition(condition):
    if 'clear sky' in condition.lower():
        return 'circle'
    elif 'mist' in condition.lower():
        return 'square'
    elif 'shower rain' in condition.lower():
        return 'square'
    elif 'thunderstorm' in condition.lower():
        return 'square'
    elif 'snow' in condition.lower():
        return 'diamond'
    else:
        return 'cross'

# User input for starting and ending locations
start_location = input("Enter the starting location: ")
end_location = input("Enter the ending location: ")

start_coord = get_coordinates(start_location)
end_coord = get_coordinates(end_location)

if start_coord is not None and end_coord is not None:
    colors = ['blue', 'red', 'green']
    symbols = ['circle', 'square', 'diamond']

    url = f"https://router.project-osrm.org/route/v1/driving/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}?overview=full&alternatives=3"

    openweathermap_api_key = 'ab108dea362ed6304d6016c0586c5db6'
    google_maps_api_key = 'AIzaSyA0ww23rGFMcYza3W0ws0T02ArWWtKyT1s'

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        routes = data['routes']
        m = folium.Map(location=[start_coord[0], start_coord[1]], zoom_start=8)

        for i, route in enumerate(routes):
            print(f"Route {i + 1}:")
            print(f"Distance: {route['distance'] / 1000} km")
            print(f"Duration: {route['duration'] / 60} minutes")

            # Calculate the duration in HH:MM format
            duration_minutes = route['duration'] / 60
            duration_str = f"{duration_minutes:02} minutes"

            file_name = f"route_coordinates{i + 1}.csv"
            encoded_polyline = route['geometry']
            decoded_coordinates = decode(encoded_polyline)

            color = colors[i % len(colors)]
            symbol = symbols[i % len(symbols)]

            # Get weather data for start and end locations
            start_location = decoded_coordinates[0]
            end_location = decoded_coordinates[-1]
            start_weather_data = get_weather_data(openweathermap_api_key, start_location[0], start_location[1])
            end_weather_data = get_weather_data(openweathermap_api_key, end_location[0], end_location[1])

            # Get traffic duration
            traffic_duration = get_traffic_info(google_maps_api_key, start_location, end_location)

            # Construct the tooltip
            tooltip = f"Route {i + 1}\nDuration: {duration_str}\n"

            # Add the route with the updated tooltip
            folium.PolyLine(locations=decoded_coordinates, color=color, weight=5, opacity=0.7, tooltip=tooltip).add_to(m)

            with open(file_name, mode='w', newline='') as file:
                writer = csv.writer(file)
                for coord in decoded_coordinates:
                    writer.writerow([coord[0], coord[1]])

            start_location = decoded_coordinates[0]
            end_location = decoded_coordinates[-1]

            start_weather_data = get_weather_data(openweathermap_api_key, start_location[0], start_location[1])
            end_weather_data = get_weather_data(openweathermap_api_key, end_location[0], end_location[1])

            traffic_duration = get_traffic_info(google_maps_api_key, start_location, end_location)

            folium.Marker(location=[start_location[0], start_location[1]], tooltip=f"Start Location\nTemperature: {start_weather_data['temp_F']}°F, Conditions: {start_weather_data['conditions']}", icon=folium.Icon(color=color, icon=symbol)).add_to(m)
            folium.Marker(location=[end_location[0], end_location[1]], tooltip=f"End Location\nTemperature: {end_weather_data['temp_F']}°F, Conditions: {end_weather_data['conditions']}\nTraffic Duration: {traffic_duration} (HH:MM)", icon=folium.Icon(color=color, icon=symbol)).add_to(m)

        m.save("route_map.html")
        print("Alternative routes displayed on the map!")
    else:
        print("Error:", response.status_code)
        print(response.text)
else:
    print("Error: Unable to obtain coordinates for the provided locations.")
