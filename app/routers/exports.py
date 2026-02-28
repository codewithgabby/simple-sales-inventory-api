from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from datetime import date, timedelta, datetime, timezone
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.core.auth import get_current_user
from app.core.subscription import get_active_subscription
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.models.products import Product
from app.models.export_access import ExportAccess
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/exports", tags=["Exports"])


# =========================================================
# ACCESS CHECK HELPER
# =========================================================
def _require_export_access(db: Session, business_id: int, period_type: str):
    today = datetime.now(timezone.utc).date()

    access = (
        db.query(ExportAccess)
        .filter(
            ExportAccess.business_id == business_id,
            ExportAccess.period_type == period_type,
            ExportAccess.start_date <= today,
            ExportAccess.end_date >= today,
        )
        .first()
    )

    if not access:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Please pay to download this export",
        )


# =========================================================
# EXPORT ROUTES
# =========================================================

@router.get("/daily")
@limiter.limit("10/minute")
def export_daily_sales(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    today = datetime.now(timezone.utc).date()
    return _generate_export(db, current_user.business_id, "daily", today, today)


@router.get("/weekly")
@limiter.limit("5/minute")
def export_weekly_sales(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _require_export_access(db, current_user.business_id, "weekly")

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=6)
    return _generate_export(db, current_user.business_id, "weekly", start_date, today)


@router.get("/monthly")
@limiter.limit("5/minute")
def export_monthly_sales(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    _require_export_access(db, current_user.business_id, "monthly")

    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=29)
    return _generate_export(db, current_user.business_id, "monthly", start_date, today)


# =========================================================
# CORE EXPORT GENERATOR
# =========================================================
def _generate_export(db: Session, business_id: int, period_type: str, start_date: date, end_date: date):

    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())

    sales = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .all()
    )

    subscription = get_active_subscription(db, business_id)

    return _build_excel(
        db=db,
        sales=sales,
        business_id=business_id,
        subscription=subscription,
        period_type=period_type,
        start_date=start_date,
        end_date=end_date,
        filename=f"{period_type}_sales_{start_date}_to_{end_date}.xlsx",
    )


# =========================================================
# EXCEL BUILDER
# =========================================================
def _build_excel(
    db: Session,
    sales: list[Sale],
    business_id: int,
    subscription,
    period_type: str,
    start_date: date,
    end_date: date,
    filename: str,
):

    workbook = Workbook()

    # =======================
    # SHEET 1 - RAW SALES
    # =======================
    sheet = workbook.active
    sheet.title = "Sales Data"

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
    total_revenue = Decimal("0.00")

    for sale in sales:
        total_revenue += sale.total_amount

        for item in sale.items:
            if item.product_id not in product_cache:
                product_cache[item.product_id] = (
                    db.query(Product)
                    .filter(Product.id == item.product_id)
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

    # =======================
    # SHEET 2 - BUSINESS SUMMARY
    # =======================
    summary = workbook.create_sheet(title="Business Summary")

    summary.append(["Period", f"{start_date} to {end_date}"])
    summary.append([])

    # Calculate cost
    total_cost = (
        db.query(func.coalesce(func.sum(Product.cost_price * SaleItem.quantity), 0))
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time()),
            ),
        )
        .scalar()
    )

    total_cost = Decimal(total_cost or 0)
    total_profit = total_revenue - total_cost

    if total_revenue == 0:
        margin = Decimal("0.00")
    else:
        margin = ((total_profit / total_revenue) * 100).quantize(Decimal("0.01"))

    # Top Product
    top_product = (
        db.query(Product.name, func.sum(SaleItem.line_total).label("revenue"))
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, SaleItem.sale_id == Sale.id)
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time()),
            ),
        )
        .group_by(Product.name)
        .order_by(func.sum(SaleItem.line_total).desc())
        .first()
    )

        # ======================================================
    # PROFIT GROWTH CALCULATION (Premium Insight)
    # ======================================================

    previous_start = None
    previous_end = None

    if period_type == "daily":
        previous_start = start_date - timedelta(days=1)
        previous_end = previous_start

    elif period_type == "weekly":
        previous_start = start_date - timedelta(days=7)
        previous_end = start_date - timedelta(days=1)

    elif period_type == "monthly":
        previous_start = start_date - timedelta(days=30)
        previous_end = start_date - timedelta(days=1)

    previous_profit = Decimal("0.00")

    if previous_start and previous_end:
        prev_cost = (
            db.query(func.coalesce(func.sum(Product.cost_price * SaleItem.quantity), 0))
            .join(SaleItem, SaleItem.product_id == Product.id)
            .join(Sale, SaleItem.sale_id == Sale.id)
            .filter(
                Sale.business_id == business_id,
                Sale.created_at.between(
                    datetime.combine(previous_start, datetime.min.time()),
                    datetime.combine(previous_end, datetime.max.time()),
                ),
            )
            .scalar()
        )

        prev_revenue = (
            db.query(func.coalesce(func.sum(Sale.total_amount), 0))
            .filter(
                Sale.business_id == business_id,
                Sale.created_at.between(
                    datetime.combine(previous_start, datetime.min.time()),
                    datetime.combine(previous_end, datetime.max.time()),
                ),
            )
            .scalar()
        )

        prev_cost = Decimal(prev_cost or 0)
        prev_revenue = Decimal(prev_revenue or 0)
        previous_profit = prev_revenue - prev_cost

    if previous_profit == 0:
        if total_profit > 0:
            profit_growth = Decimal("100.00")
        else:    
            profit_growth = Decimal("0.00")
    else:
        profit_growth = (
            ((total_profit - previous_profit) / previous_profit) * 100
        ).quantize(Decimal("0.01"))

    summary.append(["Total Revenue (₦)", float(total_revenue)])

    if subscription:
        summary.append(["Total Cost (₦)", float(total_cost)])
        summary.append(["Total Profit (₦)", float(total_profit)])
        summary.append(["Profit Margin (%)", float(margin)])
        summary.append(["Top Performing Product", top_product[0] if top_product else "N/A"])
        summary.append(["Profit Growth (%)", float(profit_growth)])
    else:
        summary.append(["Total Cost (₦)", " Upgrade to unlock"])
        summary.append(["Total Profit (₦)", " Upgrade to unlock"])
        summary.append(["Profit Margin (%)", " Upgrade to unlock"])
        summary.append(["Top Performing Product", " Upgrade to unlock"])
        summary.append(["Profit Growth (%)", " Upgrade to unlock"])
    
    # =======================
    # RETURN FILE
    # =======================
    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )