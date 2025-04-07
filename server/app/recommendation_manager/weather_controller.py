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
    
    return f"Найближчий прогноз для {location} на {closest_time.strftime('%Y-%m-%d %H:%M:%S')}: {temp}°C, {weather}"

# Приклад використання
location = "Novomoskovsk, ua"
target_time = "2025-03-31 15:00:00"  # Задайте бажану дату та час
print(get_weather_at_time(location, target_time))
