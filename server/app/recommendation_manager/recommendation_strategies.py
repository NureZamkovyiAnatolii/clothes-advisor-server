from abc import ABC, abstractmethod
import json
import os
import re

from app.model.сlothing_item import CategoryEnum, ClothingItem, SeasonEnum

TEMPERATURE_MISMATCH_COEF = 0.6


def extract_score(result: str) -> float | None:
    if not result:
        return None
    matches = re.findall(r"[-+]?[0-9]*\.?[0-9]+", result)
    if matches:
        return float(matches[-1])
    return None

def get_nested_value(filename: str, path: str):
    """
    Retrieves a nested value from a JSON file by a dot-separated path, e.g., "tshirt.weather.sunny".

    :param filename: Name of the JSON file.
    :param path: Dot-separated path to the value (e.g., "tshirt.weather.sunny").
    :return: The value or an error message.
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
                return f"Path '{path}' is invalid. Key not found: '{key}'"

        return current

    except FileNotFoundError:
        return f"File '{filename}' not found."
    except json.JSONDecodeError:
        return f"File '{filename}' is not valid JSON."

class RecommendationStrategy(ABC):
    @abstractmethod
    def evaluate(self, clothing_item: ClothingItem, **kwargs):
        pass


class WeatherRecommendationStrategy(RecommendationStrategy):
    def evaluate(self, clothing_item: ClothingItem, temp: float, weather: str):
        return clothing_item.evaluate_weather_match(temp, weather, TEMPERATURE_MISMATCH_COEF)


class ColorRecommendationStrategy(RecommendationStrategy):
    def evaluate(self, clothing_item: ClothingItem, other_color: tuple[int, int, int], palette_type: str):
        return clothing_item.evaluate_color_match(other_color, palette_type)


class EventRecommendationStrategy(RecommendationStrategy):
    def evaluate(self, clothing_item: ClothingItem, event: str):
        return clothing_item.evaluate_event_match(event)


# --- Combined strategies for different scenarios ---


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

    def evaluate(self, clothing_item, temp, weather, event):
        score_weather = extract_score(self.weather_strategy.evaluate(
            clothing_item, temp, weather))
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

    def evaluate(self, clothing_item, other_color, palette_type, temp, weather):
        score_color = extract_score(self.color_strategy.evaluate(
            clothing_item, other_color, palette_type))
        score_weather = extract_score(self.weather_strategy.evaluate(
            clothing_item, temp, weather))
        if score_color is None or score_weather is None:
            return 0
        return (score_weather + score_color) / 2


class AverageRecommendationStrategy(RecommendationStrategy):
    def __init__(self):
        self.weather_strategy = WeatherRecommendationStrategy()
        self.color_strategy = ColorRecommendationStrategy()
        self.event_strategy = EventRecommendationStrategy()

    def evaluate(self, clothing_item, temp, weather, other_color, palette_type, event):
        score_weather = self.weather_strategy.evaluate(
            clothing_item, temp, weather)
        score_color = self.color_strategy.evaluate(
            clothing_item, other_color, palette_type)
        score_event = self.event_strategy.evaluate(clothing_item, event)

        scores = [score for score in (
            score_weather, score_color, score_event) if score is not None]

        if not scores:
            return 0
        return sum(scores) / len(scores)


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

    lat = 50.4501
    lon = 30.5234
    target_time = "2025-05-18 12:00:00"
    other_color = (100, 200, 255)
    palette_type = "monochromatic"
    event = "formal_event"

    weather_strategy = WeatherRecommendationStrategy()
    color_strategy = ColorRecommendationStrategy()
    event_strategy = EventRecommendationStrategy()

    print(weather_strategy.evaluate(item, lat, lon, target_time))
    print(color_strategy.evaluate(item, other_color, palette_type))
    print(event_strategy.evaluate(item, event))
