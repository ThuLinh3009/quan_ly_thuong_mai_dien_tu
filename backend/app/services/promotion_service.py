from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.core.audit import record_audit
from app.core.db_errors import call_db
from app.core.errors import ConflictError, NotFoundError
from app.repositories import promotion_repo, variant_repo
from app.schemas.common import Page
from app.schemas.promotion import FlashSaleItemCreate, PromotionCreate, PromotionUpdate


def _strip_total(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k != "total_count"}


async def create_promotion(
    conn: AsyncConnection, data: PromotionCreate, current_user: dict[str, Any]
) -> dict[str, Any]:
    if data.code is not None and await promotion_repo.code_exists(conn, data.code):
        raise ConflictError(f"Mã khuyến mãi '{data.code}' đã tồn tại")

    promotion = await promotion_repo.create(conn, **data.model_dump())
    await record_audit(
        conn, user_id=current_user["id"], action="create", entity_type="promotion",
        entity_id=promotion["id"], new_value=promotion,
    )
    return promotion


async def get_promotion(conn: AsyncConnection, promotion_id: int) -> dict[str, Any]:
    promotion = await promotion_repo.get_by_id(conn, promotion_id)
    if promotion is None:
        raise NotFoundError(f"Không tìm thấy khuyến mãi id={promotion_id}")
    return promotion


async def list_promotions(
    conn: AsyncConnection, *, type: str | None, is_active: bool | None, limit: int, offset: int
) -> Page:
    rows, total = await promotion_repo.list_promotions(conn, type=type, is_active=is_active, limit=limit, offset=offset)
    return Page(items=[_strip_total(r) for r in rows], total=total, limit=limit, offset=offset)


async def update_promotion(
    conn: AsyncConnection, promotion_id: int, data: PromotionUpdate, current_user: dict[str, Any]
) -> dict[str, Any]:
    old = await get_promotion(conn, promotion_id)
    payload = data.model_dump(exclude_unset=True)

    merged = {
        "value": payload.get("value", old["value"]),
        "min_order_amount": payload.get("min_order_amount", old["min_order_amount"]),
        "max_discount_amount": payload.get("max_discount_amount", old["max_discount_amount"]),
        "starts_at": payload.get("starts_at", old["starts_at"]),
        "ends_at": payload.get("ends_at", old["ends_at"]),
        "usage_limit": payload.get("usage_limit", old["usage_limit"]),
        "per_user_limit": payload.get("per_user_limit", old["per_user_limit"]),
        "is_active": payload.get("is_active", old["is_active"]),
    }
    if merged["ends_at"] <= merged["starts_at"]:
        raise ConflictError("ends_at phải sau starts_at")

    updated = await promotion_repo.update(conn, promotion_id, **merged)
    assert updated is not None
    await record_audit(
        conn, user_id=current_user["id"], action="update", entity_type="promotion",
        entity_id=promotion_id, old_value=old, new_value=updated,
    )
    return updated


async def set_promotion_active(
    conn: AsyncConnection, promotion_id: int, is_active: bool, current_user: dict[str, Any]
) -> dict[str, Any]:
    old = await get_promotion(conn, promotion_id)
    updated = await promotion_repo.set_active(conn, promotion_id, is_active)
    assert updated is not None
    await record_audit(
        conn, user_id=current_user["id"], action="update", entity_type="promotion",
        entity_id=promotion_id, old_value=old, new_value=updated,
    )
    return updated


async def add_flash_sale_item(
    conn: AsyncConnection, promotion_id: int, data: FlashSaleItemCreate, current_user: dict[str, Any]
) -> dict[str, Any]:
    promotion = await get_promotion(conn, promotion_id)
    if promotion["type"] != "flash_sale":
        raise ConflictError(f"Khuyến mãi id={promotion_id} không phải loại flash_sale")
    if await variant_repo.get_by_id(conn, data.product_variant_id) is None:
        raise NotFoundError(f"Không tìm thấy biến thể id={data.product_variant_id}")

    item = await promotion_repo.add_flash_sale_item(
        conn,
        promotion_id=promotion_id,
        variant_id=data.product_variant_id,
        flash_price=data.flash_price,
        quantity_limit=data.quantity_limit,
    )
    await record_audit(
        conn, user_id=current_user["id"], action="create", entity_type="flash_sale_item",
        entity_id=item["id"], new_value=item,
    )
    return item


async def list_flash_sale_items(conn: AsyncConnection, promotion_id: int) -> list[dict[str, Any]]:
    await get_promotion(conn, promotion_id)
    return await promotion_repo.list_flash_sale_items(conn, promotion_id)


async def get_active_flash_sales(conn: AsyncConnection, limit: int) -> list[dict[str, Any]]:
    return await promotion_repo.get_active_flash_sales(conn, limit)


async def preview_checkout_discount(conn: AsyncConnection, user_id: int, promotion_code: str | None) -> dict[str, Any]:
    """Dùng lại preview_checkout() (DB) để khách xem trước tổng tiền/giảm giá
    trước khi đặt hàng thật — không tạo đơn, không trừ tồn kho."""
    async def _call() -> dict[str, Any]:
        cur = await conn.execute("SELECT * FROM preview_checkout(%s, %s)", (user_id, promotion_code))
        row = await cur.fetchone()
        assert row is not None
        return row

    return await call_db(_call)
