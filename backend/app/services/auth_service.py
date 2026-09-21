from __future__ import annotations

from typing import Any

import jwt
from psycopg import AsyncConnection

from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.repositories import refresh_token_repo, user_repo
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair


async def register(conn: AsyncConnection, data: RegisterRequest) -> dict[str, Any]:
    existing = await user_repo.get_by_email(conn, data.email)
    if existing is not None:
        raise ConflictError(f"Email {data.email} đã được đăng ký")

    return await user_repo.create_user(
        conn,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role="customer",
    )


async def _issue_token_pair(conn: AsyncConnection, user: dict[str, Any]) -> TokenPair:
    access_token = create_access_token(user["id"], user["role"])
    refresh_token, _jti, expires_at = create_refresh_token(user["id"], user["role"])
    await refresh_token_repo.create(
        conn, user_id=user["id"], token_hash=hash_token(refresh_token), expires_at=expires_at
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


async def login(conn: AsyncConnection, data: LoginRequest) -> TokenPair:
    user = await user_repo.get_by_email(conn, data.email)
    if user is None or not verify_password(data.password, user["password_hash"]):
        raise UnauthorizedError("Email hoặc mật khẩu không đúng")
    if not user["is_active"]:
        raise UnauthorizedError("Tài khoản đã bị khóa")

    return await _issue_token_pair(conn, user)


async def refresh(conn: AsyncConnection, refresh_token: str) -> TokenPair:
    try:
        payload = decode_token(refresh_token)
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Refresh token không hợp lệ hoặc đã hết hạn") from exc

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Token không phải refresh token")

    token_hash = hash_token(refresh_token)
    stored = await refresh_token_repo.get_valid_by_hash(conn, token_hash)
    if stored is None:
        raise UnauthorizedError("Refresh token đã bị thu hồi hoặc không tồn tại")

    user = await user_repo.get_by_id(conn, int(payload["sub"]))
    if user is None or not user["is_active"]:
        raise UnauthorizedError("Người dùng không tồn tại hoặc đã bị khóa")

    # Rotation: thu hồi refresh token cũ, phát hành cặp token mới
    await refresh_token_repo.revoke(conn, token_hash)
    return await _issue_token_pair(conn, user)


async def logout(conn: AsyncConnection, refresh_token: str) -> None:
    await refresh_token_repo.revoke(conn, hash_token(refresh_token))
