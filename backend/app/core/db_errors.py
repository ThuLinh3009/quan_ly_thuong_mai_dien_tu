"""Chuyển lỗi RAISE EXCEPTION từ PL/pgSQL (plpgsql) thành AppError (400/409)
thay vì để lọt xuống thành lỗi hệ thống 500.

Các hàm nghiệp vụ phức tạp (place_order, add_to_cart, update_order_status,
simulate_payment_gateway, create_refund_request, process_refund_request,
submit_review...) tự RAISE EXCEPTION khi vi phạm quy tắc nghiệp vụ (hết hàng,
sai trạng thái, khuyến mãi hết hạn...). Message của các exception này đã viết
sẵn dễ hiểu nên dùng thẳng làm response detail, không cần dịch lại.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TypeVar

from psycopg.errors import RaiseException

from app.core.errors import ConflictError

T = TypeVar("T")


def _message(exc: RaiseException) -> str:
    return (exc.diag.message_primary or str(exc)).strip()


async def call_db(fn: Callable[[], Awaitable[T]]) -> T:
    """Gọi 1 coroutine thực hiện lời gọi DB; nếu DB RAISE EXCEPTION thì bọc
    lại thành ConflictError(409) với message gốc thay vì 500 chung chung."""
    try:
        return await fn()
    except RaiseException as exc:
        raise ConflictError(_message(exc)) from exc
