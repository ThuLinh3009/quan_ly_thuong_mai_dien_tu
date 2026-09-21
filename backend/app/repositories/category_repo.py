"""Repository cho Category.

Không viết SQL trực tiếp ở đây — mọi truy vấn đều gọi function đã định nghĩa
trong database/functions.sql (mục 13: category_slug_exists, create_category,
get_category_by_id, list_categories, update_category, soft_delete_category).
Sửa logic truy vấn thì sửa trong functions.sql, file này chỉ map tham số.
"""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def slug_exists(conn: AsyncConnection, slug: str, exclude_id: int | None = None) -> bool:
    cur = await conn.execute("SELECT category_slug_exists(%s, %s) AS exists", (slug, exclude_id))
    row = await cur.fetchone()
    return bool(row["exists"])


async def get_by_id(conn: AsyncConnection, category_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_category_by_id(%s)", (category_id,))
    return await cur.fetchone()


async def create(
    conn: AsyncConnection, *, name: str, slug: str, parent_id: int | None, is_active: bool
) -> dict[str, Any]:
    cur = await conn.execute(
        "SELECT * FROM create_category(%s, %s, %s, %s)", (name, slug, parent_id, is_active)
    )
    row = await cur.fetchone()
    assert row is not None
    return row


async def list_categories(
    conn: AsyncConnection,
    *,
    keyword: str | None,
    parent_id: int | None,
    is_active: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    cur = await conn.execute(
        "SELECT * FROM list_categories(%s, %s, %s, %s, %s)",
        (keyword, parent_id, is_active, limit, offset),
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update(
    conn: AsyncConnection,
    category_id: int,
    *,
    name: str,
    slug: str,
    parent_id: int | None,
    is_active: bool,
) -> dict[str, Any] | None:
    """Nhận đủ giá trị cuối cùng (đã merge với dữ liệu cũ ở service) — function
    update_category() ghi đè toàn bộ, không tự suy luận "field nào cần đổi"."""
    cur = await conn.execute(
        "SELECT * FROM update_category(%s, %s, %s, %s, %s)",
        (category_id, name, slug, parent_id, is_active),
    )
    return await cur.fetchone()


async def soft_delete(conn: AsyncConnection, category_id: int) -> bool:
    cur = await conn.execute("SELECT soft_delete_category(%s) AS deleted", (category_id,))
    row = await cur.fetchone()
    return bool(row["deleted"])
