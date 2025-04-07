from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Завантажуємо змінні з .env файлу
load_dotenv()

# Отримуємо DATABASE_URL зі змінних середовища
DATABASE_URL = os.getenv("DATABASE_URL")

# Створюємо engine для підключення до бази даних
engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

# Створюємо SessionLocal для сесії
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Основний клас для створення таблиць
Base = declarative_base()

# Імпортуємо моделі
from app.user_manager.user import User

# Перевірка існуючих таблиць в БД
inspector = inspect(engine)
existing_tables = inspector.get_table_names()

# Виведення списку існуючих таблиць до створення нових
print("Існуючі таблиці в базі даних:")
for table in existing_tables:
    print(f"- {table}")

# Створення таблиць, якщо їх ще не існує
Base.metadata.create_all(bind=engine)

# Перевірка, чи були створені нові таблиці після виклику create_all
new_tables = set(Base.metadata.tables.keys()) - set(existing_tables)

# Виведення списку нових таблиць
if new_tables:
    print(f"Були створені нові таблиці: {', '.join(new_tables)}")
else:
    print("Таблиці вже існують або не було створено нових.")

# Виведення таблиць, що є в Base після створення
print("Таблиці в Base після створення:")
for table in Base.metadata.tables:
    print(f"- {table}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
