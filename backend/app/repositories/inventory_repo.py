from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def create_for_variant(
    conn: AsyncConnection, *, product_variant_id: int, quantity_on_hand: int, reorder_level: int
) -> None:
    await conn.execute(
        """
        INSERT INTO inventories (product_variant_id, quantity_on_hand, reorder_level)
        VALUES (%s, %s, %s)
        ON CONFLICT (product_variant_id) DO UPDATE
            SET quantity_on_hand = EXCLUDED.quantity_on_hand,
                reorder_level = EXCLUDED.reorder_level,
                updated_at = now()
        """,
        (product_variant_id, quantity_on_hand, reorder_level),
    )


async def get_by_variant(conn: AsyncConnection, product_variant_id: int) -> dict[str, Any] | None:
    cur = await conn.execute(
        "SELECT * FROM inventories WHERE product_variant_id = %s", (product_variant_id,)
    )
    return await cur.fetchone()


async def update_reorder_level(conn: AsyncConnection, product_variant_id: int, reorder_level: int) -> None:
    await conn.execute(
        "UPDATE inventories SET reorder_level = %s, updated_at = now() WHERE product_variant_id = %s",
        (reorder_level, product_variant_id),
    )
