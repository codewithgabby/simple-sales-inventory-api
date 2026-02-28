from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.database import get_db
from app.core.auth import get_current_user
from app.core.subscription import require_subscription
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.models.products import Product
from app.models.inventory import Inventory

router = APIRouter(prefix="/premium", tags=["Premium Intelligence"])


@router.get("/profit-ranking")
def profit_ranking(
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
            detail="Upgrade to unlock Profit Intelligence Engine",
        )

    today = datetime.now(timezone.utc).date()

    if period == "weekly":
        start_date = today - timedelta(days=6)
    else:
        start_date = today - timedelta(days=29)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    results = (
        db.query(
            Product.id,
            Product.name,
            func.coalesce(func.sum(SaleItem.line_total), 0).label("revenue"),
            func.coalesce(func.sum(Product.cost_price * SaleItem.quantity), 0).label("cost"),
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

    formatted = []

    total_profit_all = Decimal("0.00")

    # First pass -- calculate profit per product
    for row in results:
        revenue = Decimal(row.revenue or 0)
        cost = Decimal(row.cost or 0)
        profit = revenue - cost

        total_profit_all += profit

        formatted.append({
            "product_id": row.id,
            "product_name": row.name,
            "revenue": revenue,
            "cost": cost,
            "profit": profit,
        })

    # Second pass -- calculate margin & contribution
    for item in formatted:

        revenue = item["revenue"]
        profit = item["profit"]

        if revenue == 0:
            margin = Decimal("0.00")
        else:
            margin = ((profit / revenue) * 100).quantize(Decimal("0.01"))

        if total_profit_all == 0:
            contribution = Decimal("0.00")
        else:
            contribution = ((profit / total_profit_all) * 100).quantize(Decimal("0.01"))

        item["profit_margin_percentage"] = margin
        item["profit_contribution_percentage"] = contribution

    # Sort descending for top
    sorted_desc = sorted(formatted, key=lambda x: x["profit"], reverse=True)

    # Sort ascending for bottom
    sorted_asc = sorted(formatted, key=lambda x: x["profit"])

    return {
        "period": period,
        "total_business_profit": total_profit_all,
        "top_5_products": sorted_desc[:5],
        "bottom_5_products": sorted_asc[:5],
    }



@router.get("/stock-prediction")
def stock_prediction(
    period: str = Query(..., pattern="^(weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    subscription = require_subscription(
        db,
        current_user.business_id,
        period,
    )

    if not subscription:
        raise HTTPException(
            status_code=402,
            detail="Upgrade to unlock Smart Stock Prediction",
        )

    today = datetime.now(timezone.utc).date()

    if period == "weekly":
        days_range = 7
        start_date = today - timedelta(days=6)
    else:
        days_range = 30
        start_date = today - timedelta(days=29)

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    results = []

    inventories = (
        db.query(Inventory)
        .join(Product)
        .filter(Product.business_id == current_user.business_id)
        .all()
    )

    for inv in inventories:

        total_sold = (
            db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
            .join(Sale, SaleItem.sale_id == Sale.id)
            .filter(
                Sale.business_id == current_user.business_id,
                SaleItem.product_id == inv.product_id,
                Sale.created_at.between(start_dt, end_dt),
            )
            .scalar()
        )

        total_sold = Decimal(total_sold or 0)

        if total_sold == 0:
            daily_avg = Decimal("0.00")
            days_remaining = None
            status_label = "idle"

        else:
            daily_avg = (total_sold / Decimal(days_range)).quantize(Decimal("0.01"))

            if daily_avg == 0:
                days_remaining = None
                status_label = "idle"
            else:
                days_remaining = (
                    Decimal(inv.quantity_available) / daily_avg
                ).quantize(Decimal("0.01"))

                if days_remaining <= 3:
                    status_label = "critical"
                elif days_remaining <= 7:
                    status_label = "warning"
                else:
                    status_label = "healthy"

        results.append({
            "product_id": inv.product_id,
            "product_name": inv.product.name,
            "current_stock": inv.quantity_available,
            "average_daily_sales": daily_avg,
            "estimated_days_remaining": days_remaining,
            "stock_status": status_label,
        })

    # Sort by urgency (critical first)
    priority_order = {"critical": 0, "warning": 1, "healthy": 2, "idle": 3}
    results.sort(key=lambda x: priority_order[x["stock_status"]])

    return {
        "period": period,
        "results": results
    }


@router.get("/risk-monitor")
def risk_monitor(
    days_without_sales: int = Query(30, ge=1),
    expiry_alert_days: int = Query(7, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Dead Stock & Expiry Risk Monitor

    - Products not sold in X days
    - Slow moving stock
    - Expiring soon products
    - Total capital locked in inventory
    """

    # Allow either weekly or monthly subscription
    weekly_sub = require_subscription(
        db, current_user.business_id, "weekly"
    )
    monthly_sub = require_subscription(
        db, current_user.business_id, "monthly"
    )

    if not weekly_sub and not monthly_sub:
        raise HTTPException(
            status_code=402,
            detail="Upgrade to unlock Risk Monitor",
        )

    today = datetime.now(timezone.utc).date()

    inventories = (
        db.query(Inventory)
        .join(Product)
        .filter(Product.business_id == current_user.business_id)
        .all()
    )

    dead_stock = []
    slow_moving = []
    expiring_soon = []

    total_capital_locked = Decimal("0.00")

    for inv in inventories:

        product = inv.product

        # -------------------------
        # CAPITAL LOCKED
        # -------------------------
        capital_locked = (
            Decimal(inv.quantity_available) * Decimal(product.cost_price)
        )
        total_capital_locked += capital_locked

        # -------------------------
        # LAST SOLD DATE
        # -------------------------
        last_sale = (
            db.query(func.max(Sale.created_at))
            .join(SaleItem, SaleItem.sale_id == Sale.id)
            .filter(
                Sale.business_id == current_user.business_id,
                SaleItem.product_id == product.id,
            )
            .scalar()
        )

        # -------------------------
        # DEAD STOCK CHECK
        # -------------------------
        if not last_sale:
            # Never sold
            dead_stock.append({
                "product_id": product.id,
                "product_name": product.name,
                "current_stock": inv.quantity_available,
                "capital_locked": capital_locked,
                "reason": "Never sold",
            })
        else:
            days_since_sale = (today - last_sale.date()).days

            if days_since_sale > days_without_sales:
                dead_stock.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "current_stock": inv.quantity_available,
                    "capital_locked": capital_locked,
                    "days_since_last_sale": days_since_sale,
                })
            elif days_since_sale > (days_without_sales // 2):
                slow_moving.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "current_stock": inv.quantity_available,
                    "days_since_last_sale": days_since_sale,
                })

        # -------------------------
        # EXPIRY CHECK
        # -------------------------
        if inv.expiry_date:
            days_to_expiry = (inv.expiry_date - today).days

            if 0 <= days_to_expiry <= expiry_alert_days:
                expiring_soon.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "expiry_date": inv.expiry_date,
                    "days_to_expiry": days_to_expiry,
                    "current_stock": inv.quantity_available,
                })

    return {
        "dead_stock": dead_stock,
        "slow_moving": slow_moving,
        "expiring_soon": expiring_soon,
        "total_capital_locked": total_capital_locked.quantize(Decimal("0.01")),
    }  