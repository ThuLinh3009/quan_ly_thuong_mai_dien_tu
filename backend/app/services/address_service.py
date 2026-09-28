from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.core.errors import ForbiddenError, NotFoundError
from app.repositories import address_repo
from app.schemas.address import AddressCreate


async def create_address(conn: AsyncConnection, user_id: int, data: AddressCreate) -> dict[str, Any]:
    return await address_repo.create(conn, user_id=user_id, **data.model_dump())


async def list_addresses(conn: AsyncConnection, user_id: int) -> list[dict[str, Any]]:
    return await address_repo.list_for_user(conn, user_id)


async def get_own_address(conn: AsyncConnection, user_id: int, address_id: int) -> dict[str, Any]:
    address = await address_repo.get_by_id(conn, address_id)
    if address is None:
        raise NotFoundError(f"Không tìm thấy địa chỉ id={address_id}")
    if address["user_id"] != user_id:
        raise ForbiddenError("Địa chỉ không thuộc về tài khoản hiện tại")
    return address


async def set_default(conn: AsyncConnection, user_id: int, address_id: int) -> None:
    ok = await address_repo.set_default(conn, address_id, user_id)
    if not ok:
        raise NotFoundError(f"Không tìm thấy địa chỉ id={address_id}")
