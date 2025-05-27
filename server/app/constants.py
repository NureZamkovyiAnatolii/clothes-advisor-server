import os

from dotenv import load_dotenv
load_dotenv()

SERVER_URL = os.getenv("SERVER_URL")
UPLOAD_DIR = "uploads"
OPEN_WEATHER_API_KEY = os.getenv("OPEN_WEATHER_API_KEY")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")