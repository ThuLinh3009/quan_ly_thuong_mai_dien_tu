from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

DETAIL_QUERY = """
    SELECT
        p.id, p.sku, p.name, p.slug, p.author, p.publisher, p.isbn, p.description,
        p.cover_image_url, p.base_price, p.is_active, p.created_at, p.updated_at,
        p.category_id, c.name AS category_name,
        COALESCE(
            (SELECT json_agg(json_build_object(
                'id', pv.id,
                'product_id', pv.product_id,
                'variant_name', pv.variant_name,
                'sku', pv.sku,
                'price_adjustment', pv.price_adjustment,
                'is_active', pv.is_active,
                'quantity_on_hand', inv.quantity_on_hand,
                'quantity_reserved', inv.quantity_reserved,
                'reorder_level', inv.reorder_level
             ) ORDER BY pv.id)
             FROM product_variants pv
             LEFT JOIN inventories inv ON inv.product_variant_id = pv.id
             WHERE pv.product_id = p.id
            ), '[]'::json
        ) AS variants
    FROM products p
    JOIN categories c ON c.id = p.category_id
    WHERE p.id = %s AND p.deleted_at IS NULL
"""

SORTABLE_COLUMNS = {
    "name": "p.name",
    "base_price": "p.base_price",
    "created_at": "p.created_at",
}


async def sku_exists(conn: AsyncConnection, sku: str) -> bool:
    cur = await conn.execute("SELECT 1 FROM products WHERE sku = %s", (sku,))
    return await cur.fetchone() is not None


async def slug_exists(conn: AsyncConnection, slug: str) -> bool:
    cur = await conn.execute("SELECT 1 FROM products WHERE slug = %s", (slug,))
    return await cur.fetchone() is not None


async def create(conn: AsyncConnection, **fields: Any) -> int:
    cur = await conn.execute(
        """
        INSERT INTO products (category_id, sku, name, slug, author, publisher, isbn,
                               description, cover_image_url, base_price, is_active)
        VALUES (%(category_id)s, %(sku)s, %(name)s, %(slug)s, %(author)s, %(publisher)s, %(isbn)s,
                %(description)s, %(cover_image_url)s, %(base_price)s, %(is_active)s)
        RETURNING id
        """,
        fields,
    )
    row = await cur.fetchone()
    assert row is not None
    return row["id"]


async def get_by_id(conn: AsyncConnection, product_id: int) -> dict[str, Any] | None:
    cur = await conn.execute(DETAIL_QUERY, (product_id,))
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
    conditions = ["p.deleted_at IS NULL"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if keyword:
        conditions.append("p.search_vector @@ plainto_tsquery('simple', %(keyword)s)")
        params["keyword"] = keyword
    if category_id is not None:
        conditions.append("p.category_id = %(category_id)s")
        params["category_id"] = category_id
    if min_price is not None:
        conditions.append("p.base_price >= %(min_price)s")
        params["min_price"] = min_price
    if max_price is not None:
        conditions.append("p.base_price <= %(max_price)s")
        params["max_price"] = max_price
    if is_active is not None:
        conditions.append("p.is_active = %(is_active)s")
        params["is_active"] = is_active

    where_clause = " AND ".join(conditions)
    order_column = SORTABLE_COLUMNS.get(sort_by, "p.created_at")
    order_dir = "ASC" if sort_dir.lower() == "asc" else "DESC"

    cur = await conn.execute(
        f"""
        SELECT p.id, p.sku, p.name, p.author, p.category_id, c.name AS category_name,
               p.base_price, p.cover_image_url, p.is_active, p.created_at,
               COUNT(*) OVER() AS total_count
        FROM products p
        JOIN categories c ON c.id = p.category_id
        WHERE {where_clause}
        ORDER BY {order_column} {order_dir}
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total


async def update(conn: AsyncConnection, product_id: int, fields: dict[str, Any]) -> bool:
    if not fields:
        return True
    set_clause = ", ".join(f"{key} = %({key})s" for key in fields)
    params = {**fields, "id": product_id}
    cur = await conn.execute(
        f"UPDATE products SET {set_clause} WHERE id = %(id)s AND deleted_at IS NULL",
        params,
    )
    return cur.rowcount > 0


async def soft_delete(conn: AsyncConnection, product_id: int) -> bool:
    cur = await conn.execute(
        "UPDATE products SET deleted_at = now(), is_active = FALSE WHERE id = %s AND deleted_at IS NULL",
        (product_id,),
    )
    return cur.rowcount > 0
