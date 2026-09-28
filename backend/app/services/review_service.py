from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.core.db_errors import call_db
from app.repositories import review_repo
from app.schemas.common import Page


def _strip_total(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k != "total_count"}


async def submit_review(conn: AsyncConnection, user_id: int, order_item_id: int, rating: int, comment: str | None) -> int:
    return await call_db(
        lambda: review_repo.submit(conn, order_item_id=order_item_id, user_id=user_id, rating=rating, comment=comment)
    )


async def list_for_product(conn: AsyncConnection, product_id: int, *, limit: int, offset: int) -> Page:
    rows, total = await review_repo.list_for_product(conn, product_id, limit=limit, offset=offset)
    return Page(items=[_strip_total(r) for r in rows], total=total, limit=limit, offset=offset)


async def rating_summary(conn: AsyncConnection, product_id: int) -> dict[str, Any]:
    return await review_repo.rating_summary(conn, product_id)


async def list_reviewable(conn: AsyncConnection, user_id: int) -> list[dict[str, Any]]:
    return await review_repo.list_reviewable(conn, user_id)
