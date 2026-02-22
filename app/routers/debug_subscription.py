from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.database import get_db
from app.core.auth import get_current_user
from app.models.export_access import ExportAccess

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/subscription")
def view_subscription(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    access = (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == current_user.business_id
        )
        .order_by(ExportAccess.end_date.desc())
        .all()
    )

    return [
        {
            "period_type": a.period_type,
            "start_date": a.start_date,
            "end_date": a.end_date,
        }
        for a in access
    ]


@router.post("/expire/{period_type}")
def force_expire(
    period_type: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()

    access = (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == current_user.business_id,
            ExportAccess.period_type == period_type,
        )
        .order_by(ExportAccess.end_date.desc())
        .first()
    )

    if not access:
        raise HTTPException(status_code=404, detail="No active subscription")

    access.end_date = today - timedelta(days=1)
    db.commit()

    return {"status": "subscription expired manually"}