"""Repository cho ImportLot — gọi function DB trong database/functions.sql
(mục 10 restock_from_import, mục 18 create_import_lot/add_import_receipt_items/
get_import_lot_by_id/list_import_lots). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.schemas.import_lot import ImportItemCreate


async def create_lot(conn: AsyncConnection, *, supplier_id: int, created_by: int) -> tuple[int, str]:
    cur = await conn.execute("SELECT * FROM create_import_lot(%s, %s)", (supplier_id, created_by))
    row = await cur.fetchone()
    assert row is not None
    return row["id"], row["lot_code"]


async def add_items(conn: AsyncConnection, lot_id: int, items: list[ImportItemCreate]) -> None:
    # Truyen 3 mang song song, insert het trong 1 lan goi function (xem
    # add_import_receipt_items() dung unnest() thay vi executemany tung dong).
    variant_ids = [item.product_variant_id for item in items]
    quantities = [item.quantity for item in items]
    unit_costs = [item.unit_cost for item in items]
    await conn.execute(
        "SELECT add_import_receipt_items(%s, %s, %s, %s)",
        (lot_id, variant_ids, quantities, unit_costs),
    )


async def restock_from_import(conn: AsyncConnection, lot_id: int) -> None:
    """Gọi stored procedure restock_from_import() để cộng dồn tồn kho theo lô."""
    await conn.execute("SELECT restock_from_import(%s)", (lot_id,))


async def get_lot_by_id(conn: AsyncConnection, lot_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_import_lot_by_id(%s)", (lot_id,))
    return await cur.fetchone()


async def list_lots(
    conn: AsyncConnection,
    *,
    supplier_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    cur = await conn.execute(
        "SELECT * FROM list_import_lots(%s, %s, %s)", (supplier_id, limit, offset)
    )
    rows = await cur.fetchall()
    total = rows[0]["total_count"] if rows else 0
    return rows, total
