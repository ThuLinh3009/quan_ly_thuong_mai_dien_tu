from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import get_optional_user, require_roles
from app.schemas.common import Page
from app.schemas.product import (
    ExcelImportResult,
    ProductCreate,
    ProductListItem,
    ProductOut,
    ProductUpdate,
    VariantCreate,
    VariantUpdate,
)
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])

_write_roles = require_roles("admin", "staff")


@router.get("", response_model=Page[ProductListItem])
async def list_products(
    keyword: str | None = Query(default=None, description="Tìm theo tên/tác giả/mô tả"),
    category_id: int | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    is_active: bool | None = Query(default=None, description="Chỉ Admin/Staff mới lọc được sản phẩm ẩn"),
    sort_by: Literal["name", "base_price", "created_at"] = Query(default="created_at"),
    sort_dir: Literal["asc", "desc"] = Query(default="desc"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] | None = Depends(get_optional_user),
):
    return await product_service.list_products(
        conn,
        keyword=keyword,
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        is_active=is_active,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        current_user=current_user,
    )


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] | None = Depends(get_optional_user),
):
    return await product_service.get_product(conn, product_id, current_user)


@router.post("", response_model=ProductOut, status_code=201)
async def create_product(
    data: ProductCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_write_roles),
):
    return await product_service.create_product(conn, data, current_user)


@router.put("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_write_roles),
):
    return await product_service.update_product(conn, product_id, data, current_user)


@router.delete("/{product_id}", status_code=204)
async def delete_product(
    product_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_write_roles),
):
    await product_service.delete_product(conn, product_id, current_user)


@router.post("/{product_id}/variants", response_model=ProductOut, status_code=201)
async def add_variant(
    product_id: int,
    data: VariantCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_write_roles),
):
    return await product_service.add_variant(conn, product_id, data, current_user)


@router.put("/variants/{variant_id}", response_model=ProductOut)
async def update_variant(
    variant_id: int,
    data: VariantUpdate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_write_roles),
):
    return await product_service.update_variant(conn, variant_id, data, current_user)


@router.patch("/variants/{variant_id}/deactivate", response_model=ProductOut)
async def deactivate_variant(
    variant_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_write_roles),
):
    return await product_service.deactivate_variant(conn, variant_id, current_user)


@router.post("/import-excel", response_model=ExcelImportResult)
async def import_excel(
    file: UploadFile = File(...),
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_write_roles),
):
    content = await file.read()
    return await product_service.import_products_from_excel(conn, content, current_user)
