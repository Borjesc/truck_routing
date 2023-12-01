import math
import pandas as pd
import networkx as nx
from scipy.spatial import distance as sp_distance
from scipy.spatial import distance_matrix
from python_tsp.heuristics import solve_tsp_simulated_annealing
from geopy.distance import geodesic
import requests
import folium
import os

# API keys
openweathermap_api_key = 'ab108dea362ed6304d6016c0586c5db6'
google_maps_api_key = 'AIzaSyA0ww23rGFMcYza3W0ws0T02ArWWtKyT1s'

# Weather API function
def get_weather_data(api_key, lat, lon):
    base_url = 'http://api.openweathermap.org/data/2.5/weather'
    params = {'lat': lat, 'lon': lon, 'appid': api_key, 'units': 'metric'}  # Using metric units for temperature

    response = requests.get(base_url, params=params)
    data = response.json()

    if response.status_code == 200:
        temp_celsius = data['main']['temp']
        temp_fahrenheit = (temp_celsius * 9/5) + 32  # Convert Celsius to Fahrenheit
        return {'temp_C': temp_celsius, 'temp_F': temp_fahrenheit, 'conditions': data['weather'][0]['description']}
    else:
        print(f"Error fetching weather data: {response.status_code}")
        return None

# Function to get traffic information from Google Maps API
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

        # Check if 'duration_in_traffic' is present in the response
        if 'legs' in route and route['legs'] and 'duration' in route['legs'][0]:
            duration_in_traffic = route['legs'][0]['duration']['value'] // 60  # in minutes
            return duration_in_traffic
    else:
        print(f"Error fetching traffic data: {response.status_code}")
        return None

# Function to check route suitability based on weather
def is_route_suitable(weather_conditions):
    # Add your criteria for determining if the route is suitable for extreme weather
    unsuitable_conditions = ["snow", "mist", "shower rain", "thunderstorm"]
    for condition in unsuitable_conditions:
        if condition.lower() in weather_conditions.lower():
            return False
    return True

# Define the CSV file paths
csv_file_paths = [
    "route_coordinates.csv",
    "route_coordinates2.csv",
    "route_coordinates3.csv",
]

# Initialize variables to store the best route and its distance
best_distance = float('inf')
best_route = None
best_file = None

# Iterate over the CSV file paths
for file in csv_file_paths:
    # Load the data from the current CSV file
    all_data = pd.read_csv(file)

    if "Latitude" in all_data.columns and "Longitude" in all_data.columns:
        # Create an empty graph
        G = nx.Graph()

        # Iterate over the rows in the data
        for i, row in all_data.iterrows():
            # Check if the row contains latitude and longitude values
            if not math.isnan(row['Latitude']) and not math.isnan(row['Longitude']):
                # Add the node to the graph and set its position
                lat = row['Latitude']
                lon = row['Longitude']
                G.add_node(i, pos=(lat, lon))

        # Add edges to the graph based on distance between nodes
        for i, row1 in all_data.iterrows():
            for j, row2 in all_data.iterrows():
                if i != j and not math.isnan(row1['Latitude']) and not math.isnan(row1['Longitude']) \
                        and not math.isnan(row2['Latitude']) and not math.isnan(row2['Longitude']):
                    # Calculate the distance between the two nodes
                    dis = sp_distance.euclidean((row1['Latitude'], row1['Longitude']),
                                                (row2['Latitude'], row2['Longitude']))
                    # Add the edge to the graph with the weight equal to the distance
                    G.add_edge(i, j, weight=dis)

        # Get the distance matrix for reachable nodes
        reachable_nodes = list(G.nodes)
        coordinates = [list(G.nodes[node]['pos']) for node in reachable_nodes]
        dist_matrix = distance_matrix(coordinates, coordinates)

        # Solve the TSP problem for the best route using simulated annealing
        permutation, distance = solve_tsp_simulated_annealing(dist_matrix)

        start_coord = (all_data.iloc[reachable_nodes[0]]['Latitude'], all_data.iloc[reachable_nodes[0]]['Longitude'])
        end_coord = (all_data.iloc[reachable_nodes[-1]]['Latitude'], all_data.iloc[reachable_nodes[-1]]['Longitude'])
        start_weather = get_weather_data(openweathermap_api_key, start_coord[0], start_coord[1])['conditions']
        end_weather = get_weather_data(openweathermap_api_key, end_coord[0], end_coord[1])['conditions']
        route_conditions = start_weather + " to " + end_weather

        #print(route_conditions)

        if is_route_suitable(route_conditions):
            # Fetch traffic information for the current route
            traffic_duration = get_traffic_info(google_maps_api_key, start_coord, end_coord)

            traffic_duration = (traffic_duration - 1)
            traffic_duration += (traffic_duration * 0.15)
            
            if traffic_duration is not None:
                #print(f"Estimated traffic time: {traffic_duration} minutes")

                # Check if the current route is the best so far
                if distance < best_distance:
                    best_distance = distance
                    best_route = [reachable_nodes[i] for i in permutation]
                    best_file = file
    
        if not is_route_suitable(route_conditions):

            # Fetch traffic information for the current route
            traffic_duration = get_traffic_info(google_maps_api_key, start_coord, end_coord)

            traffic_duration = (traffic_duration - 1)
            traffic_duration += (traffic_duration * 0.15)

            if traffic_duration is not None:
                #print(f"Estimated traffic time: {traffic_duration} minutes")

                # Check if the current route is the best so far
                if distance < best_distance:
                    best_distance = distance
                    best_route = [reachable_nodes[i] for i in permutation]
                    best_file = file

# Display the CSV file with the best route
#print(f"The best route is in the file {best_file}")

# Load coordinates from the best CSV file
coordinates_data = pd.read_csv(best_file)

# Update weather data for each coordinate in the route
weather_data_list = []
traffic_data_list = []

# Display menu options
print("Select a route to display:")
for i, file_path in enumerate(csv_file_paths, start=1):
    print(f"{i}. {os.path.basename(file_path)}")

# Allow the user to choose a route
while True:
    try:
        print("\n")
        user_choice = int(input("Enter the route number (0 to reveal the best route): "))
        if 0 <= user_choice <= len(csv_file_paths):
            break
        else:
            print("\nInvalid choice. Please enter a valid route number.\n")
    except ValueError:
        print("\nInvalid input. Please enter a valid route number.\n")

# Check if the user wants to reveal the best route
if user_choice == 0:
    print(f"\nThe best route is in the file {best_file}\n")
    print(f"Displaying route from file: {os.path.basename(best_file)}\n")

    coordinates_data = pd.read_csv(best_file)
else:
    # Display the chosen route
    chosen_file = csv_file_paths[user_choice - 1]
    print(f"\nDisplaying route from file: {os.path.basename(chosen_file)}\n")

    # Load the data from the chosen CSV file
    coordinates_data = pd.read_csv(chosen_file)

for i, row in coordinates_data.iterrows():
    if not math.isnan(row['Latitude']) and not math.isnan(row['Longitude']):
        # Fetch weather data for the current coordinate
        weather = get_weather_data(openweathermap_api_key, row['Latitude'], row['Longitude'])

        # Fetch traffic data for the current coordinate
        traffic_duration = get_traffic_info(google_maps_api_key, start_coord, (row['Latitude'], row['Longitude']))

        # Append weather and traffic data to the lists
        if weather and traffic_duration is not None:
            weather_data_list.append(weather)
            traffic_data_list.append(traffic_duration)

# Add traffic and weather data to the original DataFrame
weather_df = pd.DataFrame(weather_data_list)
traffic_df = pd.DataFrame({'Traffic_Duration': traffic_data_list})
coordinates_data = pd.concat([coordinates_data, traffic_df, weather_df], axis=1)

# Create a Folium map centered around the starting point
map_center = [coordinates_data['Latitude'].iloc[0], coordinates_data['Longitude'].iloc[0]]
mymap = folium.Map(location=map_center, zoom_start=14)

# Plot the route on the map
folium.PolyLine(
    locations=coordinates_data[['Latitude', 'Longitude']].values,
    color='red',
    weight=4,
    opacity=0.8
).add_to(mymap)

# Define a function to get marker color based on weather condition
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

# Define a function to get marker symbol based on weather condition
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

# Calculate total distance
total_distance = 0
for i in range(len(coordinates_data) - 1):
    coord1 = (coordinates_data.iloc[i]['Latitude'], coordinates_data.iloc[i]['Longitude'])
    coord2 = (coordinates_data.iloc[i + 1]['Latitude'], coordinates_data.iloc[i + 1]['Longitude'])
    total_distance += geodesic(coord1, coord2).kilometers

# Display estimated travel time
average_speed = 55  # Assuming average_speed is in km
total_distance_miles = total_distance * 0.621371  # Convert from kilometers to miles
time_without_traffic_hours = total_distance_miles / average_speed
hours_without_traffic = int(time_without_traffic_hours)
minutes_without_traffic = (time_without_traffic_hours - hours_without_traffic) * 60

#print(f"Estimated travel time without traffic: {hours_without_traffic} hours and {minutes_without_traffic:.2f} minutes.")

# Incorporate traffic time into the overall estimated travel time
total_time_with_traffic = time_without_traffic_hours + traffic_duration / 60  # Convert traffic duration to hours
hours_with_traffic = int(total_time_with_traffic)
minutes_with_traffic = (total_time_with_traffic - hours_with_traffic) * 60

# Get color and symbol based on weather condition
color = get_color_for_condition(weather['conditions'])
symbol = get_symbol_for_condition(weather['conditions'])

block_executed = False

if color == 'blue' or color == 'white' and not block_executed:
    if hours_with_traffic >= 1:
        hours_with_traffic += (hours_with_traffic * 0.15)
        minutes_with_traffic = (minutes_with_traffic - 1)
        minutes_with_traffic += (minutes_with_traffic * 0.15)
    
    if hours_with_traffic < 1:
        minutes_with_traffic = (minutes_with_traffic - 1)
        minutes_with_traffic += (minutes_with_traffic * 0.15)

    block_executed = True

# Display markers with weather and traffic information
for i, row in coordinates_data.iterrows():
    if not math.isnan(row['Latitude']) and not math.isnan(row['Longitude']):
        # Fetch weather data for the current coordinate
        weather = get_weather_data(openweathermap_api_key, row['Latitude'], row['Longitude'])
        # Fetch traffic data for the current coordinate
        traffic_duration = get_traffic_info(google_maps_api_key, start_coord, (row['Latitude'], row['Longitude']))

        # Create a marker for weather and traffic information
        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=f"Temperature: {weather['temp_C']:.2f}°C / {weather['temp_F']:.2f}°F\n\n"
                    f"Weather: {weather['conditions']}\n\n"
                    f"Traffic: {traffic_duration} minutes\n"
                    f"Best File: {best_file}\n"
                    f"Estimated Travel Time: {hours_with_traffic} hours and {minutes_with_traffic:.2f} minutes",
            icon=folium.Icon(color=color, icon=symbol),
        ).add_to(mymap)

# Save the map as an HTML file
mymap.save("best_route_map.html")
