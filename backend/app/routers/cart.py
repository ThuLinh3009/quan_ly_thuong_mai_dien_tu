from typing import Any

from fastapi import APIRouter, Depends
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import require_roles
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartOut
from app.services import cart_service

router = APIRouter(prefix="/cart", tags=["cart"])

_customer = require_roles("customer")


@router.get("", response_model=CartOut)
async def get_cart(
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    return await cart_service.get_cart(conn, current_user["id"])


@router.post("/items", response_model=CartOut, status_code=201)
async def add_item(
    data: CartItemAdd,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    return await cart_service.add_item(conn, current_user["id"], data.product_variant_id, data.quantity)


@router.put("/items/{variant_id}", response_model=CartOut)
async def update_item(
    variant_id: int,
    data: CartItemUpdate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    return await cart_service.update_item(conn, current_user["id"], variant_id, data.quantity)


@router.delete("/items/{variant_id}", response_model=CartOut)
async def remove_item(
    variant_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    return await cart_service.remove_item(conn, current_user["id"], variant_id)


@router.delete("", status_code=204)
async def clear_cart(
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    await cart_service.clear_cart(conn, current_user["id"])
