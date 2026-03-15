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

    if unit_data.unit_name == product.base_unit:
        raise HTTPException(
            status_code=400,
            detail="Unit cannot be the same as the base unit",
        )

    existing_unit = (
        db.query(ProductUnitConversion)
        .filter(
            ProductUnitConversion.product_id == product_id,
            ProductUnitConversion.unit_name == unit_data.unit_name,
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
        unit_name=unit_data.unit_name,
        conversion_rate=unit_data.conversion_rate,
    )

    db.add(unit)
    db.commit()
    db.refresh(unit)

    return unit


# =========================================================
# LIST PRODUCT UNITS
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

    units = (
        db.query(ProductUnitConversion)
        .filter(ProductUnitConversion.product_id == product_id)
        .all()
    )

    return units


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