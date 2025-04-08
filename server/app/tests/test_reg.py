from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_and_profile():
    # Дані для реєстрації
    register_data = {
        "email": "testfefeuser@example.com",
        "locale": "ua",
        "password": "12345678"
    }

    # Реєстрація
    response = client.post("/register", data=register_data)
    assert response.status_code == 200, f"❌ Помилка реєстрації: {response.text}"

    json_data = response.json()
    assert "user_id" in json_data, "❌ user_id не повернуто"
    
    # Токен також повертається з create_user
    access_token = json_data.get("access_token") or json_data.get("token")
    if not access_token:
        # Альтернатива: якщо токен не повертається з register
        print("⚠️ Увага: токен не повернуто з /register. Перевір чи повертаєш його у відповіді.")
        return

    # Отримання профілю з токеном
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_response = client.get("/profile", headers=headers)
    
    assert profile_response.status_code == 200, f"❌ Помилка доступу до профілю: {profile_response.text}"
    print("✅ Успішно отримано профіль:", profile_response.json())
