# app/routers/products.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core import subscription
from app.database import get_db
from app.core.auth import get_current_user
from app.core.subscription import get_active_subscription
from app.models.products import Product
from app.models.sale_items import SaleItem
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


# =========================================================
# CREATE PRODUCT
# =========================================================
@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Prevent duplicate product names per business
    existing_product = (
        db.query(Product)
        .filter(
            Product.name == product_data.name,
            Product.business_id == current_user.business_id,
        )
        .first()
    )

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product with this name already exists",
        )

    # Business rule: selling price must not be lower than cost price
    if product_data.selling_price < product_data.cost_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selling price cannot be lower than cost price",
        )

    # Prevent empty base unit
    if not product_data.base_unit.strip():
        raise HTTPException(
            status_code=400,
            detail="Base unit cannot be empty",
        )
    
    # ================================
    # PRODUCT LIMIT LOGIC 
    # ================================

    subscription = get_active_subscription(db, current_user.business_id)

    product_count = db.query(Product).filter(
        Product.business_id == current_user.business_id
    ).count()

    if not subscription:
        if product_count >= 10:
            raise HTTPException(
                status_code=403,
                detail="Free plan allows only 10 products. Upgrade to add more."
           )

    elif subscription.period_type.value == "weekly":
        if product_count >= 30:
            raise HTTPException(
                status_code=403,
                detail="Weekly plan allows only 30 products. Upgrade to monthly."
            )

    product = Product(
        name=product_data.name,
        base_unit=product_data.base_unit.strip(),
        cost_price=product_data.cost_price,
        selling_price=product_data.selling_price,
        business_id=current_user.business_id,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


# =========================================================
# LIST PRODUCTS
# =========================================================
@router.get("", response_model=list[ProductResponse])
def list_products(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    products = (
        db.query(Product)
        .filter(Product.business_id == current_user.business_id)
        .order_by(Product.id.desc())
        .all()
    )

    return products


# =========================================================
# UPDATE PRODUCT
# =========================================================
@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.business_id == current_user.business_id,
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Validate prices if either is being updated
    new_cost_price = (
        product_data.cost_price
        if product_data.cost_price is not None
        else product.cost_price
    )

    new_selling_price = (
        product_data.selling_price
        if product_data.selling_price is not None
        else product.selling_price
    )

    if new_cost_price < 0:
        raise HTTPException(
            status_code=400,
            detail="Cost price cannot be negative"
    )

    if new_selling_price <= 0:
        raise HTTPException(
            status_code=400,
            detail="Selling price must be greater than zero"
    )

    if new_selling_price < new_cost_price:
        raise HTTPException(
            status_code=400,
            detail="Selling price cannot be lower than cost price"
    )

    if product_data.name is not None:
        product.name = product_data.name

    if product_data.base_unit is not None:
        if not product_data.base_unit.strip():
            raise HTTPException(
                status_code=400,
                detail="Base unit cannot be empty",
            )
        product.base_unit = product_data.base_unit.strip()

    if product_data.cost_price is not None:
        product.cost_price = product_data.cost_price

    if product_data.selling_price is not None:
        product.selling_price = product_data.selling_price

    db.commit()
    db.refresh(product)

    return product


# =========================================================
# DELETE PRODUCT
# =========================================================
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.business_id == current_user.business_id,
        )
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Prevent deleting products that already have sales
    has_sales = (
        db.query(SaleItem)
        .filter(SaleItem.product_id == product_id)
        .first()
    )

    if has_sales:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product has sales records and cannot be deleted",
        )

    db.delete(product)
    db.commit()

    return None

# =========================================================
# BATCH FETCH UNITS FOR MULTIPLE PRODUCTS
# =========================================================
@router.get("/units/batch", response_model=dict)
def batch_get_product_units(
    product_ids: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Fetch units for multiple products in a single request.
    Accepts comma-separated product IDs: /products/units/batch?product_ids=1,2,3
    Returns a dictionary mapping product_id to list of units (including base unit)
    """
    # Import here to avoid circular imports
    from app.models.product_units import ProductUnitConversion
    
    # Parse product IDs from query parameter
    ids = []
    for id_str in product_ids.split(','):
        try:
            ids.append(int(id_str.strip()))
        except ValueError:
            continue
    
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid product IDs provided"
        )
    
    # Verify all products belong to this business
    products = (
        db.query(Product)
        .filter(
            Product.id.in_(ids),
            Product.business_id == current_user.business_id
        )
        .all()
    )
    
    # Create mapping of product_id to product
    product_map = {p.id: p for p in products}
    
    # Fetch all unit conversions for these products in one query
    units = (
        db.query(ProductUnitConversion)
        .filter(ProductUnitConversion.product_id.in_(ids))
        .all()
    )
    
    # Group units by product_id
    units_by_product = {}
    for unit in units:
        if unit.product_id not in units_by_product:
            units_by_product[unit.product_id] = []
        units_by_product[unit.product_id].append({
            "id": unit.id,
            "unit_name": unit.unit_name,
            "conversion_rate": unit.conversion_rate
        })
    
    # Build response with base unit included for each product
    result = {}
    for product_id in ids:
        product = product_map.get(product_id)
        if not product:
            # If product doesn't exist or belongs to another business, return empty units
            result[str(product_id)] = []
            continue
        
        # Get custom units for this product
        custom_units = units_by_product.get(product_id, [])
        
        # Build response with base unit first
        units_list = [
            {
                "id": 0,
                "unit_name": product.base_unit,
                "conversion_rate": 1
            }
        ] + custom_units
        
        result[str(product_id)] = units_list
    
    return result    