import os
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.close_manager.сlothing_item import ClothingItem
from datetime import datetime

# Директорія для зберігання файлів
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

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
        ClothingItem.filename == filename).first()
    if existing_item:
        raise HTTPException(
            status_code=400, detail="Clothing item with this filename already exists.")

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
