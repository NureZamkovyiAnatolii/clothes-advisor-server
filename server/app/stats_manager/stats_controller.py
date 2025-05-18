from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from app.model import ClothingItem, SeasonEnum, CategoryEnum
from app.user_manager.user_controller import get_current_user

def get_clothing_stats_by_category(db: Session, token: str):
    """
    Returns clothing statistics by categories:
    - item count
    - average age (in days) if purchase date is available

    :param db: SQLAlchemy session
    :param token: User's JWT token
    :return: List of dictionaries: [{"category": "outerwear", "count": 3, "average_age_days": 285.2}, ...]
    """

    user = get_current_user(token, db)
    if user is None or type(user) is JSONResponse:
        raise HTTPException(status_code=401, detail="Not authenticated")
    today = date.today()

    # Subquery for average age using DATEDIFF for MySQL
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

    # Main query: count + average age (via join)
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
