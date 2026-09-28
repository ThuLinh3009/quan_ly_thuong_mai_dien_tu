import pytest

from app.core.errors import ForbiddenError, NotFoundError
from app.repositories import refund_repo
from app.services import refund_service

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_customer_cannot_process_refund_request():
    customer = {"id": 1, "role": "customer"}
    with pytest.raises(ForbiddenError):
        await refund_service.process_request(conn=None, request_id=1, approve=True, current_user=customer)


async def test_customer_cannot_view_others_refund_request(monkeypatch):
    async def fake_get_by_id(conn, request_id):
        return {"id": 1, "order_id": 1, "order_code": "ORD-1", "user_id": 100, "reason": "x",
                "status": "requested", "refund_amount": "1000", "requested_at": "2026-01-01T00:00:00Z",
                "processed_by": None, "processed_at": None}

    monkeypatch.setattr(refund_repo, "get_by_id", fake_get_by_id)

    other_customer = {"id": 999, "role": "customer"}
    with pytest.raises(NotFoundError):
        await refund_service.get_request(conn=None, request_id=1, current_user=other_customer)


async def test_staff_can_view_any_refund_request(monkeypatch):
    async def fake_get_by_id(conn, request_id):
        return {"id": 1, "order_id": 1, "order_code": "ORD-1", "user_id": 100, "reason": "x",
                "status": "requested", "refund_amount": "1000", "requested_at": "2026-01-01T00:00:00Z",
                "processed_by": None, "processed_at": None}

    monkeypatch.setattr(refund_repo, "get_by_id", fake_get_by_id)

    staff = {"id": 5, "role": "staff"}
    request = await refund_service.get_request(conn=None, request_id=1, current_user=staff)
    assert request["order_id"] == 1
