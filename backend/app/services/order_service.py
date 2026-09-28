from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.core.db_errors import call_db
from app.core.errors import ForbiddenError, NotFoundError, ValidationAppError
from app.repositories import order_repo
from app.schemas.common import Page
from app.schemas.order import CheckoutRequest, OrderStatusUpdate

STAFF_ADMIN_ROLES = ("admin", "staff")

# Trạng thái khách hàng tự thao tác được (chỉ hủy đơn của chính mình khi còn
# 'pending' — DB update_order_status() cũng chặn lại nếu sai trạng thái, đây
# là lớp kiểm tra phân quyền sớm để trả lỗi rõ ràng hơn 1 lỗi DB chung chung).
_CUSTOMER_ALLOWED_TARGET_STATUS = {"cancelled"}


def _strip_total(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k != "total_count"}


async def checkout(conn: AsyncConnection, user_id: int, data: CheckoutRequest) -> dict[str, Any]:
    order_id = await call_db(
        lambda: order_repo.place_order(
            conn,
            user_id=user_id,
            address_id=data.address_id,
            payment_method=data.payment_method,
            promotion_code=data.promotion_code,
        )
    )
    order = await order_repo.get_order_detail(conn, order_id)
    assert order is not None

    try:
        from app.tasks.email_tasks import send_order_confirmation_email

        send_order_confirmation_email.delay(order_id)
    except Exception:  # noqa: BLE001 - gửi mail xác nhận không được làm hỏng luồng checkout đã thành công
        pass

    return order


async def preview_checkout(conn: AsyncConnection, user_id: int, promotion_code: str | None) -> dict[str, Any]:
    return await call_db(lambda: order_repo.preview_checkout(conn, user_id=user_id, promotion_code=promotion_code))


async def get_order(conn: AsyncConnection, order_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    order = await order_repo.get_order_detail(conn, order_id)
    if order is None:
        raise NotFoundError(f"Không tìm thấy đơn hàng id={order_id}")
    if current_user["role"] not in STAFF_ADMIN_ROLES and order["user_id"] != current_user["id"]:
        raise NotFoundError(f"Không tìm thấy đơn hàng id={order_id}")
    return order


async def list_my_orders(conn: AsyncConnection, user_id: int, *, status: str | None, limit: int, offset: int) -> Page:
    rows, total = await order_repo.list_for_user(conn, user_id=user_id, status=status, limit=limit, offset=offset)
    return Page(items=[_strip_total(r) for r in rows], total=total, limit=limit, offset=offset)


async def list_orders_admin(
    conn: AsyncConnection,
    *,
    status: str | None,
    user_id: int | None,
    date_from: Any,
    date_to: Any,
    limit: int,
    offset: int,
) -> Page:
    rows, total = await order_repo.list_admin(
        conn, status=status, user_id=user_id, date_from=date_from, date_to=date_to, limit=limit, offset=offset
    )
    return Page(items=[_strip_total(r) for r in rows], total=total, limit=limit, offset=offset)


async def update_status(
    conn: AsyncConnection, order_id: int, data: OrderStatusUpdate, current_user: dict[str, Any]
) -> dict[str, Any]:
    order = await get_order(conn, order_id, current_user)

    if current_user["role"] not in STAFF_ADMIN_ROLES:
        if order["user_id"] != current_user["id"]:
            raise NotFoundError(f"Không tìm thấy đơn hàng id={order_id}")
        if data.status not in _CUSTOMER_ALLOWED_TARGET_STATUS:
            raise ForbiddenError("Khách hàng chỉ được phép hủy đơn hàng của chính mình")

    await call_db(
        lambda: order_repo.update_status(
            conn, order_id=order_id, new_status=data.status, changed_by=current_user["id"], note=data.note
        )
    )
    updated = await order_repo.get_order_detail(conn, order_id)
    assert updated is not None
    return updated


async def simulate_payment(
    conn: AsyncConnection, order_id: int, success: bool, current_user: dict[str, Any]
) -> dict[str, Any]:
    order = await get_order(conn, order_id, current_user)
    if order["payment"] is None or order["payment"]["method"] != "simulated_gateway":
        raise ValidationAppError(f"Đơn hàng id={order_id} không dùng cổng thanh toán giả lập")

    return await call_db(
        lambda: order_repo.simulate_payment(conn, order_id=order_id, success=success, changed_by=current_user["id"])
    )
