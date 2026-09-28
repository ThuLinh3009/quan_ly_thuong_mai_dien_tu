from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

OrderStatus = Literal["pending", "confirmed", "shipping", "delivered", "cancelled"]
PaymentMethod = Literal["cod", "simulated_gateway"]
PaymentStatus = Literal["pending", "success", "failed", "refunded"]


class CheckoutRequest(BaseModel):
    address_id: int
    payment_method: PaymentMethod
    promotion_code: str | None = Field(default=None, max_length=50)


class CheckoutPreviewOut(BaseModel):
    subtotal: Decimal
    discount_amount: Decimal
    shipping_fee: Decimal
    total_amount: Decimal


class OrderAddressOut(BaseModel):
    recipient_name: str
    phone: str
    line1: str
    ward: str | None = None
    district: str | None = None
    province: str


class OrderItemOut(BaseModel):
    id: int
    product_variant_id: int
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class OrderPaymentOut(BaseModel):
    method: PaymentMethod
    status: PaymentStatus
    amount: Decimal
    paid_at: datetime | None = None


class OrderStatusHistoryOut(BaseModel):
    from_status: OrderStatus | None = None
    to_status: OrderStatus
    note: str | None = None
    created_at: datetime


class OrderDetailOut(BaseModel):
    id: int
    order_code: str
    user_id: int
    status: OrderStatus
    subtotal: Decimal
    discount_amount: Decimal
    shipping_fee: Decimal
    total_amount: Decimal
    created_at: datetime
    address: OrderAddressOut | None = None
    items: list[OrderItemOut] = []
    payment: OrderPaymentOut | None = None
    status_history: list[OrderStatusHistoryOut] = []


class OrderListItemOut(BaseModel):
    id: int
    order_code: str
    status: OrderStatus
    subtotal: Decimal
    discount_amount: Decimal
    shipping_fee: Decimal
    total_amount: Decimal
    created_at: datetime


class OrderAdminListItemOut(BaseModel):
    id: int
    order_code: str
    status: OrderStatus
    user_id: int
    customer_name: str
    total_amount: Decimal
    created_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: str | None = Field(default=None, max_length=500)


class PaymentSimulateRequest(BaseModel):
    success: bool


class PaymentSimulateOut(BaseModel):
    order_id: int
    order_status: OrderStatus
    payment_status: PaymentStatus
    transaction_ref: str | None = None
