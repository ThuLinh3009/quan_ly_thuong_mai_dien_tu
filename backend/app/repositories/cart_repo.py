"""Repository cho Cart/CartItem — gọi function DB trong database/functions.sql
(mục 3-4 get_cart_total/add_to_cart, mục 21 get_cart/update_cart_item_quantity/
remove_cart_item/clear_cart). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def add_item(conn: AsyncConnection, *, user_id: int, variant_id: int, quantity: int) -> int:
    cur = await conn.execute(
        "SELECT add_to_cart(%s, %s, %s) AS item_id", (user_id, variant_id, quantity)
    )
    row = await cur.fetchone()
    assert row is not None
    return row["item_id"]


async def get_cart(conn: AsyncConnection, user_id: int) -> dict[str, Any]:
    cur = await conn.execute("SELECT * FROM get_cart(%s)", (user_id,))
    row = await cur.fetchone()
    assert row is not None
    return row


async def update_item_quantity(conn: AsyncConnection, *, user_id: int, variant_id: int, quantity: int) -> bool:
    cur = await conn.execute(
        "SELECT update_cart_item_quantity(%s, %s, %s) AS updated", (user_id, variant_id, quantity)
    )
    row = await cur.fetchone()
    return bool(row["updated"])


async def remove_item(conn: AsyncConnection, *, user_id: int, variant_id: int) -> bool:
    cur = await conn.execute("SELECT remove_cart_item(%s, %s) AS removed", (user_id, variant_id))
    row = await cur.fetchone()
    return bool(row["removed"])


async def clear(conn: AsyncConnection, user_id: int) -> None:
    await conn.execute("SELECT clear_cart(%s)", (user_id,))
