"""Ghi audit log dùng chung cho mọi module (thay cho ASGI middleware).

Một middleware ASGI thuần không biết được "entity_type"/"entity_id nghiệp vụ"
của một request (ví dụ PUT /products/5 sửa cái gì) nếu không parse ngược route,
nên ta dùng một hàm dùng chung gọi tường minh từ service ngay sau khi thao tác
DB thành công — cùng transaction với thao tác đó (rollback cùng nhau nếu lỗi).
"""
from __future__ import annotations

import json
from typing import Any

from psycopg import AsyncConnection
from psycopg.types.json import Jsonb


def _dumps(obj: Any) -> str:
    """default=str để datetime/Decimal (từ dict_row) không làm vỡ json.dumps."""
    return json.dumps(obj, default=str)


async def record_audit(
    conn: AsyncConnection,
    *,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
) -> None:
    # Goi function record_audit() trong functions.sql (muc 19) thay vi tu INSERT.
    await conn.execute(
        "SELECT record_audit(%s, %s, %s, %s, %s, %s)",
        (
            user_id,
            action,
            entity_type,
            entity_id,
            Jsonb(old_value, dumps=_dumps) if old_value is not None else None,
            Jsonb(new_value, dumps=_dumps) if new_value is not None else None,
        ),
    )
