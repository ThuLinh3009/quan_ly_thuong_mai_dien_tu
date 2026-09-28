from __future__ import annotations

from datetime import datetime
from typing import Any

from psycopg import AsyncConnection

from app.core.cache import STATISTICS_PREFIX, STATISTICS_TTL_SECONDS, get_json, set_json
from app.repositories import statistics_repo


async def top_selling_books(
    conn: AsyncConnection, *, date_from: datetime, date_to: datetime, limit: int
) -> list[dict[str, Any]]:
    cache_key = f"{STATISTICS_PREFIX}:top-selling:{date_from}:{date_to}:{limit}"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    rows = await statistics_repo.top_selling_books(conn, date_from=date_from, date_to=date_to, limit=limit)
    await set_json(cache_key, rows, ttl=STATISTICS_TTL_SECONDS)
    return rows


async def revenue_report(conn: AsyncConnection, *, date_from: datetime, date_to: datetime) -> list[dict[str, Any]]:
    cache_key = f"{STATISTICS_PREFIX}:revenue:{date_from}:{date_to}"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    rows = await statistics_repo.revenue_report(conn, date_from=date_from, date_to=date_to)
    await set_json(cache_key, rows, ttl=STATISTICS_TTL_SECONDS)
    return rows


async def dashboard_summary(conn: AsyncConnection, *, date_from: datetime, date_to: datetime) -> dict[str, Any]:
    cache_key = f"{STATISTICS_PREFIX}:dashboard:{date_from}:{date_to}"
    cached = await get_json(cache_key)
    if cached is not None:
        return cached

    row = await statistics_repo.dashboard_summary(conn, date_from=date_from, date_to=date_to)
    await set_json(cache_key, row, ttl=STATISTICS_TTL_SECONDS)
    return row
