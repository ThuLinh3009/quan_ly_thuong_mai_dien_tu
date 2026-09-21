from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ImportItemCreate(BaseModel):
    product_variant_id: int
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class ImportLotCreate(BaseModel):
    supplier_id: int
    items: list[ImportItemCreate] = Field(min_length=1)


class ImportItemOut(BaseModel):
    id: int
    product_variant_id: int
    variant_name: str | None = None
    sku: str | None = None
    quantity: int
    unit_cost: Decimal


class ImportLotOut(BaseModel):
    id: int
    lot_code: str
    supplier_id: int
    supplier_name: str | None = None
    imported_at: datetime
    created_by: int
    items: list[ImportItemOut] = []
