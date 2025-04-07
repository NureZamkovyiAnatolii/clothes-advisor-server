from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer,Boolean, String
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), unique=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))  # Час створення
    is_email_verified = Column(Boolean, default=False)  
