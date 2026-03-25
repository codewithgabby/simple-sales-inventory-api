# app/routers/product_units.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import get_current_user
from app.models.products import Product
from app.models.product_units import ProductUnitConversion
from app.schemas.product_units import ProductUnitCreate, ProductUnitResponse

router = APIRouter(
    prefix="/products/{product_id}/units",
    tags=["Product Units"],
)


# =========================================================
# CREATE UNIT CONVERSION
# =========================================================
@router.post("", response_model=ProductUnitResponse, status_code=status.HTTP_201_CREATED)
def create_unit_conversion(
    product_id: int,
    unit_data: ProductUnitCreate,
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
        raise HTTPException(status_code=404, detail="Product not found")

    unit_name = unit_data.unit_name.strip()

    if not unit_name:
        raise HTTPException(
            status_code=400,
            detail="Unit name cannot be empty",
        )

    if unit_name.lower() == product.base_unit.lower():
        raise HTTPException(
            status_code=400,
            detail="Unit cannot be the same as the base unit",
        )

    if unit_data.conversion_rate <= 0:
        raise HTTPException(
            status_code=400,
            detail="Conversion rate must be greater than zero",
        )

    # NEW: Prevent decimal conversion rates
    if unit_data.conversion_rate % 1 != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Conversion rate must be a whole number (no decimals). For example, if 1 {unit_name} = 0.5 {product.base_unit}, use 2 {unit_name} = 1 {product.base_unit} instead (conversion rate = 2)."
        )

    existing_unit = (
        db.query(ProductUnitConversion)
        .filter(
            ProductUnitConversion.product_id == product_id,
            ProductUnitConversion.unit_name.ilike(unit_name),
        )
        .first()
    )

    if existing_unit:
        raise HTTPException(
            status_code=400,
            detail="This unit already exists for the product",
        )

    unit = ProductUnitConversion(
        product_id=product_id,
        unit_name=unit_name,
        conversion_rate=unit_data.conversion_rate,
    )

    db.add(unit)
    db.commit()
    db.refresh(unit)

    return unit


# =========================================================
# LIST PRODUCT UNITS (INCLUDES BASE UNIT)
# =========================================================
@router.get("", response_model=list[ProductUnitResponse])
def list_product_units(
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
        raise HTTPException(status_code=404, detail="Product not found")

    conversions = (
        db.query(ProductUnitConversion)
        .filter(ProductUnitConversion.product_id == product_id)
        .all()
    )

    # Include base unit as the first option
    base_unit = ProductUnitResponse(
        id=0,
        unit_name=product.base_unit,
        conversion_rate=1
    )

    return [base_unit] + conversions


# =========================================================
# DELETE UNIT CONVERSION
# =========================================================
@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit_conversion(
    product_id: int,
    unit_id: int,
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
        raise HTTPException(status_code=404, detail="Product not found")

    unit = (
        db.query(ProductUnitConversion)
        .filter(
            ProductUnitConversion.id == unit_id,
            ProductUnitConversion.product_id == product_id,
        )
        .first()
    )

    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    db.delete(unit)
    db.commit()

    return None