"""Repository cho Promotion/FlashSaleItem — gọi function DB trong
database/functions.sql (mục 22). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def code_exists(conn: AsyncConnection, code: str) -> bool:
    cur = await conn.execute("SELECT promotion_code_exists(%s) AS exists", (code,))
    row = await cur.fetchone()
    return bool(row["exists"])


async def create(conn: AsyncConnection, **kwargs: Any) -> dict[str, Any]:
    cur = await conn.execute(
        "SELECT * FROM create_promotion(%(code)s, %(type)s, %(value)s, %(min_order_amount)s, "
        "%(max_discount_amount)s, %(starts_at)s, %(ends_at)s, %(usage_limit)s, %(per_user_limit)s, %(is_active)s)",
        kwargs,
    )
    row = await cur.fetchone()
    assert row is not None
    return row


async def get_by_id(conn: AsyncConnection, promotion_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_promotion_by_id(%s)", (promotion_id,))
    return await cur.fetchone()


async def list_promotions(
    conn: AsyncConnection, *, type: str | None, is_active: bool | None, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    cur = await conn.execute(
        "SELECT * FROM list_promotions(%s, %s, %s, %s)", (type, is_active, limit, offset)
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update(conn: AsyncConnection, promotion_id: int, **kwargs: Any) -> dict[str, Any] | None:
    cur = await conn.execute(
        "SELECT * FROM update_promotion(%(id)s, %(value)s, %(min_order_amount)s, %(max_discount_amount)s, "
        "%(starts_at)s, %(ends_at)s, %(usage_limit)s, %(per_user_limit)s, %(is_active)s)",
        {"id": promotion_id, **kwargs},
    )
    return await cur.fetchone()


async def set_active(conn: AsyncConnection, promotion_id: int, is_active: bool) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM set_promotion_active(%s, %s)", (promotion_id, is_active))
    return await cur.fetchone()


async def add_flash_sale_item(
    conn: AsyncConnection, *, promotion_id: int, variant_id: int, flash_price: Any, quantity_limit: int
) -> dict[str, Any]:
    cur = await conn.execute(
        "SELECT * FROM add_flash_sale_item(%s, %s, %s, %s)",
        (promotion_id, variant_id, flash_price, quantity_limit),
    )
    row = await cur.fetchone()
    assert row is not None
    return row


async def list_flash_sale_items(conn: AsyncConnection, promotion_id: int) -> list[dict[str, Any]]:
    cur = await conn.execute("SELECT * FROM list_flash_sale_items(%s)", (promotion_id,))
    return await cur.fetchall()


async def get_active_flash_sales(conn: AsyncConnection, limit: int) -> list[dict[str, Any]]:
    cur = await conn.execute("SELECT * FROM get_active_flash_sales(%s)", (limit,))
    return await cur.fetchall()
