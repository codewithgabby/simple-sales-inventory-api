# models/sales.py

from sqlalchemy import Column, Index, Integer, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False, index=True)

    total_amount = Column(Numeric(10, 2), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    request_id = Column(String, nullable=False)

    items = relationship(
        "SaleItem",
        back_populates="sale",
        cascade="all, delete-orphan",
    )


    # Composite index for business and date filtering
    __table_args__ = (
        Index("ix_sales_business_created", "business_id", "created_at"),
        UniqueConstraint("business_id", "request_id", name="uq_business_request_id"),
    )
