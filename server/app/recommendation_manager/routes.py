import json
import logging
import os
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.user_manager import get_current_user, oauth2_scheme 
from app.database import get_db
from app.model.сlothing_item import ClothingItem
from fastapi.security import OAuth2PasswordBearer
import time

recommendation_router = APIRouter(tags=["Recommendations"])



from app.recommendation_manager.recommendation_strategies import (
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
    start_time = time.perf_counter()
    logging.info("Starting recommendation process...")
    user = get_current_user(token, db)
    if user is None or type(user) is JSONResponse:
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

        if location and target_time:
            weather_strategy = WeatherRecommendationStrategy()
            weather_score = weather_strategy.evaluate(item, location, target_time)
            item_results["final_match"] = weather_score

        if r is not None and g is not None and b is not None and palette_type:
            other_color = (r, g, b)
            color_strategy = ColorRecommendationStrategy()
            color_score = color_strategy.evaluate(item, other_color, palette_type)
            item_results["final_match"] = color_score

        if event:
            event_strategy = EventRecommendationStrategy()
            event_score = event_strategy.evaluate(item, event)
            item_results["final_match"] = event_score

        all_fields_filled = (
            location and target_time and
            r is not None and g is not None and b is not None and
            palette_type and event
        )

        # Додаємо комбіновані стратегії тільки якщо не всі параметри заповнені
        if not all_fields_filled:
            if r is not None and g is not None and b is not None and palette_type and event:
                color_event_strategy = ColorEventStrategy()
                score = color_event_strategy.evaluate(item, other_color, palette_type, event)
                item_results["final_match"] = {"type": "color_event_match", "result": score}

            if location and target_time and event:
                weather_event_strategy = WeatherEventStrategy()
                score = weather_event_strategy.evaluate(item, location, target_time, event)
                item_results["final_match"] = {"type": "weather_event_match", "result": score}

            if location and target_time and r is not None and g is not None and b is not None and palette_type:
                color_weather_strategy = ColorWeatherStrategy()
                score = color_weather_strategy.evaluate(item, other_color, palette_type, location, target_time)
                item_results["final_match"] = {"type": "color_weather_match", "result": score}

        # Додаємо лише average_match якщо всі поля заповнені
        if all_fields_filled:
            average_strategy = AverageRecommendationStrategy()
            avg_score = average_strategy.evaluate(
                item,
                location,
                target_time,
                (r, g, b),
                palette_type,
                event,
            )
            item_results["final_match"] = {"type": "average_match", "result": avg_score}

        results[item.id] = {
            "name": item.name,
            "category": item.category.value,
            **item_results
        }
    # Завантаження JSON один раз
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, "clothing_grouping.json")
    with open(full_path, "r", encoding="utf-8") as f:
        grouping = json.load(f)

    def get_category_group(category_name: str, grouping: dict) -> str:
        for group, categories in grouping.items():
            if category_name in categories:
                return group
        return "unknown"

    # у циклі
    for item_data in results.values():
        group = get_category_group(item_data["category"], grouping)
        logging.info(f"Item {item_data['name']} belongs to group {group}")
    # у циклі
    grouped_items = {
        "tops": [],
        "bottoms": [],
        "outerwear": [],
        "one_piece": []
    }

    for item_id, item_data in results.items():
        group = get_category_group(item_data["category"], grouping)
        item_data["group"] = group
        grouped_items.setdefault(group, []).append({**item_data, "id": item_id})

    # Створення комбінованих наборів
    outfits = []
    def extract_score(item: dict) -> float:
        match = item.get("final_match")
        if isinstance(match, dict):
            return match.get("result", 0.0)
        elif isinstance(match, (int, float)):
            return match
        return 0.0

    def average_score(*items: dict) -> float:
        scores = [extract_score(item) for item in items]
        return sum(scores) / len(scores) if scores else 0.0

    # Комбінація tops + bottoms
    for top in grouped_items.get("tops", []):
        for bottom in grouped_items.get("bottoms", []):
            outfits.append({
                "type": "tops_bottoms",
                "items": [top["id"], bottom["id"]],
                "score_avg": average_score(top, bottom)
            })

    # Комбінація outerwear + bottoms
    for outer in grouped_items.get("outerwear", []):
        for bottom in grouped_items.get("bottoms", []):
            outfits.append({
                "type": "outerwear_bottoms",
                "items": [outer["id"], bottom["id"]],
                "score_avg": average_score(outer, bottom)
            })

    # Одноелементні набори з one_piece
    for piece in grouped_items.get("one_piece", []):
        outfits.append({
            "type": "one_piece",
            "items": [piece["id"]],
            "score_avg": extract_score(piece)
        })
    # Додаємо текстове повідомлення щодо сформованих образів
    outfits_detail = (
        f"{len(outfits)} outfit(s) generated successfully."
        if outfits else
        "No outfit combinations could be generated from your wardrobe."
    )
    outfits.sort(key=lambda x: x["score_avg"], reverse=True)
    duration = time.perf_counter() - start_time
    logging.info(f"⏳Request to /recommendations processed in {duration:.3f} seconds.")

    return {
        "detail": "Recommendations computed successfully.",
        "data": {
            "clothes": results,
            "outfits": {
                "detail": outfits_detail,
                "items": outfits
            }
        }
    }





