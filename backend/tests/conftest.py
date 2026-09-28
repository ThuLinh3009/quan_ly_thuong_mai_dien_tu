import pytest


@pytest.fixture
def anyio_backend():
    """Chỉ chạy test async trên backend asyncio (mặc định anyio còn hỗ trợ
    trio nhưng project không dùng), tránh test chạy 2 lần trên 2 backend."""
    return "asyncio"
