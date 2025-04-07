from fastapi import FastAPI
from app.routes import router
from app.user_manager.routes import user_manager_router  # Імпортуємо маршрути
#from app.photo_manager.routes import photo_router  # Імпортуємо маршрути
from .database import engine
import logging

try:
    connection = engine.connect()
    print("✅Підключення до бази даних успішне!")
    app = FastAPI(debug=True)
    logging.basicConfig(level=logging.DEBUG)
    app.include_router(router)

    # Додаємо маршрути з модуля user_manager
    app.include_router(user_manager_router)
 #   app.include_router(photo_router)
    print("Connected to database!")
    @app.get("/")
    def read_root():
        return {"message": "FastAPI"}
except Exception as e:
    print(f"❌ Помилка підключення до бази даних: {e}")




