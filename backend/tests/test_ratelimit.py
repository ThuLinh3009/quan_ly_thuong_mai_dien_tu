import pytest

from app.core import ratelimit
from app.core.errors import TooManyRequestsError

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class FakeRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, ttl: int) -> None:
        pass


async def test_enforce_rate_limit_allows_under_limit(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(ratelimit, "get_redis", lambda: fake)

    for _ in range(5):
        await ratelimit.enforce_rate_limit("key-a", limit=5, window=60)


async def test_enforce_rate_limit_blocks_over_limit(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(ratelimit, "get_redis", lambda: fake)

    for _ in range(3):
        await ratelimit.enforce_rate_limit("key-b", limit=3, window=60)

    with pytest.raises(TooManyRequestsError):
        await ratelimit.enforce_rate_limit("key-b", limit=3, window=60)


async def test_enforce_rate_limit_fails_open_when_redis_unavailable(monkeypatch):
    def broken_get_redis():
        raise ConnectionError("redis down")

    monkeypatch.setattr(ratelimit, "get_redis", broken_get_redis)

    # Không raise, không chặn request khi Redis lỗi (rate limit là lớp bảo vệ thêm)
    await ratelimit.enforce_rate_limit("key-c", limit=1, window=60)
