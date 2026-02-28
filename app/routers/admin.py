# app/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta, timezone

from app.database import get_db
from app.core.auth import get_admin_user
from app.models.business import Business
from app.models.users import User
from app.models.products import Product
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.models.export_access import ExportAccess


router = APIRouter(prefix="/admin", tags=["Admin"])


# =========================================================
# PLATFORM OVERVIEW (ROLLING 30 DAYS)
# =========================================================

@router.get("/overview")
def platform_overview(
    db: Session = Depends(get_db),
    admin = Depends(get_admin_user),
):
    today = datetime.now(timezone.utc).date()
    start_30 = today - timedelta(days=29)

    total_businesses = db.query(func.count(Business.id)).scalar()
    suspended_businesses = db.query(func.count(Business.id)).filter(
        Business.is_suspended == True
    ).scalar()

    active_businesses = total_businesses - suspended_businesses

    total_revenue = db.query(
        func.coalesce(func.sum(Sale.total_amount), 0)
    ).scalar()

    revenue_last_30 = db.query(
        func.coalesce(func.sum(Sale.total_amount), 0)
    ).filter(
        Sale.created_at >= start_30
    ).scalar()

    total_subscription_revenue = db.query(
        func.coalesce(func.sum(ExportAccess.amount_paid), 0)
    ).scalar()

    active_premium = db.query(func.count(func.distinct(ExportAccess.business_id))).filter(
        ExportAccess.start_date <= today,
        ExportAccess.end_date >= today,
    ).scalar()

    active_weekly = db.query(func.count(func.distinct(ExportAccess.business_id))).filter(
        ExportAccess.period_type == "weekly",
        ExportAccess.start_date <= today,
        ExportAccess.end_date >= today,
    ).scalar()

    active_monthly = db.query(func.count(func.distinct(ExportAccess.business_id))).filter(
        ExportAccess.period_type == "monthly",
        ExportAccess.start_date <= today,
        ExportAccess.end_date >= today,
    ).scalar()

    premium_penetration = (
        (active_premium / total_businesses) * 100
        if total_businesses else 0
    )

    return {
        "total_businesses": total_businesses,
        "active_businesses": active_businesses,
        "suspended_businesses": suspended_businesses,
        "total_revenue": float(total_revenue),
        "revenue_last_30_days": float(revenue_last_30),
        "total_subscription_revenue": float(total_subscription_revenue),
        "active_premium_subscriptions": active_premium,
        "active_weekly_businesses": active_weekly,
        "active_monthly_businesses": active_monthly,
        "premium_penetration_percent": round(premium_penetration, 2),
    }


# BUSINESS MANAGEMENT

@router.get("/businesses")
def list_businesses(
    search: str = None,
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    admin = Depends(get_admin_user),
):
    if page < 1:
        page = 1

    if limit < 1 or limit > 50:
        limit = 10

    query = db.query(Business)

    if search:
        query = query.filter(Business.name.ilike(f"%{search}%"))

    total_records = query.count()

    businesses = (
        query
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    results = []

    for biz in businesses:

        owner = db.query(User).filter(
            User.business_id == biz.id,
            User.is_admin == False
        ).first()

        total_users = db.query(User).filter(
            User.business_id == biz.id
        ).count()

        total_products = db.query(Product).filter(
            Product.business_id == biz.id
        ).count()

        total_sales = db.query(Sale).filter(
            Sale.business_id == biz.id
        ).count()

        total_revenue = db.query(
            func.coalesce(func.sum(Sale.total_amount), 0)
        ).filter(
            Sale.business_id == biz.id
        ).scalar()

        active_subscription = db.query(ExportAccess).filter(
            ExportAccess.business_id == biz.id,
            ExportAccess.start_date <= date.today(),
            ExportAccess.end_date >= date.today(),
        ).first()

        results.append({
            "business_id": biz.id,
            "business_name": biz.name,
            "owner_email": owner.email if owner else None,
            "created_at": biz.created_at,
            "is_suspended": biz.is_suspended,
            "total_users": total_users,
            "total_products": total_products,
            "total_sales": total_sales,
            "total_revenue": float(total_revenue),
            "subscription_type": active_subscription.period_type if active_subscription else None,
            "subscription_expires_at": active_subscription.end_date if active_subscription else None,
        })

    return {
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "data": results
    }

# =========================================================
# SUSPEND / ACTIVATE BUSINESS
# =========================================================

@router.post("/business/{business_id}/suspend")
def suspend_business(
    business_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin_user),
):
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.is_suspended = True
    db.commit()

    return {"message": "Business suspended successfully"}


@router.post("/business/{business_id}/activate")
def activate_business(
    business_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin_user),
):
    business = db.query(Business).filter(Business.id == business_id).first()

    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    business.is_suspended = False
    db.commit()

    return {"message": "Business reactivated successfully"}

# =========================================================
# BUSINESS FINANCIAL DRILLDOWN
# =========================================================

@router.get("/business/{business_id}/overview")
def business_financial_overview(
    business_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_admin_user),
):
    today = datetime.now(timezone.utc).date()
    start_30 = today - timedelta(days=29)

    revenue = db.query(
        func.coalesce(func.sum(Sale.total_amount), 0)
    ).filter(
        Sale.business_id == business_id,
        Sale.created_at >= start_30
    ).scalar()

    cost = db.query(
        func.coalesce(func.sum(Product.cost_price * SaleItem.quantity), 0)
    ).join(SaleItem, SaleItem.product_id == Product.id
    ).join(Sale, SaleItem.sale_id == Sale.id
    ).filter(
        Sale.business_id == business_id,
        Sale.created_at >= start_30
    ).scalar()

    profit = revenue - cost

    subscription = db.query(ExportAccess).filter(
        ExportAccess.business_id == business_id,
        ExportAccess.start_date <= today,
        ExportAccess.end_date >= today,
    ).order_by(ExportAccess.end_date.desc()).first()

    return {
        "revenue_last_30_days": float(revenue),
        "profit_last_30_days": float(profit),
        "active_subscription": subscription.period_type if subscription else None,
        "subscription_expires": subscription.end_date if subscription else None,
    }