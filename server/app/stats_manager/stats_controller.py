from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.model import ClothingItem, SeasonEnum, CategoryEnum
from app.user_manager.user_controller import get_current_user

def get_clothing_stats_by_category(db: Session, token: str):
    """
    Повертає статистику одягу за категоріями:
    - кількість речей
    - середній вік (у днях) при наявності дати покупки

    :param db: Сесія SQLAlchemy
    :param token: JWT токен користувача
    :return: Список словників: [{"category": "верхній одяг", "count": 3, "average_age_days": 285.2}, ...]
    """

    user = get_current_user(token, db)
    today = date.today()

    # Підзапит для середнього віку з використанням DATEDIFF для MySQL
    avg_age_subquery = (
        db.query(
            ClothingItem.category.label("category"),
            func.avg(func.datediff(today, ClothingItem.purchase_date)).label("average_age_days")
        )
        .filter(
            ClothingItem.owner_id == user.id,
            ClothingItem.purchase_date.isnot(None)
        )
        .group_by(ClothingItem.category)
        .subquery()
    )

    # Основний запит: кількість + середній вік (через join)
    results = (
        db.query(
            ClothingItem.category,
            func.count(ClothingItem.id).label("count"),
            avg_age_subquery.c.average_age_days
        )
        .outerjoin(
            avg_age_subquery,
            ClothingItem.category == avg_age_subquery.c.category
        )
        .filter(ClothingItem.owner_id == user.id)
        .group_by(ClothingItem.category)
        .all()
    )

    return [
        {
            "category": category.value,
            "count": count,
            "average_age_days": round(avg_age, 1) if avg_age is not None else None
        }
        for category, count, avg_age in results
    ]