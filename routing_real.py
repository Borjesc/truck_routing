import osmnx as ox
import networkx as nx
import requests
import folium
import csv
from shapely.geometry import Point, LineString, MultiLineString
from shapely.ops import nearest_points
from geopy.distance import geodesic

class MapRouter:
    def __init__(self, city_name):
        self.graph = ox.graph_from_place(city_name, network_type="drive_service")  # Consider only main roads
        self.graph_projected = ox.project_graph(self.graph)
        self.node_points = [Point(data['x'], data['y']) for node, data in self.graph.nodes(data=True)]
        self.edge_lines = [LineString([(self.graph.nodes[n1]['x'], self.graph.nodes[n1]['y']), (self.graph.nodes[n2]['x'], self.graph.nodes[n2]['y'])]) for n1, n2 in self.graph.edges()]

    def get_coordinates(self, address):
        base_url = "https://nominatim.openstreetmap.org/search"
        parameters = {"q": address, "format": "json"}
        response = requests.get(base_url, parameters)
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                print(f"Coordinates for {address}: {lat}, {lon}")
                return lat, lon
        return None
    
    def get_nearest_node(self, point):
        point = Point(point[1], point[0])  # Convert (lat, lon) to (lon, lat) for Shapely
        nearest_point = nearest_points(point, MultiLineString(self.edge_lines))[0]
        nearest_node = ox.distance.nearest_nodes(self.graph, nearest_point.x, nearest_point.y)
        return nearest_node
    
    def calculate_custom_route(self, start_point, end_point):
        start_node = self.get_nearest_node(start_point)
        end_node = self.get_nearest_node(end_point)
        
        # Define a custom cost function that considers both distance and number of turns
        def custom_cost(node1, node2, data):
            # Calculate the distance based on edge data
            if 'length' in data:
                distance = data['length']
            else:
                # You can use an alternative approach, such as calculating the geodesic distance
                point1 = Point(self.graph.nodes[node1]['x'], self.graph.nodes[node1]['y'])
                point2 = Point(self.graph.nodes[node2]['x'], self.graph.nodes[node2]['y'])
                distance = geodesic((point1.y, point1.x), (point2.y, point2.x)).meters

            # Calculate the number of turns
            num_turns = 0
            if node1 is not None:
                edge1 = self.graph[node1][node2]
                if 'geometry' in edge1:
                    num_turns = len(edge1['geometry']['coordinates']) - 2

            # You can adjust the weight for the number of turns as needed
            turn_weight = 0.1

            # Calculate the total cost as a combination of distance and turns
            total_cost = distance + turn_weight * num_turns

            return total_cost
        
        # Find the route using the custom cost function
        route = nx.shortest_path(self.graph, start_node, end_node, weight=custom_cost)
        return route
    def calculate_custom_turn_route2(self, start_point, end_point):
        start_node = self.get_nearest_node(start_point)
        end_node = self.get_nearest_node(end_point)
    
        # Define a custom cost function that considers the number of turns and penalizes longer routes
        def custom_cost(node1, node2, data):
            # Calculate the number of turns
            num_turns = 0
            if node1 is not None:
                edge1 = self.graph[node1][node2]
                if 'geometry' in edge1:
                    num_turns = len(edge1['geometry']['coordinates']) - 2

            # Penalize longer distances to maximize turns
            distance_penalty = data['length'] if 'length' in data else 1.0

            # You can adjust the weight for the number of turns and the distance penalty as needed
            turn_weight = 1.0  # High weight for turns
            distance_weight = 0.1  # Low weight for distance

            # Calculate the total cost as a combination of turns and distance penalty
            total_cost = turn_weight * num_turns + distance_weight * distance_penalty

            return total_cost
        
        # Find the route using the custom cost function
        route = nx.shortest_path(self.graph, start_node, end_node, weight=custom_cost)
        return route

    def calculate_route(self, start_point, end_point):
        start_node = self.get_nearest_node(start_point)
        end_node = self.get_nearest_node(end_point)
        route = nx.shortest_path(self.graph, start_node, end_node, weight='length')
        return route

    def visualize_route1(self, route, route_num,output_file="route.html"):
        # Add markers for the start and end points
        folium.Marker([self.graph.nodes[route[0]]['y'], self.graph.nodes[route[0]]['x']], popup="Start").add_to(m)
        folium.Marker([self.graph.nodes[route[-1]]['y'], self.graph.nodes[route[-1]]['x']], popup="End").add_to(m)
        
        # Add the route as a polyline
        route_coords = [(self.graph.nodes[node]['y'], self.graph.nodes[node]['x']) for node in route]
        if route_num == 1:
            folium.PolyLine(locations=route_coords, color='blue', weight=2.5, opacity=1).add_to(m)
        elif route_num == 2:
            folium.PolyLine(locations=route_coords, color='red', weight=2.5, opacity=1).add_to(m)
        elif route_num == 3:
            folium.PolyLine(locations=route_coords, color='green', weight=2.5, opacity=1).add_to(m)
        
        m.save(output_file)

    def calculate_route_with_coordinates(self,route):
            # Get the coordinates of nodes in the route
            coordinates = [self.graph.nodes[node_id] for node_id in route]

            # Extract latitude and longitude from the coordinates
            latitudes = [node['y'] for node in coordinates]
            longitudes = [node['x'] for node in coordinates]

            # Pair latitudes and longitudes together
            route_coordinates = list(zip(latitudes, longitudes))
            return route_coordinates

    def save_coordinates_to_csv(self, route_coordinates, filename):
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Longitude', 'Latitude'])
            writer.writerows(route_coordinates)

# Map Creation
m = folium.Map(location=[36.1880, -94.5400], zoom_start=16)
router = MapRouter("Arkansas, USA")

# start and stop address
start_address = "2000 W University St, Siloam Springs, AR 72761"
end_address = "555 Mckee Dr, Gentry, AR 72761"

# get coordinates
start_point = router.get_coordinates(start_address)
end_point = router.get_coordinates(end_address)

# calculate route
route = router.calculate_route(start_point, end_point)
route2 = router.calculate_custom_route(start_point, end_point)
route3 = router.calculate_custom_turn_route2(start_point, end_point)

# visualize route
router.visualize_route1(route,1)
router.visualize_route1(route2,2)
router.visualize_route1(route3,3)

# get route coordinates
route_coordinates = router.calculate_route_with_coordinates(route)
route_coordinates2 = router.calculate_route_with_coordinates(route2)
route_coordinates3 = router.calculate_route_with_coordinates(route3)



# router.save_coordinates_to_csv(route_coordinates, 'route_coordinates.csv')
router.save_coordinates_to_csv(route_coordinates2, 'route_coordinates2.csv')
# router.save_coordinates_to_csv(route_coordinates3, 'route_coordinates3.csv')
print("done")

