from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db
from app.core.auth import get_current_user
from app.core.subscription import get_active_subscription

router = APIRouter(prefix="/subscription", tags=["Subscription"])


@router.get("/status")
def subscription_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    subscription = get_active_subscription(
        db,
        current_user.business_id,
    )

    if not subscription:
        return {
            "active": False,
            "period_type": None,
            "start_date": None,
            "end_date": None,
        }

    return {
        "active": True,
        "period_type": subscription.period_type,
        "start_date": subscription.start_date,
        "end_date": subscription.end_date,
    }