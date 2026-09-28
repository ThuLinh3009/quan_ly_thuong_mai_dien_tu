"""Repository cho RefundRequest — gọi function DB trong database/functions.sql
(mục 25). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def create(conn: AsyncConnection, *, order_id: int, user_id: int, reason: str) -> dict[str, Any]:
    cur = await conn.execute(
        "SELECT * FROM create_refund_request(%s, %s, %s)", (order_id, user_id, reason)
    )
    row = await cur.fetchone()
    assert row is not None
    return row


async def get_by_id(conn: AsyncConnection, request_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_refund_request_by_id(%s)", (request_id,))
    return await cur.fetchone()


async def list_requests(
    conn: AsyncConnection, *, status: str | None, user_id: int | None, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    cur = await conn.execute(
        "SELECT * FROM list_refund_requests(%s, %s, %s, %s)", (status, user_id, limit, offset)
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def process(conn: AsyncConnection, *, request_id: int, approve: bool, processed_by: int) -> dict[str, Any]:
    cur = await conn.execute(
        "SELECT * FROM process_refund_request(%s, %s, %s)", (request_id, approve, processed_by)
    )
    row = await cur.fetchone()
    assert row is not None
    return row
