
# Конфігурація SMTP
import logging
import os
import random
import string
from typing import Optional
from fastapi import HTTPException
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from requests import Session

from app.model.user import User

SERVER_URL = os.getenv("SERVER_URL")
conf = ConnectionConfig(
    MAIL_USERNAME="clothesadvisor0@gmail.com",
    MAIL_PASSWORD="juyn xudt moyv uwcx",
    MAIL_FROM="clothesadvisor0@gmail.com",
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,

)

# Словник для збереження кодів підтвердження (краще використовувати БД)
verification_codes = {}

def generate_verification_code(length=6) -> str:
    """Генерує випадковий 6-значний код підтвердження."""
    code  = ''.join(random.choices(string.digits, k=length))
    logging.debug(f"Generated key  {code} for user_id ")
    return code

async def send_verification_code(email: str, user_id: int, locale: Optional[str] = "en"):
    """Надсилає код підтвердження на email, враховуючи локалізацію (ua або en)."""
    
    # Генерація коду підтвердження
    code = generate_verification_code()
    verification_codes[user_id] = code  # Збереження коду (краще використовувати БД)
    
    # Текст повідомлення залежно від локалізації
    if locale == "en":
        subject = "Your verification code"
        body = f"Your verification code is: {code}"
    else:
        # За замовчуванням (якщо не en, то ua)
        subject = "Ваш код підтвердження"
        body = f"Ваш код підтвердження: {code}"

    # Створення повідомлення
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype="html",
    )
    
    # Відправка повідомлення
    fm = FastMail(conf)
    await fm.send_message(message)

async def send_verification_link(email: str, token: str, locale: Optional[str] = "en"):
    """
    Надсилає лінк для підтвердження email.
    :param email: Адреса електронної пошти
    :param token: Токен підтвердження
    :param locale: Локалізація повідомлення
    """
    verification_url = f"{SERVER_URL}/verify_email?token={token}"

    if locale == "en":
        subject = "Email verification"
        body = f"Click the link to verify your email: <a href='{verification_url}'>{verification_url}</a>"
    else:
        subject = "Підтвердження електронної пошти"
        body = f"Перейдіть за посиланням, щоб підтвердити email: <a href='{verification_url}'>{verification_url}</a>"

    # Створення повідомлення
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=body,
        subtype="html",
    )

    fm = FastMail(conf)
    await fm.send_message(message)


async def verify_code(user_id: int, code: str, db: Session) -> bool:
    logging.debug(f"Поточний список кодів підтвердження: {verification_codes}")
    """Перевіряє код підтвердження для user_id і оновлює статус верифікації email у БД."""
    logging.debug(f"Перевірка коду {code} для user_id {user_id}")
    stored_code = verification_codes.get(user_id)
    logging.debug(f"Stored key  {stored_code} for user_id {user_id}")
    if stored_code == code:
        logging.debug(f"Код підтверджено для user_id {user_id}")
        del verification_codes[user_id]  # Видаляємо код після успішної перевірки
        
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_email_verified = True
            db.add(user)
            db.commit()
            db.refresh(user)
            logging.debug(f"Email користувача {user_id} підтверджено у БД")
            return True
    logging.debug(f"Невірний код або користувача {user_id} не знайдено")
    return False

async def send_password_change_form(
        email: str,
        subject: str,
        html_content: str,
    ):
    """
    Sends an email with a password change form.

    - **Parameters**:
        - `email`: Recipient's email address.
        - `subject`: Subject of the email.
        - `html_content`: The HTML content for the email body.
        - `locale`: The language of the email content (default is 'ua').

    This function sends an email using FastMail service.
    """
    message = MessageSchema(
        subject=subject,
        recipients=[email],
        body=html_content,
        subtype="html",
        charset="utf-8"
    )

    # Використовуємо FastMail для відправки email
    fm = FastMail(conf)

    try:
        await fm.send_message(message)
        return {"detail": "Password reset email sent successfully."}
    except Exception as e:
        # Логування або обробка помилок
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")