# =========================================================
# SALESZY SUBSCRIPTION HELPER
# Centralized logic for checking active subscription
# =========================================================

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.export_access import ExportAccess


def get_active_subscription(db: Session, business_id: int):
    today = datetime.now(timezone.utc).date()

    return (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == business_id,
            ExportAccess.start_date <= today,
            ExportAccess.end_date >= today,
        )
        .order_by(ExportAccess.end_date.desc())
        .first()
    )


def require_subscription(db: Session, business_id: int, period_type: str):
    today = datetime.now(timezone.utc).date()

    return (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == business_id,
            ExportAccess.period_type == period_type,
            ExportAccess.start_date <= today,
            ExportAccess.end_date >= today,
        )
        .order_by(ExportAccess.end_date.desc())
        .first()
    )