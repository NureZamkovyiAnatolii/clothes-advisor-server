from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Float
from sqlalchemy.orm import relationship
from app.database import Base  # або твоя база Base, якщо інша

class ClothingItem(Base):
    __tablename__ = "clothing_items"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, nullable=False)  # шлях до фото
    name = Column(String(100), nullable=False)  # назва одягу
    category = Column(String(50), nullable=False)  # категорія (головний убір тощо)
    season = Column(String(20), nullable=False)  # сезонність
    color = Column(String(30), nullable=False)  # основний колір
    material = Column(String(50), nullable=False)  # матеріал

    brand = Column(String(100), nullable=True)  # опційне поле
    purchase_date = Column(Date, nullable=True)  # дата придбання (опційно)
    price = Column(Float, nullable=True)  # вартість (опційно)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User")

    combinations = relationship( 
        "ClothingCombination",
        secondary="clothing_combination_items",
        back_populates="items"
    )


