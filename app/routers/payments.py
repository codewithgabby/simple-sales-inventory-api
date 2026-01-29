from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests
import os
from datetime import date, timedelta

from app.database import get_db
from app.core.auth import get_current_user

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

    amount = 15000 if period_type == "weekly" else 50000  # kobo

    today = date.today()
    start_date = today - timedelta(days=6) if period_type == "weekly" else today.replace(day=1)
    end_date = today

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
        raise HTTPException(status_code=400, detail="Payment initialization failed")

    return {
        "payment_url": data["data"]["authorization_url"]
    }
