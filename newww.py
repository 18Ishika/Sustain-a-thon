from flask import Flask, render_template, jsonify, redirect, url_for
import requests
from datetime import datetime, timedelta
from shelter_finder import ShelterFinder
from math import radians, sin, cos, sqrt, atan2
from dotenv import load_dotenv
import os

app = Flask(__name__)

# OpenWeatherMap API Key
API_KEY = os.getenv("OPEN_WEATHER_API_KEY")

# Initialize shelter finder
shelter_finder = ShelterFinder()

# Cache for shelter data (reduces API calls)
shelter_cache = {}

# Coastal cities with coordinates
cities = {
    'East Coast': [
        ('Kolkata', 22.5726, 88.3639),
        ('Chennai', 13.0827, 80.2707),
        ('Visakhapatnam', 17.6868, 83.2185),
        ('Paradip', 20.2587, 86.6044),
        ('Puri', 19.8135, 85.8310),
        ('Gopalpur', 19.2876, 84.9333),
        ('Digha', 21.6275, 87.5212),
        ('Balasore', 21.4930, 86.9301),
        ('Pondicherry', 11.9416, 79.8083)
    ],
    'West Coast': [
        ('Mumbai', 19.0760, 72.8777),
        ('Surat', 21.1702, 72.8311),
        ('Goa', 15.2993, 74.1240),
        ('Mangalore', 12.9141, 74.8560),
        ('Kochi', 9.9312, 76.2673),
        ('Kozhikode', 11.2588, 75.7804),
        ('Kannur', 11.8745, 75.3704),
        ('Karwar', 14.7992, 74.1305),
        ('Thiruvananthapuram', 8.5241, 76.9366)
    ]
}

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    R = 6371  # Earth's radius in km
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return round(R * c, 2)

def fetch_weather(city, lat, lon):
    url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if data['cod'] == 200:
            main = data['main']
            weather = data['weather'][0]
            wind = data['wind']
            return {
                'city': city,
                'temp': round(main['temp']),
                'feels_like': round(main['feels_like']),
                'temp_min': round(main['temp_min']),
                'temp_max': round(main['temp_max']),
                'humidity': main['humidity'],
                'pressure': main['pressure'],
                'wind_speed': wind['speed'],
                'wind_deg': wind.get('deg', 0),
                'visibility': data.get('visibility', 0) / 1000,
                'condition': weather['description'],
                'icon': weather['icon'],
                'main': weather['main'],
                'lat': lat,
                'lon': lon
            }
    except Exception as e:
        print(f"Error fetching weather for {city}: {e}")
    return None

def determine_storm_type(humidity, wind_speed, pressure, coast):
    """Determine the type of storm based on conditions"""
    if wind_speed > 25 and pressure < 990:
        return "Severe Cyclonic Storm"
    elif wind_speed > 17 and pressure < 1000:
        return "Tropical Storm"
    elif wind_speed > 12 and humidity > 85:
        return "Thunderstorm with Heavy Rain"
    elif humidity > 80 and wind_speed > 8:
        return "Moderate Thunderstorm"
    else:
        return "Light Rain Showers"

def determine_rainfall_type(humidity, wind_speed):
    """Determine rainfall intensity"""
    if humidity > 90 and wind_speed > 15:
        return "Heavy to Very Heavy Rain (115-204 mm)"
    elif humidity > 85 and wind_speed > 10:
        return "Heavy Rain (64.5-115.5 mm)"
    elif humidity > 75 and wind_speed > 7:
        return "Moderate Rain (35.5-64.4 mm)"
    elif humidity > 65:
        return "Light Rain (2.5-15.5 mm)"
    else:
        return "Very Light Rain (<2.5 mm)"

def get_storm_data(city, coast, weather):
    humidity = weather['humidity']
    wind_speed = weather['wind_speed']
    pressure = weather['pressure']
    
    # Calculate storm probability
    probability = 0
    
    if coast == 'East Coast':
        if humidity >= 85 and wind_speed >= 12:
            probability = min(95, int(humidity * 0.6 + wind_speed * 3.5 + (1010 - pressure) * 0.5))
            risk_level = 'Critical'
            alert_color = '#dc2626'
        elif humidity >= 75 and wind_speed >= 8:
            probability = min(70, int(humidity * 0.4 + wind_speed * 2.5))
            risk_level = 'High'
            alert_color = '#ef4444'
        elif humidity >= 65 and wind_speed >= 5:
            probability = min(45, int(humidity * 0.3 + wind_speed * 1.5))
            risk_level = 'Moderate'
            alert_color = '#f97316'
        else:
            probability = min(25, int(humidity * 0.2 + wind_speed * 0.8))
            risk_level = 'Low'
            alert_color = '#10b981'
    else:  # West Coast
        if humidity >= 90 and wind_speed >= 15:
            probability = min(85, int(humidity * 0.5 + wind_speed * 3 + (1010 - pressure) * 0.4))
            risk_level = 'High'
            alert_color = '#ef4444'
        elif humidity >= 80 and wind_speed >= 10:
            probability = min(60, int(humidity * 0.35 + wind_speed * 2))
            risk_level = 'Moderate'
            alert_color = '#f97316'
        elif humidity >= 70 and wind_speed >= 6:
            probability = min(35, int(humidity * 0.25 + wind_speed * 1.2))
            risk_level = 'Low'
            alert_color = '#eab308'
        else:
            probability = min(15, int(humidity * 0.15 + wind_speed * 0.5))
            risk_level = 'Very Low'
            alert_color = '#10b981'

    storm_type = determine_storm_type(humidity, wind_speed, pressure, coast)
    rainfall_type = determine_rainfall_type(humidity, wind_speed)
    
    # Generate timeline
    now = datetime.now()
    timeline = []
    
    if probability > 70:
        timeline = [
            {'time': now.strftime('%H:%M'), 'event': f'{storm_type}', 'rainfall': rainfall_type},
            {'time': (now + timedelta(hours=3)).strftime('%H:%M'), 'event': 'Peak Storm Activity', 'rainfall': 'Extremely Heavy Rain (>205 mm)'},
            {'time': (now + timedelta(hours=6)).strftime('%H:%M'), 'event': 'Gradual Weakening', 'rainfall': 'Heavy Rain (64.5-115.5 mm)'},
            {'time': (now + timedelta(hours=12)).strftime('%H:%M'), 'event': 'Storm Subsiding', 'rainfall': 'Moderate Rain (35.5-64.4 mm)'},
            {'time': (now + timedelta(hours=24)).strftime('%H:%M'), 'event': 'Clear Conditions Expected', 'rainfall': 'Light Drizzle'}
        ]
    elif probability > 45:
        timeline = [
            {'time': now.strftime('%H:%M'), 'event': f'{storm_type}', 'rainfall': rainfall_type},
            {'time': (now + timedelta(hours=2)).strftime('%H:%M'), 'event': 'Intensifying Conditions', 'rainfall': 'Heavy Rain (64.5-115.5 mm)'},
            {'time': (now + timedelta(hours=6)).strftime('%H:%M'), 'event': 'Peak Wind Activity', 'rainfall': 'Moderate to Heavy Rain'},
            {'time': (now + timedelta(hours=12)).strftime('%H:%M'), 'event': 'Conditions Improving', 'rainfall': 'Light Rain (2.5-15.5 mm)'},
            {'time': (now + timedelta(hours=18)).strftime('%H:%M'), 'event': 'Clearing Up', 'rainfall': 'Scattered Showers'}
        ]
    elif probability > 25:
        timeline = [
            {'time': now.strftime('%H:%M'), 'event': f'{storm_type}', 'rainfall': rainfall_type},
            {'time': (now + timedelta(hours=3)).strftime('%H:%M'), 'event': 'Possible Thunderstorms', 'rainfall': 'Moderate Rain (35.5-64.4 mm)'},
            {'time': (now + timedelta(hours=8)).strftime('%H:%M'), 'event': 'Weather Stabilizing', 'rainfall': 'Light Rain (2.5-15.5 mm)'},
            {'time': (now + timedelta(hours=16)).strftime('%H:%M'), 'event': 'Mostly Clear', 'rainfall': 'Isolated Showers'}
        ]
    else:
        timeline = [
            {'time': now.strftime('%H:%M'), 'event': 'Calm Conditions', 'rainfall': 'No Significant Rain'},
            {'time': (now + timedelta(hours=6)).strftime('%H:%M'), 'event': 'Partly Cloudy', 'rainfall': 'Very Light Rain (<2.5 mm)'},
            {'time': (now + timedelta(hours=12)).strftime('%H:%M'), 'event': 'Stable Weather', 'rainfall': 'No Rain Expected'},
            {'time': (now + timedelta(hours=24)).strftime('%H:%M'), 'event': 'Clear Skies', 'rainfall': 'Dry Conditions'}
        ]

    factors = [
        f"Humidity: {humidity}% {'(Critical)' if humidity > 85 else '(Elevated)' if humidity > 75 else '(Normal)'}",
        f"Wind Speed: {wind_speed} m/s {'(Dangerous)' if wind_speed > 12 else '(Strong)' if wind_speed > 8 else '(Moderate)'}",
        f"Pressure: {pressure} hPa {'(Very Low)' if pressure < 995 else '(Low)' if pressure < 1005 else '(Normal)'}",
        f"Coastal Location: {coast}",
        f"Storm Type: {storm_type}",
        f"Expected Rainfall: {rainfall_type}"
    ]

    recommendations = {
        'Critical': 'URGENT: Evacuate coastal areas immediately. Seek shelter inland. Avoid all travel. Severe storm conditions imminent.',
        'High': 'Secure all loose objects, avoid coastal areas and sea travel. Stay indoors and monitor emergency updates continuously.',
        'Moderate': 'Stay alert and avoid unnecessary travel near coast. Keep emergency supplies ready. Monitor weather updates.',
        'Low': 'Normal precautions. Keep umbrella handy. Avoid prolonged exposure to rain.',
        'Very Low': 'No significant precautions needed. Enjoy your day with minimal weather concerns.'
    }

    return {
        'risk_level': risk_level,
        'alert_color': alert_color,
        'probability': probability,
        'storm_type': storm_type,
        'rainfall_type': rainfall_type,
        'wind_info': 'Strong onshore flow' if coast == 'East Coast' else 'Moderate sea breeze',
        'recommendation': recommendations.get(risk_level, recommendations['Low']),
        'timeline': timeline,
        'factors': factors
    }

def get_shelters(city_name, lat, lon):
    """Get top 4-5 nearest shelters for a city with caching"""
    cache_key = f"{city_name}_{lat:.4f}_{lon:.4f}"
    
    if cache_key in shelter_cache:
        print(f"Using cached shelters for {city_name}")
        return shelter_cache[cache_key]
    
    print(f"Fetching shelters for {city_name}...")
    try:
        shelters = shelter_finder.get_shelters_near_location(lat, lon, radius_km=10)
        
        # Calculate distances from city center for initial sorting only
        for shelter in shelters:
            shelter['distance'] = calculate_distance(lat, lon, shelter['lat'], shelter['lon'])
        
        # Sort by distance and take top 5
        shelters_sorted = sorted(shelters, key=lambda x: x['distance'])[:5]
        
        # Remove distance field - will be calculated client-side
        for shelter in shelters_sorted:
            del shelter['distance']
        
        shelter_cache[cache_key] = shelters_sorted
        print(f"Found {len(shelters_sorted)} nearest shelters for {city_name}")
        return shelters_sorted
    except Exception as e:
        print(f"Error getting shelters for {city_name}: {e}")
        return []

@app.route('/')
def index():
    city_list = []
    for coast, cities_list in cities.items():
        for city, lat, lon in cities_list:
            city_list.append({'name': city, 'coast': coast})
    return render_template('index.html', cities=city_list)

@app.route('/weather/<city>')
def weather_page(city):
    city_data = None
    coast_name = None
    for coast, cities_list in cities.items():
        for c_name, lat, lon in cities_list:
            if c_name.lower() == city.lower():
                city_data = {'name': c_name, 'lat': lat, 'lon': lon}
                coast_name = coast
                break
        if city_data:
            break

    if not city_data:
        return redirect(url_for('index'))

    weather = fetch_weather(city_data['name'], city_data['lat'], city_data['lon'])
    if not weather:
        return redirect(url_for('index'))

    city_list = []
    for coast, cities_list in cities.items():
        for c_name, _, _ in cities_list:
            city_list.append({'name': c_name, 'coast': coast})

    return render_template('weather.html', weather=weather, cities=city_list, selected_city=city)

@app.route('/storm/<city>')
def storm_page(city):
    city_data = None
    coast_name = None
    for coast, cities_list in cities.items():
        for c_name, lat, lon in cities_list:
            if c_name.lower() == city.lower():
                city_data = {'name': c_name, 'lat': lat, 'lon': lon}
                coast_name = coast
                break
        if city_data:
            break

    if not city_data:
        return redirect(url_for('index'))

    weather = fetch_weather(city_data['name'], city_data['lat'], city_data['lon'])
    if not weather:
        return redirect(url_for('index'))

    storm = get_storm_data(city_data['name'], coast_name, weather)
    
    # Get top 4-5 nearest shelters
    shelters = get_shelters(city_data['name'], city_data['lat'], city_data['lon'])

    city_list = []
    for coast, cities_list in cities.items():
        for c_name, _, _ in cities_list:
            city_list.append({'name': c_name, 'coast': coast})

    return render_template('storm.html', weather=weather, storm=storm, shelters=shelters, cities=city_list)

@app.route('/api/weather/<city>')
def get_weather_api(city):
    for coast, cities_list in cities.items():
        for city_name, lat, lon in cities_list:
            if city_name.lower() == city.lower():
                weather = fetch_weather(city_name, lat, lon)
                if weather:
                    weather['coast'] = coast
                    return jsonify(weather)
    return jsonify({'error': 'City not found'}), 404

@app.route('/api/shelters/<city>')
def get_shelters_api(city):
    """API endpoint to get shelters for a city"""
    for coast, cities_list in cities.items():
        for city_name, lat, lon in cities_list:
            if city_name.lower() == city.lower():
                shelters = get_shelters(city_name, lat, lon)
                return jsonify({'shelters': shelters, 'count': len(shelters)})
    return jsonify({'error': 'City not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)