"""
A python program that extracts latitude and longitude from an address
Version: 3.11.6
"""
from urllib.parse import urlencode
import requests
import pandas as pd

# Reads in google API key from text file
with open("google_api_key.txt", "r") as api_file:
    API_KEY = api_file.read().strip()

# Function to extract latitude and longitude given an address
def extract_lat_lng(address, data_type = "json"):
    global API_KEY
    # Defines endpoint and parameters
    endpoint = f"https://maps.googleapis.com/maps/api/geocode/{data_type}"
    params = {"address": address, "key": API_KEY}
    url_params = urlencode(params)
    url = f"{endpoint}?{url_params}" 
    # Makes a request to API
    r = requests.get(url)
    # Checks if request was successful
    if r.status_code not in range(200, 299):
        return {}
    latlng = {}
    # Extract latitude and longitude
    try:
        latlng = r.json()["results"][0]["geometry"]["location"]
    except:
        print("Latitude and longitude not found.")
    return latlng.get("lat"), latlng.get("lng")       