Web application that enables users to visualise road closures in the Moreton Bay region based on rainfall amounts and also permits navigation between two locations avoiding all flooded roads on the map. Additionally users can receive notifications displaying various information when navigating, including the route, live rainfall for the Moreton Bay region, trip distance and the trip duration.

To run simply install required libraries and attain relevant API credentials then run "map.py". A url will be displayed in the terminal which will need to be copied into a browser to proceed.

Note that if using a free version account in Twilio, notifications will only be sent to verified phone numbers.

**Prerequisites:**
OpenRouteServices API,
OpenWeatherMap API,
Twilio API,
flask (3.0.0),
folium (0.14.0),
pandas (2.1.0),
openrouteservice (2.3.3),
shapely (2.0.2),
pyproj (3.6.1),
requests (2.31.0),
twilio (8.10.0),
phonenumbers (8.13.24),
