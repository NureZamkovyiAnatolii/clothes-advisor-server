import json
import logging
import os
import requests
from datetime import datetime

def get_weather_at_time(location: str, target_time: str, api_key: str = "9eb8fb241802a2c7631250c97cbe31cd"):
    url = "https://api.openweathermap.org/data/2.5/forecast"
    
    # Параметри запиту
    params = {
        "appid": api_key,
        "q": location,
        "units": "metric"
    }

    # Запит до API
    response = requests.get(url, params=params)
    data = response.json()

    # Перевірка на наявність даних
    if response.status_code != 200 or "list" not in data:
        return f"Помилка отримання даних для {location}."
    
    forecasts = data["list"]
    
    # Перетворення заданого часу в об'єкт datetime
    target_time = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")

    # Перебір прогнозів та пошук найближчого до заданого часу
    for forecast in forecasts:
        forecast_time = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
        if forecast_time == target_time:
            temp = forecast["main"]["temp"]  # Температура
            weather = forecast["weather"][0]["description"]  # Опис погоди
            return f"Погода в {location} на {target_time.strftime('%Y-%m-%d %H:%M:%S')}: {temp}°C, {weather}"
    
    # Якщо точного співпадіння не знайдено, шукаємо найближчий прогноз
    closest_forecast = min(forecasts, key=lambda x: abs(datetime.strptime(x["dt_txt"], "%Y-%m-%d %H:%M:%S") - target_time))
    closest_time = datetime.strptime(closest_forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
    temp = closest_forecast["main"]["temp"]
    weather = closest_forecast["weather"][0]["description"]
    
    return temp, weather

# Завантаження даних з JSON файлу
def load_clothing_weather_conditions():
    base_path = os.path.dirname(__file__)
    full_path = os.path.join(base_path, "weather_recommendations.json")
    logging.info(f"Using file  {full_path}")
    with open(full_path, "r") as file:
        return json.load(file)
    
# Функція для отримання погодних умов для конкретного типу одягу
def get_weather_for_clothing(clothing_type):
    clothing_data = load_clothing_weather_conditions()
    if clothing_type in clothing_data:
        return clothing_data[clothing_type].get("weather", {})
    else:
        return f"❌ Тип одягу '{clothing_type}' не знайдено."

# Отримання значення для погодних умов "broken clouds"
def get_weather_value_for_condition(clothing_type, condition):
    weather_conditions = get_weather_for_clothing(clothing_type)
    if isinstance(weather_conditions, dict) and condition in weather_conditions:
        return weather_conditions[condition]
    else:
        return f"❌ Погода '{condition}' не знайдена для {clothing_type}."

# Приклад використання:
clothing_type = "pants"  # Тут можна змінити тип одягу
condition = "broken clouds"  # Погода, для якої потрібно отримати значення
# Отримання погоди
temp, weather = get_weather_at_time("Kyiv", "2025-07-05 12:00:00")
print(f"Temperature: {temp}, Weather: {weather}")

# Отримуємо значення для "broken clouds"
weather_value = get_weather_value_for_condition(clothing_type, condition)
print(f"Значення для погодних умов '{condition}': {weather_value}")

