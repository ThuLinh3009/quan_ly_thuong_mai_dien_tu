from datetime import datetime, timedelta, timezone

import pytest

from app.core.errors import ConflictError
from app.repositories import promotion_repo
from app.schemas.promotion import PromotionCreate, PromotionUpdate
from app.services import promotion_service

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_promotion_create_rejects_end_before_start():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        PromotionCreate(
            type="percentage",
            value=10,
            starts_at=now,
            ends_at=now - timedelta(days=1),
        )


def test_promotion_create_rejects_percentage_over_100():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        PromotionCreate(
            type="percentage",
            value=150,
            starts_at=now,
            ends_at=now + timedelta(days=1),
        )


def test_promotion_create_accepts_valid_payload():
    now = datetime.now(timezone.utc)
    promo = PromotionCreate(
        code="SALE10",
        type="percentage",
        value=10,
        starts_at=now,
        ends_at=now + timedelta(days=7),
    )
    assert promo.code == "SALE10"


async def test_update_promotion_rejects_end_before_start_after_merge(monkeypatch):
    old = {
        "id": 1,
        "code": "SALE10",
        "type": "percentage",
        "value": 10,
        "min_order_amount": 0,
        "max_discount_amount": None,
        "starts_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "ends_at": datetime(2026, 1, 10, tzinfo=timezone.utc),
        "usage_limit": None,
        "per_user_limit": None,
        "is_active": True,
    }

    async def fake_get_by_id(conn, promotion_id):
        return old

    monkeypatch.setattr(promotion_repo, "get_by_id", fake_get_by_id)

    admin = {"id": 1, "role": "admin"}
    # ends_at mới sớm hơn starts_at cũ (không đổi starts_at) -> phải bị chặn ở service
    update = PromotionUpdate(ends_at=datetime(2025, 12, 31, tzinfo=timezone.utc))

    with pytest.raises(ConflictError):
        await promotion_service.update_promotion(conn=None, promotion_id=1, data=update, current_user=admin)
