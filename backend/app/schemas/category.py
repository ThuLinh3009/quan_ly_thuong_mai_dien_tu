from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    slug: str | None = Field(default=None, max_length=160)
    parent_id: int | None = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    slug: str | None = Field(default=None, max_length=160)
    parent_id: int | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    id: int
    parent_id: int | None
    name: str
    slug: str
    is_active: bool
