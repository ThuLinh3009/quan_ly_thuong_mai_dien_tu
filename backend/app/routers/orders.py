from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import get_current_user, require_roles
from app.schemas.common import Page
from app.schemas.order import (
    CheckoutPreviewOut,
    CheckoutRequest,
    OrderAdminListItemOut,
    OrderDetailOut,
    OrderListItemOut,
    OrderStatusUpdate,
    PaymentSimulateOut,
    PaymentSimulateRequest,
)
from app.services import order_service, pdf_service

router = APIRouter(prefix="/orders", tags=["orders"])

_customer = require_roles("customer")
_staff_admin = require_roles("admin", "staff")


@router.get("/checkout/preview", response_model=CheckoutPreviewOut)
async def preview_checkout(
    promotion_code: str | None = Query(default=None),
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    """Xem trước subtotal/discount/shipping/total (áp mã giảm giá nếu có)
    trước khi đặt hàng thật — không tạo đơn, không trừ tồn kho."""
    return await order_service.preview_checkout(conn, current_user["id"], promotion_code)


@router.post("/checkout", response_model=OrderDetailOut, status_code=201)
async def checkout(
    data: CheckoutRequest,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    return await order_service.checkout(conn, current_user["id"], data)


@router.get("", response_model=Page[OrderListItemOut])
async def list_my_orders(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    return await order_service.list_my_orders(conn, current_user["id"], status=status, limit=limit, offset=offset)


@router.get("/admin", response_model=Page[OrderAdminListItemOut])
async def list_orders_admin(
    status: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    return await order_service.list_orders_admin(
        conn, status=status, user_id=user_id, date_from=date_from, date_to=date_to, limit=limit, offset=offset
    )


@router.get("/{order_id}", response_model=OrderDetailOut)
async def get_order(
    order_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    return await order_service.get_order(conn, order_id, current_user)


@router.patch("/{order_id}/status", response_model=OrderDetailOut)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    return await order_service.update_status(conn, order_id, data, current_user)


@router.post("/{order_id}/payment/simulate", response_model=PaymentSimulateOut)
async def simulate_payment(
    order_id: int,
    data: PaymentSimulateRequest,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Giả lập callback từ cổng thanh toán (payment_method=simulated_gateway):
    client gọi lại endpoint này với success=true/false sau khi 'thanh toán'
    xong ở cổng giả lập."""
    return await order_service.simulate_payment(conn, order_id, data.success, current_user)


@router.get("/{order_id}/invoice", response_class=Response)
async def download_invoice(
    order_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    order = await order_service.get_order(conn, order_id, current_user)
    pdf_bytes = pdf_service.render_invoice(order)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{order["order_code"]}.pdf"'},
    )
