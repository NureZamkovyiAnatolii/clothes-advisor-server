import json
import os
import pytest
from fastapi.testclient import TestClient
import io
from app.main import app
from app.database.database import SessionLocal, CA_Base, engine, get_db
from app.model import *
from sqlalchemy.orm import Session


client = TestClient(app)

# Фікстура для тестової бази
@pytest.fixture(scope="function")
def db_session():
    CA_Base.metadata.create_all(bind=engine)
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

# Основний тест
def test_sync_data_with_files(db_session: Session, auth_token):
    # Підготовка даних речей та комбінацій
    
    clothing_items_data = [
    {
        "id": 3,  
        "filename": "test1.jpg",
        "name": "Test Pants",
        "category": "pants",
        "season": "winter",
        "red": 100,
        "green": 100,
        "blue": 255,
        "material": "Cotton",
        "brand": "TestBrand",
        "purchase_date": "2023-01-01",
        "price": 1000.50,
        "is_favorite": True
    },
    {
        "id": 4,  
        "filename": "test2.jpg",
        "name": "Test Jacket",
        "category": "jacket",
        "season": "winter",
        "red": 50,
        "green": 50,
        "blue": 255,
        "material": "Wool",
        "brand": "TestBrand",
        "purchase_date": "2023-02-01",
        "price": 1500.75,
        "is_favorite": False
    }
]   
    # Старі ID речей
    clothing_combinations_data = [
    {   
        "id": 1,
        "name": "Test Combo",
        "item_ids": [3, 4]
    }
]

    # Перетворення словників у JSON-рядки
    clothing_items_str = json.dumps(clothing_items_data)
    clothing_combinations_str = json.dumps(clothing_combinations_data)

    # Підготовка фейкових зображень
    file1_content = b"fake image data 1"
    file2_content = b"fake image data 2"

    files = [
        ("files", ("test1.jpg", io.BytesIO(file1_content), "image/jpeg")),
        ("files", ("test2.jpg", io.BytesIO(file2_content), "image/jpeg")),
    ]

    # Надсилання запиту з multipart/form-data
    response = client.post(
        "/synchronize",
        data={
            "clothing_items": clothing_items_str,
            "clothing_combinations": clothing_combinations_str,
            "is_server_to_local": False 
        },
        files=files,
        headers=auth_token
    )

    # Перевірка статусу
    assert response.status_code == 200, f"Sync error: {response.text}"

    # Отримуємо користувача з бази
    user = db_session.query(User).filter_by(email="test@gmail.com").first()
    assert user is not None
    user_id = user.id

    # Перевіряємо, що збережено 1 річ і 1 комбінацію
    items = db_session.query(ClothingItem).filter_by(owner_id=user_id).all()
    combos = db_session.query(ClothingCombination).filter_by(owner_id=user_id).all()

    
    assert len(items) == 2
    assert items[0].name == "Test Pants"
    assert items[1].name == "Test Jacket"
    assert items[0].filename.endswith(".jpg")

    assert len(combos) == 1
    assert combos[0].name == "Test Combo"
    assert len(combos[0].items) == 2

    # Перевірка, що файл існує на сервері
    saved_filename = items[0].filename  

    # Витягуємо лише ім’я файлу
    import os
    from urllib.parse import urlparse

    filename_only = os.path.basename(urlparse(saved_filename).path)
    local_path = os.path.join("uploads_tests", filename_only)

    assert os.path.exists(local_path), f"File {local_path} not found on server"