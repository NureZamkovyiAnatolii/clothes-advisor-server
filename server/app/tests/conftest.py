# tests/conftest.py
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    from app.database.database import engine
    from app.seeding_manager import seed
    print("🚀 Setup test database once for all tests")
    connection = engine.connect()
    seed.seed()  # Сідінг лише один раз
    yield
    print("🧹 Closing DB connection after all tests")
    connection.close()
