from datetime import datetime

from pydantic import BaseModel, Field


class AddressCreate(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=150)
    phone: str = Field(min_length=1, max_length=20)
    line1: str = Field(min_length=1, max_length=255)
    ward: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    province: str = Field(min_length=1, max_length=100)
    is_default: bool = False


class AddressOut(BaseModel):
    id: int
    user_id: int
    recipient_name: str
    phone: str
    line1: str
    ward: str | None
    district: str | None
    province: str
    is_default: bool
    created_at: datetime
