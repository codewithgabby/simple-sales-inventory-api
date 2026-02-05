# schemas/report.py

from pydantic import BaseModel
from datetime import date
from decimal import Decimal


class SalesReportResponse(BaseModel):
    total_sales: Decimal
    total_orders: int
    total_items_sold: int
    start_date: date
    end_date: date

