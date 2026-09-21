from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

COLUMNS = "id, product_id, variant_name, sku, price_adjustment, is_active"


async def sku_exists(conn: AsyncConnection, sku: str) -> bool:
    cur = await conn.execute("SELECT 1 FROM product_variants WHERE sku = %s", (sku,))
    return await cur.fetchone() is not None


async def create(
    conn: AsyncConnection,
    *,
    product_id: int,
    variant_name: str,
    sku: str,
    price_adjustment: Any,
    is_active: bool,
) -> dict[str, Any]:
    cur = await conn.execute(
        f"""
        INSERT INTO product_variants (product_id, variant_name, sku, price_adjustment, is_active)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING {COLUMNS}
        """,
        (product_id, variant_name, sku, price_adjustment, is_active),
    )
    row = await cur.fetchone()
    assert row is not None
    return row


async def get_by_id(conn: AsyncConnection, variant_id: int) -> dict[str, Any] | None:
    cur = await conn.execute(f"SELECT {COLUMNS} FROM product_variants WHERE id = %s", (variant_id,))
    return await cur.fetchone()


async def update(conn: AsyncConnection, variant_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    if not fields:
        return await get_by_id(conn, variant_id)
    set_clause = ", ".join(f"{key} = %({key})s" for key in fields)
    params = {**fields, "id": variant_id}
    cur = await conn.execute(
        f"UPDATE product_variants SET {set_clause} WHERE id = %(id)s RETURNING {COLUMNS}",
        params,
    )
    return await cur.fetchone()


async def set_active(conn: AsyncConnection, variant_id: int, is_active: bool) -> dict[str, Any] | None:
    cur = await conn.execute(
        f"UPDATE product_variants SET is_active = %s WHERE id = %s RETURNING {COLUMNS}",
        (is_active, variant_id),
    )
    return await cur.fetchone()
