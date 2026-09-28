import pytest

from app.core.errors import ForbiddenError, NotFoundError
from app.repositories import order_repo
from app.schemas.order import OrderStatusUpdate
from app.services import order_service

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _order_row(**overrides):
    row = {
        "id": 1,
        "order_code": "ORD-1",
        "user_id": 100,
        "status": "pending",
        "subtotal": "100000",
        "discount_amount": "0",
        "shipping_fee": "30000",
        "total_amount": "130000",
        "created_at": "2026-01-01T00:00:00Z",
        "address": None,
        "items": [],
        "payment": {"method": "cod", "status": "pending", "amount": "130000", "paid_at": None},
        "status_history": [],
    }
    row.update(overrides)
    return row


async def test_customer_cannot_see_other_users_order(monkeypatch):
    async def fake_get_order_detail(conn, order_id):
        return _order_row(user_id=100)

    monkeypatch.setattr(order_repo, "get_order_detail", fake_get_order_detail)

    other_customer = {"id": 999, "role": "customer"}
    with pytest.raises(NotFoundError):
        await order_service.get_order(conn=None, order_id=1, current_user=other_customer)


async def test_staff_can_see_any_order(monkeypatch):
    async def fake_get_order_detail(conn, order_id):
        return _order_row(user_id=100)

    monkeypatch.setattr(order_repo, "get_order_detail", fake_get_order_detail)

    staff = {"id": 999, "role": "staff"}
    order = await order_service.get_order(conn=None, order_id=1, current_user=staff)
    assert order["id"] == 1


async def test_customer_cannot_confirm_own_order(monkeypatch):
    async def fake_get_order_detail(conn, order_id):
        return _order_row(user_id=100, status="pending")

    monkeypatch.setattr(order_repo, "get_order_detail", fake_get_order_detail)

    owner = {"id": 100, "role": "customer"}
    with pytest.raises(ForbiddenError):
        await order_service.update_status(
            conn=None, order_id=1, data=OrderStatusUpdate(status="confirmed"), current_user=owner
        )


async def test_customer_can_cancel_own_pending_order(monkeypatch):
    calls = []

    async def fake_get_order_detail(conn, order_id):
        return _order_row(user_id=100, status="pending")

    async def fake_update_status(conn, *, order_id, new_status, changed_by, note):
        calls.append((order_id, new_status, changed_by, note))

    monkeypatch.setattr(order_repo, "get_order_detail", fake_get_order_detail)
    monkeypatch.setattr(order_repo, "update_status", fake_update_status)

    owner = {"id": 100, "role": "customer"}
    result = await order_service.update_status(
        conn=None, order_id=1, data=OrderStatusUpdate(status="cancelled"), current_user=owner
    )

    assert calls == [(1, "cancelled", 100, None)]
    assert result["user_id"] == 100


async def test_simulate_payment_rejects_non_gateway_orders(monkeypatch):
    async def fake_get_order_detail(conn, order_id):
        return _order_row(payment={"method": "cod", "status": "pending", "amount": "130000", "paid_at": None})

    monkeypatch.setattr(order_repo, "get_order_detail", fake_get_order_detail)

    owner = {"id": 100, "role": "customer"}
    from app.core.errors import ValidationAppError

    with pytest.raises(ValidationAppError):
        await order_service.simulate_payment(conn=None, order_id=1, success=True, current_user=owner)
