from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.core.audit import record_audit
from app.core.errors import NotFoundError
from app.repositories import supplier_repo
from app.schemas.common import Page
from app.schemas.supplier import SupplierCreate, SupplierUpdate


async def create_supplier(conn: AsyncConnection, data: SupplierCreate, current_user: dict[str, Any]) -> dict[str, Any]:
    supplier = await supplier_repo.create(
        conn,
        name=data.name,
        contact_phone=data.contact_phone,
        email=data.email,
        address=data.address,
        is_active=data.is_active,
    )
    await record_audit(
        conn, user_id=current_user["id"], action="create", entity_type="supplier",
        entity_id=supplier["id"], new_value=supplier,
    )
    return supplier


async def list_suppliers(
    conn: AsyncConnection, *, keyword: str | None, is_active: bool | None, limit: int, offset: int
) -> Page:
    rows, total = await supplier_repo.list_suppliers(
        conn, keyword=keyword, is_active=is_active, limit=limit, offset=offset
    )
    items = [{k: v for k, v in row.items() if k != "total_count"} for row in rows]
    return Page(items=items, total=total, limit=limit, offset=offset)


async def get_supplier(conn: AsyncConnection, supplier_id: int) -> dict[str, Any]:
    supplier = await supplier_repo.get_by_id(conn, supplier_id)
    if supplier is None:
        raise NotFoundError(f"Không tìm thấy supplier id={supplier_id}")
    return supplier


async def update_supplier(
    conn: AsyncConnection, supplier_id: int, data: SupplierUpdate, current_user: dict[str, Any]
) -> dict[str, Any]:
    old = await get_supplier(conn, supplier_id)
    fields = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
    updated = await supplier_repo.update(conn, supplier_id, fields) if fields else old
    await record_audit(
        conn, user_id=current_user["id"], action="update", entity_type="supplier",
        entity_id=supplier_id, old_value=old, new_value=updated,
    )
    return updated


async def deactivate_supplier(conn: AsyncConnection, supplier_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    """Suppliers không có cột deleted_at trong schema -> 'xóa' = khóa (is_active=false)."""
    old = await get_supplier(conn, supplier_id)
    updated = await supplier_repo.set_active(conn, supplier_id, False)
    if updated is None:
        raise NotFoundError(f"Không tìm thấy supplier id={supplier_id}")
    await record_audit(
        conn, user_id=current_user["id"], action="deactivate", entity_type="supplier",
        entity_id=supplier_id, old_value=old, new_value=updated,
    )
    return updated
