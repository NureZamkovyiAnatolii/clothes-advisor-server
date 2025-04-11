import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import router
from app.user_manager.routes import user_manager_router  # Import routes
from app.close_manager.routes import close_router
# from app.photo_manager.routes import photo_router  # Import routes
from .database import engine
import logging
from fastapi.middleware.cors import CORSMiddleware

try:
    connection = engine.connect()
    print("✅ Successfully connected to the database!")
    app = FastAPI(debug=True)

    # Allow requests from React (localhost:3000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # or ["*"] for all
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    logging.basicConfig(level=logging.DEBUG)
    app.include_router(router)

    # Add routes from the user_manager module
    app.include_router(user_manager_router)
    app.include_router(close_router)
    app.mount("/uploads", StaticFiles(directory=os.path.abspath("uploads")), name="uploads")

    @app.get("/", tags=["Ping"])
    def read_root():
        return {"message": "FastAPI"}

except Exception as e:
    print(f"❌ Database connection error: {e}")
