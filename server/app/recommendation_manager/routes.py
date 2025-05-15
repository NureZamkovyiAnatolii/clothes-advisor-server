from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from app.user_manager import get_current_user
from app.database import get_db
from app.model.сlothing_item import ClothingItem
from fastapi.security import OAuth2PasswordBearer

recommendation_router = APIRouter(tags=["Recommendations"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


from app.recommendation_manager.main import (
    WeatherRecommendationStrategy,
    ColorRecommendationStrategy,
    EventRecommendationStrategy,
    ColorEventStrategy,
    WeatherEventStrategy,
    ColorWeatherStrategy,
    AverageRecommendationStrategy,
)

@recommendation_router.post("/recommendations")
async def get_recommendations(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    location: Optional[str] = Form(None),
    target_time: Optional[str] = Form(None),
    red: Optional[str] = Form(None),
    green: Optional[str] = Form(None),
    blue: Optional[str] = Form(None),
    palette_type: Optional[str] = Form(None),
    event: Optional[str] = Form(None),
):
    user = get_current_user(token, db)
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    def parse_color_component(value: Optional[str]) -> Optional[int]:
        try:
            return int(value) if value is not None and value != "" else None
        except ValueError:
            return None

    r = parse_color_component(red)
    g = parse_color_component(green)
    b = parse_color_component(blue)

    items = db.query(ClothingItem).filter(ClothingItem.owner_id == user.id).all()
    if not items:
        return {"detail": "No clothing items found for user.", "data": {}}

    results = {}

    for idx, item in enumerate(items, start=1):
        item_results = {}

        # Базові стратегії
        if location and target_time:
            weather_strategy = WeatherRecommendationStrategy()
            weather_score = weather_strategy.evaluate(item, location, target_time)
            item_results["weather_match"] = weather_score

        if r is not None and g is not None and b is not None and palette_type:
            other_color = (r, g, b)
            color_strategy = ColorRecommendationStrategy()
            color_score = color_strategy.evaluate(item, other_color, palette_type)
            item_results["color_match"] = color_score

        if event:
            event_strategy = EventRecommendationStrategy()
            event_score = event_strategy.evaluate(item, event)
            item_results["event_match"] = event_score

        # Якщо **хоч один параметр не заповнений** — додаємо комбіновані стратегії
        if not (
            location and target_time and
            r is not None and g is not None and b is not None and
            palette_type and event
        ):
            if r is not None and g is not None and b is not None and palette_type and event:
                color_event_strategy = ColorEventStrategy()
                item_results["color_event_match"] = color_event_strategy.evaluate(item, other_color, palette_type, event)

            if location and target_time and event:
                weather_event_strategy = WeatherEventStrategy()
                item_results["weather_event_match"] = weather_event_strategy.evaluate(item, location, target_time, event)

            if location and target_time and r is not None and g is not None and b is not None and palette_type:
                color_weather_strategy = ColorWeatherStrategy()
                item_results["color_weather_match"] = color_weather_strategy.evaluate(item, other_color, palette_type, location, target_time)

        # Якщо всі параметри заповнені — додаємо лише average_match
        if (
            location and target_time and
            r is not None and g is not None and b is not None and
            palette_type and event
        ):
            average_strategy = AverageRecommendationStrategy()
            avg_score = average_strategy.evaluate(
                item,
                location,
                target_time,
                (r, g, b),
                palette_type,
                event,
            )
            item_results["average_match"] = avg_score

        results[f"item_{idx}"] = {
            "name": item.name,
            "category": item.category.value,
            **item_results
        }

    return {"detail": "Recommendations computed successfully.", "data": results}



