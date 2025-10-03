from flask import Flask, render_template, jsonify, request, redirect, url_for
import requests
from datetime import datetime

app = Flask(__name__)

# OpenWeatherMap API Key
API_KEY = 'd2ba287382664e0b087311e66ebf7d7c'


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

def fetch_weather(city, lat, lon):
    """Fetch weather data from OpenWeatherMap API"""
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

@app.route('/')
def index():
    """Main dashboard home page"""
    city_list = []
    for coast, cities_list in cities.items():
        for city, lat, lon in cities_list:
            city_list.append({
                'name': city,
                'coast': coast,
                'lat': lat,
                'lon': lon
            })
    
    return render_template('index.html', cities=city_list)

@app.route('/weather/<city>')
def weather_page(city):
    """Weather detail page for specific city"""
    # Find city data
    city_data = None
    coast_name = None
    
    for coast, cities_list in cities.items():
        for city_name, lat, lon in cities_list:
            if city_name.lower() == city.lower():
                city_data = {'name': city_name, 'lat': lat, 'lon': lon}
                coast_name = coast
                break
        if city_data:
            break
    
    if not city_data:
        return redirect(url_for('index'))
    
    # Fetch weather data
    weather = fetch_weather(city_data['name'], city_data['lat'], city_data['lon'])
    
    if not weather:
        return redirect(url_for('index'))
    
    weather['coast'] = coast_name
    
    # Get all cities for dropdown
    city_list = []
    for coast, cities_list in cities.items():
        for c_name, c_lat, c_lon in cities_list:
            city_list.append({
                'name': c_name,
                'coast': coast,
                'lat': c_lat,
                'lon': c_lon
            })
    
    return render_template('weather.html', weather=weather, cities=city_list, selected_city=city)

@app.route('/api/weather/<city>')
def get_weather_api(city):
    """API endpoint to get weather for a specific city"""
    for coast, cities_list in cities.items():
        for city_name, lat, lon in cities_list:
            if city_name.lower() == city.lower():
                weather = fetch_weather(city_name, lat, lon)
                if weather:
                    weather['coast'] = coast
                    return jsonify(weather)
    return jsonify({'error': 'City not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)