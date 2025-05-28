import os
from fastapi.testclient import TestClient
import pytest
from app.database.database import engine
from app.main import app
from app.seeding_manager import seed
os.environ["TESTING"] = "1"
client = TestClient(app)
@pytest.fixture(scope="session", autouse=True)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"detail": "FastAPI"}