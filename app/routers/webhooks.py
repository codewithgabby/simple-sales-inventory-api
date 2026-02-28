# =========================================================
# PAYSTACK WEBHOOK (PRODUCTION SAFE)
# - Verifies signature
# - Validates amount
# - Validates metadata
# - Idempotent by transaction reference
# - Prevents duplicate unlock
# =========================================================

from decimal import Decimal
import hmac
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.export_access import ExportAccess
from app.models.business import Business
from app.core.config import settings
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

logger = logging.getLogger("app")


def _verify_paystack_signature(request_body: bytes, signature: str):
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
        logger.warning("Invalid Paystack signature attempt")
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
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        logger.warning("Missing Paystack signature")
        raise HTTPException(
            status_code=401,
            detail="Missing Paystack signature",
        )

    raw_body = await request.body()
    _verify_paystack_signature(raw_body, signature)

    payload = await request.json()

    if payload.get("event") != "charge.success":
        return {"status": "ignored"}

    data = payload.get("data", {})
    metadata = data.get("metadata", {})

    business_id = metadata.get("business_id")
    period_type = metadata.get("period_type")
    amount_kobo = data.get("amount")
    reference = data.get("reference")

    if not business_id or period_type not in {"weekly", "monthly"}:
        logger.error("Invalid metadata in webhook")
        raise HTTPException(status_code=400, detail="Invalid payment metadata")

    if not reference:
        logger.error("Missing reference in webhook")
        raise HTTPException(status_code=400, detail="Missing transaction reference")

    expected_amount = 15000 if period_type == "weekly" else 50000

    if amount_kobo != expected_amount:
        logger.error(f"Incorrect payment amount: {amount_kobo}")
        raise HTTPException(status_code=400, detail="Incorrect payment amount")

    # Verify business exists
    business_exists = db.query(Business).filter(Business.id == business_id).first()
    if not business_exists:
        logger.error(f"Business not found: {business_id}")
        raise HTTPException(status_code=400, detail="Invalid business")

    existing_reference = (
        db.query(ExportAccess)
        .filter(ExportAccess.transaction_reference == reference)
        .first()
    )

    if existing_reference:
        return {"status": "already_processed"}

    today = datetime.now(timezone.utc).date()

    active_subscription = (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == business_id,
            ExportAccess.period_type == period_type,
            ExportAccess.end_date >= today,
        )
        .order_by(ExportAccess.end_date.desc())
        .first()
    )

    if active_subscription:
        start_date = active_subscription.end_date + timedelta(days=1)
    else:
        start_date = today    
                
    if period_type == "weekly":
        end_date = start_date + timedelta(days=6)
    else:
        end_date = start_date + timedelta(days=29)

    access = ExportAccess(
        business_id=business_id,
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
        amount_paid= Decimal(expected_amount) / Decimal("100"),
        transaction_reference=reference,
    )

    db.add(access)
    db.commit()

    logger.info(
        f"Subscription activated for business {business_id} ({period_type})"
    )

    return {"status": "subscription_activated"}