from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

PromotionType = Literal["percentage", "fixed_amount", "flash_sale"]


class PromotionCreate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    type: PromotionType
    value: Decimal = Field(gt=0)
    min_order_amount: Decimal = Field(default=Decimal("0"), ge=0)
    max_discount_amount: Decimal | None = Field(default=None, ge=0)
    starts_at: datetime
    ends_at: datetime
    usage_limit: int | None = Field(default=None, gt=0)
    per_user_limit: int | None = Field(default=None, gt=0)
    is_active: bool = True

    @model_validator(mode="after")
    def _check_dates(self) -> "PromotionCreate":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at phải sau starts_at")
        if self.type == "percentage" and self.value > 100:
            raise ValueError("Khuyến mãi phần trăm không được vượt quá 100")
        return self


class PromotionUpdate(BaseModel):
    value: Decimal | None = Field(default=None, gt=0)
    min_order_amount: Decimal | None = Field(default=None, ge=0)
    max_discount_amount: Decimal | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = Field(default=None, gt=0)
    per_user_limit: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class PromotionOut(BaseModel):
    id: int
    code: str | None
    type: PromotionType
    value: Decimal
    min_order_amount: Decimal
    max_discount_amount: Decimal | None
    starts_at: datetime
    ends_at: datetime
    usage_limit: int | None
    per_user_limit: int | None
    is_active: bool


class FlashSaleItemCreate(BaseModel):
    product_variant_id: int
    flash_price: Decimal = Field(ge=0)
    quantity_limit: int = Field(gt=0)


class FlashSaleItemOut(BaseModel):
    id: int
    promotion_id: int
    product_variant_id: int
    variant_name: str | None = None
    product_name: str | None = None
    flash_price: Decimal
    quantity_limit: int
    quantity_sold: int


class ActiveFlashSaleOut(BaseModel):
    promotion_id: int
    product_variant_id: int
    product_id: int
    product_name: str
    variant_name: str
    base_price: Decimal
    flash_price: Decimal
    quantity_limit: int
    quantity_sold: int
    ends_at: datetime
