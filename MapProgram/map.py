"""
A python program that uses flask and creates an interactive map displaying weather and various other properties/functionality.
Version: 3.11.6
"""
# Import required modules
from flask import Flask, render_template, request, jsonify
import folium
import pandas as pd
import openrouteservice as ors
from ExtractLatLong import extract_lat_lng
from shapely.geometry import Polygon, mapping, MultiPolygon, LineString, Point
import pyproj
import requests
from twilio.rest import Client
import phonenumbers

# Read in OpenRouteService API key from a text file
with open("ors_api_key.txt", "r") as api_file:
    ors_key = api_file.read().strip()
# Creates a client object for ORS API
client = ors.Client(key=ors_key)
# Read in OpenWeatherMap API key from a text file
with open("owm_api_key.txt", "r") as api_file:
    owm_key = api_file.read().strip()
# Read Twilio credentials from a text file
with open("twilio_creds.txt", "r") as twilio_creds:
    account_sid = twilio_creds.readline().strip()
    auth_token = twilio_creds.readline().strip()
# Creates a client object for Twilio API
twilio_client = Client(account_sid, auth_token)
# Initialize Flask App
app = Flask(__name__)

# Read in datasets and establish directory
data = pd.read_csv("UpdatedData.csv")
# Create Variables
nav_marked = False
filtered_data = pd.DataFrame()
flooded = []
error_status = ""
# Function to create a folium map
def create_map(lat=-27.189539, lng=152.9694482):
    global current_map, layer1, layer2
    current_map = folium.Map(location=[lat, lng], zoom_start=12, prefer_canvas=True)
    layer1 = folium.FeatureGroup(name="Closure Markers").add_to(current_map)
    layer2 = folium.FeatureGroup(name="Navigation").add_to(current_map)
    folium.LayerControl().add_to(current_map)

# Create a map when the program is run
create_map()

# Function to render the map within the webpage
@app.route("/map")
def show_map():
    return current_map.get_root().render(), 200, {"Content-Type": "text/html"}

# Function to render login html
@app.route("/", methods=["GET", "POST"])
def login():
    return render_template("login.html")

# Function to render main html
@app.route("/home", methods=["GET", "POST"])
def home():
    global phone_number
    if request.method == "POST":
        phone_number = request.form.get("phoneNumber")
        # Change format of phone number to +61
        phone_number = phone_number.lstrip('0')
        phone_number = "+61" + phone_number
        try:
            # Check if the phone number is valid using phonenumbers library
            parsed_number = phonenumbers.parse(phone_number, None)
            if phonenumbers.is_valid_number(parsed_number) == False:
                phone_number = ""
        except Exception as e:
            print("An error has occured.", str(e))
    return render_template("index.html", map_url="/map")


# Function to add road closure markers to map
def add_markers():
    global flooded
    flooded =[]
    for index, row in filtered_data.iterrows():
        latitude = row["LATITUDE"]
        longitude = row["LONGITUDE"]
        rainfall = row["RAINFALL"] 
        if (rainfall_limit - rainfall) < 10:
            icon = folium.CustomIcon(icon_image="road_warning_icon.png", icon_size=(25, 20))
        else:
            icon = folium.CustomIcon(icon_image="road_closure_icon.png", icon_size=(25, 25))
        marker = folium.Marker(location=[latitude, longitude], icon=icon, popup=row["ADDRESS"].replace(", Queensland, Australia", "") + "\nFlooded:\n(" + str(row["TIME"]) + ")")
        marker.add_to(layer1)
        flood = create_buffer_polygon([latitude, longitude],resolution=2, radius=20)
        flooded.append(flood)

# Function to handle rainfall user input
@app.route("/submit", methods=["GET", "POST"])
def button_submit():
    global filtered_data, rainfall_limit
    if request.method == "POST":
        try:
            rainfall_limit = request.form.get("rainfallAmount")
            rainfall_limit = float(rainfall_limit) -10 # Convert to a numeric type
            filtered_data = data[(data["RAINFALL"] > 25) & (data["RAINFALL"] < rainfall_limit)]
            update_map()
        except Exception as e:
            print("An error has occured.", str(e))
    return render_template("index.html", map_url="/map")

# Function to update map when new rainfall or navigation inputs are submitted
def update_map():
    create_map()
    add_markers()
    if nav_marked == True:  
        calculate_route()

# Function to calculate route and add markers
def calculate_route():  
    global coordinates, start_position, end_position
    avoided_coords = [] 
    route_directions = create_route(avoided_coords, [coordinates[0][::-1], coordinates[1][::-1]]) 
    buffered_route = create_buffer(route_directions) 
    for site_poly in flooded:
        poly = Polygon([list(reversed(coord)) for coord in site_poly])
        if poly.within(buffered_route):
            avoided_coords.append(poly)
            route_directions = create_route(avoided_coords, [coordinates[0][::-1], coordinates[1][::-1]]) 
            buffered_route = create_buffer(route_directions)  
    # Extract distance and duration
    distance = route_directions['features'][0]['properties']['segments'][0]['distance']
    duration = route_directions['features'][0]['properties']['segments'][0]['duration']
    if distance > 1000:
        distance = round(float(distance / 1000), 1)
    hours = duration // 3600
    minutes = (duration % 3600) // 60
    seconds = duration % 60
    time = "{:02d}:{:02d}:{:02d}".format(int(hours), int(minutes), int(seconds))    
    # Extract coordinates from the route resp onse
    coordinate_list = [list(reversed(coord)) for coord in route_directions["features"][0]["geometry"]["coordinates"]]
    # Add a polyline with the coordinates to the map
    line = folium.PolyLine(locations=coordinate_list, color="blue")
    line.add_to(layer2)
    # Add location markers to the map
    start_marker = folium.Marker(location=list(coordinates[0]), popup=start_position, color="green")
    end_marker = folium.Marker(location=list(coordinates[1]), popup=end_position, color="green")
    start_marker.add_to(layer2)
    end_marker.add_to(layer2) 
    layer2.add_to(current_map)
    return distance, time
             
# Function to handle navigation user input
@app.route("/navigation", methods=["GET", "POST"])
def navigation():
    global nav_marked, coordinates, start_position, end_position, phone_number
    error_status = ""
    if request.method == "POST":
        try:
            start_position = request.form.get("startAddress")
            end_position = request.form.get("endAddress")
            # Extract latitude and longitude and initialize default lat & lng between locations
            coordinates = [extract_lat_lng(start_position), extract_lat_lng(end_position)]
            midpoint_lat = (coordinates[0][0] + coordinates[1][0]) / 2
            midpoint_lng = (coordinates[0][1] + coordinates[1][1]) / 2
            if nav_marked == True:
                create_map(midpoint_lat, midpoint_lng)
                add_markers()
            nav_marked = True
            # Get trip distance and time
            distance, time = calculate_route()
            # Get live rainfall data for Moreton Bay
            live_rainfall = get_live_rainfaill()
        except Exception as e:
            print(f"Unable to navigate: {str(e)}")
            error_status = "True"
    try:
        send_message(distance, time, live_rainfall)
    except Exception as e:
        print("Could not send message:", str(e))
    return render_template("index.html", map_url="/map", error_status=error_status)

def send_message(distance, time, live_rainfall):
    global phone_number
    if phone_number:
        # Send a notification using Twilio
        if live_rainfall < 10:
            message = f"Navigation started from {start_position} to {end_position}. Current rainfall is {live_rainfall}mm. The trip distance is {distance}km, and the estimated time is {time}"
        elif live_rainfall > 40:
            message = f"Navigation started from {start_position} to {end_position}. High rainfall of {live_rainfall}mm. Use caution when driving as specific roads may be closed. The trip distance is {distance}km, and the estimated time is {time}"
        else:
            message = f"Navigation started from {start_position} to {end_position}. Moderate rainfall of {live_rainfall}mm. Be careful of water on road. The trip distance is {distance}km, and the estimated time is {time}"
        twilio_client.messages.create(to=phone_number, from_=f"+12512860035", body=message)

# Function to retrieve current rainfall using OpenWeatherMap API
def get_live_rainfaill():
    # Set base url and parameters
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": "Moreton Bay, AU",
        "appid": owm_key}
    # Send a GET request to the API
    response = requests.get(base_url, params=params)
    # Check if successful and retrieve rainfall
    if response.status_code == 200:
        data = response.json()
        rainfall = data.get("rain", {}).get("24h", 0)
        return rainfall
    else:
        return None

# Function to create a buffer around each road closure coordinate
def create_buffer_polygon(point_in, resolution=2, radius=20):
    # Converting between different coordinate systems
    convert = pyproj.Transformer.from_crs("epsg:4326", "epsg:32632")
    convert_back = pyproj.Transformer.from_crs("epsg:32632", "epsg:4326")
    point_in_proj = convert.transform(*point_in)
    point_buffer_proj = Point(point_in_proj).buffer(radius, resolution=resolution) 
    poly_wgs = []
    for point in point_buffer_proj.exterior.coords:
        poly_wgs.append(convert_back.transform(*point))  # Transform back to WGS84
    return poly_wgs

# Function to create route that avoids road closures using ORS API
def create_route(avoided_point_list, coordinates):
    route = {
        "coordinates": coordinates,
        "profile": "driving-car",
        "format": "geojson",
        "preference": "shortest",
        "options": {
            "avoid_polygons": mapping(MultiPolygon(avoided_point_list))}}
    route_directions = client.directions(**route)
    return route_directions


# Function to create a buffer around the route
def create_buffer(route):
    line_tup = []
    for line in route["features"][0]["geometry"]["coordinates"]:
        tup_format = tuple(line)
        line_tup.append(tup_format)

    new_linestring = LineString(line_tup)
    buffered_route = new_linestring.buffer(0.001)
    return buffered_route


if __name__ == "__main__":
    app.run(debug=False)
