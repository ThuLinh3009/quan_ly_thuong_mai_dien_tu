"""Repository cho Product — gọi function DB trong database/functions.sql
(mục 1 get_book_by_id, mục 2 search_books, mục 15 product CRUD).
Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def sku_exists(conn: AsyncConnection, sku: str) -> bool:
    cur = await conn.execute("SELECT product_sku_exists(%s) AS exists", (sku,))
    row = await cur.fetchone()
    return bool(row["exists"])


async def slug_exists(conn: AsyncConnection, slug: str) -> bool:
    cur = await conn.execute("SELECT product_slug_exists(%s) AS exists", (slug,))
    row = await cur.fetchone()
    return bool(row["exists"])


async def create(conn: AsyncConnection, **fields: Any) -> int:
    cur = await conn.execute(
        "SELECT create_product(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS id",
        (
            fields["category_id"],
            fields["sku"],
            fields["name"],
            fields["slug"],
            fields["author"],
            fields["publisher"],
            fields["isbn"],
            fields["description"],
            fields["cover_image_url"],
            fields["base_price"],
            fields["is_active"],
        ),
    )
    row = await cur.fetchone()
    assert row is not None
    return row["id"]


async def get_by_id(conn: AsyncConnection, product_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_book_by_id(%s)", (product_id,))
    return await cur.fetchone()


async def list_products(
    conn: AsyncConnection,
    *,
    keyword: str | None,
    category_id: int | None,
    min_price: float | None,
    max_price: float | None,
    is_active: bool | None,
    sort_by: str,
    sort_dir: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    # Ép kiểu tường minh: psycopg gửi float Python là double precision, mà
    # PostgreSQL không tự chuyển double -> NUMERIC khi chọn hàm, nên không ép
    # thì lọc theo giá sẽ lỗi "function search_books(...) does not exist".
    cur = await conn.execute(
        "SELECT * FROM search_books(%s::text, %s::bigint, %s::numeric, %s::numeric, %s::boolean,"
        " %s::text, %s::text, %s::int, %s::int)",
        (keyword, category_id, min_price, max_price, is_active, sort_by, sort_dir, limit, offset),
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update(conn: AsyncConnection, product_id: int, **fields: Any) -> bool:
    """Nhận đủ giá trị cuối cùng (đã merge với dữ liệu cũ ở service)."""
    cur = await conn.execute(
        "SELECT update_product(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) AS ok",
        (
            product_id,
            fields["category_id"],
            fields["name"],
            fields["slug"],
            fields["author"],
            fields["publisher"],
            fields["isbn"],
            fields["description"],
            fields["cover_image_url"],
            fields["base_price"],
            fields["is_active"],
        ),
    )
    row = await cur.fetchone()
    return bool(row["ok"])


async def recommendations(conn: AsyncConnection, product_id: int, limit: int) -> list[dict[str, Any]]:
    cur = await conn.execute("SELECT * FROM get_book_recommendations(%s, %s)", (product_id, limit))
    return await cur.fetchall()


async def soft_delete(conn: AsyncConnection, product_id: int) -> bool:
    cur = await conn.execute("SELECT soft_delete_product(%s) AS deleted", (product_id,))
    row = await cur.fetchone()
    return bool(row["deleted"])
