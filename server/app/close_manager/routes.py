from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from PIL import Image
from io import BytesIO
from colorthief import ColorThief
from app.user_manager.user_controller import get_current_user_id, oauth2_scheme
from app.close_manager.clothing_controller import add_clothing_item_to_db, save_file

close_router = APIRouter(tags=["Close Operations"])

def get_dominant_color(file: UploadFile):
    """Визначає домінантний колір зображення"""
    img = Image.open(file.file)  # Використовуємо file.file, щоб отримати доступ до байтового потоку
    img = img.convert("RGB")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)

    color_thief = ColorThief(buffer)
    return color_thief.get_color(quality=1)  # Повертає (R, G, B)

@close_router.post("/add-clothing-item", summary="Add a new clothing item")
async def add_clothing_item(
    file: UploadFile = File(...),  # Завантаження фото
    name: str = Form(...),  
    category: str = Form(...),
    season: str = Form(...),
    red: Optional[str] = Form(None),
    green: Optional[str] = Form(None),
    blue: Optional[str] = Form(None),
    material: str = Form(...),
    brand: str = Form(None),
    purchase_date: str = Form(None),
    price: float = Form(None),
    token: str = Depends(oauth2_scheme),
    is_favorite: bool = Form(False),
    db: Session = Depends(get_db)
):
    # Збереження файлу на сервері
    filename = save_file(file)
    # Отримуємо id користувача через токен
    try:
        # Отримуємо id користувача з токена
        owner_id = get_current_user_id(token, db)

    except HTTPException as e:
        # Якщо виникла помилка (наприклад, неправильний токен або користувач не знайдений)
        raise e  # Просто перекидаємо виключення далі, щоб FastAPI міг відповісти клієнту
    # Якщо колір не вказано, визначаємо його автоматично
    if not red or not green or not blue:
        red, green, blue = get_dominant_color(file)  # Викликаємо get_dominant_color з файлом
    else:
        try:
            red = int(red)
            green = int(green)
            blue = int(blue)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid color values")
    
    # Викликаємо функцію для додавання елемента в базу
    new_clothing_item = add_clothing_item_to_db(
        db, 
        filename, 
        name, 
        category, 
        season, 
        red,
        green,
        blue, 
        material, 
        brand, 
        purchase_date, 
        price, 
        is_favorite, 
        owner_id
    )

    return {
        "detail": "Clothing item added successfully.",
        "data": {
            "id": new_clothing_item.id,
            "filename": new_clothing_item.filename,
            "name": new_clothing_item.name,
            "category": new_clothing_item.category,
            "season": new_clothing_item.season,
            "color": {
                "red": new_clothing_item.red,
                "green": new_clothing_item.green,
                "blue": new_clothing_item.blue
            },
            "material": new_clothing_item.material,
            "brand": new_clothing_item.brand,
            "purchase_date": new_clothing_item.purchase_date,
            "price": new_clothing_item.price,
            "is_favorite": new_clothing_item.is_favorite,
            "owner_id": new_clothing_item.owner_id,
        }
    }
