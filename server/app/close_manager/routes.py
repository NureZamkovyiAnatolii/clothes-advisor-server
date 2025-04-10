from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from PIL import Image
from io import BytesIO
from colorthief import ColorThief
from app.user_manager.user_controller import get_current_user, get_current_user_id, oauth2_scheme
from app.close_manager.clothing_controller import add_clothing_item_to_db, mark_clothing_item_as_favorite, save_file
from app.user_manager.user import User

close_router = APIRouter(tags=["Close Operations"])


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


@close_router.post("/add-clothing-item", summary="Add a new clothing item")
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
    # Save the file to the server
    filename = save_file(file)
    # Get the user ID via the token
    try:
        # Get the user ID from the token
        owner_id = get_current_user_id(token, db)

    except HTTPException as e:
        # If an error occurs (e.g., invalid token or user not found)
        raise e  # Simply raise the exception so FastAPI can respond to the client
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

# @close_router.post("/items/{item_id}/favorite", response_model=None)
# def favorite_item(
#     item_id: int,
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     updated_item = mark_clothing_item_as_favorite(db, item_id, current_user.id)
#     return {"message": "Item marked as favorite", "item": updated_item.id}
