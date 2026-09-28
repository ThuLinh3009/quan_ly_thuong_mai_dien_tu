from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_variant_id: int
    quantity: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartItemOut(BaseModel):
    product_variant_id: int
    product_id: int
    product_name: str
    variant_name: str
    sku: str
    cover_image_url: str | None = None
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class CartOut(BaseModel):
    cart_id: int | None
    items: list[CartItemOut] = []
    subtotal: Decimal
