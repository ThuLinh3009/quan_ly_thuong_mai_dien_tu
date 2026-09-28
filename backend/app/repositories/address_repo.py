"""Repository cho Address — gọi function DB trong database/functions.sql
(mục 28). Không viết SQL trực tiếp ở đây."""
from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection


async def create(conn: AsyncConnection, *, user_id: int, **fields: Any) -> dict[str, Any]:
    cur = await conn.execute(
        "SELECT * FROM create_address(%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            user_id,
            fields["recipient_name"],
            fields["phone"],
            fields["line1"],
            fields["ward"],
            fields["district"],
            fields["province"],
            fields["is_default"],
        ),
    )
    row = await cur.fetchone()
    assert row is not None
    return row


async def list_for_user(conn: AsyncConnection, user_id: int) -> list[dict[str, Any]]:
    cur = await conn.execute("SELECT * FROM list_addresses_for_user(%s)", (user_id,))
    return await cur.fetchall()


async def get_by_id(conn: AsyncConnection, address_id: int) -> dict[str, Any] | None:
    cur = await conn.execute("SELECT * FROM get_address_by_id(%s)", (address_id,))
    return await cur.fetchone()


async def set_default(conn: AsyncConnection, address_id: int, user_id: int) -> bool:
    cur = await conn.execute("SELECT set_default_address(%s, %s) AS ok", (address_id, user_id))
    row = await cur.fetchone()
    return bool(row["ok"])
