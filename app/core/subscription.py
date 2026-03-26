# =========================================================
# SALESZY SUBSCRIPTION HELPER
# Centralized logic for checking active subscription
# =========================================================

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.export_access import ExportAccess


def get_active_subscription(db: Session, business_id: int):
    """Get any active subscription (weekly OR monthly)"""
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
    """
    Check if user has access to the requested period.
    - Weekly plan: can access weekly features
    - Monthly plan: can access BOTH weekly AND monthly features
    """
    today = datetime.now(timezone.utc).date()

    # If requesting weekly, check for either weekly OR monthly subscription
    if period_type == "weekly":
        return (
            db.query(ExportAccess)
            .filter(
                ExportAccess.business_id == business_id,
                ExportAccess.start_date <= today,
                ExportAccess.end_date >= today,
                ExportAccess.period_type.in_(["weekly", "monthly"])  # ← KEY CHANGE
            )
            .order_by(ExportAccess.end_date.desc())
            .first()
        )
    
    # If requesting monthly, only monthly subscription works
    else:  # monthly
        return (
            db.query(ExportAccess)
            .filter(
                ExportAccess.business_id == business_id,
                ExportAccess.period_type == "monthly",
                ExportAccess.start_date <= today,
                ExportAccess.end_date >= today,
            )
            .order_by(ExportAccess.end_date.desc())
            .first()
        )