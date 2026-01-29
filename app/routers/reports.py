# routers/reports.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta

from app.database import get_db
from app.core.auth import get_current_user
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.schemas.report import SalesReportResponse

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/daily", response_model=SalesReportResponse)
def daily_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()

    total_sales = (
        db.query(func.coalesce(func.sum(Sale.total_amount), 0))
        .filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) == today,
        )
        .scalar()
    )

    total_orders = (
        db.query(func.count(Sale.id))
        .filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) == today,
        )
        .scalar()
    )

    total_items_sold = (
        db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale)
        .filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at) == today,
        )
        .scalar()
    )

    return {
        "total_sales": total_sales,
        "total_orders": total_orders,
        "total_items_sold": total_items_sold,
        "start_date": today,
        "end_date": today,
    }

@router.get("/weekly", response_model=SalesReportResponse)
def weekly_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    end_date = date.today()
    start_date = end_date - timedelta(days=6)

    total_sales = (
        db.query(func.coalesce(func.sum(Sale.total_amount), 0))
        .filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at).between(start_date, end_date),
        )
        .scalar()
    )

    total_orders = (
        db.query(func.count(Sale.id))
        .filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at).between(start_date, end_date),
        )
        .scalar()
    )

    total_items_sold = (
        db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale)
        .filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at).between(start_date, end_date),
        )
        .scalar()
    )

    return {
        "total_sales": total_sales,
        "total_orders": total_orders,
        "total_items_sold": total_items_sold,
        "start_date": start_date,
        "end_date": end_date,
    }


@router.get("/monthly", response_model=SalesReportResponse)
def monthly_report(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()
    start_date = today.replace(day=1)
    end_date = today

    total_sales = (
        db.query(func.coalesce(func.sum(Sale.total_amount), 0))
        .filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at).between(start_date, end_date),
        )
        .scalar()
    )

    total_orders = (
        db.query(func.count(Sale.id))
        .filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at).between(start_date, end_date),
        )
        .scalar()
    )

    total_items_sold = (
        db.query(func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale)
        .filter(
            Sale.business_id == current_user.business_id,
            func.date(Sale.created_at).between(start_date, end_date),
        )
        .scalar()
    )

    return {
        "total_sales": total_sales,
        "total_orders": total_orders,
        "total_items_sold": total_items_sold,
        "start_date": start_date,
        "end_date": end_date,
    }



