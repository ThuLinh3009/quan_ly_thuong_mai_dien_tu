from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg import AsyncConnection


async def create(conn: AsyncConnection, *, user_id: int, token_hash: str, expires_at: datetime) -> None:
    await conn.execute(
        "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
        (user_id, token_hash, expires_at),
    )


async def get_valid_by_hash(conn: AsyncConnection, token_hash: str) -> dict[str, Any] | None:
    cur = await conn.execute(
        """
        SELECT id, user_id, token_hash, expires_at, revoked_at
        FROM refresh_tokens
        WHERE token_hash = %s AND revoked_at IS NULL AND expires_at > now()
        """,
        (token_hash,),
    )
    return await cur.fetchone()


async def revoke(conn: AsyncConnection, token_hash: str) -> None:
    await conn.execute(
        "UPDATE refresh_tokens SET revoked_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
        (token_hash,),
    )


async def revoke_all_for_user(conn: AsyncConnection, user_id: int) -> None:
    await conn.execute(
        "UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = %s AND revoked_at IS NULL",
        (user_id,),
    )
