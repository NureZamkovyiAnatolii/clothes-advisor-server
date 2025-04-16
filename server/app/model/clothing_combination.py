from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base

clothing_combination_items = Table(
    "clothing_combination_items",
    Base.metadata,
    Column("combination_id", Integer, ForeignKey("clothing_combinations.id")),
    Column("item_id", Integer, ForeignKey("clothing_items.id"))
)

class ClothingCombination(Base):
    __tablename__ = "clothing_combinations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # Наприклад: "Зимова прогулянка", "Офіс"

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="combinations")

    items = relationship(
        "ClothingItem",
        secondary="clothing_combination_items",
        back_populates="combinations"
    )
