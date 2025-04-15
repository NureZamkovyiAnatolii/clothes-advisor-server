from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer,Boolean, String
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.dialects.mysql import DATETIME
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), unique=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))  # Час створення
    synchronized_at  = Column(DATETIME(fsp=6), default=datetime.now(timezone.utc))  # Час створення
    is_email_verified = Column(Boolean, default=False)  
    

    combinations = relationship("ClothingCombination", back_populates="owner")

    # Додати метод для серіалізації об'єкта в словник
    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
        }

