from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import require_roles
from app.schemas.common import Page
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate
from app.services import supplier_service

router = APIRouter(prefix="/suppliers", tags=["suppliers"])


@router.get("", response_model=Page[SupplierOut])
async def list_suppliers(
    keyword: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(require_roles("admin", "staff")),
):
    return await supplier_service.list_suppliers(conn, keyword=keyword, is_active=is_active, limit=limit, offset=offset)


@router.get("/{supplier_id}", response_model=SupplierOut)
async def get_supplier(
    supplier_id: int,
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(require_roles("admin", "staff")),
):
    return await supplier_service.get_supplier(conn, supplier_id)


@router.post("", response_model=SupplierOut, status_code=201)
async def create_supplier(
    data: SupplierCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(require_roles("admin")),
):
    return await supplier_service.create_supplier(conn, data, current_user)


@router.put("/{supplier_id}", response_model=SupplierOut)
async def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(require_roles("admin")),
):
    return await supplier_service.update_supplier(conn, supplier_id, data, current_user)


@router.delete("/{supplier_id}", response_model=SupplierOut)
async def deactivate_supplier(
    supplier_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(require_roles("admin")),
):
    return await supplier_service.deactivate_supplier(conn, supplier_id, current_user)
