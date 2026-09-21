"""Repository cho Inventory — gọi function DB trong database/functions.sql
(mục 15: create_inventory_for_variant, get_inventory_by_variant,
update_inventory_reorder_level). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def create_for_variant(
    conn: AsyncConnection, *, product_variant_id: int, quantity_on_hand: int, reorder_level: int
) -> None:
    await conn.execute(
        "SELECT create_inventory_for_variant(%s, %s, %s)",
        (product_variant_id, quantity_on_hand, reorder_level),
    )


async def get_by_variant(conn: AsyncConnection, product_variant_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_inventory_by_variant(%s)", (product_variant_id,))
    return await cur.fetchone()


async def update_reorder_level(conn: AsyncConnection, product_variant_id: int, reorder_level: int) -> None:
    await conn.execute(
        "SELECT update_inventory_reorder_level(%s, %s)", (product_variant_id, reorder_level)
    )
