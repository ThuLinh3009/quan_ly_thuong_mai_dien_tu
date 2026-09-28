from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.core.audit import record_audit
from app.core.db_errors import call_db
from app.core.errors import ForbiddenError, NotFoundError
from app.repositories import refund_repo
from app.schemas.common import Page

STAFF_ADMIN_ROLES = ("admin", "staff")


def _strip_total(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k != "total_count"}


async def create_request(conn: AsyncConnection, user_id: int, order_id: int, reason: str) -> dict[str, Any]:
    request = await call_db(lambda: refund_repo.create(conn, order_id=order_id, user_id=user_id, reason=reason))
    await record_audit(
        conn, user_id=user_id, action="create", entity_type="refund_request",
        entity_id=request["id"], new_value=request,
    )
    return request


async def get_request(conn: AsyncConnection, request_id: int, current_user: dict[str, Any]) -> dict[str, Any]:
    request = await refund_repo.get_by_id(conn, request_id)
    if request is None:
        raise NotFoundError(f"Không tìm thấy yêu cầu hoàn tiền id={request_id}")
    if current_user["role"] not in STAFF_ADMIN_ROLES and request["user_id"] != current_user["id"]:
        raise NotFoundError(f"Không tìm thấy yêu cầu hoàn tiền id={request_id}")
    return request


async def list_my_requests(conn: AsyncConnection, user_id: int, *, limit: int, offset: int) -> Page:
    rows, total = await refund_repo.list_requests(conn, status=None, user_id=user_id, limit=limit, offset=offset)
    return Page(items=[_strip_total(r) for r in rows], total=total, limit=limit, offset=offset)


async def list_all_requests(conn: AsyncConnection, *, status: str | None, limit: int, offset: int) -> Page:
    rows, total = await refund_repo.list_requests(conn, status=status, user_id=None, limit=limit, offset=offset)
    return Page(items=[_strip_total(r) for r in rows], total=total, limit=limit, offset=offset)


async def process_request(
    conn: AsyncConnection, request_id: int, approve: bool, current_user: dict[str, Any]
) -> dict[str, Any]:
    if current_user["role"] not in STAFF_ADMIN_ROLES:
        raise ForbiddenError("Chỉ admin/staff mới được duyệt yêu cầu hoàn tiền")

    old = await get_request(conn, request_id, current_user)
    await call_db(
        lambda: refund_repo.process(conn, request_id=request_id, approve=approve, processed_by=current_user["id"])
    )
    # process_refund_request() (DB) chi tra 5 cot toi thieu — lay lai ban day
    # du (order_code/user_id/reason/requested_at) khop voi RefundRequestDetailOut.
    updated = await refund_repo.get_by_id(conn, request_id)
    assert updated is not None
    await record_audit(
        conn, user_id=current_user["id"], action="update", entity_type="refund_request",
        entity_id=request_id, old_value=old, new_value=updated,
    )
    return updated
