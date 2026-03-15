# app/models/sale_items.py

from sqlalchemy import Column, Integer, ForeignKey, Numeric, CheckConstraint, String
from sqlalchemy.orm import relationship
from app.database import Base


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)

    sale_id = Column(
        Integer,
        ForeignKey("sales.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True,
    )

    # Quantity sold (in the unit chosen during the sale)
    quantity = Column(Numeric(14, 4), nullable=False)

    # NEW COLUMN
    # Stores the unit used during the sale
    # Example: Cup, Kongo, Bag, Tablet, Pack
    unit_name = Column(String, nullable=False)

    selling_price = Column(Numeric(10, 2), nullable=False)
    line_total = Column(Numeric(10, 2), nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_saleitem_quantity_positive"),
    )