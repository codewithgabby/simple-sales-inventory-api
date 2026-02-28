# app/models/products.py

from sqlalchemy import CheckConstraint, Column, Index, Integer, String, Numeric, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    cost_price = Column(Numeric(10, 2), nullable=False)
    selling_price = Column(Numeric(10, 2), nullable=False)

    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_products_business", "business_id"),
        UniqueConstraint("business_id", "name", name="uq_business_product_name"),
        CheckConstraint("cost_price >= 0", name="ck_cost_price_positive"),
        CheckConstraint("selling_price > 0", name="ck_selling_price_positive"),
    )