from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import require_roles
from app.schemas.common import Page
from app.schemas.review import ProductRatingSummaryOut, ReviewableOrderItemOut, ReviewCreate, ReviewOut
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])

_customer = require_roles("customer")


@router.post("", status_code=201)
async def submit_review(
    data: ReviewCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    review_id = await review_service.submit_review(
        conn, current_user["id"], data.order_item_id, data.rating, data.comment
    )
    return {"id": review_id}


@router.get("/reviewable", response_model=list[ReviewableOrderItemOut])
async def list_reviewable(
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    """Danh sách order_item đã Delivered và chưa được đánh giá — phục vụ form đánh giá."""
    return await review_service.list_reviewable(conn, current_user["id"])


@router.get("/product/{product_id}", response_model=Page[ReviewOut])
async def list_reviews_for_product(
    product_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
):
    return await review_service.list_for_product(conn, product_id, limit=limit, offset=offset)


@router.get("/product/{product_id}/summary", response_model=ProductRatingSummaryOut)
async def get_rating_summary(
    product_id: int,
    conn: AsyncConnection = Depends(get_conn),
):
    return await review_service.rating_summary(conn, product_id)
