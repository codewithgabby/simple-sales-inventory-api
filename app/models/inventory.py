# app/models/inventory.py

from sqlalchemy import Column, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    quantity_available = Column(Integer, nullable=False)
    low_stock_threshold = Column(Integer, nullable=False, default=5)
    expiry_date = Column(Date, nullable=True)

    product = relationship("Product", back_populates="inventory")
