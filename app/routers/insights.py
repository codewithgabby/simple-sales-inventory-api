# =========================================================
# SALESZY INSIGHTS ROUTER (PREMIUM ONLY)
#
# Unlocks:
# - Growth % (weekly/monthly)
# - Average Order Value
# - Top Selling Product
# - Slowest Moving Product
# - Inventory Turnover Proxy
#
# Requires active subscription based on period
# =========================================================

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal

from app.database import get_db
from app.core.auth import get_current_user
from app.core.subscription import require_subscription
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.models.products import Product
from app.models.inventory import Inventory

router = APIRouter(prefix="/insights", tags=["Insights"])


# =========================================================
# HELPER: CALCULATE DATE RANGES
# =========================================================
def _get_period_dates(period: str):
    today = datetime.now(timezone.utc).date()

    if period == "weekly":
        current_start = today - timedelta(days=6)
        previous_start = current_start - timedelta(days=7)
        previous_end = current_start - timedelta(days=1)

    elif period == "monthly":
        current_start = today - timedelta(days=29)
        previous_month_end = current_start - timedelta(days=1)
        previous_start = previous_month_end.replace(day=1)
        previous_end = previous_month_end

    else:
        raise HTTPException(status_code=400, detail="Invalid period type")

    current_end = today

    return current_start, current_end, previous_start, previous_end


# =========================================================
# HELPER: GET REVENUE + ORDER COUNT
# =========================================================
def _get_sales_summary(db, business_id, start_date, end_date):

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    base_filter = [
        Sale.business_id == business_id,
        Sale.created_at.between(start_dt, end_dt),
    ]

    total_revenue = (
        db.query(func.coalesce(func.sum(Sale.total_amount), 0))
        .filter(*base_filter)
        .scalar()
    )

    total_orders = (
        db.query(func.count(Sale.id))
        .filter(*base_filter)
        .scalar()
    )

    return Decimal(total_revenue or 0), total_orders or 0


# =========================================================
# MAIN INSIGHTS ENDPOINT
# =========================================================
@router.get("/summary")
def insights_summary(
    period: str = Query(..., pattern="^(weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    #  Require matching subscription
    subscription = require_subscription(
        db,
        current_user.business_id,
        period,
    )

    if not subscription:
        raise HTTPException(
            status_code=402,
            detail="Upgrade to unlock Business Insights",
        )

    current_start, current_end, previous_start, previous_end = _get_period_dates(period)

    # ----------------------------
    # Current & Previous Revenue
    # ----------------------------
    current_revenue, current_orders = _get_sales_summary(
        db,
        current_user.business_id,
        current_start,
        current_end,
    )

    previous_revenue, _ = _get_sales_summary(
        db,
        current_user.business_id,
        previous_start,
        previous_end,
    )

    # ----------------------------
    # Growth %
    # ----------------------------
    if previous_revenue == 0:
        if current_revenue > 0:
            growth_percentage = Decimal("100.00")
        else:
            growth_percentage = Decimal("0.00")
    else:
        growth_percentage = (
            (current_revenue - previous_revenue) / previous_revenue
        ) * 100

    growth_percentage = growth_percentage.quantize(Decimal("0.01"))

    # ----------------------------
    # Average Order Value
    # ----------------------------
    if current_orders == 0:
        average_order_value = Decimal("0.00")
    else:
        average_order_value = (current_revenue / current_orders).quantize(
            Decimal("0.01")
        )

    # ----------------------------
    # Product Movement Analysis
    # ----------------------------
    start_dt = datetime.combine(current_start, datetime.min.time())
    end_dt = datetime.combine(current_end, datetime.max.time())

    product_sales = (
        db.query(
            Product.name,
            func.coalesce(func.sum(SaleItem.quantity), 0).label("quantity_sold"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.business_id == current_user.business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .group_by(Product.id, Product.name)
        .all()
    )

    top_selling_product = None
    slowest_product = None

    if product_sales:
        sorted_products = sorted(product_sales, key=lambda x: x.quantity_sold, reverse=True)

        top_selling_product = sorted_products[0].name
        slowest_product = sorted_products[-1].name

    # ----------------------------
    # Inventory Turnover Proxy
    # ----------------------------
    total_items_sold = sum(p.quantity_sold for p in product_sales) if product_sales else 0

    total_inventory_items = (
        db.query(func.coalesce(func.sum(Inventory.quantity_available), 0))
        .join(Product, Product.id == Inventory.product_id)
        .filter(Product.business_id == current_user.business_id)
        .scalar()
    )

    if not total_inventory_items:
        inventory_turnover_rate = Decimal("0.00")
    else:
        inventory_turnover_rate = (
            Decimal(total_items_sold) / Decimal(total_inventory_items)
        ).quantize(Decimal("0.01"))

    return {
        "period": period,
        "current_revenue": current_revenue,
        "previous_revenue": previous_revenue,
        "growth_percentage": growth_percentage,
        "average_order_value": average_order_value,
        "top_selling_product": top_selling_product,
        "slowest_product": slowest_product,
        "inventory_turnover_rate": inventory_turnover_rate,
    }