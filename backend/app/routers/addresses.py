from typing import Any

from fastapi import APIRouter, Depends
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import require_roles
from app.schemas.address import AddressCreate, AddressOut
from app.services import address_service

router = APIRouter(prefix="/addresses", tags=["addresses"])

_customer = require_roles("customer")


@router.get("", response_model=list[AddressOut])
async def list_addresses(
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    return await address_service.list_addresses(conn, current_user["id"])


@router.post("", response_model=AddressOut, status_code=201)
async def create_address(
    data: AddressCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    return await address_service.create_address(conn, current_user["id"], data)


@router.post("/{address_id}/default", response_model=None, status_code=204)
async def set_default_address(
    address_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_customer),
):
    await address_service.set_default(conn, current_user["id"], address_id)
