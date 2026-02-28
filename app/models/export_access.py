from sqlalchemy import (
    Column,
    Integer,
    Date,
    DateTime,
    String,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    CheckConstraint,
)
from sqlalchemy.sql import func

from app.database import Base


class ExportAccess(Base):
    __tablename__ = "export_access"

    __table_args__ = (
        UniqueConstraint(
            "transaction_reference",
            name="uq_export_access_reference",
        ),
        CheckConstraint(
            "period_type IN ('weekly', 'monthly')",
            name="ck_period_type_valid",
        ),
        CheckConstraint(
            "end_date >= start_date",
            name="ck_subscription_date_valid",
        ),
        CheckConstraint(
            "amount_paid > 0",
            name="ck_amount_paid_positive",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(
        Integer,
        ForeignKey("businesses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    period_type = Column(String, nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    amount_paid = Column(Numeric(10, 2), nullable=False)

    transaction_reference = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )