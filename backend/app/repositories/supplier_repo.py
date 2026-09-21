"""Repository cho Supplier — gọi function DB trong database/functions.sql
(mục 14: create_supplier, get_supplier_by_id, list_suppliers, update_supplier,
set_supplier_active). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def get_by_id(conn: AsyncConnection, supplier_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_supplier_by_id(%s)", (supplier_id,))
    return await cur.fetchone()


async def create(
    conn: AsyncConnection,
    *,
    name: str,
    contact_phone: str | None,
    email: str | None,
    address: str | None,
    is_active: bool,
) -> dict[str, Any]:
    cur = await conn.execute(
        "SELECT * FROM create_supplier(%s, %s, %s, %s, %s)",
        (name, contact_phone, email, address, is_active),
    )
    row = await cur.fetchone()
    assert row is not None
    return row


async def list_suppliers(
    conn: AsyncConnection,
    *,
    keyword: str | None,
    is_active: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    cur = await conn.execute(
        "SELECT * FROM list_suppliers(%s, %s, %s, %s)", (keyword, is_active, limit, offset)
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update(
    conn: AsyncConnection,
    supplier_id: int,
    *,
    name: str,
    contact_phone: str | None,
    email: str | None,
    address: str | None,
    is_active: bool,
) -> dict[str, Any] | None:
    """Nhận đủ giá trị cuối cùng (đã merge với dữ liệu cũ ở service)."""
    cur = await conn.execute(
        "SELECT * FROM update_supplier(%s, %s, %s, %s, %s, %s)",
        (supplier_id, name, contact_phone, email, address, is_active),
    )
    return await cur.fetchone()


async def set_active(conn: AsyncConnection, supplier_id: int, is_active: bool) -> dict[str, Any] | None:
    cur = await conn.execute(
        "SELECT * FROM set_supplier_active(%s, %s)", (supplier_id, is_active)
    )
    return await cur.fetchone()
