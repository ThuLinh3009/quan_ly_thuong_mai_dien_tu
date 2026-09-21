"""Cache Redis đơn giản cho danh mục/sản phẩm — key theo prefix để invalidate theo nhóm.

Mọi lỗi kết nối Redis đều bị nuốt (log qua structlog) để cache không bao giờ làm sập API:
cache chỉ là tối ưu hiệu năng, không phải nguồn dữ liệu chính.
"""
from __future__ import annotations

import json
from typing import Any

import structlog

from app.core.redis import get_redis

logger = structlog.get_logger(__name__)

DEFAULT_TTL_SECONDS = 300

CATEGORY_PREFIX = "cache:categories"
PRODUCT_PREFIX = "cache:products"


async def get_json(key: str) -> Any | None:
    try:
        raw = await get_redis().get(key)
    except Exception:  # noqa: BLE001 - cache không được làm hỏng request chính
        logger.warning("cache_get_failed", key=key)
        return None
    return json.loads(raw) if raw is not None else None


async def set_json(key: str, value: Any, ttl: int = DEFAULT_TTL_SECONDS) -> None:
    try:
        await get_redis().set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:  # noqa: BLE001
        logger.warning("cache_set_failed", key=key)


async def invalidate_prefix(prefix: str) -> None:
    try:
        redis = get_redis()
        async for key in redis.scan_iter(match=f"{prefix}:*"):
            await redis.delete(key)
    except Exception:  # noqa: BLE001
        logger.warning("cache_invalidate_failed", prefix=prefix)
