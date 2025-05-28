import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.model import *
os.environ["TESTING"] = "1"
client = TestClient(app)
# Фікстура для створення користувача і отримання токена
@pytest.fixture
def auth_token():
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

def test_recommendations_weather_match(auth_token):

    payload = {
        "lat": 50.45,
        "lon": 30.523,
        "target_time": "2025-05-26 12:00:00",
        "red": "",
        "green": "",
        "blue": "",
        "palette_types": [""],
        "event": "",
        "include_favorites": False
    }

    response = client.post("/recommendations", json=payload, headers=auth_token)
    assert response.status_code == 200, f"Unexpected error: {response.json()}"

    data = response.json()
    assert "data" in data
    outfits = data["data"]["outfits"]
    assert outfits, "No outfits returned"
    # Шукаємо перший item в першому outfit
    first_outfit = outfits[0]
    items = first_outfit["items"]
    assert items, "No items in first outfit"

    # Беремо перший item
    first_item = items[0]
    final_match = first_item.get("final_match")
    assert final_match is not None, "Missing final_match"
    assert isinstance(final_match, dict), "final_match is not a dict"

    # 🔍 Тестуємо тип відповідності
    assert final_match.get("type") == "weather_match", f"Expected 'weather_match', got: {final_match.get('type')}"
def test_recommendations_color_match(auth_token):

    payload = {
        "lat": None ,
        "lon": None ,
        "target_time": "",
        "red": "100",
        "green": "100",
        "blue": "100",
        "palette_types": ["analogous"],
        "event": None,
        "include_favorites": False
    }

    response = client.post("/recommendations", json=payload, headers=auth_token)
    assert response.status_code == 200, f"Unexpected error: {response.json()}"

    data = response.json()
    assert "data" in data
    outfits = data["data"]["outfits"]
    assert outfits, "No outfits returned"
    # Шукаємо перший item в першому outfit
    first_outfit = outfits[0]
    items = first_outfit["items"]
    assert items, "No items in first outfit"

    # Беремо перший item
    first_item = items[0]
    final_match = first_item.get("final_match")
    assert final_match is not None, "Missing final_match"
    assert isinstance(final_match, dict), "final_match is not a dict"

    # 🔍 Тестуємо тип відповідності
    assert final_match.get("type") == "color_match", f"Expected 'color_match', got: {final_match.get('type')}"

def test_recommendations_event_match(auth_token):

    payload = {
        "lat": None ,
        "lon": None ,
        "target_time": "",
        "red":  None,
        "green":  None,
        "blue":  None,
        "palette_types": [""],
        "event": "home_relax",
        "include_favorites": False
    }

    response = client.post("/recommendations", json=payload, headers=auth_token)
    assert response.status_code == 200, f"Unexpected error: {response.json()}"

    data = response.json()
    assert "data" in data
    outfits = data["data"]["outfits"]
    assert outfits, "No outfits returned"
    # Шукаємо перший item в першому outfit
    first_outfit = outfits[0]
    items = first_outfit["items"]
    assert items, "No items in first outfit"

    # Беремо перший item
    first_item = items[0]
    final_match = first_item.get("final_match")
    assert final_match is not None, "Missing final_match"
    assert isinstance(final_match, dict), "final_match is not a dict"

    # 🔍 Тестуємо тип відповідності
    assert final_match.get("type") == "event_match", f"Expected 'event_match', got: {final_match.get('type')}"

def test_recommendations_color_event_match(auth_token):

    payload = {
        "lat": None ,
        "lon": None ,
        "target_time": "",
        "red": "100",
        "green": "100",
        "blue": "100",
        "palette_types": ["analogous"],
        "event": "home_relax",
        "include_favorites": False
    }

    response = client.post("/recommendations", json=payload, headers=auth_token)
    assert response.status_code == 200, f"Unexpected error: {response.json()}"

    data = response.json()
    assert "data" in data
    outfits = data["data"]["outfits"]
    assert outfits, "No outfits returned"
    # Шукаємо перший item в першому outfit
    first_outfit = outfits[0]
    items = first_outfit["items"]
    assert items, "No items in first outfit"

    # Беремо перший item
    first_item = items[0]
    final_match = first_item.get("final_match")
    assert final_match is not None, "Missing final_match"
    assert isinstance(final_match, dict), "final_match is not a dict"

    # 🔍 Тестуємо тип відповідності
    assert final_match.get("type") == "color_event_match", f"Expected 'color_event_match', got: {final_match.get('type')}"

def test_recommendations_weather_event_match(auth_token):

    payload = {
        "lat": 50.45,
        "lon": 30.523,
        "target_time": "2025-05-26 12:00:00",
        "red": "100",
        "green": "",
        "blue": "",
        "palette_types": [""],
        "event": "casual_walk",
        "include_favorites": False
    }

    response = client.post("/recommendations", json=payload, headers=auth_token)
    assert response.status_code == 200, f"Unexpected error: {response.json()}"

    data = response.json()
    assert "data" in data
    outfits = data["data"]["outfits"]
    assert outfits, "No outfits returned"
    # Шукаємо перший item в першому outfit
    first_outfit = outfits[0]
    items = first_outfit["items"]
    assert items, "No items in first outfit"

    # Беремо перший item
    first_item = items[0]
    final_match = first_item.get("final_match")
    assert final_match is not None, "Missing final_match"
    assert isinstance(final_match, dict), "final_match is not a dict"

    # 🔍 Тестуємо тип відповідності
    assert final_match.get("type") == "weather_event_match", f"Expected 'weather_event_match', got: {final_match.get('type')}"

def test_recommendations_color_weather_match(auth_token):

    payload = {
        "lat": 50.45,
        "lon": 30.523,
        "target_time": "2025-05-26 12:00:00",
        "red": "100",
        "green": "150",
        "blue": "200",
        "palette_types": ["analogous"],
        "event": "",
        "include_favorites": False
    }

    response = client.post("/recommendations", json=payload, headers=auth_token)
    assert response.status_code == 200, f"Unexpected error: {response.json()}"

    data = response.json()
    assert "data" in data
    outfits = data["data"]["outfits"]
    assert outfits, "No outfits returned"
    # Шукаємо перший item в першому outfit
    first_outfit = outfits[0]
    items = first_outfit["items"]
    assert items, "No items in first outfit"

    # Беремо перший item
    first_item = items[0]
    final_match = first_item.get("final_match")
    assert final_match is not None, "Missing final_match"
    assert isinstance(final_match, dict), "final_match is not a dict"

    # 🔍 Тестуємо тип відповідності
    assert final_match.get("type") == "color_weather_match", f"Expected 'color_weather_match', got: {final_match.get('type')}"

def test_recommendations_average_match(auth_token):

    payload = {
        "lat": 50.45,
        "lon": 30.523,
        "target_time": "2025-05-26 12:00:00",
        "red": "100",
        "green": "150",
        "blue": "200",
        "palette_types": ["analogous"],
        "event": "casual_walk",
        "include_favorites": False
    }

    response = client.post("/recommendations", json=payload, headers=auth_token)
    assert response.status_code == 200, f"Unexpected error: {response.json()}"

    data = response.json()
    assert "data" in data
    outfits = data["data"]["outfits"]
    assert outfits, "No outfits returned"
    # Шукаємо перший item в першому outfit
    first_outfit = outfits[0]
    items = first_outfit["items"]
    assert items, "No items in first outfit"

    # Беремо перший item
    first_item = items[0]
    final_match = first_item.get("final_match")
    assert final_match is not None, "Missing final_match"
    assert isinstance(final_match, dict), "final_match is not a dict"

    # 🔍 Тестуємо тип відповідності
    assert final_match.get("type") == "average_match", f"Expected 'average_match', got: {final_match.get('type')}"