from collections.abc import AsyncIterator

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


async def get_conn() -> AsyncIterator:
    """FastAPI dependency: một transaction cho mỗi request (commit khi thành công, rollback khi lỗi)."""
    assert pool is not None, "Database pool chưa được khởi tạo"
    async with pool.connection() as conn:
        yield conn
