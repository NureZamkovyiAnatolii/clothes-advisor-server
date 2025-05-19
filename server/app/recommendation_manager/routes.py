from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import logging
import os
import time
from typing import Optional
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
from sqlalchemy.orm import Session
from app.user_manager import get_current_user, oauth2_scheme
from app.database import get_db
from app.model.сlothing_item import ClothingItem
from app.recommendation_manager.recommendation_strategies import (
    WeatherRecommendationStrategy,
    ColorRecommendationStrategy,
    EventRecommendationStrategy,
    ColorEventStrategy,
    WeatherEventStrategy,
    ColorWeatherStrategy,
    AverageRecommendationStrategy,
)

recommendation_router = APIRouter(tags=["Recommendations"])

def get_weather_at_time_by_coords(lat: float, lon: float, target_time: str, api_key: str = "9eb8fb241802a2c7631250c97cbe31cd"):
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {
        "appid": api_key,
        "lat": lat,
        "lon": lon,
        "units": "metric"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if response.status_code != 200 or "list" not in data:
        return f"❌ Failed to retrieve data for coordinates: ({lat}, {lon})."

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

class RecommendationRequest(BaseModel):
    lat: Optional[float]
    lon: Optional[float]
    target_time: Optional[str]
    red: Optional[str]
    green: Optional[str]
    blue: Optional[str]
    palette_type: Optional[str]
    event: Optional[str]

@recommendation_router.post("/recommendations")
async def get_recommendations(
    data: RecommendationRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    lat = data.lat
    lon = data.lon
    target_time = data.target_time
    red = data.red
    green = data.green
    blue = data.blue
    palette_type = data.palette_type
    event = data.event
    start_total = time.perf_counter()
    logging.info("Starting recommendation process...")

    # === User Authentication Block ===
    start = time.perf_counter()
    user = get_current_user(token, db)
    if user is None or isinstance(user, JSONResponse):
        raise HTTPException(status_code=401, detail="Not authenticated")
    logging.info(f"User authentication took {time.perf_counter() - start:.3f} seconds.")

    # === Color Parsing Block ===
    start = time.perf_counter()
    def parse_color_component(value: Optional[str]) -> Optional[int]:
        try:
            return int(value) if value else None
        except ValueError:
            return None

    r = parse_color_component(red)
    g = parse_color_component(green)
    b = parse_color_component(blue)
    logging.info(f"Color parsing took {time.perf_counter() - start:.3f} seconds.")

    # === Item Fetching Block ===
    start = time.perf_counter()
    items = db.query(ClothingItem).filter(ClothingItem.owner_id == user.id).all()
    if not items:
        return {"detail": "No clothing items found for user.", "data": {}}
    logging.info(f"Fetching items took {time.perf_counter() - start:.3f} seconds.")

    # === Evaluation Block ===
    start = time.perf_counter()
    results = {}
    location = True if lat and lon else False
    temp, weather = get_weather_at_time_by_coords(lat, lon, target_time) if location and target_time else (None, None)
    def evaluate_item(item : ClothingItem):
        item_results = {}
        other_color = (r, g, b) if None not in (r, g, b) else None
        all_fields_filled = all([location, target_time, r is not None, g is not None, b is not None, palette_type, event])

        if location and target_time:
            weather_score = WeatherRecommendationStrategy().evaluate(item, float(temp), weather)
            item_results["final_match"] = weather_score

        if other_color and palette_type:
            color_score = ColorRecommendationStrategy().evaluate(item, other_color, palette_type)
            item_results["final_match"] = color_score

        if event:
            event_score = EventRecommendationStrategy().evaluate(item, event)
            item_results["final_match"] = event_score

        if not all_fields_filled:
            if other_color and palette_type and event:
                score = ColorEventStrategy().evaluate(item, other_color, palette_type, event)
                item_results["final_match"] = {"type": "color_event_match", "result": score}
            if location and target_time and event:
                score = WeatherEventStrategy().evaluate(item, temp, weather, event)
                item_results["final_match"] = {"type": "weather_event_match", "result": score}
            if location and target_time and other_color and palette_type:
                score = ColorWeatherStrategy().evaluate(item, other_color, palette_type, temp, weather)
                item_results["final_match"] = {"type": "color_weather_match", "result": score}

        if all_fields_filled:
            avg_score = AverageRecommendationStrategy().evaluate(item, temp, weather, other_color, palette_type, event)
            item_results["final_match"] = {"type": "average_match", "result": avg_score}

        return item.id, {
            "name": item.name,
            "category": item.category.value,
            **item_results
        }

    # Use ThreadPoolExecutor to evaluate items in parallel
    with ThreadPoolExecutor() as executor:
        futures = executor.map(evaluate_item, items)

    # Collect results
    results = {item_id: result for item_id, result in futures}
    logging.info(f"Evaluation took {time.perf_counter() - start:.3f} seconds.")

    # === Grouping Block ===
    start = time.perf_counter()
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, "clothing_grouping.json")
    with open(full_path, "r", encoding="utf-8") as f:
        grouping = json.load(f)

    def get_category_group(category_name: str, grouping: dict) -> str:
        for group, categories in grouping.items():
            if category_name in categories:
                return group
        return "unknown"

    grouped_items = {"tops": [], "bottoms": [], "outerwear": [], "one_piece": []}
    for item_id, item_data in results.items():
        group = get_category_group(item_data["category"], grouping)
        item_data["group"] = group
        grouped_items.setdefault(group, []).append({**item_data, "id": item_id})
    logging.info(f"Grouping took {time.perf_counter() - start:.3f} seconds.")

    # === Outfit Generation Block ===
    start = time.perf_counter()
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

    for top in grouped_items.get("tops", []):
        for bottom in grouped_items.get("bottoms", []):
            outfits.append({"type": "tops_bottoms", "items": [top["id"], bottom["id"]], "score_avg": average_score(top, bottom)})

    for outer in grouped_items.get("outerwear", []):
        for bottom in grouped_items.get("bottoms", []):
            outfits.append({"type": "outerwear_bottoms", "items": [outer["id"], bottom["id"]], "score_avg": average_score(outer, bottom)})

    for piece in grouped_items.get("one_piece", []):
        outfits.append({"type": "one_piece", "items": [piece["id"]], "score_avg": extract_score(piece)})

    outfits.sort(key=lambda x: x["score_avg"], reverse=True)
    outfits_detail = f"{len(outfits)} outfit(s) generated successfully." if outfits else "No outfit combinations could be generated from your wardrobe."
    logging.info(f"Outfit generation took {time.perf_counter() - start:.3f} seconds.")

    total_duration = time.perf_counter() - start_total
    logging.info(f"\u23f3Request to /recommendations processed in {total_duration:.3f} seconds.")
    if location:
        return {
            "detail": "Recommendations computed successfully.",
            "data": {
                "weather": {
                    "temp": temp,
                    "weather": weather
                },  
                "clothes": results,
                "outfits": {
                    "detail": outfits_detail,
                    "items": outfits
                }
            }
        }
    else:
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
