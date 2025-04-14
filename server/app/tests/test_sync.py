import json
import os
import pytest
from fastapi.testclient import TestClient
import io
from app.main import app
from app.database import SessionLocal, Base, engine, get_db
from app.user_manager.user import User
from app.close_manager.clothing_combination import ClothingCombination
from app.close_manager.сlothing_item import ClothingItem
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

# Основний тест
def test_sync_data_with_files(db_session: Session, auth_token):
    # Підготовка даних речей та комбінацій
    clothing_items_data = [
        {
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
            "price": 100.50,
            "is_favorite": True,
            "owner_id": 1
        }
    ]
    clothing_combinations_data = [
        {
            "name": "Test Combo",
            "item_filenames": ["test1.jpg"],
            "owner_id": 1
        }
    ]

    # Перетворення словників у JSON-рядки
    clothing_items_str = json.dumps(clothing_items_data)
    clothing_combinations_str = json.dumps(clothing_combinations_data)

    # Підготовка фейкового зображення
    file_content = b"fake image data"
    file = ("files", ("test1.jpg", io.BytesIO(file_content), "image/jpeg"))

    # Надсилання запиту з multipart/form-data
    response = client.post(
        "/syncronize",
        data={
            "clothing_items": clothing_items_str,
            "clothing_combinations": clothing_combinations_str
        },
        files=[file],
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

    
    assert len(items) == 1
    assert items[0].name == "Test Pants"
    assert items[0].filename.endswith(".jpg")

    assert len(combos) == 1
    assert combos[0].name == "Test Combo"
    assert len(combos[0].items) == 1

    # Перевірка, що файл існує на сервері
    saved_filename = items[0].filename
    file_path = os.path.join("uploads", saved_filename)
    assert os.path.exists(file_path), f"File {file_path} not found on server"

    # 🔄 Прибирання за собою (опційно)
    #os.remove(file_path)