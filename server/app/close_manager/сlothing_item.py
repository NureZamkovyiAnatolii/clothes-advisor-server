from fastapi import HTTPException
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from app.database import Base  # або твоя база Base, якщо інша

from enum import Enum
from sqlalchemy import Enum as SqlEnum

class SeasonEnum(str, Enum):
    winter = "winter"
    spring = "spring"
    summer = "summer"
    autumn = "autumn"

class CategoryEnum(str, Enum):
    tshirt = "tshirt"
    pants = "pants"
    jacket = "jacket"
    dress = "dress"


class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False)  # шлях до фото
    name = Column(String(100), nullable=False)  # назва одягу
    category = Column(SqlEnum(CategoryEnum), nullable=False)  # категорія (головний убір тощо)
    season = Column(SqlEnum(SeasonEnum), nullable=False)  # сезонність

    red = Column(Integer, nullable=True)  # червоний компонент (0-255)
    green = Column(Integer, nullable=True)  # зелений компонент (0-255)
    blue = Column(Integer, nullable=True)  # синій компонент (0-255)

    material = Column(String(50), nullable=False)  # матеріал

    brand = Column(String(100), nullable=True)  # опційне поле
    purchase_date = Column(Date, nullable=True)  # дата придбання (опційно)
    price = Column(Float, nullable=True)  # вартість (опційно)
    is_favorite = Column(Boolean, default=False, nullable=False)  # чи є улюбленим
    
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User")

    combinations = relationship( 
        "ClothingCombination",
        secondary="clothing_combination_items",
        back_populates="items"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        if self.season not in SeasonEnum.__members__:
            raise HTTPException(status_code=400, detail=f"Invalid season value: {self.season}")
        
        if self.category not in CategoryEnum.__members__:
            raise HTTPException(status_code=400, detail=f"Invalid category value: {self.category}")


