from pydantic import BaseModel, Field
from decimal import Decimal


class ProductUnitCreate(BaseModel):
    unit_name: str

    # how many base units equal ONE of this unit
    conversion_rate: Decimal = Field(..., gt=0)


class ProductUnitResponse(BaseModel):
    id: int
    unit_name: str
    conversion_rate: Decimal

    class Config:
        from_attributes = True