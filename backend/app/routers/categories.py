from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import require_roles
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.schemas.common import Page
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=Page[CategoryOut])
async def list_categories(
    keyword: str | None = Query(default=None, description="Tìm theo tên"),
    parent_id: int | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
):
    return await category_service.list_categories(
        conn, keyword=keyword, parent_id=parent_id, is_active=is_active, limit=limit, offset=offset
    )


@router.get("/{category_id}", response_model=CategoryOut)
async def get_category(category_id: int, conn: AsyncConnection = Depends(get_conn)):
    return await category_service.get_category(conn, category_id)


@router.post("", response_model=CategoryOut, status_code=201)
async def create_category(
    data: CategoryCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(require_roles("admin")),
):
    return await category_service.create_category(conn, data, current_user)


@router.put("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(require_roles("admin")),
):
    return await category_service.update_category(conn, category_id, data, current_user)


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(require_roles("admin")),
):
    await category_service.delete_category(conn, category_id, current_user)
