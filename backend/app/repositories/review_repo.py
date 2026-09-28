"""Repository cho Review — gọi function DB trong database/functions.sql
(mục 11 submit_review, mục 26 list_reviews_for_product/get_product_rating_summary/
list_reviewable_order_items). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def submit(conn: AsyncConnection, *, order_item_id: int, user_id: int, rating: int, comment: str | None) -> int:
    cur = await conn.execute(
        "SELECT submit_review(%s, %s, %s, %s) AS review_id", (order_item_id, user_id, rating, comment)
    )
    row = await cur.fetchone()
    assert row is not None
    return row["review_id"]


async def list_for_product(
    conn: AsyncConnection, product_id: int, *, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    cur = await conn.execute(
        "SELECT * FROM list_reviews_for_product(%s, %s, %s)", (product_id, limit, offset)
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def rating_summary(conn: AsyncConnection, product_id: int) -> dict[str, Any]:
    cur = await conn.execute("SELECT * FROM get_product_rating_summary(%s)", (product_id,))
    row = await cur.fetchone()
    assert row is not None
    return row


async def list_reviewable(conn: AsyncConnection, user_id: int) -> list[dict[str, Any]]:
    cur = await conn.execute("SELECT * FROM list_reviewable_order_items(%s)", (user_id,))
    return await cur.fetchall()
