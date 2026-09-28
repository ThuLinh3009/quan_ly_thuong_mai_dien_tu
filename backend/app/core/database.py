from collections.abc import AsyncIterator

import psycopg
from fastapi import Request
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import get_settings

pool: AsyncConnectionPool | None = None


async def open_pool() -> None:
    global pool
    pool = AsyncConnectionPool(
        get_settings().database_url,
        min_size=1,
        max_size=10,
        kwargs={"row_factory": dict_row},
        open=False,
    )
    await pool.open()


async def close_pool() -> None:
    if pool is not None:
        await pool.close()


async def get_conn(request: Request) -> AsyncIterator:
    """FastAPI dependency: trả về connection mà DBTransactionMiddleware đã mở
    sẵn cho request này (xem middleware.py).

    Không tự mở/đóng pool.connection() ở đây nữa (như bản trước) vì FastAPI
    chỉ chạy code sau `yield` của 1 dependency SAU KHI response đã được gửi
    xong cho client (dependency-with-yield's cleanup nằm trong AsyncExitStack,
    đóng sau dòng `await response(scope, receive, send)` — xem
    fastapi/routing.py). Nghĩa là nếu để commit ở đây, 2 request liên tiếp rất
    nhanh từ cùng 1 client (vd thêm giỏ hàng rồi checkout ngay) có thể khiến
    request sau đọc DB TRƯỚC KHI request trước kịp commit. DBTransactionMiddleware
    giải quyết việc này bằng cách buffer response, commit/rollback xong mới
    forward response thật ra ngoài.
    """
    yield request.scope["db_conn"]


def get_sync_connection() -> psycopg.Connection:
    """Kết nối đồng bộ (không qua pool async) dùng trong Celery worker — worker
    chạy tiến trình riêng, không có event loop nên không dùng chung pool với API."""
    return psycopg.connect(get_settings().database_url, row_factory=dict_row)
