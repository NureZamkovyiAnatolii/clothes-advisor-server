from fastapi import APIRouter, Depends
from requests import Session

from app.stats_manager.stats_controller import get_clothing_stats_by_category
from app.database.database import get_db
from app.user_manager import oauth2_scheme

stats_router = APIRouter(tags=["Stats"])

@stats_router.get("/stats/category")
def wardrobe_analysis(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    return get_clothing_stats_by_category(db, token)
