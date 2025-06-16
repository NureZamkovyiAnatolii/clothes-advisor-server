from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from requests import Session
from sqlalchemy import text

from app.stats_manager.stats_controller import get_clothing_stats_by_category
from app.database.database import get_db
from app.user_manager import get_current_user_id, oauth2_scheme

stats_router = APIRouter(tags=["Stats"])
@stats_router.get("/stats/category")
def get_category_stats(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    owner_id = get_current_user_id(token, db)
    try:
        result = db.execute(
            text("CALL get_category_stats_by_owner(:owner_id)"),
            {"owner_id": owner_id}
        )
        rows = result.fetchall()
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]
        return JSONResponse(content={"data": data})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
