from decimal import Decimal
from pydantic import BaseModel, Field
from datetime import datetime


class ProductCreate(BaseModel):
    name: str

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
    cost_price: float | None = None
    selling_price: float | None = None    

class ProductResponse(BaseModel):
    id: int
    name: str
    cost_price: float
    selling_price: float
    created_at: datetime

    class Config:
        from_attributes = True
