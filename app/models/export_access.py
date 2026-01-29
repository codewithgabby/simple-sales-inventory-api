# app/models/export_access.py

from sqlalchemy import (
    Column,
    Integer,
    Date,
    DateTime,
    String,
    ForeignKey,
    Numeric,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class ExportAccess(Base):
    __tablename__ = "export_access"

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "period_type",
            "start_date",
            "end_date",
            name="uq_export_access_period",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(
        Integer,
        ForeignKey("businesses.id"),
        nullable=False,
        index=True,
    )

    period_type = Column(String, nullable=False)  # "weekly" or "monthly"

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    amount_paid = Column(Numeric(10, 2), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
