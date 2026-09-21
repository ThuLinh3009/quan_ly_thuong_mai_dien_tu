from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

COLUMNS = "id, name, contact_phone, email, address, is_active"


async def get_by_id(conn: AsyncConnection, supplier_id: int) -> dict[str, Any] | None:
    cur = await conn.execute(f"SELECT {COLUMNS} FROM suppliers WHERE id = %s", (supplier_id,))
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
        f"""
        INSERT INTO suppliers (name, contact_phone, email, address, is_active)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING {COLUMNS}
        """,
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
    conditions = ["1 = 1"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if keyword:
        conditions.append("name ILIKE %(keyword)s")
        params["keyword"] = f"%{keyword}%"
    if is_active is not None:
        conditions.append("is_active = %(is_active)s")
        params["is_active"] = is_active

    where_clause = " AND ".join(conditions)
    cur = await conn.execute(
        f"""
        SELECT {COLUMNS}, COUNT(*) OVER() AS total_count
        FROM suppliers
        WHERE {where_clause}
        ORDER BY name
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update(conn: AsyncConnection, supplier_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    if not fields:
        return await get_by_id(conn, supplier_id)

    set_clause = ", ".join(f"{key} = %({key})s" for key in fields)
    params = {**fields, "id": supplier_id}
    cur = await conn.execute(
        f"UPDATE suppliers SET {set_clause} WHERE id = %(id)s RETURNING {COLUMNS}",
        params,
    )
    return await cur.fetchone()


async def set_active(conn: AsyncConnection, supplier_id: int, is_active: bool) -> dict[str, Any] | None:
    cur = await conn.execute(
        f"UPDATE suppliers SET is_active = %s WHERE id = %s RETURNING {COLUMNS}",
        (is_active, supplier_id),
    )
    return await cur.fetchone()
