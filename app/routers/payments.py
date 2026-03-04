# =========================================================
# PAYMENTS ROUTER (PRODUCTION HARDENED VERSION)
# - Prevents duplicate subscription initialization
# - Server-controlled pricing
# - Clean metadata structure
# - Startup validation for secret key
# - Internal logging for debugging
# =========================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import requests
import logging
from datetime import datetime, timezone

from app.database import get_db
from app.core.auth import get_current_user
from app.models.export_access import ExportAccess
from app.core.config import settings


router = APIRouter(prefix="/payments", tags=["Payments"])

logger = logging.getLogger("app")

PAYSTACK_INIT_URL = "https://api.paystack.co/transaction/initialize"

#  Fail fast if secret key is missing
if not settings.PAYSTACK_SECRET_KEY:
    raise RuntimeError("PAYSTACK_SECRET_KEY not configured")

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY


@router.post("/initialize")
def initialize_payment(
    period_type: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    #  Validate period type
    if period_type not in {"weekly", "monthly"}:
        raise HTTPException(status_code=400, detail="Invalid period type")

    today = datetime.now(timezone.utc).date()

    #  Prevent duplicate active subscription for same period
    existing_access = (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == current_user.business_id,
            ExportAccess.period_type == period_type,
            ExportAccess.end_date >= today,
        )
        .first()
    )

    if existing_access:
        raise HTTPException(
            status_code=400,
            detail="Subscription already active",
        )

    #  Server-controlled pricing (in kobo)
    amount_kobo = 15000 if period_type == "weekly" else 50000

    payload = {
        "email": current_user.email,
        "amount": amount_kobo,
        "metadata": {
            "business_id": current_user.business_id,
            "period_type": period_type,
        },
    }

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    #  Call Paystack
    try:
        response = requests.post(
            PAYSTACK_INIT_URL,
            json=payload,
            headers=headers,
            timeout=10,
        )
    except requests.RequestException as e:
        logger.error(f"Paystack connection error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Unable to connect to payment provider",
        )

    #  If Paystack responds with error
    if response.status_code != 200:
        logger.error(
            f"Paystack init failed. Status: {response.status_code}, Body: {response.text}"
        )
        raise HTTPException(
            status_code=400,
            detail="Payment initialization failed",
        )

    try:
        data = response.json()
    except ValueError:
        logger.error("Paystack returned invalid JSON")
        raise HTTPException(
            status_code=500,
            detail="Invalid response from payment provider",
        )

    if not data.get("status"):
        logger.error(f"Paystack init unsuccessful response: {data}")
        raise HTTPException(
            status_code=400,
            detail="Payment initialization failed",
        )

    return {
        "payment_url": data["data"]["authorization_url"]
    }