# =========================================================
# SALESZY SUBSCRIPTION HELPER
# Centralized logic for checking active subscription
# =========================================================

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.export_access import ExportAccess
from datetime import datetime, timezone

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


def is_premium_or_trial(db: Session, business_id: int, user=None):
    """
    Returns True if user has active subscription OR is in trial period.
    Use this for feature gates (profit, insights, etc.)
    """
    

    # Check trial first
    if user and user.trial_end_date and user.trial_end_date > datetime.now(timezone.utc):
        return True

    # Check subscription
    sub = get_active_subscription(db, business_id)
    return sub is not None


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