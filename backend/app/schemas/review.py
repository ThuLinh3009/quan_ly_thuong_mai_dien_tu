from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.core.text import strip_html_tags


class ReviewCreate(BaseModel):
    order_item_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def _sanitize_comment(cls, value: str | None) -> str | None:
        return strip_html_tags(value) if value else value


class ReviewOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    rating: int
    comment: str | None
    created_at: datetime


class ReviewableOrderItemOut(BaseModel):
    order_item_id: int
    order_id: int
    order_code: str
    product_id: int
    product_name: str
    sku: str
    delivered_at: datetime


class ProductRatingSummaryOut(BaseModel):
    average_rating: float
    review_count: int
