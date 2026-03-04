from pydantic import BaseModel, Field
from datetime import date


class InventoryCreate(BaseModel):
    quantity_available: int = Field(..., ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)
    expiry_date: date | None = None

class InventoryUpdate(BaseModel):
    quantity_available: int | None = Field(None, ge=0)
    low_stock_threshold: int | None = Field(None, ge=0)
    expiry_date: date | None = None

class InventoryResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity_available: int
    low_stock_threshold: int
    expiry_date: date | None

    class Config:
        from_attributes = True

