import requests
import folium
from polyline import decode
import csv

start_coord = (-94.554382, 36.187222)
end_coord = (-94.148018, 36.128029)
colors = ['blue', 'red', 'green']  # Different colors for routes

# URL for the OSRM routing API
url = f"https://router.project-osrm.org/route/v1/driving/{start_coord[0]},{start_coord[1]};{end_coord[0]},{end_coord[1]}?overview=full&alternatives=3"

# Sending GET request to the OSRM server
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    routes = data['routes']
    # Create a Folium map centered on the route
    m = folium.Map(location=[start_coord[1], start_coord[0]], zoom_start=8)

    for i, route in enumerate(routes):
        file_name = f"route_coordinates{i + 1}.csv"  # Filename with route number
        encoded_polyline = route['geometry']
        decoded_coordinates = decode(encoded_polyline)
        # Use different color for each route
        folium.PolyLine(locations=decoded_coordinates, color=colors[i], weight=5, opacity=0.7, tooltip=f"Route {i+1}").add_to(m)

        # Open a CSV file in write mode for the current route
        with open(file_name, mode='w', newline='') as file:
            writer = csv.writer(file)
            
            # Write coordinates to the CSV file
            for coord in decoded_coordinates:
                writer.writerow([coord[0], coord[1]])  # Writing latitude and longitude to each row in CSV

        print(f"Coordinates of route {i + 1} saved to '{file_name}'!")

    # Save the map to an HTML file or display it
    m.save("route_map.html")
    print("Alternative routes displayed on the map!")
else:
    print("Error:", response.status_code)
    print(response.text)  # Print the error message if any