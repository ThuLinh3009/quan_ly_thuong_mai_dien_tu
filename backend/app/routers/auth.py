from typing import Any

from fastapi import APIRouter, Depends
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import get_current_user
from app.core.ratelimit import login_rate_limit
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(data: RegisterRequest, conn: AsyncConnection = Depends(get_conn)):
    return await auth_service.register(conn, data)


@router.post("/login", response_model=TokenPair, dependencies=[Depends(login_rate_limit)])
async def login(data: LoginRequest, conn: AsyncConnection = Depends(get_conn)):
    return await auth_service.login(conn, data)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshRequest, conn: AsyncConnection = Depends(get_conn)):
    return await auth_service.refresh(conn, data.refresh_token)


@router.post("/logout", status_code=204)
async def logout(data: RefreshRequest, conn: AsyncConnection = Depends(get_conn)):
    await auth_service.logout(conn, data.refresh_token)


@router.post("/logout-all", status_code=204)
async def logout_all(
    user: dict[str, Any] = Depends(get_current_user),
    conn: AsyncConnection = Depends(get_conn),
):
    """Đăng xuất khỏi mọi thiết bị: thu hồi toàn bộ refresh token của chính
    người đang đăng nhập (cần access token). Access token hiện tại vẫn còn hiệu
    lực tới khi hết hạn."""
    await auth_service.logout_all(conn, user["id"])


@router.get("/me", response_model=UserOut)
async def me(user: dict[str, Any] = Depends(get_current_user)):
    return user
