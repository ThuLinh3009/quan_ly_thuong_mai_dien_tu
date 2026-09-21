"""Repository cho users (Admin/Staff/Customer dùng chung bảng) — gọi function
DB trong database/functions.sql (mục 16). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def get_by_email(conn: AsyncConnection, email: str) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_user_by_email(%s)", (email,))
    return await cur.fetchone()


async def get_by_id(conn: AsyncConnection, user_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_user_by_id(%s)", (user_id,))
    return await cur.fetchone()


async def create_user(
    conn: AsyncConnection,
    *,
    email: str,
    password_hash: str,
    full_name: str,
    phone: str | None,
    role: str = "customer",
) -> dict[str, Any]:
    cur = await conn.execute(
        "SELECT * FROM create_user(%s, %s, %s, %s, %s)",
        (email, password_hash, full_name, phone, role),
    )
    row = await cur.fetchone()
    assert row is not None
    return row


async def list_staff(
    conn: AsyncConnection,
    *,
    keyword: str | None,
    is_active: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    cur = await conn.execute(
        "SELECT * FROM list_staff(%s, %s, %s, %s)", (keyword, is_active, limit, offset)
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update_staff(
    conn: AsyncConnection, user_id: int, *, full_name: str, phone: str | None
) -> dict[str, Any] | None:
    """Nhận đủ giá trị cuối cùng (đã merge với dữ liệu cũ ở service)."""
    cur = await conn.execute("SELECT * FROM update_staff(%s, %s, %s)", (user_id, full_name, phone))
    return await cur.fetchone()


async def set_staff_active(conn: AsyncConnection, user_id: int, is_active: bool) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM set_staff_active(%s, %s)", (user_id, is_active))
    return await cur.fetchone()


async def soft_delete_staff(conn: AsyncConnection, user_id: int) -> bool:
    cur = await conn.execute("SELECT soft_delete_staff(%s) AS deleted", (user_id,))
    row = await cur.fetchone()
    return bool(row["deleted"])
