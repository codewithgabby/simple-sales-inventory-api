# app/models/product_units.py

from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class ProductUnitConversion(Base):
    __tablename__ = "product_unit_conversions"

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Example values:
    # Kongo
    # Derica
    # Bag
    # Pack
    # Carton
    unit_name = Column(String, nullable=False)

    # How many BASE UNITS equal ONE of this unit
    #
    # Example:
    # base_unit = Cup
    #
    # Kongo = 5 Cups
    # conversion_rate = 5
    #
    # Bag = 250 Cups
    # conversion_rate = 250
    conversion_rate = Column(Numeric(14, 4), nullable=False)

    product = relationship("Product", back_populates="unit_conversions")

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "unit_name",
            name="uq_product_unit_name",
        ),
    )