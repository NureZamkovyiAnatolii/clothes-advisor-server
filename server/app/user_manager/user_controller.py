import json
import re
from typing import Optional
import bcrypt
from fastapi.responses import JSONResponse
import jwt
import os
import logging
from datetime import datetime, timedelta, timezone
from scipy import stats
from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from fastapi.security import OAuth2PasswordBearer

from app.user_manager.mail_controller import send_password_change_form, send_verification_link
from app.model import *

# Налаштування логування
logging.basicConfig(level=logging.DEBUG)

# Конфігурація JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Час життя токену
SERVER_URL = os.getenv("SERVER_URL")

# FastAPI security scheme (очікує токен у заголовку Authorization)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# 🔹 Хешування пароля
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

# 🔹 Перевірка пароля


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# Оновлена функція створення користувача


async def create_user(db: Session, email: str, password: str, locale: str):
    try:
        # Перевірка формату email
        email_regex = r"(^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$)"
        if not re.match(email_regex, email):
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Invalid email format",
                    "data": None
                }
            )

        # Перевірка, чи email вже існує в базі
        user = db.query(User).filter(User.email == email).first()
        if user:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Email is already taken",
                    "data": None
                }
            )

        # Хешування пароля
        hashed_password = hash_password(password)

        # Створення користувача
        user = User(
            email=email,
            password=hashed_password,
            is_email_verified=False,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Створення токену доступу
        token = create_access_token(
            {"sub": email}, expires_delta=timedelta(hours=24))

        # Надсилання посилання для підтвердження електронної пошти
        await send_verification_link(email, token, locale)

        # Повернення відповіді про успіх
        return JSONResponse(
            status_code=201,
            content={
                "detail": "Resister successful. Please verify your email",
                "data": {
                    "access_token": token,
                    "token_type": "bearer"
                }
            }
        )

    except SQLAlchemyError as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Database error",
                "data": None
            }
        )


# 🔹 Authenticate user and generate JWT token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(
        timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})  # Додаємо час дії токену
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 🔹 Аутентифікація користувача та створення JWT-токена


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    logging.debug(f"Retrieved user: {user}")

    # Check if user exists in DB
    if not user:
        logging.debug(f"No user found with email: {email}")
        return JSONResponse(
            status_code=404,
            content={
                "detail": "User not found",
                "data": None
            }
        )
    
    # Check password
    if not verify_password(password, user.password):
        logging.debug(f"Authentication failed for user: {email}")
        return JSONResponse(
            status_code=401,
            content={
                "detail": "Incorrect password",
                "data": None
            }
        )
    if user.is_email_verified == False:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Email not verified",
                "data": None
            }
        )
    # Generate token for the user
    access_token = create_access_token(
        data={"sub": str(user.email)},
        expires_delta=timedelta(minutes=30)
    )

    return {
        "detail": "Authentication successful",
        "data": {
            "access_token": access_token,
            "token_type": "bearer"
        }
    }


def get_current_user(token: str, db: Session):
    logging.debug("Decoding token: %s", token)  # Логування токена
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        if not user_email:
            # Логування помилки, якщо email відсутній
            logging.error("Invalid token: User email not found")
            # Повертаємо JSONResponse при помилці
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        # Логування email користувача
        logging.debug("Decoded user email: %s", user_email)
    except jwt.ExpiredSignatureError:
        # Логування, якщо токен прострочений
        logging.error("Token has expired")
        return JSONResponse(status_code=401, content={"detail": "Token has expired"})
    except jwt.PyJWTError as e:
        # Логування помилки декодування
        logging.error("JWT decoding error: %s", str(e))
        return JSONResponse(status_code=401, content={"detail": "Could not validate credentials"})

    user = db.query(User).filter(User.email == user_email).first()
    if user is None:
        # Логування, якщо користувач не знайдений
        logging.debug("User with email %s not found in DB", user_email)
        return JSONResponse(status_code=401, content={"detail": "User not found"})
    # Логування знайденого користувача
    logging.debug("User found in DB: %s", user.email)
    return user  # Повертаємо користувача, якщо він знайдений


def get_current_user_id(token: str, db: Session):
    logging.debug("Decoding token: %s", token)  # Логування токена
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_email: str = payload.get("sub")
        if not user_email:
            # Логування помилки, якщо ID відсутнє
            logging.error("Invalid token: User ID not found")
            raise HTTPException(status_code=401, detail="Invalid token")
        # Логування ID користувача
        logging.debug("Decoded user email: %s", user_email)
    except jwt.PyJWTError as e:
        logging.debug("JWT error: %s", str(e))  # Логування помилки декодування
        raise HTTPException(
            status_code=401, detail="Could not validate credentials")

    user = db.query(User).filter(User.email == user_email).first()
    if user is None:
        # Логування, якщо користувач не знайдений
        logging.debug("User with email %s not found in DB", user_email)
        raise HTTPException(status_code=401, detail="User not found")
    # Логування знайденого користувача
    logging.debug("User found in DB: %s", user.email)
    return user.id

def synchronize_user_data(
    token: str,
    clothing_items: str,
    clothing_combinations: str,
    db: Session,
    files: list[tuple[str, tuple[str, bytes, str]]]
):
    logging.debug("Received request for data synchronization")
    logging.debug("clothing_items: %s", clothing_items)  
    logging.debug("clothing_combinations: %s", clothing_combinations) 

    if isinstance(clothing_items, str):
        items_data = json.loads(clothing_items)
    else:
        items_data = clothing_items
    combos_data = json.loads(clothing_combinations)

    logging.debug("items_data: %s, type: %s", items_data, type(items_data))
    logging.debug("combos_data: %s, type: %s", combos_data, type(combos_data))



    current_user = get_current_user(token, db)
    
    # 1. Видалити старі речі та комбінації користувача
    old_combos = db.query(ClothingCombination).filter_by(owner_id = current_user.id).all()
    for combo in old_combos:
        combo.items.clear()  # очищає many-to-many зв'язки
        db.delete(combo)

    old_items = db.query(ClothingItem).filter_by(owner_id=current_user.id).all()
    for item in old_items:
        db.delete(item)

    db.commit()
    print(f"🧹 Cleared old items and combinations for user {current_user.email}")

    # 2. Додати нові речі
    filename_map = {}
    saved_filenames = []
    for file in files:
        from app.close_manager.clothing_controller import save_file
        saved_name = save_file(file)
        filename_map[file.filename] = saved_name  # запам’ятовуємо, під якою назвою зберегли
        saved_filenames.append(f"{SERVER_URL}/uploads/{saved_name}")

    old_to_new_items_map = {}  # Мапа старих ID до нових

    new_items = []
    for item in items_data:
        # Видаляємо 'id' та 'owner_id' зі словника
        item_data_cleaned = {
            k: v for k, v in item.items()
            if k not in ("id", "owner_id")
        }

        # Оновлюємо назву файлу, якщо є така у мапі
        original_filename = item.get("filename")
        if original_filename in filename_map:
            item_data_cleaned["filename"] = filename_map[original_filename]

        # Створюємо новий об’єкт з прив’язкою до користувача
        new_item = ClothingItem(**item_data_cleaned, owner_id=current_user.id)

        db.add(new_item)
        db.commit()  # Зберігаємо об'єкт в базі даних, щоб отримати його новий ID

        # Мапуємо старий ID на новий
        old_to_new_items_map[item["id"]] = new_item.id
        new_items.append(new_item)

    db.commit()

    # 3. Додати нові комбінації
    old_to_new_combos_map = {}  # мапа старих ID комбінацій до нових

    for combo in combos_data:
        old_combo_id = combo["id"]

        new_combo = ClothingCombination(
            name=combo["name"], owner_id=current_user.id)
        db.add(new_combo)
        db.commit()  # щоб combo.id був доступний

        # Мапуємо старий ID на новий
        old_to_new_combos_map[old_combo_id] = new_combo.id

        for old_item_id in combo["item_ids"]:
            new_item_id = old_to_new_items_map.get(old_item_id)
            if new_item_id:
                item = db.query(ClothingItem).get(new_item_id)
                if item:
                    new_combo.items.append(item)

        db.commit()

    current_user.synchronized_at = datetime.now(timezone.utc)
    db.commit()
    # Перетворення мап у список словників з додаванням нового шляху до файлу
    id_to_filename = {item['id']: item['filename'] for item in items_data}

# Формуємо фінальний список з URL
    item_mapping_list = [
    {
        "old": old_id,
        "new": new_id,
        "new_file": f"{saved_filename}"
    }
    for (old_id, new_id), saved_filename in zip(old_to_new_items_map.items(), saved_filenames)
]

    combo_id_mapping_list = [{"old": old_id, "new": new_id} for old_id, new_id in old_to_new_combos_map.items()]

    return JSONResponse(
        status_code=200,
        content={
            "detail": "Synchronized data updated",
            "data": {
                "synchronized_at": current_user.synchronized_at.isoformat(),
                "item_mapping": item_mapping_list,
                "combo_id_mapping": combo_id_mapping_list,
                "file_mapping": saved_filenames  # 🆕 Added this part
            }
        }
    )

def update_synchronized_at(token: str, db: Session):
    current_user = get_current_user(token, db)
    current_user.synchronized_at = datetime.now(timezone.utc)
    db.commit()
    return JSONResponse(
        status_code=200,
        content={
            "detail": "Synchronized at updated",
            "data": {
                "synchronized_at": current_user.synchronized_at.isoformat()
            }
        }
    )
def get_user_data(token: str, db: Session):
    from app.close_manager.clothing_controller import get_all_combinations_for_user, get_all_clothing_items_for_user
    items = get_all_clothing_items_for_user(db, token)
    combos = get_all_combinations_for_user(db,token)
    combo_ids = []
    for combo in combos:
        items_only = []
        
        # Перебираємо кожен елемент у списку items
        for item in combo['items']:
            items_only.append(item['id'])
        
        combo_ids.append({
            'id': combo["id"],
            'name': combo["name"],
            'items': items_only
        })

    logging.debug(f"Items: {items}, Combinations: {combos}")

    # Отримуємо дані з ключа 'data'
    items_data = [
        item.to_dict() if hasattr(item, 'to_dict') else item
        for item in items['data'].values()  # Звертаємося до 'data', і використовуємо values()
        ]
    
    current_user = get_current_user(token, db)
    logging.debug(f"items_data: {items_data}")
    return JSONResponse(content={
        "detail": "All data retrieved successfully",
        "data": {
            "items": items_data,
            "combinations": combo_ids,
            "synchronized_at": current_user.synchronized_at.isoformat() if current_user.synchronized_at else None, 
        }
    })
def is_user_verified(user_id, db: Session) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    return user is not None and user.is_email_verified

# Functions to update the user's password
def create_password_reset_token(email: str, expires_delta: timedelta = timedelta(hours=1)) -> str:
    """
    Creates a password reset token.

    - **Parameters**:
        - `email`: User's email address.
        - `expires_delta`: Expiration time for the token.

    - **Returns**: JWT token for password reset.
    """
    to_encode = {"sub": email, "exp": datetime.utcnow() + expires_delta}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
async def send_password_reset_email(db: Session, email: str, locale: Optional[str] = 'en'):
    """
    Sends a password reset form to the user's email after verifying the password.
    
    - **Parameters**:
        - `db`: Database session.
        - `email`: User's email address.
        - `locale`: The language for the reset message ('ua' for Ukrainian, 'en' for English).
    - **Raises**:
        - HTTPException: If the email doesn't exist or the password is incorrect.
    """
    # Перевірка, чи є користувач з вказаним email
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")


    # Створення токену для скидання пароля
    reset_token = create_password_reset_token(email=email)

    # Формуємо посилання для зміни пароля
    reset_url = f"{SERVER_URL}/change-password-form?token={reset_token}&locale={locale}"

    # Створюємо HTML контент в залежності від мови
    if locale == 'ua':
        html_content = f"""
        <html>
            <body>
                <h3>Зміна пароля</h3>
                <p>Щоб змінити пароль, натисніть на посилання нижче:</p>
                <a href="{reset_url}">Змінити пароль</a>
                <p>Якщо ви не робили запит на зміну пароля, проігноруйте цей лист.</p>
            </body>
        </html>
        """
        subject="Запит на зміну пароля"
    else:
        html_content = f"""
        <html>
            <body>
                <h3>Password Change</h3>
                <p>To change your password, click the link below:</p>
                <a href="{reset_url}">Change Password</a>
                <p>If you did not request a password change, please ignore this email.</p>
            </body>
        </html>
        """
        subject="Password change request"

    # Відправка email користувачу
    try:
        await send_password_change_form(
            email=email,
            subject=subject,
            html_content=html_content
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")

    return {"detail": "Password reset email sent successfully."}

def update_user_password(db: Session, user: User, old_password: str, new_password: str):
    """
    Updates the user's password after verifying the old password.

    :param db: Database session
    :param user: The current user (User object)
    :param old_password: The user's current password
    :param new_password: The new password for the user
    :raises HTTPException: If the old password is incorrect
    :return: A message confirming the successful password change
    """
    if not verify_password(old_password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    user.password = hash_password(new_password)
    db.commit()

    return {"detail": "Password successfully updated", "data": ""}

# Function to update the user's email


async def update_user_email(db: Session, user: User, password: str, new_email: str, locale: str):
    """
    Updates the user's email after verifying the password.
    """
    if not verify_password(password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    try:
        # Перевірка формату email
        email_regex = r"(^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$)"
        if not re.match(email_regex, new_email):
            raise HTTPException(
                status_code=400,
                detail="Invalid email format"
            )

        # Перевірка, чи email вже існує в базі
        test_user = db.query(User).filter(User.email == new_email).first()
        if test_user:
            raise HTTPException(
                status_code=400,
                detail="Email is already taken"
            )
        logging.error(f"Updating email from { user.email} to  {new_email}")
        # Створення токену доступу
        token = create_access_token(
            {"sub": new_email}, expires_delta=timedelta(hours=24))

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database error"
        )
    user.email = new_email
    user.is_email_verified = False
    db.commit()
    # Надсилання посилання для підтвердження електронної пошти
    await send_verification_link(new_email, token, locale)

    return {"detail": "Email successfully updated. Please verify new email", "data": ""}
