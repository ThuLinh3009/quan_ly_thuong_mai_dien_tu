"""Repository cho Order/Payment — gọi function DB trong database/functions.sql
(mục 5-7 place_order/update_order_status/get_order_detail, mục 24
list_orders_for_user/list_orders_admin/simulate_payment_gateway). Không viết
SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def place_order(
    conn: AsyncConnection, *, user_id: int, address_id: int, payment_method: str, promotion_code: str | None
) -> int:
    cur = await conn.execute(
        "SELECT place_order(%s, %s, %s, %s) AS order_id",
        (user_id, address_id, payment_method, promotion_code),
    )
    row = await cur.fetchone()
    assert row is not None
    return row["order_id"]


async def preview_checkout(conn: AsyncConnection, *, user_id: int, promotion_code: str | None) -> dict[str, Any]:
    cur = await conn.execute("SELECT * FROM preview_checkout(%s, %s)", (user_id, promotion_code))
    row = await cur.fetchone()
    assert row is not None
    return row


async def get_order_detail(conn: AsyncConnection, order_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_order_detail(%s)", (order_id,))
    return await cur.fetchone()


async def list_for_user(
    conn: AsyncConnection, *, user_id: int, status: str | None, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    cur = await conn.execute(
        "SELECT * FROM list_orders_for_user(%s, %s, %s, %s)", (user_id, status, limit, offset)
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def list_admin(
    conn: AsyncConnection,
    *,
    status: str | None,
    user_id: int | None,
    date_from: Any,
    date_to: Any,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    cur = await conn.execute(
        "SELECT * FROM list_orders_admin(%s, %s, %s, %s, %s, %s)",
        (status, user_id, date_from, date_to, limit, offset),
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update_status(
    conn: AsyncConnection, *, order_id: int, new_status: str, changed_by: int | None, note: str | None
) -> None:
    await conn.execute(
        "SELECT update_order_status(%s, %s, %s, %s)", (order_id, new_status, changed_by, note)
    )


async def simulate_payment(
    conn: AsyncConnection, *, order_id: int, success: bool, changed_by: int | None
) -> dict[str, Any]:
    cur = await conn.execute(
        "SELECT * FROM simulate_payment_gateway(%s, %s, %s)", (order_id, success, changed_by)
    )
    row = await cur.fetchone()
    assert row is not None
    return row
