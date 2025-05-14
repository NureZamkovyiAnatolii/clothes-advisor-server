import os
from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.recommendation_manager.weather_controller import check_clothing_for_weather, get_weather_at_time, load_clothing_weather_conditions
from app.user_manager import get_current_user, oauth2_scheme
from app.recommendation_manager.color_controller import is_color_match
from app.database import get_db
from app.model.сlothing_item import ClothingItem

recommendation_router = APIRouter(
    tags=["Recommendations"]
)

def check_user_clothing_for_weather_and_palette(
        token: str,
        db: Session,
        location: str,
        target_time: str,
        red : int ,
        green : int ,
        blue : int ,
        palette_type: str) -> List[str]:
    """
    Функція отримує користувача по токену, перевіряє всі його речі на відповідність погоді та палітрі кольору.
    
    Параметри:
        token (str): Токен користувача для автентифікації.
        location (str): Місце, для якого потрібно перевірити погодні умови.
        target_time (str): Час, на який перевіряється погода.
        palette_type (str): Тип палітри для перевірки кольору ('monochromatic', 'analogous', 'complementary' тощо).
    
    Повертає:
        List[str]: Список результатів перевірки для кожної речі користувача.
    """
    # Отримуємо користувача по токену
    user = get_current_user(token, db)
    
    # Отримуємо всі речі користувача
    clothing_items = db.query(ClothingItem).filter(
        ClothingItem.owner_id == user.id).all()
    
    # Для кожної речі перевіряємо відповідність погоді та палітрі кольору
    results = []
    for item in clothing_items:
        clothing_conditions = load_clothing_weather_conditions()
        weather_match = check_clothing_for_weather(location, target_time, clothing_conditions, item.season, item.category)
        color = (item.red, item.green, item.blue)  # Отримуємо колір речі
        # Перевіряємо відповідність кольору
        if red is not None and green is not None and blue is not None:
            color = (red, green, blue)
            color_match = is_color_match(color, (red, green, blue), palette_type)  # Наприклад, порівнюємо з білим кольором
        else:
            color_match = True
        
        
        if weather_match and color_match:
            results.append(f"✅ {item.name} підходить по погоді та кольору.")
        else:
            results.append(f"❌ {item.name} не підходить по погоді або кольору.")
    
    return results

@recommendation_router.post("/recommendations")
async def get_recommendations(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    location: str = Form(None), 
    target_time: str = Form(None),
    red: str = Form(None), 
    green: str = Form(None), 
    blue: str = Form(None)):
    """
    Get clothing recommendations based on weather and color preferences.
    """
    red = int(red) if red else None
    green = int(green) if green else None
    blue = int(blue) if blue else None
    # Validate the color values, only if the color is not None
    if red is not None and (red < 0 or red > 255):
        raise HTTPException(status_code=400, detail="Red color value must be between 0 and 255.")
    if green is not None and (green < 0 or green > 255):
        raise HTTPException(status_code=400, detail="Green color value must be between 0 and 255.")
    if blue is not None and (blue < 0 or blue > 255):
        raise HTTPException(status_code=400, detail="Blue color value must be between 0 and 255.")
    else:
        return check_user_clothing_for_weather_and_palette(
            token, db, location, target_time, red, green, blue, palette_type="monochromatic"
        )

from abc import ABC, abstractmethod
from typing import Dict, Any, List


# 🔸 Strategy interface
class RecommendationStrategy(ABC):
    @abstractmethod
    def get_recommendation(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass


# 🔹 Basic strategies (one input factor each)

class ColorPreferenceStrategy(RecommendationStrategy):
    def get_recommendation(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Filter clothes based on the user's preferred color
        pass

class LocationWeatherStrategy(RecommendationStrategy):
    def get_recommendation(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Select clothes based on current weather in the user's location
        pass

class EventTypeStrategy(RecommendationStrategy):
    def get_recommendation(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Recommend based on the event type (formal, casual, sport)
        pass

class DateSeasonStrategy(RecommendationStrategy):
    def get_recommendation(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Recommend based on season derived from the date
        pass


# 🔹 Composite strategies (combined input factors)

class ColorAndLocationStrategy(RecommendationStrategy):
    def get_recommendation(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Combine color preference and weather/location data
        pass

class EventAndSeasonStrategy(RecommendationStrategy):
    def get_recommendation(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Combine event type and seasonal appropriateness
        pass

class FullContextStrategy(RecommendationStrategy):
    def get_recommendation(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Use all parameters: color, location, date, event type
        pass


# 🔹 Strategy context class

class RecommendationContext:
    def __init__(self, strategy: RecommendationStrategy):
        self.strategy = strategy

    def set_strategy(self, strategy: RecommendationStrategy):
        self.strategy = strategy

    def recommend(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self.strategy.get_recommendation(user_data)


# 🔹 Example of strategy selection logic (simplified)

def choose_strategy(user_data: Dict[str, Any]) -> RecommendationStrategy:
    if all(k in user_data for k in ["color", "location", "date", "event"]):
        return FullContextStrategy()
    elif "color" in user_data and "location" in user_data:
        return ColorAndLocationStrategy()
    elif "event" in user_data and "date" in user_data:
        return EventAndSeasonStrategy()
    elif "color" in user_data:
        return ColorPreferenceStrategy()
    elif "location" in user_data:
        return LocationWeatherStrategy()
    elif "event" in user_data:
        return EventTypeStrategy()
    elif "date" in user_data:
        return DateSeasonStrategy()
    else:
        raise ValueError("Insufficient data for recommendation")

# 🔹 Usage example

# user_data = {"color": "red", "location": "Kyiv", "date": "2025-05-10", "event": "work"}
# strategy = choose_strategy(user_data)
# context = RecommendationContext(strategy)
# recommendations = context.recommend(user_data)
