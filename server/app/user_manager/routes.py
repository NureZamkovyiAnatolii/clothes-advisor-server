from fastapi import APIRouter, Depends,Form ,HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from sqlalchemy.orm import Session
from app.database import get_db
from app.user_manager.user import User
from .user_controller import ALGORITHM, SECRET_KEY, create_user, authenticate_user, get_current_user, is_user_verified,oauth2_scheme, update_user_password
from .mail_controller import verify_code
import logging

user_manager_router = APIRouter()

# Реєстрація користувача
@user_manager_router.post("/register", description="Create a new user in the system.")
async def register(
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    locale: str = Form('ua',description="Language for the confirmation message. Options: 'ua' for Ukrainian, 'en' for English.")  # Додаємо параметр локалізації з значенням за замовчуванням 'ua'
):
    user = await create_user(db, email, password, locale)
    logging.debug(f"Retrieved user: {user}")

    return {"message": "User registered successfully", "user_id": user['user'].id}

# Додаємо OAuth2 схему для Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Авторизація (отримання JWT-токена)
@user_manager_router.post("/token")
def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    email = form_data.username  # Використовуємо `username` як email
    return authenticate_user(db, email, form_data.password)

@user_manager_router.post("/login_with_email")
def login_with_email(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Повертаємо токен (або JWT, якщо ти його створюєш)
    return {
        "access_token": user["access_token"],  # наприклад, якщо функція повертає словник
        "token_type": "bearer"
    }

@user_manager_router.get("/verify_email", response_class=HTMLResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_email_verified:
            return "<h3>Email вже підтверджено ✅</h3>"

        user.is_email_verified = True
        db.commit()
        return "<h3>Дякуємо! Ваш email підтверджено 🎉</h3>"

    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

@user_manager_router.get("/profile")
def get_profile(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    logging.debug("Received request for profile with token: %s", token)  # Логування отриманого токена
    try:
        current_user = get_current_user(token, db)  # Передаємо токен сюди
        logging.debug("User found: %s", current_user.email)  # Логування знайденого користувача
        return {
            "id": current_user.id,
            "email": current_user.email
        }
    except HTTPException as e:
        logging.error("Error retrieving user profile: %s", e.detail)  # Логування помилки, якщо вона сталася
        raise e

@user_manager_router.get("/is_activated")
def is_user_activated(user_id: int, db: Session = Depends(get_db)):
    return is_user_verified(user_id,db)

@user_manager_router.put("/change-password", summary="Changes the password for the currently authenticated user")
def change_password(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    old_password: str = Form(...),
    new_password: str = Form(...)
):
    """
    **Changes the password for the currently authenticated user**
    
    - **Headers**: `Authorization: Bearer <token>`
    - **Parameters**:
        - `old_password`: Current password.
        - `new_password`: New password.
    - **Response**:
        - `200 OK`: Password changed successfully.
        - `400 Bad Request`: Old password is incorrect.
        - `401 Unauthorized`: User is not authenticated.
    """

    current_user = get_current_user(token, db)
    return update_user_password(db, current_user, old_password, new_password)