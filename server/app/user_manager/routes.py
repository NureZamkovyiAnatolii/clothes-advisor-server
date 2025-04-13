from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from sqlalchemy.orm import Session
from app.database import get_db
from app.user_manager.user import User
from .user_controller import ALGORITHM, SECRET_KEY, create_user, authenticate_user, get_current_user, hash_password, is_user_verified, oauth2_scheme, send_password_reset_email, update_user_email, update_user_password
import logging

user_manager_router = APIRouter(tags=["Users"])


@user_manager_router.post("/register", description="Create a new user in the system.")
async def register(
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    locale: str = Query(
        'en', description="Language for the confirmation message. Options: 'ua' for Ukrainian, 'en' for English.")
):
    response = await create_user(db, email, password, locale)
    logging.debug(f"Retrieved response: {response}")

    # Тепер треба отримувати дані з content
    return response

# Додаємо OAuth2 схему для Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


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
            detail=auth_result.body.decode() if hasattr(
                auth_result, "body") else auth_result.content
        )

    return auth_result["data"]  # повертаємо саме доступ до токену


@user_manager_router.post("/login_with_email")
def login_with_email(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    result = authenticate_user(db, email, password)
    user = db.query(User).filter(User.email == email).first()
    if user.is_email_verified == False:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Email not verified",
                "data": None
            }
        )

    # Якщо це JSONResponse — тобто помилка, просто повертаємо її
    if isinstance(result, JSONResponse):
        return result

    # Інакше — успішна автентифікація
    return result


@user_manager_router.get("/verify_email", response_class=JSONResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
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
    logging.debug("Received request for profile with token: %s",
                  token)  # Логування отриманого токена

    if not token:
        logging.error("Token is missing.")
        # Повертання помилки через JSONResponse
        return JSONResponse(status_code=400, content={"detail": "Token is missing"})

    # Викликаємо функцію для отримання поточного користувача
    current_user = get_current_user(token, db)

    # Якщо current_user є JSONResponse (помилка в get_current_user), то просто повертаємо його
    if isinstance(current_user, JSONResponse):
        return current_user  # Повертаємо JSONResponse помилки

    # Логування знайденого користувача
    logging.debug("User found: %s", current_user.email)

    # Повертаємо дані користувача через JSONResponse
    return JSONResponse(
        status_code=200,
        content={
            "detail": "User retrieved successfully",
            "data": {
                "id": current_user.id,
                "email": current_user.email,
                "synchronized_at": current_user.synchronized_at.isoformat() if current_user.synchronized_at else None

            }
        }
    )

@user_manager_router.post("/synchronize")
def synchronize_user_data(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    logging.debug("Received request for synchronization with token: %s",
                  token)
    current_user = get_current_user(token, db)

    # Якщо current_user є JSONResponse (помилка в get_current_user), то просто повертаємо його
    if isinstance(current_user, JSONResponse):
        return current_user  # Повертаємо JSONResponse помилки

    # Логування знайденого користувача
    logging.debug("User found: %s", current_user.email)
    current_user.synchronized_at = datetime.now(timezone.utc)
    db.commit()
    return JSONResponse(
    status_code=200,
    content={
        "detail": "Synchronized data updated",
        "data": {
            "synchronized_at": current_user.synchronized_at.isoformat() if current_user.synchronized_at else None
        }
    }
)

    

@user_manager_router.get("/is_activated")
def is_user_activated(user_id: int, db: Session = Depends(get_db)):
    try:
        # Перевірка, чи користувач активований
        is_verified = is_user_verified(user_id, db)
        return JSONResponse(
            status_code=200,
            # Повертаємо статус активації користувача
            content={"is_activated": is_verified}
        )
    except Exception as e:
        logging.error("Unexpected error: %s", str(e))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )


@user_manager_router.post("/forgot-password", summary="Initiates a password reset process")
async def forgot_password(
        email: str = Form(...),
        # Мова для повідомлення (за замовчуванням українська)
        locale: str = Query('en'),
        db: Session = Depends(get_db)
):
    """
    **Initiates the password reset process for the user**

    - **Parameters**:
        - `email`: The email address associated with the account.
        - `password`: The current password of the user.
        - `locale`: Language for the confirmation message. Options: 'ua' for Ukrainian, 'en' for English.

    - **Response**:
        - `200 OK`: Password reset link sent successfully.
        - `400 Bad Request`: Invalid email format.
        - `404 Not Found`: User not found.
        - `500 Internal Server Error`: Unexpected server error.
    """

    try:
        # Викликаємо вже готову функцію для відправки email з формою скидання пароля
        response = await send_password_reset_email(
            db=db,
            email=email,
            locale=locale
        )
        return response

    except HTTPException as e:
        # Повертаємо помилки, якщо вони виникають
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    except Exception as e:
        # Обробка загальних помилок
        return JSONResponse(status_code=500, content={"detail": f"Internal server error: {str(e)}"})


@user_manager_router.get("/change-password-form", summary="Gets the password change form for the currently authenticated user", response_class=HTMLResponse, include_in_schema=False)
async def get_change_password_form_from_forgot_password(
    db: Session = Depends(get_db),
    token: str = Query(),
    locale: Optional[str] = 'en'
):
    """
    **Gets the form for changing the password for the currently authenticated user**

    - **Headers**: `Authorization: Bearer <token>`
    """
    try:
        # Отримуємо користувача на основі токену
        current_user = get_current_user(token, db)

        if locale == "ua":
            # Створюємо HTML форму для зміни пароля
            html_form = f"""
            <html>
                <body>
                    <h2>Зміна пароля</h2>
                    <form id="changePasswordForm"action="/change-password-form" method="PUT" onsubmit="handleSubmit(event)">
                        <label for="new_password">Новий пароль:</label>
                        <input type="password" id="new_password" name="new_password" required><br><br>
                        <label for="confirm_password">Підтвердьте новий пароль:</label>
                        <input type="hidden" id="token" value="{{ token }}">
                        <input type="password" id="confirm_password" name="confirm_password" required><br><br>
                        <input type="submit" value="Змінити пароль">
                    </form>
                    <script>
                async function handleSubmit(event) {{
                    event.preventDefault(); // Запобігає стандартній відправці форми
                    
                    // Отримання даних з форми
                    const form = document.getElementById("changePasswordForm");
                    const formData = new FormData(form);
                    
                    // Отримуємо токен з хардкоду або вставляємо як з серверу
                    // Отримання параметрів з URL
                    const urlParams = new URLSearchParams(window.location.search);
                    // Отримуємо значення параметра "token"
                    const token = urlParams.get('token');
                    // Перевірка наявності токена
    if (token) {{
        console.log("Token:", token);
    }} else {{
        console.log("Token not found in URL.");
    }}
                    // Виконання запиту до серверу
                    try {{
                        const response = await fetch("/change-password-form?token=" + token, {{
                            method: "PUT", // Відправляємо запит методом PUT
                            body: formData
                        }});

                        if (response.ok) {{
                            // Якщо зміна пароля успішна, перенаправляємо на сторінку успіху
                            window.location.href = "/change-password-success";
                        }} else {{
                            // Якщо щось пішло не так, вивести повідомлення
                            alert("Щось пішло не так. Спробуйте ще раз.");
                        }}
                    }} catch (error) {{
                        console.error("Error:", error);
                        alert("Помилка при відправці запиту.");
                    }}
                }}
            </script>
                </body>
            </html>

            """
        else:
            html_form = f"""
            <html>
                <body>
                    <h2>Password change form</h2>
                    <form id="changePasswordForm"action="/change-password-form" method="PUT" onsubmit="handleSubmit(event)">
                        <label for="new_password">New password:</label>
                        <input type="password" id="new_password" name="new_password" required><br><br>
                        <label for="confirm_password">Confirm new password:</label>
                        <input type="hidden" id="token" value="{{ token }}">
                        <input type="password" id="confirm_password" name="confirm_password" required><br><br>
                        <input type="submit" value="Submit">
                    </form>
                    <script>
                async function handleSubmit(event) {{
                    event.preventDefault();
                    
                    const form = document.getElementById("changePasswordForm");
                    const formData = new FormData(form);
                    
                    const urlParams = new URLSearchParams(window.location.search);
                    const token = urlParams.get('token');
    if (token) {{
        console.log("Token:", token);
    }} else {{
        console.log("Token not found in URL.");
    }}
                    try {{
                        const response = await fetch("/change-password-form?token=" + token, {{
                            method: "PUT", // Відправляємо запит методом PUT
                            body: formData
                        }});

                        if (response.ok) {{
                            window.location.href = "/change-password-success";
                        }} else {{
                            alert("Щось пішло не так. Спробуйте ще раз.");
                        }}
                    }} catch (error) {{
                        console.error("Error:", error);
                        alert("Помилка при відправці запиту.");
                    }}
                }}
            </script>
                </body>
            </html>

            """
        return HTMLResponse(content=html_form)

    except Exception as e:
        logging.error(f"Error getting password change form: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@user_manager_router.put("/change-password-form", summary="Changes the password for the currently authenticated user", include_in_schema=False)
async def change_password_form_from_forgot_password(
    db: Session = Depends(get_db),
    token: str = Query(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    """
    **Changes the password for the currently authenticated user after form submission**

    - **Headers**: `Authorization: Bearer <token>`
    - **Parameters**: `current_password`, `new_password`, `confirm_password`
    """
    try:
        # Перевірка чи новий пароль та підтвердження пароля співпадають
        if new_password != confirm_password:
            raise HTTPException(
                status_code=400, detail="New password and confirm password do not match")

        # Отримуємо користувача на основі токену
        current_user = get_current_user(token, db)
    except HTTPException as e:
        logging.error(f"Error in password change: {e.detail}")
        raise e
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

        # Пошук користувача за ID
    user = db.query(User).filter(User.id == current_user.id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Оновлюємо пароль (можливо, потрібно зашифрувати пароль перед збереженням)
    # Увага: тут потрібно зашифрувати пароль
    user.password = hash_password(new_password)
    db.commit()

    return RedirectResponse(url="/change-password-success", status_code=303)


@user_manager_router.get("/change-password-success", summary="Success page for password change", response_class=HTMLResponse, include_in_schema=False)
async def change_password_success(locale: Optional[str] = 'en'):
    if locale=="ua":
        return HTMLResponse(content="<html><body><h2>Пароль успішно змінено!</h2></body></html>")
    else:
        return HTMLResponse(content="<html><body><h2>Password changed!</h2></body></html>")


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
        result = update_user_password(
            db, current_user, old_password, new_password)
        return JSONResponse(status_code=200, content=result)

    except HTTPException as e:
        logging.error(f"Error updating password: {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail, "data": ""})

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "data": ""})


@user_manager_router.put("/change-email", summary="Changes the email for the currently authenticated user")
async def change_email(
        db: Session = Depends(get_db),
        token: str = Depends(oauth2_scheme),
        password: str = Form(...),
        new_email: str = Form(...),
        locale: str = Query('ua')):
    """
    **Changes the email for the currently authenticated user**
    """
    try:
        current_user = get_current_user(token, db)
        if current_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        logging.debug(current_user.email)
        result = await update_user_email(
            db, current_user, password, new_email, locale)
        return result  # Просто повертаємо результат з update_user_email

    except HTTPException as e:
        logging.error(f"Error updating email: {e.detail}")
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
