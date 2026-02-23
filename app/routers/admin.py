# app/routers/admin.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date

from app.database import get_db
from app.core.auth import get_admin_user
from app.models.business import Business
from app.models.users import User
from app.models.products import Product
from app.models.sales import Sale
from app.models.export_access import ExportAccess


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# ==========================================
# PLATFORM OVERVIEW
# ==========================================

@router.get("/overview")
def platform_overview(
    db: Session = Depends(get_db),
    admin = Depends(get_admin_user),
):

    today = date.today()
    first_day_of_month = today.replace(day=1)

    total_businesses = db.query(func.count(Business.id)).scalar()
    total_users = db.query(func.count(User.id)).scalar()
    total_products = db.query(func.count(Product.id)).scalar()
    total_sales = db.query(func.count(Sale.id)).scalar()

    total_revenue = db.query(
        func.coalesce(func.sum(Sale.total_amount), 0)
    ).scalar()

    # New businesses this month
    businesses_this_month = db.query(func.count(Business.id)).filter(
        Business.created_at >= first_day_of_month
    ).scalar()

    # Sales this month
    sales_this_month = db.query(func.count(Sale.id)).filter(
        Sale.created_at >= first_day_of_month
    ).scalar()

    revenue_this_month = db.query(
        func.coalesce(func.sum(Sale.total_amount), 0)
    ).filter(
        Sale.created_at >= first_day_of_month
    ).scalar()

    return {
        "total_businesses": total_businesses,
        "businesses_this_month": businesses_this_month,

        "total_users": total_users,
        "total_products": total_products,

        "total_sales": total_sales,
        "sales_this_month": sales_this_month,

        "total_revenue": float(total_revenue),
        "revenue_this_month": float(revenue_this_month),
    }


# ==========================================
# SUBSCRIPTION ANALYTICS
# ==========================================

@router.get("/subscriptions")
def subscription_analytics(
    db: Session = Depends(get_db),
    admin = Depends(get_admin_user),
):

    today = date.today()

    active_weekly = db.query(func.count(ExportAccess.id)).filter(
        ExportAccess.period_type == "weekly",
        ExportAccess.start_date <= today,
        ExportAccess.end_date >= today,
    ).scalar()

    active_monthly = db.query(func.count(ExportAccess.id)).filter(
        ExportAccess.period_type == "monthly",
        ExportAccess.start_date <= today,
        ExportAccess.end_date >= today,
    ).scalar()

    expired_weekly = db.query(func.count(ExportAccess.id)).filter(
        ExportAccess.period_type == "weekly",
        ExportAccess.end_date < today,
    ).scalar()

    expired_monthly = db.query(func.count(ExportAccess.id)).filter(
        ExportAccess.period_type == "monthly",
        ExportAccess.end_date < today,
    ).scalar()

    total_subscriptions = db.query(func.count(ExportAccess.id)).scalar()

    total_subscription_revenue = db.query(
        func.coalesce(func.sum(ExportAccess.amount_paid), 0)
    ).scalar()

    return {
        "active_weekly_subscriptions": active_weekly,
        "active_monthly_subscriptions": active_monthly,

        "expired_weekly_subscriptions": expired_weekly,
        "expired_monthly_subscriptions": expired_monthly,

        "total_subscriptions_ever": total_subscriptions,
        "total_subscription_revenue": float(total_subscription_revenue),
    }

# ==========================================
# BUSINESS DRILLDOWN WITH SEARCH + PAGINATION
# ==========================================

@router.get("/businesses")
def business_breakdown(
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

    query = (
        db.query(Business, User)
        .join(User, User.business_id == Business.id)
    )

    #  Search by business name OR email
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            func.lower(Business.name).like(search_term) |
            func.lower(User.email).like(search_term)
        )

    total_records = query.count()

    businesses = (
        query
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    results = []

    for biz, user in businesses:

        total_products = db.query(func.count(Product.id)).filter(
            Product.business_id == biz.id
        ).scalar()

        total_sales = db.query(func.count(Sale.id)).filter(
            Sale.business_id == biz.id
        ).scalar()

        total_revenue = db.query(
            func.coalesce(func.sum(Sale.total_amount), 0)
        ).filter(
            Sale.business_id == biz.id
        ).scalar()

        results.append({
            "business_id": biz.id,
            "business_name": biz.name,
            "owner_email": user.email,
            "created_at": biz.created_at,
            "total_products": total_products,
            "total_sales": total_sales,
            "total_revenue": float(total_revenue),
        })

    return {
        "page": page,
        "limit": limit,
        "total_records": total_records,
        "data": results
    }