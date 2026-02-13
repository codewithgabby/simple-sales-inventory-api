from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta, datetime
from typing import Optional
from decimal import Decimal

from app.database import get_db
from app.core.auth import get_current_user
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.models.products import Product
from app.schemas.report import (
    SalesReportResponse,
    ProductProfitReportResponse,
    ProductProfitResponse,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


# =========================================================
# SUMMARY REPORT CALCULATOR (TIMESTAMP SAFE)
# =========================================================
def _calculate_report(
    db: Session,
    business_id: int,
    start_date: date,
    end_date: date,
):
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    total_sales = (
        db.query(func.coalesce(func.sum(Sale.total_amount), 0))
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .scalar()
    )

    total_orders = (
        db.query(func.count(Sale.id))
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .scalar()
    )

    total_items_sold = (
        db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale)
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .scalar()
    )

    total_cost = (
        db.query(
            func.coalesce(
                func.sum(Product.cost_price * SaleItem.quantity),
                0,
            )
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .scalar()
    )

    total_sales = Decimal(total_sales or 0)
    total_cost = Decimal(total_cost or 0)
    total_profit = total_sales - total_cost

    return {
        "total_sales": total_sales,
        "total_cost": total_cost,
        "total_profit": total_profit,
        "total_orders": total_orders,
        "total_items_sold": total_items_sold,
        "start_date": start_date,
        "end_date": end_date,
    }


# =========================================================
# PRODUCT PROFIT CALCULATOR (FILTER + PAGINATION SAFE)
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

    query = (
        db.query(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            func.coalesce(func.sum(SaleItem.quantity), 0).label("total_quantity_sold"),
            func.coalesce(func.sum(SaleItem.line_total), 0).label("total_revenue"),
            func.coalesce(
                func.sum(Product.cost_price * SaleItem.quantity),
                0,
            ).label("total_cost"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .group_by(Product.id, Product.name)
        .order_by(func.sum(SaleItem.line_total).desc())
    )

    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))

    total_products = query.count()

    results = query.limit(limit).offset(offset).all()

    formatted_results = []

    for row in results:
        total_revenue = Decimal(row.total_revenue or 0)
        total_cost = Decimal(row.total_cost or 0)
        total_profit = total_revenue - total_cost

        formatted_results.append(
            ProductProfitResponse(
                product_id=row.product_id,
                product_name=row.product_name,
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
# SUMMARY ENDPOINTS
# =========================================================
@router.get("/daily", response_model=SalesReportResponse)
def daily_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()

    return _calculate_report(
        db=db,
        business_id=current_user.business_id,
        start_date=today,
        end_date=today,
    )


@router.get("/weekly", response_model=SalesReportResponse)
def weekly_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    end_date = date.today()
    start_date = end_date - timedelta(days=6)

    return _calculate_report(
        db=db,
        business_id=current_user.business_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/monthly", response_model=SalesReportResponse)
def monthly_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()
    start_date = today.replace(day=1)

    return _calculate_report(
        db=db,
        business_id=current_user.business_id,
        start_date=start_date,
        end_date=today,
    )


# =========================================================
# PRODUCT PROFIT ENDPOINTS
# =========================================================
@router.get("/daily/products", response_model=ProductProfitReportResponse)
def daily_product_profit(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
):
    today = date.today()

    return _calculate_product_profit(
        db=db,
        business_id=current_user.business_id,
        start_date=today,
        end_date=today,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/weekly/products", response_model=ProductProfitReportResponse)
def weekly_product_profit(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
):
    end_date = date.today()
    start_date = end_date - timedelta(days=6)

    return _calculate_product_profit(
        db=db,
        business_id=current_user.business_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get("/monthly/products", response_model=ProductProfitReportResponse)
def monthly_product_profit(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1),
    offset: int = Query(0, ge=0),
):
    today = date.today()
    start_date = today.replace(day=1)

    return _calculate_product_profit(
        db=db,
        business_id=current_user.business_id,
        start_date=start_date,
        end_date=today,
        search=search,
        limit=limit,
        offset=offset,
    )
