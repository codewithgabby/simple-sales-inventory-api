# =========================================================
# SALES ROUTER (PREMIUM HISTORY LOCK SECURED)
#
# FREE USERS:
# - Can create sales
# - Can see only last 7 days of sales
# - Cannot access older sales directly by ID
#
# PAID USERS:
# - Full history access
#
# Secure against ID-based history bypass
# =========================================================

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal
from datetime import timedelta, datetime
import pytz

from app.database import get_db
from app.core.auth import get_current_user
from app.core.subscription import get_active_subscription
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.models.products import Product
from app.models.inventory import Inventory
from app.models.business import Business
from app.models.product_units import ProductUnitConversion
from app.schemas.sale import SaleCreate, SaleResponse
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/sales", tags=["Sales"])


# =========================================================
# CREATE SALE
# =========================================================
@router.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def create_sale(
    request: Request,
    sale_data: SaleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not sale_data.items:
        raise HTTPException(status_code=400, detail="Sale must contain items")

    product_ids = [item.product_id for item in sale_data.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="Duplicate products in sale are not allowed")

    # ===============================
    # IDEMPOTENCY CHECK
    # ===============================
    existing_sale = (
        db.query(Sale)
        .filter(
            Sale.business_id == current_user.business_id,
            Sale.request_id == sale_data.request_id,
        )
        .first()
    )

    if existing_sale:
        return existing_sale

    total_amount = Decimal("0.00")
    sale_items_objects = []

    try:
        sale = Sale(
            business_id=current_user.business_id,
            total_amount=Decimal("0.00"),
            request_id=sale_data.request_id,
        )
        db.add(sale)
        db.flush()

        for item in sale_data.items:

            if item.quantity is None or item.quantity <= 0:
                raise HTTPException(status_code=400, detail="Item quantity must be greater than zero")

            product = (
                db.query(Product)
                .filter(
                    Product.id == item.product_id,
                    Product.business_id == current_user.business_id,
                )
                .first()
            )

            if not product:
                raise HTTPException(status_code=404, detail="Product not found")

            inventory = (
                db.query(Inventory)
                .filter(Inventory.product_id == product.id)
                .with_for_update()
                .first()
            )

            if not inventory:
                raise HTTPException(status_code=400, detail=f"No inventory for {product.name}")

            # ====================================
            # UNIT CONVERSION LOGIC
            # ====================================

            sale_unit = item.unit
            quantity = Decimal(item.quantity)

            if sale_unit == product.base_unit:
                deduction = quantity
            else:
                conversion = (
                    db.query(ProductUnitConversion)
                    .filter(
                        ProductUnitConversion.product_id == product.id,
                        ProductUnitConversion.unit_name == sale_unit,
                    )
                    .first()
                )

                if not conversion:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unit '{sale_unit}' is not defined for {product.name}",
                    )

                deduction = quantity * Decimal(conversion.conversion_rate)

            # ====================================
            # STOCK CHECK
            # ====================================

            if inventory.quantity_available < deduction:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {product.name}",
                )

            # ====================================
            # LINE TOTAL
            # ====================================

            line_total = product.selling_price * deduction
            total_amount += line_total

            # ====================================
            # DEDUCT INVENTORY
            # ====================================

            inventory.quantity_available -= deduction

            sale_items_objects.append(
                SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    quantity=deduction,
                    unit_name=sale_unit,
                    selling_price=product.selling_price,
                    line_total=line_total,
                )
            )

        sale.total_amount = total_amount
        db.add_all(sale_items_objects)
        

        # ====================================
        # UPDATE STREAK FOR BUSINESS
        # ====================================
        tz = pytz.timezone('Africa/Lagos')
        sale_nigerian_date = datetime.now(tz).date()
        
        business = db.query(Business).filter(Business.id == current_user.business_id).first()
        
        if business:
            last_date = business.last_sale_date
            current_streak = business.current_streak or 0
            
            if last_date == sale_nigerian_date:
                new_streak = current_streak
            elif last_date == sale_nigerian_date - timedelta(days=1):
                new_streak = current_streak + 1
            else:
                new_streak = 1
            
            business.last_sale_date = sale_nigerian_date
            business.current_streak = new_streak
            
        db.commit()
        db.refresh(sale)    

        return sale

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to complete sale")


# =========================================================
# LIST SALES (HISTORY LOCK APPLIED)
# =========================================================
@router.get("", response_model=list[SaleResponse])
def list_sales(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    subscription = get_active_subscription(db, current_user.business_id)

    query = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(Sale.business_id == current_user.business_id)
    )

    if not subscription:
        tz = pytz.timezone('Africa/Lagos')
        seven_days_ago = datetime.now(tz) - timedelta(days=6)
        query = query.filter(Sale.created_at >= seven_days_ago)

    sales = (
        query
        .order_by(Sale.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return sales


# =========================================================
# GET ALL SALES (FOR DASHBOARD METRICS ONLY)
# =========================================================
@router.get("/all", response_model=list[SaleResponse])
def list_all_sales_for_dashboard(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    subscription = get_active_subscription(db, current_user.business_id)

    query = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(Sale.business_id == current_user.business_id)
        .order_by(Sale.created_at.desc())
    )

    if not subscription:
        tz = pytz.timezone('Africa/Lagos')
        seven_days_ago = datetime.now(tz) - timedelta(days=6)
        query = query.filter(Sale.created_at >= seven_days_ago)

    return query.all()


# =========================================================
# GET SINGLE SALE
# =========================================================
@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    sale = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(
            Sale.id == sale_id,
            Sale.business_id == current_user.business_id,
        )
        .first()
    )

    if not sale:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sale not found",
        )

    subscription = get_active_subscription(db, current_user.business_id)

    if not subscription:
        tz = pytz.timezone('Africa/Lagos')
        seven_days_ago = datetime.now(tz) - timedelta(days=6)
        
        if sale.created_at < seven_days_ago:
            raise HTTPException(
                status_code=402,
                detail="Upgrade to access historical sales",
            )

    return sale