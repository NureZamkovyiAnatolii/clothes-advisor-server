from fastapi import APIRouter, Depends,Form ,HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from sqlalchemy.orm import Session
from app.database import get_db
from app.user_manager.user import User
from .user_controller import ALGORITHM, SECRET_KEY, create_user, authenticate_user, get_current_user, is_user_verified,oauth2_scheme, update_user_email, update_user_password
import logging

user_manager_router = APIRouter(tags=["Users"])

@user_manager_router.post("/register", description="Create a new user in the system.")
async def register(
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    locale: str = Query('ua', description="Language for the confirmation message. Options: 'ua' for Ukrainian, 'en' for English.")
):
    response = await create_user(db, email, password, locale)
    logging.debug(f"Retrieved response: {response}")

    # Тепер треба отримувати дані з content
    return response

# Додаємо OAuth2 схему для Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

from pydantic import BaseModel

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

# Авторизація (отримання JWT-токена)
@user_manager_router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    email = form_data.username
    auth_result = authenticate_user(db, email, form_data.password)

    if isinstance(auth_result, JSONResponse):
        raise HTTPException(
            status_code=auth_result.status_code,
            detail=auth_result.body.decode() if hasattr(auth_result, "body") else auth_result.content
        )

    return auth_result["data"]  # повертаємо саме доступ до токену


@user_manager_router.post("/login_with_email")
def login_with_email(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    result = authenticate_user(db, email, password)

    # Якщо це JSONResponse — тобто помилка, просто повертаємо її
    if isinstance(result, JSONResponse):
        return result

    # Інакше — успішна автентифікація
    return result

@user_manager_router.get("/verify_email", response_class=JSONResponse)
async def verify_email(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        # Декодуємо токен
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        
        if email is None:
            return JSONResponse(
                status_code=400,
                content={
                    "detail": "Invalid token",
                    "data": None
                }
            )

        # Перевіряємо, чи існує користувач з таким email
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return JSONResponse(
                status_code=404,
                content={
                    "detail": "User not found",
                    "data": None
                }
            )

        # Перевіряємо, чи вже підтверджено email
        if user.is_email_verified:
            return JSONResponse(
                status_code=200,
                content={
                    "detail": "Email already verified ✅",
                    "data": None
                }
            )

        # Оновлюємо статус підтвердження email
        user.is_email_verified = True
        db.commit()

        # Повертаємо успішну відповідь
        return JSONResponse(
            status_code=200,
            content={
                "detail": "Thank you! Your email has been verified 🎉",
                "data": None
            }
        )

    except jwt.PyJWTError:
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Invalid or expired token",
                "data": None
            }
        )

@user_manager_router.get("/profile")
def get_profile(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    logging.debug("Received request for profile with token: %s", token)  # Логування отриманого токена

    if not token:
        logging.error("Token is missing.")
        return JSONResponse(status_code=400, content={"detail": "Token is missing"})  # Повертання помилки через JSONResponse

    current_user = get_current_user(token, db)  # Викликаємо функцію для отримання поточного користувача
    
    # Якщо current_user є JSONResponse (помилка в get_current_user), то просто повертаємо його
    if isinstance(current_user, JSONResponse):
        return current_user  # Повертаємо JSONResponse помилки

    logging.debug("User found: %s", current_user.email)  # Логування знайденого користувача

    # Повертаємо дані користувача через JSONResponse
    return JSONResponse(
        status_code=200,
        content={
            "detail": "User retrieved successfully",
            "data": {
                "id": current_user.id,
                "email": current_user.email
            }
        }
    )

@user_manager_router.get("/is_activated")
def is_user_activated(user_id: int, db: Session = Depends(get_db)):
    try:
        is_verified = is_user_verified(user_id, db)  # Перевірка, чи користувач активований
        return JSONResponse(
            status_code=200,
            content={"is_activated": is_verified}  # Повертаємо статус активації користувача
        )
    except Exception as e:
        logging.error("Unexpected error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )

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

    try:
        current_user = get_current_user(token, db)
        result = update_user_password(db, current_user, old_password, new_password)
        return JSONResponse(status_code=200, content=result)

    except HTTPException as e:
        logging.error(f"Error updating password: {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail,"data":""})

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error","data":""})
    

@user_manager_router.put("/change-email", summary="Changes the email for the currently authenticated user")
def change_email(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
    password: str = Form(...),
    new_email: str = Form(...)
):
    """
    **Changes the email for the currently authenticated user**
    
    - **Headers**: `Authorization: Bearer <token>`
    - **Parameters**:
        - `password`: Current password.
        - `new_email`: New email.
    - **Response**:
        - `200 OK`: Email changed successfully.
        - `400 Bad Request`: Incorrect password.
        - `401 Unauthorized`: User is not authenticated.
    """

    try:
        current_user = get_current_user(token, db)
        result = update_user_email(db, current_user, password, new_email)
        return JSONResponse(status_code=200, content=result)

    except HTTPException as e:
        logging.error(f"Error updating email: {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})