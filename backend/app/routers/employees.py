from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import require_roles
from app.schemas.common import Page
from app.schemas.employee import StaffCreate, StaffOut, StaffUpdate
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["employees"])

_admin_only = require_roles("admin")


@router.get("", response_model=Page[StaffOut])
async def list_staff(
    keyword: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_admin_only),
):
    return await employee_service.list_staff(conn, keyword=keyword, is_active=is_active, limit=limit, offset=offset)


@router.get("/{staff_id}", response_model=StaffOut)
async def get_staff(
    staff_id: int,
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_admin_only),
):
    return await employee_service.get_staff(conn, staff_id)


@router.post("", response_model=StaffOut, status_code=201)
async def create_staff(
    data: StaffCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin_only),
):
    return await employee_service.create_staff(conn, data, current_user)


@router.put("/{staff_id}", response_model=StaffOut)
async def update_staff(
    staff_id: int,
    data: StaffUpdate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin_only),
):
    return await employee_service.update_staff(conn, staff_id, data, current_user)


@router.patch("/{staff_id}/lock", response_model=StaffOut)
async def lock_staff(
    staff_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin_only),
):
    return await employee_service.set_staff_active(conn, staff_id, False, current_user)


@router.patch("/{staff_id}/unlock", response_model=StaffOut)
async def unlock_staff(
    staff_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin_only),
):
    return await employee_service.set_staff_active(conn, staff_id, True, current_user)


@router.delete("/{staff_id}", status_code=204)
async def delete_staff(
    staff_id: int,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_admin_only),
):
    await employee_service.delete_staff(conn, staff_id, current_user)
