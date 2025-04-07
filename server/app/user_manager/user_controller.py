import bcrypt
import jwt
import os
import logging
from datetime import datetime, timedelta, timezone
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
async def create_user(db: Session, email: str, password: str, locale: str):
    try:
        hashed_password = hash_password(password)

        user = User(
            email=email,
            password=hashed_password,
            is_email_verified=False,  # Email ще не підтверджений
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        user = db.query(User).filter(User.email == email).first()
        token = create_access_token({"sub": email}, expires_delta=timedelta(hours=24))
        # Відправка лінку для підтвердження email
        await send_verification_link(email, token, locale)  
        return {"user": user, "access_token": token, "token_type": "bearer"}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# 🔹 Функція створення JWT-токена
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})  # Додаємо час дії токену
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# 🔹 Аутентифікація користувача та створення JWT-токена
def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()
    logging.debug(f"Retrieved user: {user}")

    if not user or not verify_password(password, user.password):
        logging.debug(f"Authentication failed for user: {email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Створюємо токен для користувача
    access_token = create_access_token(data={"sub": str(user.id)}, expires_delta=timedelta(minutes=30))
    return {"access_token": access_token, "token_type": "bearer"}

def get_current_user(token: str, db: Session):
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

def update_user_password(db: Session, user: User, old_password: str, new_password: str):
    """
    Оновлює пароль користувача після перевірки старого пароля.
    
    :param db: Сесія бази даних
    :param user: Поточний користувач (об'єкт User)
    :param old_password: Поточний пароль користувача
    :param new_password: Новий пароль для користувача
    :raises HTTPException: Якщо старий пароль неправильний
    :return: Повідомлення про успішну зміну пароля
    """
    if not verify_password(old_password, user.password):
        raise HTTPException(status_code=400, detail="Неправильний старий пароль")

    user.password = hash_password(new_password)
    db.commit()

    return {"message": "Пароль успішно змінено"}

def update_user_email(db: Session, user: User, password: str, new_email: str):
    if not verify_password(password, user.password):
        raise HTTPException(status_code=400, detail="Неправильний пароль")

    user.email = new_email
    db.commit()

    return {"message": "Email успішно змінено"}