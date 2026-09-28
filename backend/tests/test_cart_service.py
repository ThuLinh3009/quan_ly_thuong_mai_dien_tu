import pytest

from app.core.errors import NotFoundError
from app.repositories import cart_repo
from app.services import cart_service

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


_FAKE_CART_ROW = {
    "cart_id": 1,
    "items": [
        {
            "product_variant_id": 10,
            "product_id": 5,
            "product_name": "Số Đỏ",
            "variant_name": "Bìa mềm",
            "sku": "SACH-001-BM",
            "cover_image_url": None,
            "quantity": 2,
            "unit_price": "85000",
            "line_total": "170000",
        }
    ],
    "subtotal": "170000",
}


async def test_get_cart_maps_row_to_schema(monkeypatch):
    async def fake_get_cart(conn, user_id):
        assert user_id == 1
        return _FAKE_CART_ROW

    monkeypatch.setattr(cart_repo, "get_cart", fake_get_cart)

    cart = await cart_service.get_cart(conn=None, user_id=1)

    assert cart.cart_id == 1
    assert cart.subtotal == 170000
    assert len(cart.items) == 1
    assert cart.items[0].quantity == 2


async def test_update_item_raises_not_found_when_variant_missing(monkeypatch):
    async def fake_update_item_quantity(conn, *, user_id, variant_id, quantity):
        return False

    monkeypatch.setattr(cart_repo, "update_item_quantity", fake_update_item_quantity)

    with pytest.raises(NotFoundError):
        await cart_service.update_item(conn=None, user_id=1, variant_id=999, quantity=3)


async def test_remove_item_raises_not_found_when_absent(monkeypatch):
    async def fake_remove_item(conn, *, user_id, variant_id):
        return False

    monkeypatch.setattr(cart_repo, "remove_item", fake_remove_item)

    with pytest.raises(NotFoundError):
        await cart_service.remove_item(conn=None, user_id=1, variant_id=999)


async def test_add_item_then_returns_refreshed_cart(monkeypatch):
    async def fake_add_item(conn, *, user_id, variant_id, quantity):
        return 123

    async def fake_get_cart(conn, user_id):
        return _FAKE_CART_ROW

    monkeypatch.setattr(cart_repo, "add_item", fake_add_item)
    monkeypatch.setattr(cart_repo, "get_cart", fake_get_cart)

    cart = await cart_service.add_item(conn=None, user_id=1, variant_id=10, quantity=2)
    assert cart.subtotal == 170000
