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
    response = client.post("/login_with_email", data=login_data)
    assert response.status_code == 200, f"Error obtaining token: {response.json()}"

    # Extract token from response["data"]
    token_data = response.json().get("data")
    assert token_data, "Token data missing"

    token = token_data.get("access_token")
    assert token, "Access token not found in response"

    # Request to /profile with the token
    headers = {"Authorization": f"Bearer {token}"}
    profile_response = client.get("/profile", headers=headers)

    # Check the server response
    assert profile_response.status_code == 200, f"Error accessing profile: {profile_response.json()}"
    print("✅ Successfully retrieved profile:", profile_response.json())
