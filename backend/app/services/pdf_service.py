"""Xuất PDF hóa đơn/báo cáo bằng ReportLab (Sprint 4 — mục 41).

Chỉ nhận dict thuần (kết quả từ get_order_detail()/get_revenue_report()) để
không phụ thuộc ngược vào router/schema — dễ test độc lập.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_STYLES = getSampleStyleSheet()
_TITLE_STYLE = ParagraphStyle("InvoiceTitle", parent=_STYLES["Title"], fontSize=16)
_HEADING_STYLE = _STYLES["Heading2"]
_NORMAL_STYLE = _STYLES["Normal"]


def _money(value: Any) -> str:
    amount = Decimal(str(value))
    return f"{amount:,.0f} VND"


def render_invoice(order: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story: list[Any] = [
        Paragraph("TBookStore — Hóa đơn bán hàng", _TITLE_STYLE),
        Spacer(1, 0.5 * cm),
        Paragraph(f"Mã đơn hàng: <b>{order['order_code']}</b>", _NORMAL_STYLE),
        Paragraph(f"Ngày tạo: {order['created_at']}", _NORMAL_STYLE),
        Paragraph(f"Trạng thái: {order['status']}", _NORMAL_STYLE),
    ]

    address = order.get("address")
    if address:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Địa chỉ giao hàng:", _HEADING_STYLE))
        story.append(Paragraph(f"{address['recipient_name']} — {address['phone']}", _NORMAL_STYLE))
        line_parts = [address.get("line1"), address.get("ward"), address.get("district"), address.get("province")]
        story.append(Paragraph(", ".join(p for p in line_parts if p), _NORMAL_STYLE))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Chi tiết sản phẩm:", _HEADING_STYLE))

    table_data = [["Sản phẩm", "SKU", "SL", "Đơn giá", "Thành tiền"]]
    for item in order.get("items") or []:
        table_data.append(
            [item["product_name"], item["sku"], str(item["quantity"]), _money(item["unit_price"]), _money(item["line_total"])]
        )

    table = Table(table_data, colWidths=[6 * cm, 3 * cm, 1.5 * cm, 3 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(table)

    story.append(Spacer(1, 0.5 * cm))
    summary_data = [
        ["Tạm tính", _money(order["subtotal"])],
        ["Giảm giá", _money(order["discount_amount"])],
        ["Phí vận chuyển", _money(order["shipping_fee"])],
        ["Tổng cộng", _money(order["total_amount"])],
    ]
    summary_table = Table(summary_data, colWidths=[13.5 * cm, 3 * cm])
    summary_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black),
            ]
        )
    )
    story.append(summary_table)

    payment = order.get("payment")
    if payment:
        story.append(Spacer(1, 0.5 * cm))
        story.append(
            Paragraph(
                f"Thanh toán: {payment['method']} — {payment['status']} ({_money(payment['amount'])})",
                _NORMAL_STYLE,
            )
        )

    doc.build(story)
    return buffer.getvalue()


def render_revenue_report(rows: list[dict[str, Any]], date_from: datetime, date_to: datetime) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story: list[Any] = [
        Paragraph("TBookStore — Báo cáo doanh thu", _TITLE_STYLE),
        Spacer(1, 0.3 * cm),
        Paragraph(f"Từ ngày {date_from:%d/%m/%Y} đến ngày {date_to:%d/%m/%Y}", _NORMAL_STYLE),
        Spacer(1, 0.5 * cm),
    ]

    table_data = [["Ngày", "Số đơn hàng", "Doanh thu"]]
    total_orders = 0
    total_revenue = Decimal("0")
    for row in rows:
        table_data.append([str(row["report_date"]), str(row["orders_count"]), _money(row["revenue"])])
        total_orders += row["orders_count"]
        total_revenue += Decimal(str(row["revenue"]))
    table_data.append(["Tổng cộng", str(total_orders), _money(total_revenue)])

    table = Table(table_data, colWidths=[6 * cm, 5 * cm, 5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(table)

    doc.build(story)
    return buffer.getvalue()
