from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.schemas.import_lot import ImportItemCreate

LOT_DETAIL_QUERY = """
    SELECT
        l.id, l.lot_code, l.supplier_id, s.name AS supplier_name, l.imported_at, l.created_by,
        COALESCE(
            (SELECT json_agg(json_build_object(
                'id', iri.id,
                'product_variant_id', iri.product_variant_id,
                'variant_name', pv.variant_name,
                'sku', pv.sku,
                'quantity', iri.quantity,
                'unit_cost', iri.unit_cost
             ) ORDER BY iri.id)
             FROM import_receipt_items iri
             JOIN product_variants pv ON pv.id = iri.product_variant_id
             WHERE iri.import_lot_id = l.id
            ), '[]'::json
        ) AS items
    FROM import_lots l
    JOIN suppliers s ON s.id = l.supplier_id
    WHERE l.id = %s
"""


async def create_lot(conn: AsyncConnection, *, supplier_id: int, created_by: int) -> tuple[int, str]:
    cur = await conn.execute(
        """
        INSERT INTO import_lots (supplier_id, lot_code, created_by)
        VALUES (%(supplier_id)s, 'LOT-' || to_char(now(), 'YYYYMMDDHH24MISS') || '-' || %(supplier_id)s, %(created_by)s)
        RETURNING id, lot_code
        """,
        {"supplier_id": supplier_id, "created_by": created_by},
    )
    row = await cur.fetchone()
    assert row is not None
    return row["id"], row["lot_code"]


async def add_items(conn: AsyncConnection, lot_id: int, items: list[ImportItemCreate]) -> None:
    async with conn.cursor() as cur:
        await cur.executemany(
            """
            INSERT INTO import_receipt_items (import_lot_id, product_variant_id, quantity, unit_cost)
            VALUES (%s, %s, %s, %s)
            """,
            [(lot_id, item.product_variant_id, item.quantity, item.unit_cost) for item in items],
        )


async def restock_from_import(conn: AsyncConnection, lot_id: int) -> None:
    """Gọi stored procedure restock_from_import() để cộng dồn tồn kho theo lô."""
    await conn.execute("SELECT restock_from_import(%s)", (lot_id,))


async def get_lot_by_id(conn: AsyncConnection, lot_id: int) -> dict[str, Any] | None:
    cur = await conn.execute(LOT_DETAIL_QUERY, (lot_id,))
    return await cur.fetchone()


async def list_lots(
    conn: AsyncConnection,
    *,
    supplier_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    conditions = ["1 = 1"]
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if supplier_id is not None:
        conditions.append("l.supplier_id = %(supplier_id)s")
        params["supplier_id"] = supplier_id

    where_clause = " AND ".join(conditions)
    cur = await conn.execute(
        f"""
        SELECT l.id, l.lot_code, l.supplier_id, s.name AS supplier_name, l.imported_at, l.created_by,
               COUNT(*) OVER() AS total_count
        FROM import_lots l
        JOIN suppliers s ON s.id = l.supplier_id
        WHERE {where_clause}
        ORDER BY l.imported_at DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        params,
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total
