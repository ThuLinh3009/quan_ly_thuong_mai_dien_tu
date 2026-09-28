from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import get_current_user, require_roles
from app.schemas.common import Page
from app.schemas.refund import RefundDecisionRequest, RefundRequestCreate, RefundRequestDetailOut, RefundRequestOut
from app.services import refund_service

router = APIRouter(prefix="/refunds", tags=["refunds"])

_customer = require_roles("customer")
_staff_admin = require_roles("admin", "staff")


@router.post("", response_model=RefundRequestOut, status_code=201)
async def create_refund_request(
    data: RefundRequestCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    """Khách hàng yêu cầu trả hàng/hoàn tiền — chỉ áp dụng cho đơn đã Delivered."""
    return await refund_service.create_request(conn, current_user["id"], data.order_id, data.reason)


@router.get("", response_model=Page[RefundRequestOut])
async def list_my_refund_requests(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    return await refund_service.list_my_requests(conn, current_user["id"], limit=limit, offset=offset)


@router.get("/admin", response_model=Page[RefundRequestOut])
async def list_all_refund_requests(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    return await refund_service.list_all_requests(conn, status=status, limit=limit, offset=offset)


@router.get("/{request_id}", response_model=RefundRequestDetailOut)
async def get_refund_request(
    request_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    return await refund_service.get_request(conn, request_id, current_user)


@router.post("/{request_id}/process", response_model=RefundRequestDetailOut)
async def process_refund_request(
    request_id: int,
    data: RefundDecisionRequest,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_staff_admin),
):
    return await refund_service.process_request(conn, request_id, data.approve, current_user)
