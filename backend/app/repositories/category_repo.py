from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

COLUMNS = "id, parent_id, name, slug, is_active"


async def get_by_slug(conn: AsyncConnection, slug: str) -> dict[str, Any] | None:
    cur = await conn.execute(
        f"SELECT {COLUMNS} FROM categories WHERE slug = %s AND deleted_at IS NULL", (slug,)
    )
    return await cur.fetchone()


async def get_by_id(conn: AsyncConnection, category_id: int) -> dict[str, Any] | None:
    cur = await conn.execute(
        f"SELECT {COLUMNS} FROM categories WHERE id = %s AND deleted_at IS NULL", (category_id,)
    )
    return await cur.fetchone()


async def create(conn: AsyncConnection, *, name: str, slug: str, parent_id: int | None, is_active: bool) -> dict[str, Any]:
    cur = await conn.execute(
        f"""
        INSERT INTO categories (parent_id, name, slug, is_active)
        VALUES (%s, %s, %s, %s)
        RETURNING {COLUMNS}
        """,
        (parent_id, name, slug, is_active),
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
    conditions = ["deleted_at IS NULL"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if keyword:
        conditions.append("name ILIKE %(keyword)s")
        params["keyword"] = f"%{keyword}%"
    if parent_id is not None:
        conditions.append("parent_id = %(parent_id)s")
        params["parent_id"] = parent_id
    if is_active is not None:
        conditions.append("is_active = %(is_active)s")
        params["is_active"] = is_active

    where_clause = " AND ".join(conditions)
    cur = await conn.execute(
        f"""
        SELECT {COLUMNS}, COUNT(*) OVER() AS total_count
        FROM categories
        WHERE {where_clause}
        ORDER BY name
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update(conn: AsyncConnection, category_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    if not fields:
        return await get_by_id(conn, category_id)

    set_clause = ", ".join(f"{key} = %({key})s" for key in fields)
    params = {**fields, "id": category_id}
    cur = await conn.execute(
        f"""
        UPDATE categories SET {set_clause}
        WHERE id = %(id)s AND deleted_at IS NULL
        RETURNING {COLUMNS}
        """,
        params,
    )
    return await cur.fetchone()


async def soft_delete(conn: AsyncConnection, category_id: int) -> bool:
    cur = await conn.execute(
        "UPDATE categories SET deleted_at = now(), is_active = FALSE WHERE id = %s AND deleted_at IS NULL",
        (category_id,),
    )
    return cur.rowcount > 0
