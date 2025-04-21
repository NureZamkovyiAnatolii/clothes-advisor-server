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
