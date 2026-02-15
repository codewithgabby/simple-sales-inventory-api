# app/routers/payments.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import requests
import os
from datetime import date, timedelta

from app.database import get_db
from app.core.auth import get_current_user
from app.models.export_access import ExportAccess

router = APIRouter(prefix="/payments", tags=["Payments"])

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")
PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"


@router.post("/initialize")
def initialize_payment(
    period_type: str,  # "weekly" or "monthly"
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if period_type not in ["weekly", "monthly"]:
        raise HTTPException(status_code=400, detail="Invalid period type")

    today = date.today()

    # Determine access window and amount
    if period_type == "weekly":
        start_date = today - timedelta(days=6)
        end_date = today
        amount = 15000  # kobo
    else:
        start_date = today.replace(day=1)
        end_date = today
        amount = 50000  # kobo

    # BLOCK DUPLICATE PAYMENT FOR SAME PERIOD
    existing_access = (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == current_user.business_id,
            ExportAccess.period_type == period_type,
            ExportAccess.start_date == start_date,
            ExportAccess.end_date == end_date,
        )
        .first()
    )

    if existing_access:
        raise HTTPException(
            status_code=400,
            detail="Export already unlocked for this period",
        )

    payload = {
        "email": current_user.email,
        "amount": amount,
        "metadata": {
            "business_id": current_user.business_id,
            "period_type": period_type,
            "start_date": str(start_date),
            "end_date": str(end_date),
        },
    }

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(PAYSTACK_INIT_URL, json=payload, headers=headers)
    data = response.json()

    if not data.get("status"):
        raise HTTPException(
            status_code=400,
            detail="Payment initialization failed",
        )

    return {
        "payment_url": data["data"]["authorization_url"]
    }
