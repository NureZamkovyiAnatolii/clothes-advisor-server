from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_profile_with_token():
    # Login data (replace with real credentials)
    login_data = {
        "email": "zamochek9120@gmail.com",
        "password": "123"
    }

    # Get the token
    response = client.post("/login_with_email", data=login_data) # use http://127.0.0.1:8000/token in real project  
    assert response.status_code == 200, f"Error obtaining token: {response.json()}"

    # Get the token
    token = response.json().get("access_token")
    assert token, "Token not obtained"

    # Request to /profile with the token
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = client.get("/profile", headers=headers)

    # Check the server response
    assert profile_response.status_code == 200, f"Error accessing profile: {profile_response.json()}"
    print("✅ Successfully retrieved profile:", profile_response.json())
