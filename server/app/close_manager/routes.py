from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from app.database import get_db
from app.user_manager.user_controller import  oauth2_scheme
close_router = APIRouter(tags=["Close Operations"])

@close_router.post("/close/upload")
async def upload_photo_route(
    file: UploadFile = File(...),
    name: str = Form(...),
    token: str = Depends(oauth2_scheme),
    red: Optional[str] = Form(None),
    green: Optional[str] = Form(None),
    blue: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Route for uploading a photo"""
    return
