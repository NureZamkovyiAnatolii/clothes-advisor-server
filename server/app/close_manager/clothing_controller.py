import os
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.close_manager.сlothing_item import ClothingItem
from datetime import datetime

from app.close_manager.clothing_combination import ClothingCombination
from app.user_manager.mail_controller import SERVER_URL
from app.user_manager.user_controller import get_current_user_id

# Директорія для зберігання файлів
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_CLOTHING_ITEMS_COUNT = 100  
MAX_CLOTHING_COMBINATIONS_COUNT = 50

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Функція для збереження файлу на сервері


def save_file(file):
    # Генерація унікального імені для файлу
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    # Перевірка розміру
    if len(file.file.read()) > MAX_FILE_SIZE_BYTES:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Файл перевищує {MAX_FILE_SIZE_MB} МБ."}
        )
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    return unique_filename


# Створення роутера для додавання елемента одягу
clothing_item_router = APIRouter()


def add_clothing_item_to_db(

    db: Session,
    filename: str,
    name: str,
    category: str,
    season: str,
    red: str,
    green: str,
    blue: str,
    material: str,
    brand: str,
    purchase_date: str,
    price: float,
    is_favorite: bool,
    owner_id: int
) -> ClothingItem:
    existing_item = db.query(ClothingItem).filter(
        ClothingItem.name == name).first()
    if existing_item:
        raise HTTPException(
            status_code=400, detail="Clothing item with this filenamename already exists.")
    # ✅ Перевірка кількості елементів користувача
    item_count = db.query(ClothingItem).filter(ClothingItem.owner_id == owner_id).count()
    if item_count >= MAX_CLOTHING_ITEMS_COUNT:
        raise HTTPException(
            status_code=400, detail="Item limit reached. Maximum 100 clothing items allowed per user.")
    
    new_clothing_item = ClothingItem(
        filename=filename,
        name=name,
        category=category,
        season=season,
        red=red,
        green=green,
        blue=blue,
        material=material,
        brand=brand,
        purchase_date=datetime.strptime(
            purchase_date, "%Y-%m-%d") if purchase_date else None,
        price=price,
        is_favorite=is_favorite,
        owner_id=owner_id
    )

    db.add(new_clothing_item)
    db.commit()
    db.refresh(new_clothing_item)

    return new_clothing_item


def mark_clothing_item_as_favorite(
    db: Session,
    item_id: int,
    owner_id: int
) -> ClothingItem:
    # Знаходимо елемент за ID та власником
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id,
        ClothingItem.owner_id == owner_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    # Встановлюємо прапорець улюбленого
    item.is_favorite = True
    db.commit()
    db.refresh(item)

    return item


def mark_clothing_item_as_unfavorite(
    db: Session,
    item_id: int,
    owner_id: int
) -> ClothingItem:
    # Знаходимо елемент за ID та власником
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id,
        ClothingItem.owner_id == owner_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    item.is_favorite = False
    db.commit()
    db.refresh(item)

    return item


def get_all_combinations_for_user(
    db: Session,
    token: str
) -> list[dict]:
    user_id = get_current_user_id(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    combinations = db.query(ClothingCombination).filter_by(
        owner_id=user_id).all()
    result = []

    for combo in combinations:
        items = [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "season": item.season,
                "red": item.red,
                "green": item.green,
                "blue": item.blue,
                "material": item.material,
                "brand": item.brand,
                "price": item.price,
                "is_favorite": item.is_favorite,
                "filename": f"{SERVER_URL}/uploads/{item.filename}"
            }
            for item in combo.items
        ]
        result.append({
            "id": combo.id,
            "name": combo.name,
            "items": items
        })

    return result

def get_all_clothing_items_for_user(
    db: Session ,
    token: str 
):
    user_id = get_current_user_id(token,db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    items = db.query(ClothingItem).filter(ClothingItem.owner_id == user_id).all()
    for item in items:
        item.filename =f"{SERVER_URL}/uploads/"+  item.filename
    result = {}
    for idx, item in enumerate(items, start=1):
        result[f"item_{idx}"] = item

    return {
        "detail": "Clothing items fetched successfully.",
        "data": result
    }

def create_combination_in_db(
    db: Session,
    name: str,
    item_ids: list[int],
    owner_id: int
) -> ClothingCombination:

    # ✅ Перевірка кількості вже створених комбінацій
    combo_count = db.query(ClothingCombination).filter(
        ClothingCombination.owner_id == owner_id
    ).count()
    if combo_count >= MAX_CLOTHING_COMBINATIONS_COUNT:
        raise HTTPException(
            status_code=400, detail="Combination limit reached. Maximum 50 combinations allowed per user.")
    
    items = db.query(ClothingItem).filter(
        ClothingItem.id.in_(item_ids),
        ClothingItem.owner_id == owner_id
    ).all()

    if len(items) != len(item_ids):
        raise HTTPException(
            status_code=400, detail="Some items not found or don't belong to user.")

    combination = ClothingCombination(
        name=name,
        owner_id=owner_id,
        items=items
    )

    db.add(combination)
    db.commit()
    db.refresh(combination)

    return combination
