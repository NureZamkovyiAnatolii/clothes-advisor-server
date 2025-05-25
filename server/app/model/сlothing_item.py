import logging
from fastapi import HTTPException
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from app.database import Base  # або твоя база Base, якщо інша

from enum import Enum
from sqlalchemy import Enum as SqlEnum

class SeasonEnum(str, Enum):
    winter = "winter"
    spring = "spring"
    summer = "summer"
    autumn = "autumn"

class CategoryEnum(str, Enum):
    tshirt = "tshirt"  # футболка
    pants = "pants"  # штани
    jacket = "jacket"  # жакет
    dress = "dress"  # сукня
    skirt = "skirt"  # спідниця
    shorts = "shorts"  # шорти
    hoodie = "hoodie"  # худі
    sweater = "sweater"  # светр
    coat = "coat"  # пальто
    blouse = "blouse"  # блуза
    shoes = "shoes"  # взуття
    accessories = "accessories"  # аксесуари
    boots = "boots"  # черевики
    sneakers = "sneakers"  # кросівки
    sandals = "sandals"  # сандалі
    hat = "hat"  # капелюх
    scarf = "scarf"  # шарф
    gloves = "gloves"  # рукавички
    socks = "socks"  # носки
    underwear = "underwear"  # білизна
    swimwear = "swimwear"  # купальник
    belt = "belt"  # ремінь
    bag = "bag"  # сумка
    watch = "watch"  # годинник
    jeans = "jeans"  # джинси
    leggings = "leggings"  # легінси
    tank_top = "tank_top"  # майка
    overalls = "overalls"  # комбінезон
    beanie = "beanie"  # шапка


class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False)  # шлях до фото
    name = Column(String(100), nullable=False)  # назва одягу
    category = Column(SqlEnum(CategoryEnum), nullable=False)  # категорія (головний убір тощо)
    season = Column(SqlEnum(SeasonEnum), nullable=False)  # сезонність

    red = Column(Integer, nullable=True)  # червоний компонент (0-255)
    green = Column(Integer, nullable=True)  # зелений компонент (0-255)
    blue = Column(Integer, nullable=True)  # синій компонент (0-255)

    material = Column(String(50), nullable=False)  # матеріал

    brand = Column(String(100), nullable=True)  # опційне поле
    purchase_date = Column(Date, nullable=True)  # дата придбання (опційно)
    price = Column(Float, nullable=True)  # вартість (опційно)
    is_favorite = Column(Boolean, default=False, nullable=False)  # чи є улюбленим
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User")

    combinations = relationship( 
        "ClothingCombination",
        secondary="clothing_combination_items",
        back_populates="items",
        cascade="all, delete"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        if self.season not in SeasonEnum.__members__:
            raise HTTPException(status_code=400, detail=f"Invalid season value: {self.season}")
        
        if self.category not in CategoryEnum.__members__:
            raise HTTPException(status_code=400, detail=f"Invalid category value: {self.category}")
        
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,  # Якщо це enum, потрібно додавати `.value`
            "season": self.season.value,
            "material": self.material,
            "brand": self.brand,
            "price": self.price,
            "is_favorite": self.is_favorite,
            "filename": self.filename,
            "red": self.red,
            "green": self.green,
            "blue": self.blue,
            "purchase_date": self.purchase_date.strftime('%Y-%m-%d') if self.purchase_date else None
        }
    
    def evaluate_color_match(self, other_color: tuple[int, int, int], palette_type: str):
        from app.recommendation_manager.color_controller import color_match_score
        color_rgb = (self.red, self.green, self.blue)
        color_score = color_match_score(color_rgb, other_color, palette_type)
        return f"Color match score for {self.category.value} with '{other_color}': {color_score}"


    def evaluate_event_match(self, event: str):
        from app.recommendation_manager.recommendation_strategies import get_nested_value
        path = f"{self.category.value}.event.{event}"
        event_match = get_nested_value("event_recommendations.json", path)
        return f"Event match score for {self.category.value} for '{event}': {event_match}"
    
    def evaluate_weather_match(self, temp:float,weather, temperature_mismatch: float):
        from app.recommendation_manager.recommendation_strategies import  get_nested_value
        clothing_weather_path = f"{self.category.value}.weather.{weather}"
        season_weather_path = f"{self.season.value}.weather.{weather}"
        clothing_temp_range_path = f"{self.category.value}.temperature_range"
        season_temp_range_path = f"{self.season.value}.temperature_range"

        clothing_weather = get_nested_value("weather_recommendations.json", clothing_weather_path)
        season_weather = get_nested_value("weather_recommendations.json", season_weather_path)
        clothing_temp_range = get_nested_value("weather_recommendations.json", clothing_temp_range_path)
        season_temp_range = get_nested_value("weather_recommendations.json", season_temp_range_path)
        logging.debug(f"Clothing weather: {clothing_weather}, Season weather: {season_weather}, ")
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
            temp = float(temp)
            return min_temp <= temp <= max_temp

        if clothing_weather is None or season_weather is None or clothing_temp_range is None or season_temp_range is None:
            return f"❌ Missing data for weather evaluation."

        result = max(clothing_weather, season_weather)
        merged_range = merge_temperature_ranges(clothing_temp_range, season_temp_range)

        if not is_temp_in_range(temp, merged_range):
            result *= temperature_mismatch

        return result


