"""Truy vấn bảng users. Mọi hàm nhận sẵn 1 connection (transaction do FastAPI dependency quản lý)."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

USER_COLUMNS = "id, email, password_hash, full_name, phone, role, is_active, created_at, updated_at"


async def get_by_email(conn: AsyncConnection, email: str) -> dict[str, Any] | None:
    cur = await conn.execute(
        f"SELECT {USER_COLUMNS} FROM users WHERE email = %s AND deleted_at IS NULL",
        (email,),
    )
    return await cur.fetchone()


async def get_by_id(conn: AsyncConnection, user_id: int) -> dict[str, Any] | None:
    cur = await conn.execute(
        f"SELECT {USER_COLUMNS} FROM users WHERE id = %s AND deleted_at IS NULL",
        (user_id,),
    )
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
        f"""
        INSERT INTO users (email, password_hash, full_name, phone, role)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING {USER_COLUMNS}
        """,
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
    conditions = ["deleted_at IS NULL", "role = 'staff'"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if keyword:
        conditions.append("(full_name ILIKE %(keyword)s OR email ILIKE %(keyword)s)")
        params["keyword"] = f"%{keyword}%"
    if is_active is not None:
        conditions.append("is_active = %(is_active)s")
        params["is_active"] = is_active

    where_clause = " AND ".join(conditions)
    cur = await conn.execute(
        f"""
        SELECT {USER_COLUMNS}, COUNT(*) OVER() AS total_count
        FROM users
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update_staff(
    conn: AsyncConnection,
    user_id: int,
    *,
    full_name: str | None,
    phone: str | None,
) -> dict[str, Any] | None:
    cur = await conn.execute(
        f"""
        UPDATE users
        SET full_name = COALESCE(%(full_name)s, full_name),
            phone = COALESCE(%(phone)s, phone)
        WHERE id = %(id)s AND deleted_at IS NULL AND role = 'staff'
        RETURNING {USER_COLUMNS}
        """,
        {"id": user_id, "full_name": full_name, "phone": phone},
    )
    return await cur.fetchone()


async def set_staff_active(conn: AsyncConnection, user_id: int, is_active: bool) -> dict[str, Any] | None:
    cur = await conn.execute(
        f"""
        UPDATE users
        SET is_active = %s
        WHERE id = %s AND deleted_at IS NULL AND role = 'staff'
        RETURNING {USER_COLUMNS}
        """,
        (is_active, user_id),
    )
    return await cur.fetchone()


async def soft_delete_staff(conn: AsyncConnection, user_id: int) -> bool:
    cur = await conn.execute(
        "UPDATE users SET deleted_at = now(), is_active = FALSE "
        "WHERE id = %s AND deleted_at IS NULL AND role = 'staff'",
        (user_id,),
    )
    return cur.rowcount > 0
