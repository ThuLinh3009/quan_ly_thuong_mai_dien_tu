from redis.asyncio import Redis

from app.core.config import get_settings

redis_client: Redis | None = None


async def open_redis() -> None:
    global redis_client
    redis_client = Redis.from_url(get_settings().redis_url, decode_responses=True)
    await redis_client.ping()


async def close_redis() -> None:
    if redis_client is not None:
        await redis_client.aclose()


def get_redis() -> Redis:
    assert redis_client is not None, "Redis client chưa được khởi tạo"
    return redis_client
