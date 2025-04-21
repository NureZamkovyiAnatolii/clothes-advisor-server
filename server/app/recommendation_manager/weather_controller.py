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
    logging.info(f"Завантаження файлу з {full_path}")
    with open(full_path, "r") as file:
        return json.load(file)

# Функція для знаходження перехрестя між сезоном та одягом
def get_weather_intersection(season: str, category: str, clothing_conditions: dict):
    """
    Функція повертає перехрестя температур між сезоном та категорією одягу і об'єднує погодні умови.
    Параметри:
        season: сезон (winter, spring, summer, autumn)
        category: категорія одягу (наприклад, tshirt, pants, jacket тощо)
        clothing_conditions: словник, що містить умови для одягу в залежності від сезону.
    """
    # Перевіряємо чи існує даний сезон в словнику
    if season not in clothing_conditions:
        return f"Не знайдено інформації для сезону '{season}'."
    
    season_data = clothing_conditions[season]

    # Перевіряємо чи існує категорія одягу в словнику
    if category not in clothing_conditions:
        return f"Не знайдено інформації для одягу '{category}'."
    
    clothing_data = clothing_conditions[category]

    # Дані по температурі для сезону і одягу
    season_temp_range = season_data["temperature_range"].split(" to ")
    clothing_temp_range = clothing_data["temperature_range"].split(" to ")

    # Перетворення температур у числа
    season_min_temp = int(season_temp_range[0])
    season_max_temp = int(season_temp_range[1])
    
    clothing_min_temp = int(clothing_temp_range[0])
    clothing_max_temp = int(clothing_temp_range[1])

    # Знаходимо перехрестя температур
    intersection_min = min(season_min_temp, clothing_min_temp)
    intersection_max = max(season_max_temp, clothing_max_temp)

    # Якщо перехрестя не існує (коли мінімум більший за максимум)
    if intersection_min > intersection_max:
        return f"Немає перехрестя температур між сезоном '{season}' і одягом '{category}'."

    # Об'єднання погодних умов
    season_weather = season_data["weather"]
    clothing_weather = clothing_data["weather"]
    
    # Видалення можливих дублювань в погодних умовах
    combined_weather = list(set(season_weather + clothing_weather))

    return {
        "temperature_range": f"{intersection_min}°C до {intersection_max}°C",
        "weather": combined_weather
    }

# Основна функція для отримання погодних умов та перевірки одягу
def check_clothing_for_weather(location: str, target_time: str, clothing_conditions: dict, season: str, category: str):
    logging.info(f"Отримання погодних умов для локації: {location} на {target_time}")
    
    # Отримуємо температуру та погоду
    temp, weather = get_weather_at_time(location, target_time)
    
    if isinstance(temp, str):
        logging.error(f"Не вдалося отримати погодні умови для {location} на {target_time}. Помилка: {temp}")
        return False  # Повертаємо False, якщо не вдалося отримати погодні умови
    
    logging.info(f"Отримано погодні умови: Температура {temp}°C, Погода: {weather}")
    
    # Отримуємо підходящий одяг
    result = get_weather_intersection(season, category, clothing_conditions)
    
    if isinstance(result, dict):
        # Перевірка температури
        suitable_weather_conditions = result["weather"]
        weather_conditions_list = weather.split(", ")

        temp_match = (result["temperature_range"].split(" до ")[0].replace("°C", "") <= str(temp) <= result["temperature_range"].split(" до ")[1].replace("°C", ""))
        
        # Перевірка на наявність хоча б однієї спільної умови між одягом і реальною погодою
        weather_match = any(condition in suitable_weather_conditions for condition in weather_conditions_list)

        if temp_match and weather_match:
            logging.info(f"Одяг підходить для локації {location} на {target_time}: Температура: {result['temperature_range']}, Погода: {result['weather']}")
            return True
        else:
            if not temp_match:
                logging.warning(f"Температурний діапазон одягу '{category}' не підходить для температури {temp}°C.")
            if not weather_match:
                logging.warning(f"Погодні умови '{weather}' не підходять для одягу '{category}'.")
            return False
    else:
        logging.error(f"Не вдалося знайти відповідний одяг для сезону '{season}' та категорії '{category}'.")
        return False
# Приклад використання
# location = "Novomoskovsk, ua"
# target_time = "2025-03-31 15:00:00"  # Задайте бажану дату та час
# print(get_weather_at_time(location, target_time))

clothing_conditions = load_clothing_weather_conditions()
# Запит сезон і категорії одягу
season = "summer"
category = "jacket"

result = get_weather_intersection(season, category, clothing_conditions)

if isinstance(result, dict):
    print(f"Перехрестя температур: {result['temperature_range']}")
    print(f"Об'єднані погодні умови: {result['weather']}")
else:
    print(result)


# Приклад використання
# if __name__ == "__main__":
#     clothing_conditions = load_clothing_weather_conditions("server/app/recommendation_manager/weather_recommendations.json")
#     location = "Kyiv"
#     target_time = "2024-07-15 12:00:00"
#     season = "summer"
#     category = "tshirt"
    
#     result = check_clothing_for_weather(location, target_time, clothing_conditions, season, category)
#     print(result)
