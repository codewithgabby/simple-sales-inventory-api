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
from app.models.product_units import ProductUnitConversion
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/exports", tags=["Exports"])


# =========================================================
# UNIT CONVERSION HELPER
# =========================================================
def convert_to_readable(quantity: Decimal, product, units_by_product: dict):
    """Convert quantity to readable format using product units"""
    
    # Get units for this product from cache
    units = units_by_product.get(product.id, [])
    
    # Convert Decimal to float for calculations
    remaining = float(quantity)
    
    if not units:
        # No units configured, use base unit
        if remaining.is_integer():
            qty = int(remaining)
        else:
            qty = remaining
        unit = product.base_unit or "unit"
        if qty != 1 and not unit.endswith('s'):
            unit = unit + 's'
        return f"{qty} {unit}"
    
    # Sort units from largest to smallest
    sorted_units = sorted(units, key=lambda u: float(u.conversion_rate), reverse=True)
    
    parts = []
    
    for unit in sorted_units:
        rate = float(unit.conversion_rate)
        count = int(remaining // rate)
        if count > 0:
            unit_name = unit.unit_name
            if count == 1:
                parts.append(f"{count} {unit_name}")
            else:
                # Add 's' for plural if needed
                if not unit_name.endswith('s'):
                    parts.append(f"{count} {unit_name}s")
                else:
                    parts.append(f"{count} {unit_name}")
            remaining = remaining % rate
    
    # Add remaining base units
    if remaining > 0:
        if remaining.is_integer():
            qty = int(remaining)
        else:
            qty = remaining
        unit = product.base_unit or "unit"
        if qty != 1 and not unit.endswith('s'):
            unit = unit + 's'
        parts.append(f"{qty} {unit}")
    
    return " ".join(parts)


def fetch_units_for_products(db: Session, product_ids: list):
    """Fetch all units for given products in one query"""
    if not product_ids:
        return {}
    
    units = db.query(ProductUnitConversion).filter(
        ProductUnitConversion.product_id.in_(product_ids)
    ).all()
    
    # Organize by product_id
    units_by_product = {}
    for unit in units:
        if unit.product_id not in units_by_product:
            units_by_product[unit.product_id] = []
        units_by_product[unit.product_id].append(unit)
    
    return units_by_product


# =========================================================
# ACCESS CHECK HELPER
# =========================================================

def _require_export_access(db: Session, business_id: int, period_type: str):
    today = datetime.now(timezone.utc).date()

    # If requesting weekly export, check for weekly OR monthly subscription
    if period_type == "weekly":
        access = (
            db.query(ExportAccess)
            .filter(
                ExportAccess.business_id == business_id,
                ExportAccess.start_date <= today,
                ExportAccess.end_date >= today,
                ExportAccess.period_type.in_(["weekly", "monthly"])  # ← KEY CHANGE
            )
            .first()
        )
    else:  # monthly
        access = (
            db.query(ExportAccess)
            .filter(
                ExportAccess.business_id == business_id,
                ExportAccess.period_type == "monthly",
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
        .options(joinedload(Sale.items).joinedload(SaleItem.product))
        .filter(
            Sale.business_id == business_id,
            Sale.created_at.between(start_dt, end_dt),
        )
        .all()
    )
    
    # Get all unique product IDs from sales
    product_ids = set()
    for sale in sales:
        for item in sale.items:
            if item.product_id:
                product_ids.add(item.product_id)
    
    # Fetch all units for these products in one go
    units_by_product = fetch_units_for_products(db, list(product_ids))

    subscription = get_active_subscription(db, business_id)

    return _build_excel(
        db=db,
        sales=sales,
        units_by_product=units_by_product,
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
    units_by_product: dict,
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

    total_revenue = Decimal("0.00")

    for sale in sales:
        total_revenue += sale.total_amount

        for item in sale.items:
            product = item.product
            
            if product:
                # Create a simple object for the product
                class SimpleProduct:
                    def __init__(self, id, base_unit):
                        self.id = id
                        self.base_unit = base_unit
                
                simple_product = SimpleProduct(product.id, product.base_unit)
                
                # Convert quantity to readable format
                try:
                    readable_qty = convert_to_readable(item.quantity, simple_product, units_by_product)
                except Exception as e:
                    print(f"Error converting quantity for product {product.id}: {e}")
                    # Fallback to simple format
                    qty = float(item.quantity)
                    if qty.is_integer():
                        qty = int(qty)
                    readable_qty = f"{qty} {product.base_unit or 'units'}"
            else:
                readable_qty = f"{int(item.quantity)} units"

            sheet.append([
                sale.created_at.strftime("%Y-%m-%d"),
                sale.id,
                product.name if product else "Deleted product",
                readable_qty,
                f"₦{float(item.selling_price):,.2f}",
                f"₦{float(item.line_total):,.2f}",
                f"₦{float(sale.total_amount):,.2f}",
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