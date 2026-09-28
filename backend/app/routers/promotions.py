from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import require_roles
from app.schemas.common import Page
from app.schemas.promotion import (
    ActiveFlashSaleOut,
    FlashSaleItemCreate,
    FlashSaleItemOut,
    PromotionCreate,
    PromotionOut,
    PromotionUpdate,
)
from app.services import promotion_service

router = APIRouter(prefix="/promotions", tags=["promotions"])

_admin = require_roles("admin")


@router.get("/flash-sales/active", response_model=list[ActiveFlashSaleOut])
async def get_active_flash_sales(
    limit: int = Query(default=20, ge=1, le=100),
    conn: AsyncConnection = Depends(get_conn),
):
    """Endpoint công khai — khu vực flash sale trang chủ (không cần đăng nhập)."""
    return await promotion_service.get_active_flash_sales(conn, limit)


@router.get("", response_model=Page[PromotionOut])
async def list_promotions(
    type: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_admin),
):
    return await promotion_service.list_promotions(conn, type=type, is_active=is_active, limit=limit, offset=offset)


@router.get("/{promotion_id}", response_model=PromotionOut)
async def get_promotion(
    promotion_id: int,
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_admin),
):
    return await promotion_service.get_promotion(conn, promotion_id)


@router.post("", response_model=PromotionOut, status_code=201)
async def create_promotion(
    data: PromotionCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin),
):
    return await promotion_service.create_promotion(conn, data, current_user)


@router.put("/{promotion_id}", response_model=PromotionOut)
async def update_promotion(
    promotion_id: int,
    data: PromotionUpdate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin),
):
    return await promotion_service.update_promotion(conn, promotion_id, data, current_user)


@router.post("/{promotion_id}/deactivate", response_model=PromotionOut)
async def deactivate_promotion(
    promotion_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin),
):
    return await promotion_service.set_promotion_active(conn, promotion_id, False, current_user)


@router.post("/{promotion_id}/activate", response_model=PromotionOut)
async def activate_promotion(
    promotion_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin),
):
    return await promotion_service.set_promotion_active(conn, promotion_id, True, current_user)


@router.post("/{promotion_id}/flash-sale-items", response_model=FlashSaleItemOut, status_code=201)
async def add_flash_sale_item(
    promotion_id: int,
    data: FlashSaleItemCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin),
):
    return await promotion_service.add_flash_sale_item(conn, promotion_id, data, current_user)


@router.get("/{promotion_id}/flash-sale-items", response_model=list[FlashSaleItemOut])
async def list_flash_sale_items(
    promotion_id: int,
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_admin),
):
    return await promotion_service.list_flash_sale_items(conn, promotion_id)
