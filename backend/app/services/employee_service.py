from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.core.audit import record_audit
from app.core.errors import ConflictError, NotFoundError
from app.core.security import hash_password
from app.repositories import user_repo
from app.schemas.common import Page
from app.schemas.employee import StaffCreate, StaffUpdate


async def create_staff(conn: AsyncConnection, data: StaffCreate, current_user: dict[str, Any]) -> dict[str, Any]:
    if await user_repo.get_by_email(conn, data.email) is not None:
        raise ConflictError(f"Email {data.email} đã được sử dụng")

    staff = await user_repo.create_user(
        conn,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role="staff",
    )
    await record_audit(
        conn, user_id=current_user["id"], action="create", entity_type="staff",
        entity_id=staff["id"], new_value=_public(staff),
    )
    return staff


async def list_staff(
    conn: AsyncConnection, *, keyword: str | None, is_active: bool | None, limit: int, offset: int
) -> Page:
    rows, total = await user_repo.list_staff(conn, keyword=keyword, is_active=is_active, limit=limit, offset=offset)
    items = [_public({k: v for k, v in row.items() if k != "total_count"}) for row in rows]
    return Page(items=items, total=total, limit=limit, offset=offset)


async def get_staff(conn: AsyncConnection, staff_id: int) -> dict[str, Any]:
    staff = await user_repo.get_by_id(conn, staff_id)
    if staff is None or staff["role"] != "staff":
        raise NotFoundError(f"Không tìm thấy nhân viên id={staff_id}")
    return staff


async def update_staff(
    conn: AsyncConnection, staff_id: int, data: StaffUpdate, current_user: dict[str, Any]
) -> dict[str, Any]:
    old = await get_staff(conn, staff_id)
    updated = await user_repo.update_staff(conn, staff_id, full_name=data.full_name, phone=data.phone)
    if updated is None:
        raise NotFoundError(f"Không tìm thấy nhân viên id={staff_id}")
    await record_audit(
        conn, user_id=current_user["id"], action="update", entity_type="staff",
        entity_id=staff_id, old_value=_public(old), new_value=_public(updated),
    )
    return updated


async def set_staff_active(
    conn: AsyncConnection, staff_id: int, is_active: bool, current_user: dict[str, Any]
) -> dict[str, Any]:
    old = await get_staff(conn, staff_id)
    updated = await user_repo.set_staff_active(conn, staff_id, is_active)
    if updated is None:
        raise NotFoundError(f"Không tìm thấy nhân viên id={staff_id}")
    await record_audit(
        conn, user_id=current_user["id"], action="lock" if not is_active else "unlock", entity_type="staff",
        entity_id=staff_id, old_value=_public(old), new_value=_public(updated),
    )
    return updated


async def delete_staff(conn: AsyncConnection, staff_id: int, current_user: dict[str, Any]) -> None:
    old = await get_staff(conn, staff_id)
    deleted = await user_repo.soft_delete_staff(conn, staff_id)
    if not deleted:
        raise NotFoundError(f"Không tìm thấy nhân viên id={staff_id}")
    await record_audit(
        conn, user_id=current_user["id"], action="delete", entity_type="staff",
        entity_id=staff_id, old_value=_public(old),
    )


def _public(user: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in user.items() if k != "password_hash"}
