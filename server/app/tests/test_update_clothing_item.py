import json
import os
import pytest
from fastapi.testclient import TestClient
import io
from app.main import app
from app.database import SessionLocal, Base, engine, get_db
from app.model import *
from sqlalchemy.orm import Session


client = TestClient(app)

# Фікстура для тестової бази
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Переопреділяємо залежність
    app.dependency_overrides[get_db] = lambda: db

    yield db

    db.close()
    app.dependency_overrides.clear()  # очищаємо після тесту

# Фікстура для створення користувача і отримання токена
@pytest.fixture
def auth_token(db_session: Session):
    # Login data (replace with real credentials)
    login_data = {
        "email": "test@gmail.com",
        "password": "pass"
    }

    # Get the token
    response = client.post("/login_with_email", data=login_data) # use http://127.0.0.1:8000/token in real project  
    assert response.status_code == 200, f"Error obtaining token: {response.json()}"

    # Get the token
    token = response.json()["data"]["access_token"]

    assert token, "Token not obtained"

    # Request to /profile with the token
    headers = {"Authorization": f"Bearer {token}"}
    return headers



def test_update_clothing_item(db_session, auth_token):
 # 2. Дані для оновлення
    update_payload = {
        "name": "Updated Shirt",
        "category": "tshirt",
        "season": "spring",
        "red": "200",
        "green": "150",
        "blue": "100",
        "material": "Linen",
        "brand": "Uniqlo",
        "purchase_date": "2024-02-02",
        "price": "39.99",
        "is_favorite": True
    }

    # 3. PUT-запит
    response = client.put(f"/clothing-items/{12}", json=update_payload, headers=auth_token)

    # 4. Перевірка відповіді
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["updated_item"]["name"] == "Updated Shirt"
    assert data["updated_item"]["price"] == 39.99
    assert data["updated_item"]["is_favorite"] is True
    assert data["updated_item"]["brand"] == "Uniqlo"