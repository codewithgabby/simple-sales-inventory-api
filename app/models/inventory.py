# app/models/inventory.py

from sqlalchemy import CheckConstraint, Column, Index, Integer, Date, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # CHANGED: Integer → Numeric
    # Inventory must support decimal quantities because
    # unit conversion may result in fractional base units.
    #
    # Example:
    # Base unit = Kongo
    # 3 Cups sold
    # 3 Cups = 0.6 Kongo
    #
    # Inventory becomes 49.4 Kongos
    quantity_available = Column(Numeric(14, 4), nullable=False)

    low_stock_threshold = Column(Integer, nullable=False, default=5)

    expiry_date = Column(Date, nullable=True)

    product = relationship("Product", back_populates="inventory")

    __table_args__ = (
        CheckConstraint("quantity_available >= 0", name="ck_inventory_quantity_non_negative"),
        CheckConstraint("low_stock_threshold >= 0", name="ck_low_stock_non_negative"),
    )