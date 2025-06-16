import os

from dotenv import load_dotenv
load_dotenv()

SERVER_URL = os.getenv("SERVER_URL")
if os.getenv("TESTING") == "1":
    DATABASE_URL = os.getenv("TEST_DATABASE_URL")
    UPLOAD_DIR = "uploads_tests"
else:
    DATABASE_URL = os.getenv("DATABASE_URL")
    UPLOAD_DIR = "uploads"


OPEN_WEATHER_API_KEY = os.getenv("OPEN_WEATHER_API_KEY")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_CLOTHING_ITEMS_COUNT = 100
MAX_CLOTHING_COMBINATIONS_COUNT = 50