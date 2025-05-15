from abc import ABC, abstractmethod
from datetime import datetime
import re
import requests

from app.model.сlothing_item import CategoryEnum, ClothingItem, SeasonEnum
from app.recommendation_manager.color_controller import color_match_score
from app.recommendation_manager.myjson import get_nested_value

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
        return evaluate_weather_match(clothing_item,location, target_time)


class ColorRecommendationStrategy(RecommendationStrategy):
    def evaluate(self, clothing_item: ClothingItem, other_color: tuple[int, int, int], palette_type: str):
        return evaluate_color_match(clothing_item,other_color, palette_type)


class EventRecommendationStrategy(RecommendationStrategy):
    def evaluate(self, clothing_item: ClothingItem, event: str):
        return evaluate_event_match(clothing_item,event)


# --- Комбіновані стратегії ---


class ColorEventStrategy(RecommendationStrategy):
    def __init__(self):
        self.color_strategy = ColorRecommendationStrategy(
            )
        self.event_strategy = EventRecommendationStrategy()

    def evaluate(self, clothing_item, other_color, palette_type, event):
        score_color = extract_score(self.color_strategy.evaluate(clothing_item, other_color, palette_type))
        score_event = extract_score(self.event_strategy.evaluate(clothing_item, event))
        if score_color is None or score_event is None:
            return 0
        return (score_color + score_event) / 2


class WeatherEventStrategy(RecommendationStrategy):
    def __init__(self):
        self.weather_strategy = WeatherRecommendationStrategy(
            )
        self.event_strategy = EventRecommendationStrategy()

    def evaluate(self, clothing_item, location, target_time, event):
        score_weather = extract_score(self.weather_strategy.evaluate(clothing_item, location, target_time))
        score_event = extract_score(self.event_strategy.evaluate(clothing_item, event))
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
        score_color = extract_score(self.color_strategy.evaluate(clothing_item, other_color, palette_type))
        score_weather = extract_score(self.weather_strategy.evaluate(clothing_item, location, target_time))
        if score_color is None or score_weather is None:
            return 0
        return (score_weather + score_color) / 2


class AverageRecommendationStrategy(RecommendationStrategy):
    def __init__(self):
        self.weather_strategy = WeatherRecommendationStrategy()
        self.color_strategy = ColorRecommendationStrategy()
        self.event_strategy = EventRecommendationStrategy()

    def evaluate(self, clothing_item, location, target_time, other_color, palette_type, event):
        score_weather = extract_score(self.weather_strategy.evaluate(clothing_item, location, target_time))
        score_color = extract_score(self.color_strategy.evaluate(clothing_item, other_color, palette_type))
        score_event = extract_score(self.event_strategy.evaluate(clothing_item, event))

        scores = [score for score in (score_weather, score_color, score_event) if score is not None]

        if not scores:
            return 0
        return sum(scores) / len(scores)




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
        forecast_time = datetime.strptime(forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
        if forecast_time == target_time_dt:
            temp = forecast["main"]["temp"]
            weather = forecast["weather"][0]["description"]
            return temp, weather

    closest_forecast = min(
        forecasts,
        key=lambda x: abs(datetime.strptime(x["dt_txt"], "%Y-%m-%d %H:%M:%S") - target_time_dt)
    )
    temp = closest_forecast["main"]["temp"]
    weather = closest_forecast["weather"][0]["description"]
    return temp, weather


def evaluate_weather_match(item: ClothingItem, location: str, target_time: str):
    temp, weather = get_weather_at_time(location, target_time)
    if isinstance(temp, str):
        return temp

    clothing_type = item.category.value
    season = item.season.value

    clothing_weather_path = f"{clothing_type}.weather.{weather}"
    season_weather_path = f"{season}.weather.{weather}"
    clothing_temp_range_path = f"{clothing_type}.temperature_range"
    season_temp_range_path = f"{season}.temperature_range"

    clothing_weather = get_nested_value("weather_recommendations.json", clothing_weather_path)
    season_weather = get_nested_value("weather_recommendations.json", season_weather_path)
    clothing_temp_range = get_nested_value("weather_recommendations.json", clothing_temp_range_path)
    season_temp_range = get_nested_value("weather_recommendations.json", season_temp_range_path)

    def merge_temperature_ranges(range1: str, range2: str) -> str:
        def parse_range(r):
            parts = r.replace(" ", "").split("to")
            return int(parts[0]), int(parts[1])

        min1, max1 = parse_range(range1)
        min2, max2 = parse_range(range2)
        return f"{min(min1, min2)} to {max(max1, max2)}"

    def is_temp_in_range(temp: float, temp_range: str) -> bool:
        parts = temp_range.replace(" ", "").split("to")
        min_temp = int(parts[0])
        max_temp = int(parts[1])
        return min_temp <= temp <= max_temp

    if clothing_weather is None or season_weather is None or clothing_temp_range is None or season_temp_range is None:
        return f"❌ Missing data for weather evaluation."

    result = max(clothing_weather, season_weather)
    merged_range = merge_temperature_ranges(clothing_temp_range, season_temp_range)

    if not is_temp_in_range(temp, merged_range):
        result *= TEMPERATURE_MISMATCH_COEF

    return f"✅ Weather match score for '{clothing_type}' in '{weather}': {result}"


def evaluate_color_match(item: ClothingItem, other_color: tuple[int, int, int], palette_type: str):
    color_rgb = (item.red, item.green, item.blue)
    color_score = color_match_score(color_rgb, other_color, palette_type)
    return f"Color match score for {item.category.value} with '{other_color}': {color_score}"


def evaluate_event_match(item: ClothingItem, event: str):
    path = f"{item.category.value}.event.{event}"
    event_match = get_nested_value("event_recommendations.json", path)
    return f"Event match score for {item.category.value} for '{event}': {event_match}"


def main():
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
    target_time = "2025-02-05 12:00:00"
    other_color = (100, 200, 255)
    palette_type = "monochromatic"
    event = "formal_event"

    weather_strategy = WeatherRecommendationStrategy()
    color_strategy = ColorRecommendationStrategy()
    event_strategy = EventRecommendationStrategy()

    print(weather_strategy.evaluate(item, location, target_time))
    print(color_strategy.evaluate(item, other_color, palette_type))
    print(event_strategy.evaluate(item, event))
