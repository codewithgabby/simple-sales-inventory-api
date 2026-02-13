# app/routers/webhooks.py

import hmac
import hashlib
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta

from app.database import get_db
from app.models.export_access import ExportAccess
from app.core.config import settings
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _verify_paystack_signature(request_body: bytes, signature: str):
    """
    Verify that the request is truly from Paystack
    """
    if not settings.PAYSTACK_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Paystack secret key not configured",
        )

    computed_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        request_body,
        hashlib.sha512,
    ).hexdigest()

    if not hmac.compare_digest(computed_signature, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Paystack signature",
        )


@router.post("/paystack")
@limiter.limit("20/minute")
async def paystack_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Paystack bank-transfer webhook
    Unlocks weekly or monthly exports after successful payment
    """

    signature = request.headers.get("x-paystack-signature")
    if not signature:
        raise HTTPException(
            status_code=401,
            detail="Missing Paystack signature",
        )

    raw_body = await request.body()

    # Verify webhook signature
    _verify_paystack_signature(raw_body, signature)

    payload = await request.json()

    # Only process successful payments
    if payload.get("event") != "charge.success":
        return {"status": "ignored"}

    data = payload.get("data", {})
    metadata = data.get("metadata", {})

    business_id = metadata.get("business_id")
    period_type = metadata.get("period_type")  # "weekly" or "monthly"
    amount_kobo = data.get("amount")

    if not business_id or period_type not in {"weekly", "monthly"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment metadata",
        )

    # Validate payment amount
    expected_amount = 15000 if period_type == "weekly" else 50000
    if amount_kobo != expected_amount:
        raise HTTPException(
            status_code=400,
            detail="Incorrect payment amount",
        )

    today = date.today()

    if period_type == "weekly":
        start_date = today - timedelta(days=6)
        end_date = today
    else:
        start_date = today.replace(day=1)
        end_date = today

    # Idempotency check (avoid double unlock)
    existing_access = (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == business_id,
            ExportAccess.period_type == period_type,
            ExportAccess.start_date <= start_date,
            ExportAccess.end_date >= end_date,
        )
        .first()
    )

    if existing_access:
        return {"status": "already_unlocked"}

    # Grant export access
    access = ExportAccess(
        business_id=business_id,
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
        amount_paid=expected_amount / 100,  # store in naira
    )

    db.add(access)
    db.commit()

    return {"status": "export_unlocked"}
