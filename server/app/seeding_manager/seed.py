from datetime import date, datetime, timezone
import os

import requests
from app.database.database import get_db
from app.model.user import User
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.user_manager.user_controller import hash_password
from app.model import *
from concurrent.futures import ThreadPoolExecutor

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
            "red": 0, "green": 0, "blue": 0,
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
            "red": 113, "green": 175, "blue": 222,
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
            "red": 255, "green": 255, "blue": 255,
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
        },
        {
            "filename": "5.jpg",
            "name": "Шорти",
            "category": CategoryEnum.shorts,
            "season": SeasonEnum.spring,
            "red": 0, "green": 0, "blue": 0,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": False,
            "owner_id": 1
        },
        {
            "filename": "6.jpg",
            "name": "Жовте худі",
            "category": CategoryEnum.hoodie,
            "season": SeasonEnum.autumn,
            "red": 252, "green": 186, "blue": 3,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": True,
            "owner_id": 1
        },
        {
            "filename": "7.jpg",
            "name": "Джинси",
            "category": CategoryEnum.jeans,
            "season": SeasonEnum.winter,
            "red": 53, "green": 23, "blue": 135,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": True,
            "owner_id": 1
        },
        {
            "filename": "8.jpg",
            "name": "Червона майка",
            "category": CategoryEnum.tank_top,
            "season": SeasonEnum.summer,
            "red": 255, "green": 0, "blue": 0,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": True,
            "owner_id": 1
        },
        {
            "filename": "9.jpg",
            "name": "Кросівки",
            "category": CategoryEnum.sneakers,
            "season": SeasonEnum.summer,
            "red": 22, "green": 255, "blue": 75,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": False,
            "owner_id": 1
        },
        {
            "filename": "10.jpg",
            "name": "Шарф",
            "category": CategoryEnum.scarf,
            "season": SeasonEnum.winter,
            "red": 62, "green": 57, "blue": 82,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": False,
            "owner_id": 1
        },
        {
            "filename": "11.jpg",
            "name": "Apple Watch",
            "category": CategoryEnum.watch,
            "season": SeasonEnum.summer,
            "red": 245, "green": 122, "blue": 7,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": True,
            "owner_id": 1
        },
        {
            "filename": "12.jpg",
            "name": "Сандалі",
            "category": CategoryEnum.sandals,
            "season": SeasonEnum.summer,
            "red": 66, "green": 36, "blue": 7,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": False,
            "owner_id": 1
        },
        {
            "filename": "13.jpg",
            "name": "Кепка",
            "category": CategoryEnum.hat,
            "season": SeasonEnum.summer,
            "red": 140, "green": 97, "blue": 140,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": False,
            "owner_id": 1
        },
        {
            "filename": "14.jpg",
            "name": "Браслет",
            "category": CategoryEnum.accessories,
            "season": SeasonEnum.summer,
            "red": 0, "green": 0, "blue": 255,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": True,
            "owner_id": 1
        },
        {
            "filename": "15.jpg",
            "name": "Жовті штани",
            "category": CategoryEnum.pants,
            "season": SeasonEnum.summer,
            "red": 188, "green": 212, "blue": 34,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": True,
            "owner_id": 1
        },
        {
            "filename": "16.jpg",
            "name": "Жовта футболка",
            "category": CategoryEnum.tshirt,
            "season": SeasonEnum.summer,
            "red": 233, "green": 237, "blue": 2,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": True,
            "owner_id": 1
        },
        {
            "filename": "17.jpg",
            "name": "Жовті кросівки",
            "category": CategoryEnum.sneakers,
            "season": SeasonEnum.summer,
            "red": 237, "green": 202, "blue": 2,
            "material": "Бавовна",
            "brand": "Uniqlo",
            "purchase_date": date(2023, 4, 10),
            "price": 199.00,
            "is_favorite": True,
            "owner_id": 1
        }
    ]

    image_urls = [
        "https://fahrenheit.ua/files/products/4x7a3262.1000x1000.jpg",
        "https://lingerie.ua/files/product/0/19020/19020.jpg",
        "https://preview.free3d.com/img/2014/08/2162617793575388491/fulrgt7a.jpg",
        "https://tornado.kiev.ua/image/cache/catalog/image/cache/new/41210_2-1000x1200.webp",
        "https://gard.com.ua/image/cache/catalog/image/cache/catalog/shop/products/cf8cb7c8-2f1d-11f0-80d8-ba4fdc50ab5f-450x600.webp",
        "https://football-world.com.ua/product-images/default/Jako/38648-64a5320c81ade.webp",
        "https://thenormalbrand.com/cdn/shop/files/FLATLAY_GB_804d9c90-577f-4d7a-981d-4fd547514e0a.jpg?v=1741813113&width=1445",
        "https://prostomayki.com.ua/calc/images/Mayki/mayka_red.jpg",
        "https://images.prom.ua/3638886825_w600_h600_3638886825.jpg",
        "https://business-style.com.ua/image/cache/catalog/product/9132_main-1164x1340.jpg",
        "https://iplanet.one/cdn/shop/files/Apple_Watch_Ultra_2_LTE_49mm_Titanium_Orange_Ocean_Band_PDP_Image_Avail_Position-1__en-IN_9ca47923-c612-46ac-a932-fbce9b5c705c.jpg?v=1698878148&width=1445",
        "https://site-obuvi.com.ua/images/products/bosonozhki_s667-12_na_site-obuvi.com__2_.jpg",
        "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSSG9CAt7HBLoSoWCcs29-JraQQqxdooapRXQ&s",
        "https://shop.energetix.tv/media/image/21/52/e0/3191-26_WEB_DBF55E0E0E5372B410889F2CB7F86CD3_768x768@2x.jpg",
        "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRficzLtsl8jurQG7SjFCaSI6zj9oaYKJNBbA&s",
        "https://ladan-shop.com.ua/assets/images/products/5768/dj4-sonyashnyk.jpg",
        "https://aspolo.ua/image/cache/catalog/obuv19/muzhskie-vysokie-krossovki-adidas-forum-mid-refined-zheltye-810895-1-800x533.jpg"
    ]

    uploads_dir = os.path.join(os.getcwd(), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    def download_image(image_url, dest_file):
        if os.path.exists(dest_file):
            print(f"📁 Image {os.path.basename(dest_file)} already exists. Skipping download.")
            return

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
            }
            response = requests.get(image_url, headers=headers)
            response.raise_for_status()
            with open(dest_file, "wb") as f:
                f.write(response.content)
            print(f"📥 Downloaded image: {os.path.basename(dest_file)}")
        except Exception as e:
            print(f"❌ Failed to download {image_url}: {e}")
    # 📌 Завантажуємо зображення в паралельному режимі
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = []
        for idx, item_data in enumerate(items_data):
            image_url = image_urls[idx]
            dest_file = os.path.join(uploads_dir, item_data["filename"])
            futures.append(executor.submit(download_image, image_url, dest_file))
        for future in futures:
            future.result()  # чекаємо завершення всіх
    for idx, item_data in enumerate(items_data):
        # Перевірка, чи одяг уже існує
        existing = db.query(ClothingItem).filter_by(filename=item_data["filename"]).first()
        if existing:
            print(f"ℹ️ ClothingItem {item_data['filename']} already exists. Skipping.")
            continue

        # Створення нового одягу
        clothing_item = ClothingItem(**item_data)
        db.add(clothing_item)
        print(f"✅ Added ClothingItem: {item_data['name']}")

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
