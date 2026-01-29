from pydantic import BaseModel
from datetime import date


class InventoryCreate(BaseModel):
    quantity_available: int
    low_stock_threshold: int = 5
    expiry_date: date | None = None

class InventoryUpdate(BaseModel):
    quantity_available: int | None = None
    low_stock_threshold: int | None = None
    expiry_date: date | None = None    

class InventoryResponse(BaseModel):
    id: int
    product_id: int
    quantity_available: int
    low_stock_threshold: int
    expiry_date: date | None

    class Config:
        from_attributes = True

