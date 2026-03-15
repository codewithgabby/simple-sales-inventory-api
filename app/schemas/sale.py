# schemas/sale.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List
from decimal import Decimal


class SaleItemCreate(BaseModel):
    product_id: int

    # quantity sold in the chosen unit
    quantity: Decimal = Field(..., gt=0)

    # NEW FIELD
    # unit used during the sale
    # examples: Cup, Kongo, Bag, Tablet, Pack
    unit: str


class SaleCreate(BaseModel):
    request_id: str
    items: List[SaleItemCreate]


class SaleItemResponse(BaseModel):
    product_id: int

    quantity: Decimal

    # return the unit used during the sale
    unit_name: str

    selling_price: Decimal
    line_total: Decimal

    class Config:
        from_attributes = True


class SaleResponse(BaseModel):
    id: int
    total_amount: Decimal
    created_at: datetime
    items: List[SaleItemResponse]

    class Config:
        from_attributes = True