import re
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

from app.user_manager.mail_controller import send_verification_code, send_verification_link
from .user import User

# Налаштування логування
logging.basicConfig(level=logging.DEBUG)

# Конфігурація JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Час життя токену

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
from fastapi.responses import JSONResponse

async def create_user(db: Session, email: str, password: str, locale: str):
    try:
        # Перевірка формату email
        email_regex = r"(^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$)"
        if not re.match(email_regex, email):
            return JSONResponse(
                status_code=400,
                content={
                    "message": "Invalid email format",
                    "data": None
                }
            )

        # Перевірка, чи email вже існує в базі
        user = db.query(User).filter(User.email == email).first()
        if user:
            return JSONResponse(
                status_code=400,
                content={
                    "message": "Email is already taken",
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
        token = create_access_token({"sub": email}, expires_delta=timedelta(hours=24))

        # Надсилання посилання для підтвердження електронної пошти
        await send_verification_link(email, token, locale)

        # Повернення відповіді про успіх
        return JSONResponse(
            status_code=201,
            content={
                "message": "Authentication successful",
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
                "message": "Database error",
                "data": None
            }
        )


# 🔹 Authenticate user and generate JWT token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
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
                "message": "User not found",
                "data": None
            }
        )

    # Check password
    if not verify_password(password, user.password):
        logging.debug(f"Authentication failed for user: {email}")
        return JSONResponse(
            status_code=401,
            content={
                "message": "Incorrect password",
                "data": None
            }
        )

    # Generate token for the user
    access_token = create_access_token(
        data={"sub": str(user.email)},
        expires_delta=timedelta(minutes=30)
    )

    return {
        "message": "Authentication successful",
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
            logging.error("Invalid token: User ID not found")  # Логування помилки, якщо ID відсутнє
            raise HTTPException(status_code=401, detail="Invalid token")
        logging.debug("Decoded user email: %s", user_email)  # Логування ID користувача
    except jwt.PyJWTError as e:
        logging.debug("JWT error: %s", str(e))  # Логування помилки декодування
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = db.query(User).filter(User.email == user_email).first()
    if user is None:
        logging.debug("User with email %s not found in DB", user_email)  # Логування, якщо користувач не знайдений
        raise HTTPException(status_code=401, detail="User not found")
    logging.debug("User found in DB: %s", user.email)  # Логування знайденого користувача
    return user

def get_current_user_id(token: str, db: Session):
    logging.debug("Decoding token: %s", token)  # Логування токена
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if not user_id:
            logging.error("Invalid token: User ID not found")  # Логування помилки, якщо ID відсутнє
            raise HTTPException(status_code=401, detail="Invalid token")
        logging.debug("Decoded user ID: %s", user_id)  # Логування ID користувача
    except jwt.PyJWTError as e:
        logging.debug("JWT error: %s", str(e))  # Логування помилки декодування
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        logging.debug("User with ID %s not found in DB", user_id)  # Логування, якщо користувач не знайдений
        raise HTTPException(status_code=401, detail="User not found")
    logging.debug("User found in DB: %s", user.email)  # Логування знайденого користувача
    return user.id

def is_user_verified(user_id, db: Session) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    return user is not None and user.is_email_verified

# Function to update the user's password
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

    return {"message": "Password successfully updated", "data":""}

# Function to update the user's email
def update_user_email(db: Session, user: User, password: str, new_email: str):
    """
    Updates the user's email after verifying the password.
    
    :param db: Database session
    :param user: The current user (User object)
    :param password: The user's current password
    :param new_email: The new email address for the user
    :raises HTTPException: If the password is incorrect
    :return: A message confirming the successful email change
    """
    if not verify_password(password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")

    user.email = new_email
    db.commit()

    return {"message": "Email successfully updated", "data":""}