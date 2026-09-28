from datetime import datetime, timezone

from app.services import pdf_service


def test_render_invoice_returns_pdf_bytes():
    order = {
        "order_code": "ORD-TEST-1",
        "created_at": "2026-01-01T00:00:00Z",
        "status": "delivered",
        "address": {
            "recipient_name": "Nguyễn Văn A",
            "phone": "0900000000",
            "line1": "123 Đường ABC",
            "ward": None,
            "district": None,
            "province": "Hà Nội",
        },
        "items": [
            {"product_name": "Số Đỏ", "sku": "SACH-001-BM", "quantity": 2, "unit_price": "85000", "line_total": "170000"},
        ],
        "subtotal": "170000",
        "discount_amount": "0",
        "shipping_fee": "30000",
        "total_amount": "200000",
        "payment": {"method": "cod", "status": "pending", "amount": "200000", "paid_at": None},
    }

    pdf_bytes = pdf_service.render_invoice(order)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_render_revenue_report_returns_pdf_bytes():
    rows = [
        {"report_date": "2026-01-01", "orders_count": 5, "revenue": "500000"},
        {"report_date": "2026-01-02", "orders_count": 3, "revenue": "300000"},
    ]
    pdf_bytes = pdf_service.render_revenue_report(
        rows, datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc)
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500
