"""Dependency xác thực JWT + phân quyền theo role (Admin/Staff/Customer).

FastAPI không route theo role trước khi vào handler, nên "RBAC middleware" ở đây
được cài đặt như một dependency chuẩn (`require_roles`) gắn vào từng router —
đây là cách làm khuyến nghị của FastAPI, tương đương middleware phân quyền nhưng
truy cập được path params/role yêu cầu của từng route.
"""
from __future__ import annotations

from typing import Any

import jwt
from fastapi import Depends, Header
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.repositories import user_repo


async def get_current_user(
    authorization: str | None = Header(default=None),
    conn: AsyncConnection = Depends(get_conn),
) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Thiếu access token (header Authorization: Bearer <token>)")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Access token đã hết hạn") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Access token không hợp lệ") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Token không phải access token")

    user = await user_repo.get_by_id(conn, int(payload["sub"]))
    if user is None:
        raise UnauthorizedError("Người dùng không tồn tại")
    if not user["is_active"]:
        raise ForbiddenError("Tài khoản đã bị khóa")

    return user


async def get_optional_user(
    authorization: str | None = Header(default=None),
    conn: AsyncConnection = Depends(get_conn),
) -> dict[str, Any] | None:
    """Dùng cho endpoint public nhưng muốn biết role nếu có đăng nhập (vd: admin xem cả sản phẩm ẩn)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        return await get_current_user(authorization=authorization, conn=conn)
    except Exception:  # noqa: BLE001 - token hỏng thì coi như khách vãng lai, không chặn request
        return None


def require_roles(*roles: str):
    async def _checker(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if user["role"] not in roles:
            raise ForbiddenError(f"Yêu cầu role thuộc {roles}, tài khoản hiện tại là '{user['role']}'")
        return user

    return _checker
