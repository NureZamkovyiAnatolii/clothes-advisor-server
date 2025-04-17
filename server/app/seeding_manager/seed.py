from datetime import date, datetime, timezone
import os
import shutil

import requests
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
    image_urls = [
            "https://fahrenheit.ua/files/products/4x7a3262.1000x1000.jpg",
            "https://lingerie.ua/files/product/0/19020/19020.jpg",
            "https://preview.free3d.com/img/2014/08/2162617793575388491/fulrgt7a.jpg",
            "https://tornado.kiev.ua/image/cache/catalog/image/cache/new/41210_2-1000x1200.webp"
            
        ]
    os.makedirs(uploads_dir, exist_ok=True)

    for item_data in items_data:
        
        os.makedirs("uploads", exist_ok=True)
        for idx, item_data in enumerate(items_data):
            image_url = image_urls[idx]
            dest_file = os.path.join("uploads", item_data["filename"])

            if not os.path.exists(dest_file):
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                    }
                    response = requests.get(image_url, headers=headers)
                    response.raise_for_status()

                    with open(dest_file, "wb") as f:
                        f.write(response.content)

                    print(f"📥 Downloaded image as {item_data['filename']} to uploads/")
                except Exception as e:
                    print(f"❌ Failed to download image from {image_url}: {e}")
        existing = db.query(ClothingItem).filter_by(filename=item_data["filename"]).first()
        if existing:
            print(f"ℹ️ ClothingItem {item_data['filename']} already exists. Skipping.")
            continue

        dest_file = os.path.join(uploads_dir, item_data["filename"])

        


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
