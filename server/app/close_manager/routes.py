import asyncio
import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database.database import get_db
from PIL import Image
from io import BytesIO
from colorthief import ColorThief
from app.user_manager.user_controller import get_current_user, get_current_user_id, oauth2_scheme
from app.close_manager.clothing_controller import *
from app.model import *
from app.user_manager import *
from app.constants import SERVER_URL

clothing_router = APIRouter(tags=["Close Operations"])

def get_dominant_color(file: UploadFile):
    """Determines the dominant color of an image"""
    img = Image.open(
        file.file)  # Use file.file to access the byte stream
    img = img.convert("RGB")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)

    color_thief = ColorThief(buffer)
    return color_thief.get_color(quality=1)  # (R, G, B)


@clothing_router.get("/clothing-items")
def get_user_clothing_items(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    return get_all_clothing_items_for_user(db, token)


@clothing_router.post("/add-clothing-item", summary="Add a new clothing item")
async def add_clothing_item(
    file: UploadFile = File(...),  # Upload image
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
    """
    **Adds a new clothing item to the collection.**

    - **Headers**: `Authorization: Bearer <token>`
    - **Parameters**:
        - `file`: Image of the clothing item.
        - `name`: Name of the clothing item.
        - `category`: Category of the clothing item (e.g., shirt, pants).
        - `season`: Season for the clothing item (e.g., summer, winter).
        - `red`, `green`, `blue`: Optional color values for the clothing item. If not provided, the color will be determined automatically from the image.
        - `material`: Material of the clothing item (e.g., cotton, leather).
        - `brand`: Brand of the clothing item.
        - `purchase_date`: Date of purchase for the clothing item.
        - `price`: Price of the clothing item.
        - `is_favorite`: Boolean indicating whether the item is a favorite.
    - **Response**:
        - `200 OK`: Clothing item added successfully.
        - `400 Bad Request`: Invalid color values (if provided).
        - `401 Unauthorized`: User is not authenticated.
        - `422 Unprocessable Entity`: Image processing error or missing required parameters.
    """
    # Get the user ID via the token
    try:
        # Get the user ID from the token
        owner_id = get_current_user_id(token, db)

    except HTTPException as e:
        # If an error occurs (e.g., invalid token or user not found)
        raise e  # Simply raise the exception so FastAPI can respond to the client
    # ✅ Checking the number of user items
    item_count = db.query(ClothingItem).filter(
        ClothingItem.owner_id == owner_id).count()
    if item_count >= MAX_CLOTHING_ITEMS_COUNT:
        raise HTTPException(
            status_code=400, detail="Item limit reached. Maximum 100 clothing items allowed per user.")
    # If color is not specified, determine it automatically
    if not red or not green or not blue:
        # Call get_dominant_color with the file
        red, green, blue = get_dominant_color(file)
    else:
        try:
            red = int(red)
            green = int(green)
            blue = int(blue)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid color values")
    # Save the file to the server
    filename = save_file(file)
    # Call the function to add the item to the database
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
    update_synchronized_at(token, db)
    return {
        "detail": "Clothing item added successfully.",
        "data": {
            "id": new_clothing_item.id,
            "filename": f"{SERVER_URL}/{UPLOAD_DIR}/{new_clothing_item.filename}",
            "name": new_clothing_item.name,
            "category": new_clothing_item.category,
            "season": new_clothing_item.season,
            "red": new_clothing_item.red,
            "green": new_clothing_item.green,
            "blue": new_clothing_item.blue,
            "material": new_clothing_item.material,
            "brand": new_clothing_item.brand,
            "purchase_date": new_clothing_item.purchase_date,
            "price": new_clothing_item.price,
            "is_favorite": new_clothing_item.is_favorite,
            "owner_id": new_clothing_item.owner_id,
        },
        "synchronized_at": get_current_user(token, db).synchronized_at_iso
    }


@clothing_router.put("/clothing-items/{item_id}", summary="Update existing clothing item")
async def update_clothing_item(
    item_id: int,
    file: UploadFile = File(None),
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
    is_favorite: bool = Form(None),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    **Updates a clothing item.**

    - **Headers**: `Authorization: Bearer <token>`
    - If a new image is uploaded, the old one will be removed.
    """
    # Get the user ID via the token
    current_user: User = get_current_user(token, db)

    clothing_item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id).first()

    if not clothing_item or clothing_item.owner_id != current_user.id:
        raise HTTPException(
            status_code=404, detail="Clothing item not found")

    # 🔄 Handle colors (if not provided, use existing ones from the DB)
    red = int(red) if red else clothing_item.red
    green = int(green) if green else clothing_item.green
    blue = int(blue) if blue else clothing_item.blue

    # 🔄 Update other fields (if not provided, use existing ones from the DB)
    clothing_item.name = name or clothing_item.name
    clothing_item.category = category or clothing_item.category
    clothing_item.season = season or clothing_item.season
    clothing_item.red = red
    clothing_item.green = green
    clothing_item.blue = blue
    clothing_item.material = material or clothing_item.material
    clothing_item.brand = brand if brand is not None else None
    clothing_item.purchase_date = datetime.strptime(
        purchase_date, "%Y-%m-%d").date() if purchase_date else None
    clothing_item.price = price if price is not None else None
    clothing_item.is_favorite = is_favorite if is_favorite is not None else clothing_item.is_favorite

    # 📁 Remove old file and save new one
    if file:
        old_filename = clothing_item.filename
        filename = save_file(file)
        clothing_item.filename = filename

        if old_filename:
            old_file_path = os.path.join("{UPLOAD_DIR}", old_filename)
            if os.path.exists(old_file_path):
                try:
                    os.remove(old_file_path)
                except Exception as e:
                    logging.warning(f"Failed to delete old file: {e}")

    db.commit()
    db.refresh(clothing_item)
    update_synchronized_at(token, db)

    return {
        "detail": "Clothing item updated successfully.",
        "data": {
            "id": clothing_item.id,
            "filename": f"{SERVER_URL}/{UPLOAD_DIR}/{clothing_item.filename}",
            "name": clothing_item.name,
            "category": clothing_item.category,
            "season": clothing_item.season,
            "red": clothing_item.red,
            "green": clothing_item.green,
            "blue": clothing_item.blue,
            "material": clothing_item.material,
            "brand": clothing_item.brand,
            "purchase_date": clothing_item.purchase_date.isoformat() if clothing_item.purchase_date else None,
            "price": clothing_item.price,
            "is_favorite": clothing_item.is_favorite,
        },
        "synchronized_at": current_user.synchronized_at_iso
    }


@clothing_router.get("/clothing-items/{clothing_item_id}/preview-remove-background")
async def preview_remove_clothing_item_background(
    clothing_item_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    current_user: User = get_current_user(token, db)

    clothing_item = db.query(ClothingItem).filter(
        ClothingItem.id == clothing_item_id,
        ClothingItem.owner_id == current_user.id
    ).first()

    if not clothing_item:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    new_filename, output_io = remove_background_preview(clothing_item.filename)

    # Важливо "перемотати" віртуальний файл на початок
    output_io.seek(0)

    # Повертаємо файл напряму з пам'яті
    return StreamingResponse(
        output_io,
        media_type="image/png",  # бо у тебе output.png
        headers={"Content-Disposition": f"attachment; filename={new_filename}"}
    )


@clothing_router.put("/items/{item_id}/toggle-favorite", response_model=None)
def toggle_favorite_item(
    item_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    current_user: User = get_current_user(token, db)

    # Find the user's clothing item
    clothing_item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id,
        ClothingItem.owner_id == current_user.id
    ).first()

    if not clothing_item:
        raise HTTPException(
            status_code=404, detail="Clothing item not found")

    # Toggle the value of is_favorite
    clothing_item.is_favorite = not clothing_item.is_favorite
    db.commit()
    db.refresh(clothing_item)

    update_synchronized_at(token, db)

    return {
        "detail": f"Item with {item_id}{'added to' if clothing_item.is_favorite else 'removed from'} favorites",
        "data": {
            "is_favorite": clothing_item.is_favorite
        },
        "synchronized_at": current_user.synchronized_at_iso
    }


@clothing_router.delete("/clothing-items/{item_id}", summary="Delete clothing item")
async def delete_clothing_item(
    item_id: int,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    **Deletes a clothing item.**

    - **Headers**: `Authorization: Bearer <token>`
    - Deletes the file from disk if it exists.
    """
    # Get the current user
    current_user: User = get_current_user(token, db)

    # Find the clothing item
    clothing_item = db.query(ClothingItem).filter(
        ClothingItem.id == item_id).first()

    if not clothing_item or clothing_item.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Clothing item not found")

    # Delete associated file if it exists
    if clothing_item.filename:
        file_path = os.path.join("{UPLOAD_DIR}", clothing_item.filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logging.warning(f"Failed to delete file: {e}")

    # Delete the item from the database
    db.delete(clothing_item)
    db.commit()
    update_synchronized_at(token, db)

    return {"detail": f"Clothing item with id {item_id} deleted successfully.",
            "synchronized_at": current_user.synchronized_at_iso}


@clothing_router.get("/clothing-combinations")
def get_user_combinations(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    data = get_all_combinations_for_user(db, token)
    return {
        "detail": "Clothing combinations fetched successfully.",
        "data": data
    }


class CombinationRequest(BaseModel):
    name: str
    item_ids: List[int]


@clothing_router.put("/clothing-combinations/{combination_id}")
def update_clothing_combination(
    combination_id: int,
    request: CombinationRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    current_user = get_current_user(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    combination = db.query(ClothingCombination).filter(
        ClothingCombination.id == combination_id,
        ClothingCombination.owner_id == current_user.id
    ).first()

    if not combination:
        raise HTTPException(status_code=404, detail="Combination not found")

    if request.name:
        combination.name = request.name
    if request.item_ids is not None:
        items = db.query(ClothingItem).filter(
            ClothingItem.id.in_(request.item_ids)).all()
        found_ids = {item.id for item in items}
        requested_ids = set(request.item_ids)
        missing_ids = requested_ids - found_ids

        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail="Some clothing items from request not found."
            )

        combination.items = items

    db.commit()
    db.refresh(combination)

    update_synchronized_at(token, db)

    return {
        "detail": "Clothing combination updated successfully.",
        "data": {"combination_id": combination.id},
        "synchronized_at": current_user.synchronized_at_iso
    }


@clothing_router.post("/clothing-combinations")
def create_clothing_combination(
    request: CombinationRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    user_id = get_current_user_id(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    combination = create_combination_in_db(
        db=db,
        name=request.name,
        item_ids=request.item_ids,
        owner_id=user_id
    )
    if combination is HTTPException:
        raise combination
    update_synchronized_at(token, db)
    return {
        "detail": "Clothing combination created successfully.",
        "data": {"combination_id": combination.id},
        "synchronized_at": get_current_user(token, db).synchronized_at_iso
    }


@clothing_router.delete("/clothing-combinations/{combination_id}")
def delete_clothing_combination(
    combination_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    current_user = get_current_user(token, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    combination = db.query(ClothingCombination).filter(
        ClothingCombination.id == combination_id,
        ClothingCombination.owner_id == current_user.id
    ).first()

    if not combination:
        raise HTTPException(status_code=404, detail="Combination not found")

    db.delete(combination)
    db.commit()

    update_synchronized_at(token, db)

    return {
        "detail": "Clothing combination deleted successfully.",
        "synchronized_at": current_user.synchronized_at_iso
    }
