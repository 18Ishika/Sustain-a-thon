from flask import Flask, render_template, jsonify, request, redirect, url_for
import requests
from datetime import datetime
import math

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

def get_wind_direction(degrees):
    """Convert wind degrees to compass direction"""
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = round(degrees / 22.5) % 16
    return directions[index]

def calculate_storm_probability(weather_data):
    """Enhanced storm probability calculation with more accurate thresholds"""
    score = 0
    factors = []
    
    # CRITICAL FACTOR 1: Pressure (Most important for storms)
    pressure = weather_data['pressure']
    if pressure < 980:
        score += 50
        factors.append("CRITICAL: Extremely low pressure - severe storm system")
    elif pressure < 995:
        score += 35
        factors.append("Very low atmospheric pressure - strong storm possible")
    elif pressure < 1005:
        score += 20
        factors.append("Low pressure system detected")
    elif pressure < 1010:
        score += 8
        factors.append("Below normal pressure")
    
    # FACTOR 2: Wind Speed (Key indicator)
    wind_speed = weather_data['wind_speed']
    if wind_speed > 20:
        score += 40
        factors.append(f"Very strong winds - {wind_speed} m/s (Potential cyclonic)")
    elif wind_speed > 15:
        score += 25
        factors.append(f"Strong winds - {wind_speed} m/s")
    elif wind_speed > 10:
        score += 12
        factors.append(f"Moderate to strong winds - {wind_speed} m/s")
    elif wind_speed > 7:
        score += 5
        factors.append(f"Moderate winds - {wind_speed} m/s")
    
    # FACTOR 3: Humidity + Pressure combination (Storm indicator)
    humidity = weather_data['humidity']
    if humidity > 90 and pressure < 1005:
        score += 20
        factors.append("High humidity with low pressure - storm conditions")
    elif humidity > 85:
        score += 10
        factors.append(f"Very high humidity - {humidity}%")
    elif humidity > 75:
        score += 5
        factors.append(f"High humidity - {humidity}%")
    
    # FACTOR 4: Active Weather Condition
    condition = weather_data['main'].lower()
    if 'thunderstorm' in condition:
        score += 45
        factors.append("ACTIVE THUNDERSTORM in progress")
    elif 'storm' in condition:
        score += 35
        factors.append("Storm conditions present")
    elif 'rain' in weather_data['condition'].lower() and wind_speed > 10:
        score += 18
        factors.append("Heavy rain with strong winds")
    elif 'rain' in condition:
        score += 8
        factors.append("Rainy conditions")
    
    # FACTOR 5: Temperature anomaly
    temp_diff = abs(weather_data['temp'] - weather_data['feels_like'])
    if temp_diff > 8:
        score += 15
        factors.append("Large temperature variation - unstable atmosphere")
    elif temp_diff > 5:
        score += 8
        factors.append("Temperature variation detected")
    
    # FACTOR 6: Visibility (storms reduce visibility)
    visibility = weather_data['visibility']
    if visibility < 2:
        score += 12
        factors.append(f"Poor visibility - {visibility} km")
    elif visibility < 5:
        score += 6
        factors.append(f"Reduced visibility - {visibility} km")
    
    # Cap at 100
    probability = min(score, 100)
    
    # Determine risk level with more granular thresholds
    if probability < 15:
        risk_level = "Low"
        alert_color = "#10b981"
    elif probability < 35:
        risk_level = "Moderate"
        alert_color = "#f59e0b"
    elif probability < 60:
        risk_level = "High"
        alert_color = "#ef4444"
    else:
        risk_level = "Very High"
        alert_color = "#dc2626"
    
    # Get recommendation
    if probability < 15:
        recommendation = "Weather conditions are favorable. Normal coastal activities can proceed safely."
    elif probability < 35:
        recommendation = "Monitor weather updates regularly. Exercise caution near coastal areas."
    elif probability < 60:
        recommendation = "Storm conditions developing. Avoid coastal areas, secure property, and stay indoors."
    else:
        recommendation = "SEVERE STORM ALERT: Immediate action required. Stay indoors, avoid all coastal areas, emergency supplies ready."
    
    # Wind direction info
    wind_dir = get_wind_direction(weather_data['wind_deg'])
    wind_info = f"Winds from {wind_dir} ({weather_data['wind_deg']}°)"
    
    return {
        'probability': probability,
        'risk_level': risk_level,
        'alert_color': alert_color,
        'factors': factors,
        'recommendation': recommendation,
        'wind_direction': wind_dir,
        'wind_degrees': weather_data['wind_deg'],
        'wind_info': wind_info
    }

def get_nearby_cities_risk(current_city_lat, current_city_lon, current_city_name):
    """Calculate storm risk for nearby coastal cities"""
    nearby_risks = []
    
    for coast, cities_list in cities.items():
        for city_name, lat, lon in cities_list:
            if city_name == current_city_name:
                continue
            
            # Calculate distance
            distance = math.sqrt((lat - current_city_lat)**2 + (lon - current_city_lon)**2) * 111  # rough km
            
            if distance < 500:  # Within 500km
                weather = fetch_weather(city_name, lat, lon)
                if weather:
                    storm_data = calculate_storm_probability(weather)
                    nearby_risks.append({
                        'city': city_name,
                        'lat': lat,
                        'lon': lon,
                        'probability': storm_data['probability'],
                        'risk_level': storm_data['risk_level'],
                        'distance': round(distance),
                        'alert_color': storm_data['alert_color']
                    })
    
    return sorted(nearby_risks, key=lambda x: x['distance'])[:5]  # Top 5 nearest

def get_hourly_forecast(lat, lon):
    """Get next 12 hours forecast using OpenWeatherMap"""
    url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric&cnt=8"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data['cod'] == '200':
            forecasts = []
            for item in data['list'][:4]:
                forecast_time = datetime.fromtimestamp(item['dt'])
                forecasts.append({
                    'time': forecast_time.strftime('%I:%M %p'),
                    'temp': round(item['main']['temp']),
                    'humidity': item['main']['humidity'],
                    'pressure': item['main']['pressure'],
                    'wind_speed': item['wind']['speed'],
                    'condition': item['weather'][0]['description'],
                    'main': item['weather'][0]['main'],
                    'icon': item['weather'][0]['icon']
                })
            return forecasts
    except Exception as e:
        print(f"Error fetching forecast: {e}")
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
    
    weather = fetch_weather(city_data['name'], city_data['lat'], city_data['lon'])
    
    if not weather:
        return redirect(url_for('index'))
    
    weather['coast'] = coast_name
    
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

@app.route('/storm/<city>')
def storm_prediction(city):
    """Storm prediction page for a city"""
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
    
    weather = fetch_weather(city_data['name'], city_data['lat'], city_data['lon'])
    if not weather:
        return redirect(url_for('index'))
    
    # Calculate storm probability
    storm_data = calculate_storm_probability(weather)
    
    # Get hourly forecast
    forecast = get_hourly_forecast(city_data['lat'], city_data['lon'])
    
    # Get nearby cities risk
    nearby_risks = get_nearby_cities_risk(city_data['lat'], city_data['lon'], city_data['name'])
    
    city_list = []
    for coast, cities_list in cities.items():
        for c_name, c_lat, c_lon in cities_list:
            city_list.append({'name': c_name, 'coast': coast})
    
    return render_template('storm.html', 
                         weather=weather,
                         storm=storm_data,
                         forecast=forecast,
                         nearby_risks=nearby_risks,
                         cities=city_list,
                         selected_city=city,
                         coast=coast_name)

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

@app.route('/api/storm/<city>')
def storm_api(city):
    """API endpoint for storm prediction"""
    for coast, cities_list in cities.items():
        for city_name, lat, lon in cities_list:
            if city_name.lower() == city.lower():
                weather = fetch_weather(city_name, lat, lon)
                if weather:
                    storm_data = calculate_storm_probability(weather)
                    forecast = get_hourly_forecast(lat, lon)
                    nearby_risks = get_nearby_cities_risk(lat, lon, city_name)
                    return jsonify({
                        'city': city_name,
                        'current_weather': weather,
                        'storm_prediction': storm_data,
                        'hourly_forecast': forecast,
                        'nearby_risks': nearby_risks
                    })
    return jsonify({'error': 'City not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)