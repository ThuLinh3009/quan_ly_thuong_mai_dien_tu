from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class TopSellingBookOut(BaseModel):
    product_id: int
    product_name: str
    total_quantity_sold: int
    total_revenue: Decimal


class RevenueReportItemOut(BaseModel):
    report_date: date
    orders_count: int
    revenue: Decimal


class DashboardSummaryOut(BaseModel):
    total_orders: int
    total_revenue: Decimal
    pending_orders: int
    new_customers: int


class DateRangeMixin(BaseModel):
    date_from: datetime
    date_to: datetime
