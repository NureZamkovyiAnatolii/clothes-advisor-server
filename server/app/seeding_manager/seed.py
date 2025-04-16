from datetime import date, datetime, timezone
import os
import shutil
from app.database import get_db
from app.model.user import User
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.user_manager.user_controller import hash_password
from app.model import *

def seed_users(db: Session):
    users_data = [
        {
            "email": "test@gmail.com",
            "password": "pass",  
            "is_email_verified": True
        },
        {
            "email": "bob@example.com",
            "password": "pass",
            "is_email_verified": False
        },
        {
            "email": "charlie@example.com",
            "password": "pass",
            "is_email_verified": True
        }
    ]

    for data in users_data:
        existing_user = db.query(User).filter_by(email=data["email"]).first()
        if existing_user:
            print(f"ℹ️ User {data['email']} already exists. Skipping.")
            continue

        user = User(
            email=data["email"],
            password=hash_password(data["password"]),
            created_at=datetime.now(timezone.utc),
            synchronized_at=datetime.now(timezone.utc),
            is_email_verified=data["is_email_verified"]
        )

        db.add(user)
        try:
            db.commit()
            print(f"✅ User {data['email']} seeded successfully.")
        except IntegrityError:
            db.rollback()
            print(f"❌ Failed to seed user {data['email']} (possible duplicate).")

def seed_clothing_items(db: Session):
    items_data = [
        {
            "filename": "1.jpg",
            "name": "Зимові штани",
            "category": CategoryEnum.pants,
            "season": SeasonEnum.winter,
            "red": 100, "green": 100, "blue": 255,
            "material": "Поліестер",
            "brand": "North Face",
            "purchase_date": date(2023, 12, 1),
            "price": 1200.50,
            "is_favorite": True,
            "owner_id": 1
        },
        {
            "filename": "2.jpg",
            "name": "Літній піджак",
            "category": CategoryEnum.jacket,
            "season": SeasonEnum.summer,
            "red": 230, "green": 200, "blue": 150,
            "material": "Бавовна",
            "brand": "H&M",
            "purchase_date": date(2022, 7, 15),
            "price": 299.99,
            "is_favorite": False,
            "owner_id": 1
        },
        {
            "filename": "3.jpg",
            "name": "Осіннє плаття",
            "category": CategoryEnum.dress,
            "season": SeasonEnum.autumn,
            "red": 150, "green": 75, "blue": 0,
            "material": "Шерсть",
            "brand": "Zara",
            "purchase_date": date(2023, 10, 5),
            "price": 450.00,
            "is_favorite": True,
            "owner_id": 2
        },
        {
            "filename": "4.jpg",
            "name": "Футболка",
            "category": CategoryEnum.tshirt,
            "season": SeasonEnum.spring,
            "red": 255, "green": 255, "blue": 255,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": False,
            "owner_id": 3
        }
    ]

    uploads_dir = os.path.join(os.getcwd(), "uploads")
    source_dir = os.path.join(os.getcwd(), "seed_data")  # Звідки брати файли

    os.makedirs(uploads_dir, exist_ok=True)

    for item_data in items_data:
        existing = db.query(ClothingItem).filter_by(filename=item_data["filename"]).first()
        if existing:
            print(f"ℹ️ ClothingItem {item_data['filename']} already exists. Skipping.")
            continue

        # Копіювання файлу в папку uploads/
        src_file = os.path.join(source_dir, item_data["filename"])
        dest_file = os.path.join(uploads_dir, item_data["filename"])

        if not os.path.exists(dest_file):
            try:
                with open(dest_file, 'w') as f:
                    pass  # створюємо порожній файл
                print(f"📁 Created empty file {item_data['filename']} in uploads/")
            except Exception as e:
                print(f"❌ Failed to create file {dest_file}: {e}")


        item = ClothingItem(**item_data)
        db.add(item)

    db.commit()
    print("✅ Clothing items seeded.")

def seed_clothing_combinations(db: Session):
    combinations_data = [
        {
            "name": "Зимова прогулянка",
            "owner_id": 1,
            "item_ids": [1, 2]
        },
        {
            "name": "Офісний образ",
            "owner_id": 2,
            "item_ids": [3, 4]
        },
        {
            "name": "Весняна прогулянка",
            "owner_id": 3,
            "item_ids": [5]
        }
    ]

    for combo_data in combinations_data:
        existing = db.query(ClothingCombination).filter_by(name=combo_data["name"]).first()
        if existing:
            print(f"ℹ️ Combination '{combo_data['name']}' already exists. Skipping.")
            continue

        combination = ClothingCombination(
            name=combo_data["name"],
            owner_id=combo_data["owner_id"]
        )

        # Додаємо речі по item_ids
        for item_id in combo_data["item_ids"]:
            item = db.query(ClothingItem).filter_by(id=item_id).first()
            if item:
                combination.items.append(item)

        db.add(combination)

    db.commit()
    print("✅ Clothing combinations seeded by ID.")

def seed():
    db = next(get_db())
    try:
        seed_users(db)
        seed_clothing_items(db)
        seed_clothing_combinations(db)
        print("✅ All data seeded successfully.")
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
