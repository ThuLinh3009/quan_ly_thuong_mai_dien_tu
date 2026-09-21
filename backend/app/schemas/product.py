from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class VariantCreate(BaseModel):
    variant_name: str = Field(min_length=1, max_length=100)
    sku: str = Field(min_length=1, max_length=60)
    price_adjustment: Decimal = Decimal("0")
    is_active: bool = True
    initial_quantity: int = Field(default=0, ge=0)
    reorder_level: int = Field(default=0, ge=0)


class VariantUpdate(BaseModel):
    variant_name: str | None = Field(default=None, min_length=1, max_length=100)
    price_adjustment: Decimal | None = None
    is_active: bool | None = None
    reorder_level: int | None = Field(default=None, ge=0)


class VariantOut(BaseModel):
    id: int
    product_id: int
    variant_name: str
    sku: str
    price_adjustment: Decimal
    is_active: bool
    quantity_on_hand: int | None = None
    quantity_reserved: int | None = None
    reorder_level: int | None = None


class ProductCreate(BaseModel):
    category_id: int
    sku: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=270)
    author: str | None = Field(default=None, max_length=150)
    publisher: str | None = Field(default=None, max_length=150)
    isbn: str | None = Field(default=None, max_length=20)
    description: str | None = None
    cover_image_url: str | None = Field(default=None, max_length=500)
    base_price: Decimal = Field(ge=0)
    is_active: bool = True
    variants: list[VariantCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    category_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=270)
    author: str | None = Field(default=None, max_length=150)
    publisher: str | None = Field(default=None, max_length=150)
    isbn: str | None = Field(default=None, max_length=20)
    description: str | None = None
    cover_image_url: str | None = Field(default=None, max_length=500)
    base_price: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductListItem(BaseModel):
    id: int
    sku: str
    name: str
    author: str | None
    category_id: int
    category_name: str
    base_price: Decimal
    cover_image_url: str | None
    is_active: bool
    created_at: datetime


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    slug: str
    author: str | None
    publisher: str | None
    isbn: str | None
    description: str | None
    cover_image_url: str | None
    base_price: Decimal
    is_active: bool
    category_id: int
    category_name: str
    created_at: datetime
    updated_at: datetime
    variants: list[VariantOut]


class ExcelImportResult(BaseModel):
    created: int
    failed: int
    errors: list[str]
