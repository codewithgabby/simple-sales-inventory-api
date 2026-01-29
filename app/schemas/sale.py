# schemas/sale.py

from pydantic import BaseModel
from datetime import datetime
from typing import List
from decimal import Decimal

class SaleItemCreate(BaseModel):
    product_id: int
    quantity: int

class SaleCreate(BaseModel):
    items: List[SaleItemCreate]

class SaleItemResponse(BaseModel):
    product_id: int
    quantity: int
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




