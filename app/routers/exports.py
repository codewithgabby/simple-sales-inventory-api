from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload
from datetime import date, timedelta, datetime
from io import BytesIO

from openpyxl import Workbook
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.core.auth import get_current_user
from app.models.sales import Sale
from app.models.products import Product
from app.models.export_access import ExportAccess
from app.core.rate_limiter import limiter

router = APIRouter(
    prefix="/exports",
    tags=["Exports"],
)


# =========================================================
# ACCESS CHECK HELPER (PAID EXPORTS ONLY)
# =========================================================
def _require_export_access(
    db: Session,
    business_id: int,
    period_type: str,
    start_date: date,
    end_date: date,
):
    access = (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == business_id,
            ExportAccess.period_type == period_type,
            ExportAccess.start_date <= start_date,
            ExportAccess.end_date >= end_date,
        )
        .first()
    )

    if not access:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Please pay to download this export",
        )


# =========================================================
# DAILY EXPORT — FREE
# =========================================================
@router.get("/daily")
@limiter.limit("10/minute")
def export_daily_sales(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()

    start_dt = datetime.combine(today, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    sales = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(
            Sale.business_id == current_user.business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .all()
    )

    return _build_excel(
        db=db,
        sales=sales,
        sheet_name="Daily Sales",
        filename=f"daily_sales_{today}.xlsx",
    )


# =========================================================
# WEEKLY EXPORT — PAID
# =========================================================
@router.get("/weekly")
@limiter.limit("5/minute")
def export_weekly_sales(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()
    start_date = today - timedelta(days=6)

    _require_export_access(
        db=db,
        business_id=current_user.business_id,
        period_type="weekly",
        start_date=start_date,
        end_date=today,
    )

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    sales = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(
            Sale.business_id == current_user.business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .all()
    )

    return _build_excel(
        db=db,
        sales=sales,
        sheet_name="Weekly Sales",
        filename=f"weekly_sales_{start_date}_to_{today}.xlsx",
    )


# =========================================================
# MONTHLY EXPORT — PAID
# =========================================================
@router.get("/monthly")
@limiter.limit("5/minute")
def export_monthly_sales(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today = date.today()
    start_date = today.replace(day=1)

    _require_export_access(
        db=db,
        business_id=current_user.business_id,
        period_type="monthly",
        start_date=start_date,
        end_date=today,
    )

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(today, datetime.max.time())

    sales = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(
            Sale.business_id == current_user.business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .all()
    )

    return _build_excel(
        db=db,
        sales=sales,
        sheet_name="Monthly Sales",
        filename=f"monthly_sales_{today.strftime('%Y_%m')}.xlsx",
    )


# =========================================================
# EXCEL BUILDER
# =========================================================
def _build_excel(
    db: Session,
    sales: list[Sale],
    sheet_name: str,
    filename: str,
):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name

    sheet.append([
        "Date",
        "Sale ID",
        "Product",
        "Quantity",
        "Unit Price",
        "Line Total",
        "Total Sale Amount",
    ])

    product_cache = {}
    total_sales_amount = 0.0

    for sale in sales:
        total_sales_amount += float(sale.total_amount)

        for item in sale.items:
            if item.product_id not in product_cache:
                product_cache[item.product_id] = (
                    db.query(Product)
                    .filter(
                        Product.id == item.product_id,
                        Product.business_id == sale.business_id,
                    )
                    .first()
                )

            product = product_cache[item.product_id]

            sheet.append([
                sale.created_at.strftime("%Y-%m-%d"),
                sale.id,
                product.name if product else "Deleted product",
                item.quantity,
                float(item.selling_price),
                float(item.line_total),
                float(sale.total_amount),
            ])

    sheet.append([])

    sheet.append([
        "",
        "",
        "",
        "",
        "",
        "TOTAL SALES AMOUNT (₦):",
        round(total_sales_amount, 2),
    ])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
