from io import BytesIO
import logging
import os
import uuid
from fastapi import HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
from app.model import *
from app.user_manager import get_current_user_id, SERVER_URL
from rembg import remove

# Directory for storing files, max file size, and max clothing items/combination counts
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_CLOTHING_ITEMS_COUNT = 100
MAX_CLOTHING_COMBINATIONS_COUNT = 50

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# Function for saving a file on the server


# Function for saving a file on the server
def save_file(file: UploadFile):
    # Generate a unique filename for the file
    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Create the directory if it doesn't exist
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Read the entire content of the file
    content = file.file.read()

    # Check file size
    if len(content) > MAX_FILE_SIZE_BYTES:
        return JSONResponse(
            status_code=400,
            content={"detail": f"File size more than {MAX_FILE_SIZE_MB} MB."}
        )

    # Write the file to the disk
    with open(file_path, "wb") as f:
        f.write(content)

    return unique_filename


def remove_background_preview(filename: str) -> tuple[str, BytesIO]:
    input_path = os.path.join(UPLOAD_DIR, filename)


    with open(input_path, 'rb') as input_file:
        input_data = input_file.read()
        output_data = remove(input_data)

    output_io = BytesIO(output_data)


    base_name = os.path.splitext(filename)[0]
    output_filename = f"{base_name}_bg_removed.png"

    return output_filename, output_io


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
    # ✅ Checking the number of user items
    item_count = db.query(ClothingItem).filter(
        ClothingItem.owner_id == owner_id).count()
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
    logging.debug(f"Adding clothing item: {new_clothing_item}")
    logging.debug(f"Clothing item dict: {new_clothing_item.__dict__}")

    db.add(new_clothing_item)
    db.commit()
    db.refresh(new_clothing_item)

    return new_clothing_item

def update_clothing_item_in_db(
    db: Session,
    item_id: int,
    **fields
) -> ClothingItem:
    item = db.query(ClothingItem).filter(ClothingItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    for key, value in fields.items():
        if value is not None:
            if key == "purchase_date":
                value = datetime.strptime(value, "%Y-%m-%d")
            setattr(item, key, value)

    db.commit()
    db.refresh(item)
    return item

def remove_file_by_clothing_item_id(clothing_item_id: int, is_preview: bool, db: Session):
    # Find the clothing item by its ID
    clothing_item = db.query(ClothingItem).filter(
        ClothingItem.id == clothing_item_id).first()

    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    base_name = os.path.splitext(clothing_item.filename)[0]

    # If is_preview is True, delete the original file; if False, delete the preview file
    if is_preview:
        target_filename = clothing_item.filename
    else:
        target_filename = f"{base_name}_bg_removed.png"

    target_path = os.path.join(UPLOAD_DIR, target_filename)
    logging.info(f"Target path for deletion: {target_path}")

    # Check if the file exists and delete it
    if os.path.exists(target_path):
        os.remove(target_path)

        # After deletion, update the filename with UUID in the database
        if is_preview:
            new_filename = f"{uuid.uuid4()}.png"

            old_file_path = os.path.join(
                UPLOAD_DIR, f"{base_name}_bg_removed.png")
            logging.info(f"Old file path for renaming: {old_file_path}")
            new_file_path = os.path.join(UPLOAD_DIR, new_filename)

            if os.path.exists(old_file_path):
                os.rename(old_file_path, new_file_path)

            clothing_item.filename = new_filename
            db.commit()

        return {"detail": f"File '{os.path.basename(target_path)}' was deleted, and filename updated in database to '{clothing_item.filename}'."}
    else:
        raise HTTPException(status_code=404, detail="File not found.")


def mark_clothing_item_as_favorite(
    db: Session,
    item_id: int,
    owner_id: int
) -> ClothingItem:
    # Find the clothing item by its ID and owner ID
    item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id,
        ClothingItem.owner_id == owner_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    # Update the is_favorite status
    item.is_favorite = True
    db.commit()
    db.refresh(item)
    
    return item


def mark_clothing_item_as_unfavorite(
    db: Session,
    item_id: int,
    owner_id: int
) -> ClothingItem:
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
        raise HTTPException(status_code=401, detail="Not authenticated")

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
    db: Session,
    token: str
):
    user_id = get_current_user_id(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    items = db.query(ClothingItem).filter(
        ClothingItem.owner_id == user_id).all()
    for item in items:
        item.filename = f"{SERVER_URL}/uploads/" + item.filename
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

    # ✅ Checking the number of user combinations
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
    # 🛡️ Check that each CategoryEnum appears only once
    category_counts = {}
    for item in items:
        if item.category in category_counts:
            raise HTTPException(
                status_code=400,
                detail=f"Only one item per category is allowed. Duplicate found for category: {item.category}."
            )
        category_counts[item.category] = 1
    db.add(combination)
    db.commit()
    db.refresh(combination)

    return combination
