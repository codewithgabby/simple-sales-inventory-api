# schemas/report.py

from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import List



class SalesReportResponse(BaseModel):
    total_sales: Decimal
    total_cost: Decimal
    total_profit: Decimal
    total_orders: int
    total_items_sold: int
    start_date: date
    end_date: date


class ProductProfitResponse(BaseModel):
    product_id: int
    product_name: str
    total_quantity_sold: int
    total_revenue: Decimal
    total_cost: Decimal
    total_profit: Decimal

class ProductProfitReportResponse(BaseModel):
    start_date: date
    end_date: date
    total_products: int
    results: List[ProductProfitResponse]    

    
