from abc import ABC, abstractmethod
from datetime import datetime
import json
import os
import re
import requests

from app.model.сlothing_item import CategoryEnum, ClothingItem, SeasonEnum

TEMPERATURE_MISMATCH_COEF = 0.6


def extract_score(result: str) -> float | None:
    if not result:
        return None
    matches = re.findall(r"[-+]?[0-9]*\.?[0-9]+", result)
    if matches:
        return float(matches[-1])
    return None


class RecommendationStrategy(ABC):
    @abstractmethod
    def evaluate(self, clothing_item: ClothingItem, **kwargs):
        pass


class WeatherRecommendationStrategy(RecommendationStrategy):
    def evaluate(self, clothing_item: ClothingItem, location: str, target_time: str):
        return clothing_item.evaluate_weather_match(location, target_time)


class ColorRecommendationStrategy(RecommendationStrategy):
    def evaluate(self, clothing_item: ClothingItem, other_color: tuple[int, int, int], palette_type: str):
        return clothing_item.evaluate_color_match(other_color, palette_type)


class EventRecommendationStrategy(RecommendationStrategy):
    def evaluate(self, clothing_item: ClothingItem, event: str):
        return clothing_item.evaluate_event_match(event)


# --- Комбіновані стратегії ---


class ColorEventStrategy(RecommendationStrategy):
    def __init__(self):
        self.color_strategy = ColorRecommendationStrategy(
        )
        self.event_strategy = EventRecommendationStrategy()

    def evaluate(self, clothing_item, other_color, palette_type, event):
        score_color = extract_score(self.color_strategy.evaluate(
            clothing_item, other_color, palette_type))
        score_event = extract_score(
            self.event_strategy.evaluate(clothing_item, event))
        if score_color is None or score_event is None:
            return 0
        return (score_color + score_event) / 2


class WeatherEventStrategy(RecommendationStrategy):
    def __init__(self):
        self.weather_strategy = WeatherRecommendationStrategy(
        )
        self.event_strategy = EventRecommendationStrategy()

    def evaluate(self, clothing_item, location, target_time, event):
        score_weather = extract_score(self.weather_strategy.evaluate(
            clothing_item, location, target_time))
        score_event = extract_score(
            self.event_strategy.evaluate(clothing_item, event))
        if score_weather is None or score_event is None:
            return 0
        return (score_weather + score_event) / 2


class ColorWeatherStrategy(RecommendationStrategy):
    def __init__(self):
        self.color_strategy = ColorRecommendationStrategy(
        )
        self.weather_strategy = WeatherRecommendationStrategy(
        )

    def evaluate(self, clothing_item, other_color, palette_type, location, target_time):
        score_color = extract_score(self.color_strategy.evaluate(
            clothing_item, other_color, palette_type))
        score_weather = extract_score(self.weather_strategy.evaluate(
            clothing_item, location, target_time))
        if score_color is None or score_weather is None:
            return 0
        return (score_weather + score_color) / 2


class AverageRecommendationStrategy(RecommendationStrategy):
    def __init__(self):
        self.weather_strategy = WeatherRecommendationStrategy()
        self.color_strategy = ColorRecommendationStrategy()
        self.event_strategy = EventRecommendationStrategy()

    def evaluate(self, clothing_item, location, target_time, other_color, palette_type, event):
        score_weather = extract_score(self.weather_strategy.evaluate(
            clothing_item, location, target_time))
        score_color = extract_score(self.color_strategy.evaluate(
            clothing_item, other_color, palette_type))
        score_event = extract_score(
            self.event_strategy.evaluate(clothing_item, event))

        scores = [score for score in (
            score_weather, score_color, score_event) if score is not None]

        if not scores:
            return 0
        return sum(scores) / len(scores)


def get_nested_value(filename: str, path: str):
    """
    Отримує вкладене значення з JSON-файлу за шляхом, наприклад: "tshirt.weather.sunny"

    :param filename: Назва JSON-файлу.
    :param path: Шлях до значення через крапку (наприклад: "tshirt.weather.sunny").
    :return: Значення або повідомлення про помилку.
    """
    try:
        base_path = os.path.dirname(__file__)
        full_path = os.path.join(base_path, filename)
        with open(full_path, 'r', encoding='utf-8') as file:

            data = json.load(file)

        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return f"Шлях '{path}' недійсний. Не знайдено ключ: '{key}'"

        return current

    except FileNotFoundError:
        return f"Файл '{filename}' не знайдено."
    except json.JSONDecodeError:
        return f"Файл '{filename}' не є валідним JSON."


def get_weather_at_time(location: str, target_time: str, api_key: str = "9eb8fb241802a2c7631250c97cbe31cd"):
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "appid": api_key,
        "q": location,
        "units": "metric"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code != 200 or "list" not in data:
        return f"❌ Failed to retrieve data for {location}."

    forecasts = data["list"]
    target_time_dt = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")

    for forecast in forecasts:
        forecast_time = datetime.strptime(
            forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
        if forecast_time == target_time_dt:
            temp = forecast["main"]["temp"]
            weather = forecast["weather"][0]["description"]
            return temp, weather

    closest_forecast = min(
        forecasts,
        key=lambda x: abs(datetime.strptime(
            x["dt_txt"], "%Y-%m-%d %H:%M:%S") - target_time_dt)
    )
    temp = closest_forecast["main"]["temp"]
    weather = closest_forecast["weather"][0]["description"]
    return temp, weather


def test():
    item = ClothingItem(
        filename="example.jpg",
        name="Cool Jeans",
        category=CategoryEnum.jeans,
        season=SeasonEnum.winter,
        red=100,
        green=150,
        blue=200,
        material="denim",
        owner_id=1
    )

    location = "Kyiv"
    target_time = "2025-05-18 12:00:00"
    other_color = (100, 200, 255)
    palette_type = "monochromatic"
    event = "formal_event"

    weather_strategy = WeatherRecommendationStrategy()
    color_strategy = ColorRecommendationStrategy()
    event_strategy = EventRecommendationStrategy()

    print(weather_strategy.evaluate(item, location, target_time))
    print(color_strategy.evaluate(item, other_color, palette_type))
    print(event_strategy.evaluate(item, event))
