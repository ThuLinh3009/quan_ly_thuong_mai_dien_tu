"""Repository cho refresh_tokens — gọi function DB trong database/functions.sql
(mục 17). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg import AsyncConnection


async def create(conn: AsyncConnection, *, user_id: int, token_hash: str, expires_at: datetime) -> None:
    await conn.execute("SELECT create_refresh_token(%s, %s, %s)", (user_id, token_hash, expires_at))


async def get_valid_by_hash(conn: AsyncConnection, token_hash: str) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_valid_refresh_token(%s)", (token_hash,))
    return await cur.fetchone()


async def revoke(conn: AsyncConnection, token_hash: str) -> None:
    await conn.execute("SELECT revoke_refresh_token(%s)", (token_hash,))


async def revoke_all_for_user(conn: AsyncConnection, user_id: int) -> None:
    await conn.execute("SELECT revoke_all_refresh_tokens(%s)", (user_id,))
