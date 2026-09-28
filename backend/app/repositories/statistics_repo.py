"""Repository cho báo cáo thống kê — gọi function DB trong
database/functions.sql (mục 8-9 get_top_selling_books/get_revenue_report,
mục 27 get_dashboard_summary). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg import AsyncConnection


async def top_selling_books(
    conn: AsyncConnection, *, date_from: datetime, date_to: datetime, limit: int
) -> list[dict[str, Any]]:
    cur = await conn.execute(
        "SELECT * FROM get_top_selling_books(%s, %s, %s)", (date_from, date_to, limit)
    )
    return await cur.fetchall()


async def revenue_report(conn: AsyncConnection, *, date_from: datetime, date_to: datetime) -> list[dict[str, Any]]:
    cur = await conn.execute("SELECT * FROM get_revenue_report(%s, %s)", (date_from, date_to))
    return await cur.fetchall()


async def dashboard_summary(conn: AsyncConnection, *, date_from: datetime, date_to: datetime) -> dict[str, Any]:
    cur = await conn.execute("SELECT * FROM get_dashboard_summary(%s, %s)", (date_from, date_to))
    row = await cur.fetchone()
    assert row is not None
    return row
