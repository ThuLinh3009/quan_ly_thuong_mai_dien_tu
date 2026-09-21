from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.core.audit import record_audit
from app.core.cache import PRODUCT_PREFIX, invalidate_prefix
from app.core.errors import NotFoundError
from app.repositories import import_repo, supplier_repo, variant_repo
from app.schemas.common import Page
from app.schemas.import_lot import ImportLotCreate


async def create_import_lot(
    conn: AsyncConnection, data: ImportLotCreate, current_user: dict[str, Any]
) -> dict[str, Any]:
    if await supplier_repo.get_by_id(conn, data.supplier_id) is None:
        raise NotFoundError(f"Không tìm thấy supplier id={data.supplier_id}")

    for item in data.items:
        if await variant_repo.get_by_id(conn, item.product_variant_id) is None:
            raise NotFoundError(f"Không tìm thấy biến thể id={item.product_variant_id}")

    lot_id, lot_code = await import_repo.create_lot(
        conn, supplier_id=data.supplier_id, created_by=current_user["id"]
    )
    await import_repo.add_items(conn, lot_id, data.items)
    await import_repo.restock_from_import(conn, lot_id)

    lot = await import_repo.get_lot_by_id(conn, lot_id)
    assert lot is not None
    await record_audit(
        conn, user_id=current_user["id"], action="create", entity_type="import_lot",
        entity_id=lot_id, new_value={"lot_code": lot_code, "items": len(data.items)},
    )
    await invalidate_prefix(PRODUCT_PREFIX)
    return lot


async def get_import_lot(conn: AsyncConnection, lot_id: int) -> dict[str, Any]:
    lot = await import_repo.get_lot_by_id(conn, lot_id)
    if lot is None:
        raise NotFoundError(f"Không tìm thấy phiếu nhập id={lot_id}")
    return lot


async def list_import_lots(
    conn: AsyncConnection, *, supplier_id: int | None, limit: int, offset: int
) -> Page:
    rows, total = await import_repo.list_lots(conn, supplier_id=supplier_id, limit=limit, offset=offset)
    items = [{k: v for k, v in row.items() if k != "total_count"} for row in rows]
    return Page(items=items, total=total, limit=limit, offset=offset)
