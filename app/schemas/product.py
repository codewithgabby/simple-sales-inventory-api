from pydantic import BaseModel
from datetime import datetime


class ProductCreate(BaseModel):
    name: str
    cost_price: float
    selling_price: float

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
