# routers/sales.py

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from decimal import Decimal

from app.database import get_db
from app.core.auth import get_current_user
from app.models.sales import Sale
from app.models.sale_items import SaleItem
from app.models.products import Product
from app.models.inventory import Inventory
from app.schemas.sale import SaleCreate, SaleResponse
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/sales", tags=["Sales"])


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

    # Prevent duplicate products in same sale
    product_ids = [item.product_id for item in sale_data.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate products in sale are not allowed",
        )

    total_amount = Decimal("0.00")
    sale_items_objects = []

    try:
        # Create sale FIRST
        sale = Sale(
            business_id=current_user.business_id,
            total_amount=Decimal("0.00"),
        )
        db.add(sale)
        db.flush()  # get sale.id safely

        for item in sale_data.items:
            if item.quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Item quantity must be greater than zero",
                )

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
                raise HTTPException(
                    status_code=400,
                    detail=f"No inventory for {product.name}",
                )

            if inventory.quantity_available < item.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {product.name}",
                )

            line_total = product.selling_price * item.quantity
            total_amount += line_total

            inventory.quantity_available -= item.quantity

            sale_items_objects.append(
                SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    selling_price=product.selling_price,
                    line_total=line_total,
                )
            )

        sale.total_amount = total_amount
        db.add_all(sale_items_objects)
        db.commit()
        db.refresh(sale)

        return sale

    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to complete sale",
        )





@router.get("", response_model=list[SaleResponse])
def list_sales(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    List all sales for the logged-in business
    """
    sales = (
        db.query(Sale)
        .options(joinedload(Sale.items))
        .filter(Sale.business_id == current_user.business_id)
        .order_by(Sale.created_at.desc())
        .all()
    )

    return sales


@router.get("/{sale_id}", response_model=SaleResponse)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get a single sale (receipt view)
    """
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

    return sale
