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

    now = datetime.now(timezone.utc)
    
    # 🚀 Check PAID subscription FIRST
    subscription = get_active_subscription(db, current_user.business_id)

    if subscription:
        return {
            "active": True,
            "period_type": subscription.period_type,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "trial": False,
            "days_left": 0,
        }

    # 🚀 Then check trial
    if current_user.trial_end_date and current_user.trial_end_date > now:
        days_left = (current_user.trial_end_date - now).days + 1
        return {
            "active": True,
            "period_type": "trial",
            "start_date": current_user.trial_start_date,
            "end_date": current_user.trial_end_date,
            "trial": True,
            "days_left": days_left,
        }

    # No subscription, no trial
    return {
        "active": False,
        "period_type": None,
        "start_date": None,
        "end_date": None,
        "trial": False,
        "days_left": 0,
    }