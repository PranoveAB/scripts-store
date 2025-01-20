import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

def get_weather():
    # Using a free testing API that doesn't require key
    cities = ['Nairobi', 'New York', 'Tokyo']
    weather_data = []
    
    for city in cities:
        print(f"Getting weather for {city}...")
        url = f"https://goweather.herokuapp.com/weather/{city}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            weather_data.append({
                'city': city,
                'temperature': data.get('temperature', 'N/A'),
                'description': data.get('description', 'N/A'),
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            print(f"{city}: {data.get('temperature', 'N/A')}, {data.get('description', 'N/A')}")
    
    return weather_data

def create_plot(weather_data):
    print("Creating weather plot...")
    df = pd.DataFrame(weather_data)
    
    # Extract numeric temperature values
    df['temp_numeric'] = df['temperature'].str.extract(r'([-\d]+)').astype(float)
    
    # Create plot
    plt.figure(figsize=(10, 6))
    bars = plt.bar(df['city'], df['temp_numeric'])
    plt.title('Current Temperature by City')
    plt.xlabel('City')
    plt.ylabel('Temperature (°C)')
    
    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height}°C',
                ha='center', va='bottom')
    
    # Save plot
    os.makedirs('output', exist_ok=True)
    plt.savefig('output/weather_plot.png')
    print("Plot saved as output/weather_plot.png")

if __name__ == "__main__":
    print("Weather Tracker Starting...")
    print("This script uses matplotlib and pandas - different from signal project!")
    weather_data = get_weather()
    if weather_data:
        create_plot(weather_data)
    print("Weather Tracker Completed!")