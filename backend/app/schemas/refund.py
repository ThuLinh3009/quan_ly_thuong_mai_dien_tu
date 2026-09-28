from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.text import strip_html_tags

RefundStatus = Literal["requested", "approved", "rejected", "refunded"]


class RefundRequestCreate(BaseModel):
    order_id: int
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def _sanitize_reason(cls, value: str) -> str:
        return strip_html_tags(value)


class RefundDecisionRequest(BaseModel):
    approve: bool


class RefundRequestOut(BaseModel):
    id: int
    order_id: int
    reason: str
    status: RefundStatus
    refund_amount: Decimal
    requested_at: datetime


class RefundRequestDetailOut(RefundRequestOut):
    order_code: str
    user_id: int
    processed_by: int | None = None
    processed_at: datetime | None = None
