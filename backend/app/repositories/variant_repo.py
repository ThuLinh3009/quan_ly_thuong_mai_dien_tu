"""Repository cho ProductVariant — gọi function DB trong database/functions.sql
(mục 15: variant_sku_exists, create_variant, get_variant_by_id, update_variant,
set_variant_active). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def sku_exists(conn: AsyncConnection, sku: str) -> bool:
    cur = await conn.execute("SELECT variant_sku_exists(%s) AS exists", (sku,))
    row = await cur.fetchone()
    return bool(row["exists"])


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
        "SELECT * FROM create_variant(%s, %s, %s, %s, %s)",
        (product_id, variant_name, sku, price_adjustment, is_active),
    )
    row = await cur.fetchone()
    assert row is not None
    return row


async def get_by_id(conn: AsyncConnection, variant_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_variant_by_id(%s)", (variant_id,))
    return await cur.fetchone()


async def update(
    conn: AsyncConnection, variant_id: int, *, variant_name: str, price_adjustment: Any, is_active: bool
) -> dict[str, Any] | None:
    """Nhận đủ giá trị cuối cùng (đã merge với dữ liệu cũ ở service)."""
    cur = await conn.execute(
        "SELECT * FROM update_variant(%s, %s, %s, %s)",
        (variant_id, variant_name, price_adjustment, is_active),
    )
    return await cur.fetchone()


async def set_active(conn: AsyncConnection, variant_id: int, is_active: bool) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM set_variant_active(%s, %s)", (variant_id, is_active))
    return await cur.fetchone()
