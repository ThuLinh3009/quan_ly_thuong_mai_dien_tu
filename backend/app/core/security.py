"""Hash mật khẩu (bcrypt) + tạo/giải mã JWT access & refresh token."""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import get_settings

TokenType = Literal["access", "refresh"]


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(user_id: int, role: str, token_type: TokenType, expires_delta: timedelta) -> tuple[str, str]:
    """Trả về (token, jti). jti dùng làm khóa tra cứu/thu hồi refresh token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    jti = uuid.uuid4().hex
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def create_access_token(user_id: int, role: str) -> str:
    settings = get_settings()
    token, _ = _create_token(user_id, role, "access", timedelta(minutes=settings.access_token_minutes))
    return token


def create_refresh_token(user_id: int, role: str) -> tuple[str, str, datetime]:
    """Trả về (token, jti, expires_at) để service lưu hash vào bảng refresh_tokens."""
    settings = get_settings()
    expires_delta = timedelta(days=settings.refresh_token_days)
    token, jti = _create_token(user_id, role, "refresh", expires_delta)
    expires_at = datetime.now(timezone.utc) + expires_delta
    return token, jti, expires_at


def decode_token(token: str) -> dict[str, Any]:
    """Raise jwt.PyJWTError (ExpiredSignatureError, InvalidTokenError, ...) nếu token không hợp lệ."""
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def hash_token(token: str) -> str:
    """Băm refresh token bằng SHA-256 trước khi lưu DB (không lưu JWT thô)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
