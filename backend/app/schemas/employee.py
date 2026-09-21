from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class StaffCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)
    full_name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=20)


class StaffUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=20)


class StaffOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone: str | None
    role: str
    is_active: bool
    created_at: datetime
