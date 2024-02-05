import requests
import folium
import csv
import datetime
from polyline import decode
from geopy.geocoders import Nominatim

def get_current_coordinates():
    # Attempt to get the device's current location based on IP Address
    try:
        response = requests.get("http://ip-api.com/json/")
        ip_data = response.json()
        
        # Extracting latitude and longitude from the response
        latitude = ip_data.get("lat")
        longitude = ip_data.get("lon")
        
        if latitude is not None and longitude is not None:
            return (latitude, longitude)
        else:
            return None
    except Exception as e:
        print(f"Error obtaining current location: {e}")
        return None

def get_coordinates(location=None):
    geolocator = Nominatim(user_agent="osrm_locator", timeout=10)
    if location is None:
        # If no location is provided, fetch the current coordinates based on IP
        return get_current_coordinates()
    else:
        try:
            location_info = geolocator.geocode(location)
            if location_info:
                return (location_info.latitude, location_info.longitude)
            else:
                return None
        except Exception as e:
            print(f"Error geocoding location: {e}")
            return None

def get_weather_data(api_key, lat, lon):
    base_url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'imperial'}  # Use 'imperial' for Fahrenheit

    response = requests.get(base_url, params=params)
    data = response.json()

    # print("Response: ", response)
    # print("_________________________________________")
    # print("Data: ", data)

    if response.status_code == 200:
        temp_fahrenheit = data['main']['temp']
        conditions = data['weather'][0]['description']
        return {'temp_F': temp_fahrenheit, 'conditions': conditions}
    else:
        print(f"Error fetching weather data: {response.status_code}")
        return None

def get_tomtom_traffic_info(api_key, start_coord, end_coord):
    base_url = 'https://api.tomtom.com/routing/1/calculateRoute/{}:{}/json'.format(
        ','.join(map(str, start_coord)), ','.join(map(str, end_coord)))
        
    params = {
        'key': api_key,
        'traffic': 'true',
    }

    try:
        response = requests.get(base_url, params=params)
        data = response.json()

        if response.status_code == 200 and 'routes' in data and data['routes']:
            route = data['routes'][0]
            if 'summary' in route and 'travelTimeInSeconds' in route['summary']:
                duration_in_traffic_seconds = route['summary']['travelTimeInSeconds']
                duration_in_traffic = str(datetime.timedelta(seconds=duration_in_traffic_seconds))
                return duration_in_traffic
        else:
            # Improved error handling to provide more detailed feedback
            error_message = data.get('error', 'No error message provided')
            print(f"Error fetching traffic data: {response.status_code} - {error_message}")
            return None
    except Exception as e:
        print(f"An exception occurred: {e}")
        return None
    
# User input for starting and ending locations
# start_location = input("Enter the starting location: ")
start_location = get_current_coordinates()
end_location = input("Enter the ending location: ")

start_coord = start_location
end_coord = get_coordinates(end_location)

if start_coord is not None and end_coord is not None:
    colors = ['blue', 'red', 'green']
    symbols = ['circle', 'square', 'diamond']

    url = f"https://router.project-osrm.org/route/v1/driving/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}?overview=full&alternatives=3"

    openweathermap_api_key = 'ab108dea362ed6304d6016c0586c5db6'
    tomtom_maps_api_key = 'qCjAkuMA3qAGRWqKp3GnUfrHVMzJjPfO'

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
            traffic_duration = get_tomtom_traffic_info(tomtom_maps_api_key, start_location, end_location)

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

            traffic_duration = get_tomtom_traffic_info(tomtom_maps_api_key, start_location, end_location)

            folium.Marker(location=[start_location[0], start_location[1]], tooltip=f"Start Location\nTemperature: {start_weather_data['temp_F']}°F, Conditions: {start_weather_data['conditions']}", icon=folium.Icon(color=color, icon=symbol)).add_to(m)
            folium.Marker(location=[end_location[0], end_location[1]], tooltip=f"End Location\nTemperature: {end_weather_data['temp_F']}°F, Conditions: {end_weather_data['conditions']}\nTraffic Duration: {traffic_duration} (HH:MM:SS)", icon=folium.Icon(color=color, icon=symbol)).add_to(m)

        # New section to write starting and ending coordinates to a CSV file
        with open('route_data.csv', mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Route ID', 'Start Latitude', 'Start Longitude', 'End Latitude', 'End Longitude'])

            for i, route in enumerate(routes):
                start_location = decode(route['geometry'])[0]
                end_location = decode(route['geometry'])[-1]

                writer.writerow([f'Route_{i + 1}', start_location[0], start_location[1], end_location[0], end_location[1]])

        print("Route start and end coordinates saved to route_data.csv")

        m.save("route_map.html")
        print("Alternative routes displayed on the map!")
    else:
        print("Error:", response.status_code)
        print(response.text)
else:
    print("Error: Unable to obtain coordinates for the provided locations.")
