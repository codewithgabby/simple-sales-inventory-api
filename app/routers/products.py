# app/routers/products.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import get_current_user
from app.models.products import Product
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


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

    product = Product(
        name=product_data.name,
        cost_price=product_data.cost_price,
        selling_price=product_data.selling_price,
        business_id=current_user.business_id,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


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
    new_cost_price = product_data.cost_price if product_data.cost_price is not None else product.cost_price
    new_selling_price = product_data.selling_price if product_data.selling_price is not None else product.selling_price

    if new_selling_price < new_cost_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selling price cannot be lower than cost price",
        )

    if product_data.name is not None:
        product.name = product_data.name

    if product_data.cost_price is not None:
        product.cost_price = product_data.cost_price

    if product_data.selling_price is not None:
        product.selling_price = product_data.selling_price

    db.commit()
    db.refresh(product)

    return product


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

    db.delete(product)
    db.commit()

    return None
