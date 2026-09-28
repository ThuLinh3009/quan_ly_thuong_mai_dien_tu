from __future__ import annotations

from psycopg import AsyncConnection

from app.core.db_errors import call_db
from app.core.errors import NotFoundError
from app.repositories import cart_repo
from app.schemas.cart import CartOut


async def get_cart(conn: AsyncConnection, user_id: int) -> CartOut:
    row = await cart_repo.get_cart(conn, user_id)
    return CartOut(**row)


async def add_item(conn: AsyncConnection, user_id: int, variant_id: int, quantity: int) -> CartOut:
    await call_db(lambda: cart_repo.add_item(conn, user_id=user_id, variant_id=variant_id, quantity=quantity))
    return await get_cart(conn, user_id)


async def update_item(conn: AsyncConnection, user_id: int, variant_id: int, quantity: int) -> CartOut:
    updated = await call_db(
        lambda: cart_repo.update_item_quantity(conn, user_id=user_id, variant_id=variant_id, quantity=quantity)
    )
    if not updated:
        raise NotFoundError(f"Không tìm thấy biến thể id={variant_id} trong giỏ hàng")
    return await get_cart(conn, user_id)


async def remove_item(conn: AsyncConnection, user_id: int, variant_id: int) -> CartOut:
    removed = await cart_repo.remove_item(conn, user_id=user_id, variant_id=variant_id)
    if not removed:
        raise NotFoundError(f"Không tìm thấy biến thể id={variant_id} trong giỏ hàng")
    return await get_cart(conn, user_id)


async def clear_cart(conn: AsyncConnection, user_id: int) -> None:
    await cart_repo.clear(conn, user_id)
