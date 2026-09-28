"""Rate limit dựa trên Redis (INCR + EXPIRE theo cửa sổ cố định) — chống
brute-force đăng nhập và lạm dụng API nói chung (Sprint 4, mục 44).

Không dùng thư viện ngoài (slowapi...) vì logic rất đơn giản và Redis đã có
sẵn trong stack — tránh thêm dependency chỉ để làm 2 lệnh INCR/EXPIRE.
Lỗi kết nối Redis không được chặn request (rate limit là lớp bảo vệ thêm,
không phải nguồn đúng-sai chính), giống quy ước ở core/cache.py.
"""
from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.errors import TooManyRequestsError
from app.core.redis import get_redis

logger = structlog.get_logger(__name__)

_EXEMPT_PATHS = {"/health", "/health/db"}


async def _incr_and_check(key: str, *, limit: int, window: int) -> bool:
    """Trả về True nếu vượt giới hạn. Nuốt lỗi Redis (coi như không giới hạn)."""
    try:
        redis = get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
        return count > limit
    except Exception:  # noqa: BLE001
        logger.warning("rate_limit_check_failed", key=key)
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Giới hạn chung theo IP nguồn: tối đa `limit` request / `window` giây,
    áp dụng cho toàn bộ API. Endpoint nhạy cảm hơn (login) dùng thêm
    `enforce_rate_limit()` làm dependency riêng, chặt hơn."""

    def __init__(self, app, *, limit: int = 120, window: int = 60) -> None:
        super().__init__(app)
        self.limit = limit
        self.window = window

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        exceeded = await _incr_and_check(f"ratelimit:global:{client_ip}", limit=self.limit, window=self.window)
        if exceeded:
            return JSONResponse(status_code=429, content={"detail": "Quá nhiều yêu cầu, vui lòng thử lại sau."})

        return await call_next(request)


async def enforce_rate_limit(key: str, *, limit: int, window: int) -> None:
    """Dùng làm FastAPI dependency cho 1 endpoint cụ thể (vd login) — giới hạn
    riêng, chặt hơn giới hạn chung, không cần nới lỏng giới hạn chung để bù."""
    if await _incr_and_check(key, limit=limit, window=window):
        raise TooManyRequestsError("Quá nhiều lần thử, vui lòng thử lại sau ít phút.")


async def login_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    await enforce_rate_limit(f"ratelimit:login:{client_ip}", limit=10, window=60)
