# app/routers/inventory.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.auth import get_current_user
from app.models.inventory import Inventory
from app.models.products import Product
from app.schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
)

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)


@router.post("/{product_id}", response_model=InventoryResponse, status_code=201)
def add_inventory(
    product_id: int,
    inventory_data: InventoryCreate,
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

    if product.inventory:
        raise HTTPException(status_code=400, detail="Inventory already exists")

    if inventory_data.quantity_available < 0:
        raise HTTPException(
            status_code=400,
            detail="Quantity cannot be negative",
        )

    inventory = Inventory(
        product_id=product.id,
        quantity_available=inventory_data.quantity_available,
        low_stock_threshold=inventory_data.low_stock_threshold,
        expiry_date=inventory_data.expiry_date,
    )

    db.add(inventory)
    db.commit()
    db.refresh(inventory)

    return inventory


@router.put("/{product_id}", response_model=InventoryResponse)
def update_inventory(
    product_id: int,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    inventory = (
        db.query(Inventory)
        .join(Product)
        .filter(
            Inventory.product_id == product_id,
            Product.business_id == current_user.business_id,
        )
        .first()
    )

    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    if inventory_data.quantity_available is not None:
        if inventory_data.quantity_available < 0:
            raise HTTPException(
                status_code=400,
                detail="Quantity cannot be negative",
            )
        inventory.quantity_available = inventory_data.quantity_available

    if inventory_data.low_stock_threshold is not None:
        if inventory_data.low_stock_threshold < 0:
            raise HTTPException(
                status_code=400,
                detail="Low stock threshold cannot be negative",
            )
        inventory.low_stock_threshold = inventory_data.low_stock_threshold

    if inventory_data.expiry_date is not None:
        inventory.expiry_date = inventory_data.expiry_date

    db.commit()
    db.refresh(inventory)

    return inventory


@router.get("", response_model=list[InventoryResponse])
def list_inventory(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return (
        db.query(Inventory)
        .join(Product)
        .filter(Product.business_id == current_user.business_id)
        .all()
    )
