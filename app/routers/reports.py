# =========================================================
# REPORTS ROUTER (SALESZY PREMIUM VERSION)
#
# FREE USERS:
# - Can access DAILY report fully
# - Can access WEEKLY & MONTHLY revenue
# - Cannot see cost or profit for weekly/monthly
# - Can access DAILY product profit
# - Cannot access WEEKLY/MONTHLY product profit
#
# PAID USERS:
# - Weekly subscription unlocks weekly profit + weekly product profit
# - Monthly subscription unlocks monthly profit + monthly product profit
#
# Schema-safe: Always returns Decimal (never None)
# =========================================================

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from typing import Optional
from calendar import monthrange

from app.database import get_db
from app.core.auth import get_current_user
from app.core.subscription import require_subscription, get_active_subscription
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.models.products import Product
from app.models.inventory import Inventory
from app.schemas.report import (
    SalesReportResponse,
    ProductProfitReportResponse,
    ProductProfitResponse,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


# =========================================================
# CORE SALES SUMMARY CALCULATION
# =========================================================
def _calculate_report(
    db: Session,
    business_id: int,
    start_date: date,
    end_date: date,
):
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    base_filter = [
        Sale.business_id == business_id,
        Sale.created_at.between(start_dt, end_dt),
    ]

    total_sales = (
        db.query(func.coalesce(func.sum(Sale.total_amount), 0))
        .filter(*base_filter)
        .scalar()
    )

    total_orders = (
        db.query(func.count(Sale.id))
        .filter(*base_filter)
        .scalar()
    )

    total_items_sold = (
        db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(*base_filter)
        .scalar()
    )

    total_cost = (
        db.query(func.coalesce(func.sum(Product.cost_price * SaleItem.quantity), 0))
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(*base_filter)
        .scalar()
    )

    total_sales = Decimal(total_sales or 0)
    total_cost = Decimal(total_cost or 0)
    total_profit = total_sales - total_cost

    #  PROFIT MARGIN %
    if total_sales == 0:
        profit_margin_percentage = Decimal("0.00")
    else:
        profit_margin_percentage = (
            (total_profit / total_sales) * 100
        ).quantize(Decimal("0.01"))

    return {
        "total_sales": total_sales,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "profit_margin_percentage": profit_margin_percentage,
        "total_orders": total_orders,
        "total_items_sold": total_items_sold,
        "start_date": start_date,
        "end_date": end_date,
    }


# =========================================================
# CORE PRODUCT PROFIT CALCULATION
# =========================================================
def _calculate_product_profit(
    db: Session,
    business_id: int,
    start_date: date,
    end_date: date,
    search: Optional[str],
    limit: int,
    offset: int,
):
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    base_query = (
        db.query(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.base_unit.label("base_unit"),
            func.coalesce(func.sum(SaleItem.quantity), 0).label("total_quantity_sold"),
            func.coalesce(func.sum(SaleItem.line_total), 0).label("total_revenue"),
            func.coalesce(
                func.sum(Product.cost_price * SaleItem.quantity), 0
            ).label("total_cost"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .group_by(Product.id, Product.name, Product.base_unit)
    )

    if search:
        base_query = base_query.filter(Product.name.ilike(f"%{search}%"))

    total_products = base_query.count()

    results = (
        base_query
        .order_by(func.sum(SaleItem.line_total).desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    formatted_results = []

    for row in results:
        total_revenue = Decimal(row.total_revenue or 0)
        total_cost = Decimal(row.total_cost or 0)
        total_profit = total_revenue - total_cost

        formatted_results.append(
            ProductProfitResponse(
                product_id=row.product_id,
                product_name=row.product_name,
                base_unit=row.base_unit,
                total_quantity_sold=row.total_quantity_sold,
                total_revenue=total_revenue,
                total_cost=total_cost,
                total_profit=total_profit,
            )
        )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "total_products": total_products,
        "results": formatted_results,
    }


# =========================================================
# DAILY REPORT (FREE)
# =========================================================
# =========================================================
# DAILY REPORT (PROFIT LOCKED FOR FREE USERS)
# =========================================================
@router.get("/daily", response_model=SalesReportResponse)
def daily_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = datetime.now(timezone.utc).date()
    
    report = _calculate_report(
        db,
        current_user.business_id,
        today,
        today,
    )
    
    # Check if user has active subscription
    subscription = get_active_subscription(db, current_user.business_id)
    
    if not subscription:
        # Free user - hide cost, profit, and margin
        report["total_cost"] = None
        report["total_profit"] = None
        report["profit_margin_percentage"] = None
    
    return report

# =========================================================
# WEEKLY REPORT (PROFIT LOCKED)
# =========================================================
@router.get("/weekly", response_model=SalesReportResponse)
def weekly_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=6)

    report = _calculate_report(
        db,
        current_user.business_id,
        start_date,
        today,
    )

    subscription = require_subscription(
        db,
        current_user.business_id,
        "weekly",
    )

    if not subscription:
        report["total_cost"] = Decimal("0.00")
        report["total_profit"] = Decimal("0.00")
        report["profit_margin_percentage"] = Decimal("0.00")

    return report


# =========================================================
# MONTHLY REPORT (PROFIT LOCKED)
# =========================================================
@router.get("/monthly", response_model=SalesReportResponse)
def monthly_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=29)

    report = _calculate_report(
        db,
        current_user.business_id,
        start_date,
        today,
    )

    subscription = require_subscription(
        db,
        current_user.business_id,
        "monthly",
    )

    if not subscription:
        report["total_cost"] = Decimal("0.00")
        report["total_profit"] = Decimal("0.00")
        report["profit_margin_percentage"] = Decimal("0.00")

    return report


# =========================================================
# DAILY PRODUCT PROFIT (FREE)
# =========================================================
# =========================================================
# DAILY PRODUCT PROFIT (LOCKED FOR FREE USERS)
# =========================================================
@router.get("/daily/products", response_model=ProductProfitReportResponse)
def daily_product_profit(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
):
    # Check if user has active subscription
    subscription = get_active_subscription(db, current_user.business_id)
    
    if not subscription:
        # Free user - return empty product profit data
        return {
            "start_date": datetime.now(timezone.utc).date(),
            "end_date": datetime.now(timezone.utc).date(),
            "total_products": 0,
            "results": [],
            "locked": True  # Add flag to indicate locked
        }
    
    today = datetime.now(timezone.utc).date()

    return _calculate_product_profit(
        db=db,
        business_id=current_user.business_id,
        start_date=today,
        end_date=today,
        search=search,
        limit=limit,
        offset=offset,
    )


# =========================================================
# WEEKLY PRODUCT PROFIT (LOCKED)
# =========================================================
@router.get("/weekly/products", response_model=ProductProfitReportResponse)
def weekly_product_profit(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
):
    subscription = require_subscription(
        db,
        current_user.business_id,
        "weekly",
    )

    if not subscription:
        raise HTTPException(
            status_code=402,
            detail="Upgrade to unlock weekly product profit insights",
        )

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=6)

    return _calculate_product_profit(
        db=db,
        business_id=current_user.business_id,
        start_date=start_date,
        end_date=today,
        search=search,
        limit=limit,
        offset=offset,
    )


# =========================================================
# MONTHLY PRODUCT PROFIT (LOCKED)
# =========================================================
@router.get("/monthly/products", response_model=ProductProfitReportResponse)
def monthly_product_profit(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
):
    subscription = require_subscription(
        db,
        current_user.business_id,
        "monthly",
    )

    if not subscription:
        raise HTTPException(
            status_code=402,
            detail="Upgrade to unlock monthly product profit insights",
        )

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=29)

    return _calculate_product_profit(
        db=db,
        business_id=current_user.business_id,
        start_date=start_date,
        end_date=today,
        search=search,
        limit=limit,
        offset=offset,
    )


# =========================================================
# PROFIT TREND (PAID ONLY)
# =========================================================
@router.get("/trend")
def profit_trend(
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
            detail="Upgrade to unlock Profit Trend",
        )

    today = datetime.now(timezone.utc).date()

    trend_data = []

    # For weekly, we want to show the profit for each of the last 7 days
    if period == "weekly":
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            result = _calculate_report(
                db,
                current_user.business_id,
                day,
                day,
            )
            trend_data.append({
                "date": day,
                "profit": result["total_profit"],
            })

    
    
    # For monthly, we want to show the profit for the last 3 months (including current month)
    else:  # monthly

        current_year = today.year
        current_month = today.month

        for i in range(0, 3):

            # Calculate target month
            target_month = current_month - i
            target_year = current_year

            while target_month <= 0:
                target_month += 12
                target_year -= 1

        # First day of that month
            month_start = date(target_year, target_month, 1)

        # Last day of that month
            last_day = monthrange(target_year, target_month)[1]
            month_end = date(target_year, target_month, last_day)

            result = _calculate_report(
                db,
                current_user.business_id,
                month_start,
                month_end,
            )

            trend_data.append({
                "month_start": month_start,
                "profit": result["total_profit"],
          })

    return trend_data


# =========================================================
# END OF DAY BUSINESS SUMMARY
# =========================================================

@router.get("/end-of-day")
def end_of_day_summary(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = datetime.now(timezone.utc).date()

    summary = _calculate_report(
        db,
        current_user.business_id,
        today,
        today,
    )

    # Check if user has ANY active subscription
    subscription = get_active_subscription(
        db,
        current_user.business_id,
    )

    top_product_name = None
    low_stock_products = []

    # Premium features only
    if subscription:
        # Top selling product
        top_product = (
            db.query(
                Product.name,
                func.sum(
                    (Product.selling_price - Product.cost_price) * SaleItem.quantity
                ).label("profit")
            )
            .join(SaleItem, SaleItem.product_id == Product.id)
            .join(Sale, SaleItem.sale_id == Sale.id)
            .filter(
                Sale.business_id == current_user.business_id,
                func.date(Sale.created_at) == today
            )
            .group_by(Product.name)
            .order_by(
                func.sum(
                    (Product.selling_price - Product.cost_price) * SaleItem.quantity
                ).desc()
            )
            .first()
        )

        if top_product:
            top_product_name = top_product.name

        # Low stock alerts
        low_stock = (
            db.query(
                Product.id,           
                Product.name,
                Product.base_unit,
                Inventory.quantity_available,
            )
            .join(Inventory, Inventory.product_id == Product.id)
            .filter(
                Product.business_id == current_user.business_id,
                Inventory.quantity_available <= Inventory.low_stock_threshold
            )
            .order_by(Inventory.quantity_available.asc())
            .limit(3)
            .all()
        )

        low_stock_products = [
            {
                "product_id": item.id,        
                "product_name": item.name,
                "quantity_left": item.quantity_available,
                "base_unit": item.base_unit,
            }
            for item in low_stock
        ]
        
        # For paid users - return full profit data
        return {
            "date": today,
            "total_sales": summary["total_sales"],
            "total_cost": summary["total_cost"],
            "total_profit": summary["total_profit"],
            "total_orders": summary["total_orders"],
            "total_items_sold": summary["total_items_sold"],
            "top_selling_product": top_product_name,
            "low_stock_products": low_stock_products,
        }
    
    else:
        # For FREE users - hide profit and cost
        return {
            "date": today,
            "total_sales": summary["total_sales"],
            "total_cost": None,  # Hide cost
            "total_profit": None,  # Hide profit
            "total_orders": summary["total_orders"],
            "total_items_sold": summary["total_items_sold"],
            "top_selling_product": None,  # Hide top product for free users
            "low_stock_products": low_stock_products,  # Low stock still shows (premium feature)
        }