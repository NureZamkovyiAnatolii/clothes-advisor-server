from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import logging
import os
import random
import time
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
from sqlalchemy.orm import Session
from app.user_manager import get_current_user, oauth2_scheme
from app.database.database import get_db
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
from app.constants import SERVER_URL, UPLOAD_DIR, OPEN_WEATHER_API_KEY
UNFAVORITE_NERF_COEF = 0.8
recommendation_router = APIRouter(tags=["Recommendations"])


def get_weather_at_time_by_coords(lat: float, lon: float, target_time: str, api_key: str = OPEN_WEATHER_API_KEY):
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
        forecast_time = datetime.strptime(
            forecast["dt_txt"], "%Y-%m-%d %H:%M:%S")
        if forecast_time == target_time_dt:
            temp = forecast["main"]["temp"]
            weather = forecast["weather"][0]["description"]
            icon = forecast["weather"][0]["icon"] if "icon" in forecast["weather"][0] else "None"
            code = forecast["weather"][0].get("id", -1)
            return temp, weather, icon, code

    closest_forecast = min(
        forecasts,
        key=lambda x: abs(datetime.strptime(
            x["dt_txt"], "%Y-%m-%d %H:%M:%S") - target_time_dt)
    )
    logging.info(
        f"Closest forecast found for {closest_forecast['dt_txt']} with temperature {closest_forecast['main']['temp']}°C.")
    temp = closest_forecast["main"]["temp"]
    weather = closest_forecast["weather"][0]["description"]
    icon = closest_forecast["weather"][0]["icon"] if "icon" in closest_forecast["weather"][0] else "None"
    code = closest_forecast["weather"][0].get("id", -1)
    logging.info(f"Weather code: {code}")
    return temp, weather, icon, code


class RecommendationRequest(BaseModel):
    lat: Optional[float]
    lon: Optional[float]
    target_time: Optional[str]
    red: Optional[str]
    green: Optional[str]
    blue: Optional[str]
    palette_types: Optional[Union[str, List[str]]]
    event: Optional[str]
    include_favorites: Optional[bool] = False


@recommendation_router.post("/recommendations")
async def get_recommendations(
    data: RecommendationRequest,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    lat, lon, target_time = data.lat, data.lon, data.target_time
    red, green, blue = data.red, data.green, data.blue
    palette_types = data.palette_types or [""]
    event = data.event
    include_favorites = data.include_favorites

    start_total = time.perf_counter()
    logging.info("Starting recommendation process...")

    user = get_current_user(token, db)
    if user is None or isinstance(user, JSONResponse):
        raise HTTPException(status_code=401, detail="Not authenticated")

    def parse_color_component(value: Optional[str]) -> Optional[int]:
        try:
            return int(value) if value else None
        except ValueError:
            return None

    r, g, b = parse_color_component(red), parse_color_component(green), parse_color_component(blue)
    other_color = (r, g, b) if None not in (r, g, b) else None
    location = True if lat and lon else False
    temp, weather, icon, code = get_weather_at_time_by_coords(lat, lon, target_time) if location and target_time else (None, None, None,None)

    items = db.query(ClothingItem).filter(ClothingItem.owner_id == user.id).all()
    if not items:
        return {"detail": "No clothing items found for user.", "data": {}}

    
    outfits = []
    for palette_type in palette_types:
        def evaluate_item(item: ClothingItem):
            item_results = {}
            all_fields_filled = all([location, target_time, r is not None, g is not None, b is not None, palette_type, event])

            if location and target_time:
                weather_score = WeatherRecommendationStrategy().evaluate(item, float(temp), weather)
                item_results["final_match"] = {"type": "weather_match", "result": weather_score}

            if other_color and palette_type:
                color_score = ColorRecommendationStrategy().evaluate(item, other_color, palette_type)
                item_results["final_match"] =  {"type": "color_match", "result": color_score}

            if event:
                event_score = EventRecommendationStrategy().evaluate(item, event)
                item_results["final_match"] =  {"type": "event_match", "result": event_score}

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

            # Apply nerf
            if include_favorites and not item.is_favorite:
                match = item_results.get("final_match")
                if isinstance(match, dict) and "result" in match:
                    match["result"] *= UNFAVORITE_NERF_COEF
                elif isinstance(match, (int, float)):
                    item_results["final_match"] *= UNFAVORITE_NERF_COEF

            return item.id, {
                "name": item.name,
                "category": item.category.value,
                "image": f"{SERVER_URL}/{UPLOAD_DIR}/{item.filename}",
                "is_favorite": f"{item.is_favorite}",
                **item_results
            }

        # Parallel evaluation of items
        with ThreadPoolExecutor() as executor:
            futures = executor.map(evaluate_item, items)
            

        results = {item_id: result for item_id, result in futures}
        formatted_json = json.dumps(results, indent=4, ensure_ascii=False)
        logging.info(f"📦 Evaluated items:\n{formatted_json}")
        # grouping categories
        base_path = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_path, "clothing_grouping.json")
        with open(full_path, "r", encoding="utf-8") as f:
            grouping = json.load(f)

        def get_category_group(category_name: str, grouping: dict) -> str:
            for group, categories in grouping.items():
                if category_name in categories:
                    return group
            return "unknown"

        grouped_items = {
            "tops": [], 
            "bottoms": [], 
            "outerwear": [], 
            "one_piece": [],
            "footwear": [],
            "headwear": [],
            "accessories": [],
            "underwear": []
        }
        optional_groups = ["footwear", "headwear", "accessories", "underwear"]
        def extend_with_optional_groups(base_items: list, grouped_items: dict, optional_groups: list) -> list:
            extended = base_items.copy()
            for group in optional_groups:
                items = grouped_items.get(group)
                if items:
                    # Filter items with score >= 0.7
                    good_items = [item for item in items if extract_score(item) >= 0.7]
                    logging.info(f"Good items in {group}: {good_items}")
                    if len(good_items) >= 2:
                        # Choose random item with score >= 0.7
                        chosen_item = random.choice(good_items)
                    else:
                        # Else the best item with the highest score
                        chosen_item = max(items, key=extract_score)
                    extended.append(chosen_item)
            return extended

        
        for item_id, item_data in results.items():
            group = get_category_group(item_data["category"], grouping)
            item_data["group"] = group
            grouped_items.setdefault(group, []).append({**item_data, "id": item_id})

        # creating outfits

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
                base_items = [top, bottom]
                full_outfit = extend_with_optional_groups(base_items, grouped_items, optional_groups)
                outfits.append({
                    "type": "tops_bottoms",
                    "items": full_outfit,
                    "score_avg": average_score(top, bottom),
                    "palette_type": palette_type
                })

        for outer in grouped_items.get("outerwear", []):
            for bottom in grouped_items.get("bottoms", []):
                base_items = [outer, bottom]
                full_outfit = extend_with_optional_groups(base_items, grouped_items, optional_groups)
                outfits.append({
                    "type": "outerwear_bottoms",
                    "items": full_outfit,
                    "score_avg": average_score(outer, bottom),
                    "palette_type": palette_type
                })

        for piece in grouped_items.get("one_piece", []):
            base_items = [piece]
            full_outfit = extend_with_optional_groups(base_items, grouped_items, optional_groups)
            outfits.append({
                "type": "one_piece",
                "items": outfits,
                "score_avg": extract_score(piece),
                "palette_type": palette_type
            })

        outfits.sort(key=lambda x: x["score_avg"], reverse=True)
        
    total_duration = time.perf_counter() - start_total
    logging.info(f"Request processed in {total_duration:.3f} seconds.")
    logging.info(f"Request generated {len(outfits)} items.")
    logging.info(f"Request generated\n {outfits}")
    return {
        "detail": "Recommendations computed successfully for each palette type.",
        "data":{ 
        "weather": {"temp": temp, "weather": weather, "icon": icon, "code": code} if location else None,
        "outfits": outfits}
    }
