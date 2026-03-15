# app/schemas/product.py

from decimal import Decimal
from pydantic import BaseModel, Field
from datetime import datetime


class ProductCreate(BaseModel):
    name: str

    # NEW FIELD
    # The unit used internally for inventory storage.
    # Example: Cup, Tablet, Bag, Kg, Piece
    base_unit: str

    cost_price: Decimal = Field(
        ...,
        gt=0,
        lt=100_000_000,
        description="Cost price must be below 100 million"
    )

    selling_price: Decimal = Field(
        ...,
        gt=0,
        lt=100_000_000,
        description="Selling price must be below 100 million"
    )


class ProductUpdate(BaseModel):
    name: str | None = None
    cost_price: Decimal | None = None
    selling_price: Decimal | None = None
    base_unit: str | None = None


class ProductResponse(BaseModel):
    id: int
    name: str
    base_unit: str
    cost_price: Decimal
    selling_price: Decimal
    created_at: datetime

    class Config:
        from_attributes = True