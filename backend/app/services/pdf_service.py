"""Xuất PDF hóa đơn/báo cáo bằng ReportLab (Sprint 4 — mục 41).

Chỉ nhận dict thuần (kết quả từ get_order_detail()/get_revenue_report()) để
không phụ thuộc ngược vào router/schema — dễ test độc lập.

Font: các font có sẵn của ReportLab (Helvetica...) không có chữ tiếng Việt có
dấu (hiện thành ô vuông), nên dùng DejaVu Sans đi kèm trong app/assets/fonts
(giấy phép Bitstream Vera, xem LICENSE-DejaVu.txt).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT = "DejaVuSans"
FONT_BOLD = "DejaVuSans-Bold"

if FONT not in pdfmetrics.getRegisteredFontNames():
    pdfmetrics.registerFont(TTFont(FONT, str(_FONT_DIR / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont(FONT_BOLD, str(_FONT_DIR / "DejaVuSans-Bold.ttf")))
    # Cho thẻ <b> trong Paragraph dùng đúng bản đậm của font.
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD, italic=FONT, boldItalic=FONT_BOLD)

_STYLES = getSampleStyleSheet()
_TITLE_STYLE = ParagraphStyle("InvoiceTitle", parent=_STYLES["Title"], fontName=FONT_BOLD, fontSize=16, leading=20)
_HEADING_STYLE = ParagraphStyle("InvoiceHeading", parent=_STYLES["Heading2"], fontName=FONT_BOLD, fontSize=13, leading=16)
_NORMAL_STYLE = ParagraphStyle("InvoiceNormal", parent=_STYLES["Normal"], fontName=FONT, fontSize=10, leading=14)
_CELL_STYLE = ParagraphStyle("InvoiceCell", parent=_NORMAL_STYLE, fontSize=9, leading=11)
_CELL_RIGHT = ParagraphStyle("InvoiceCellRight", parent=_CELL_STYLE, alignment=TA_RIGHT)

# Khổ A4 (21 cm) trừ lề mặc định 2 x 2,54 cm -> vùng in rộng ~15,9 cm.
_CONTENT_WIDTH = A4[0] - 2 * 2.54 * cm
_VN_TZ = timezone(timedelta(hours=7))

ORDER_STATUS_LABELS = {
    "pending": "Chờ xác nhận",
    "confirmed": "Đã xác nhận",
    "shipping": "Đang giao hàng",
    "delivered": "Đã giao hàng",
    "cancelled": "Đã hủy",
}
PAYMENT_METHOD_LABELS = {
    "cod": "Thanh toán khi nhận hàng (COD)",
    "simulated_gateway": "Thanh toán online",
}
PAYMENT_STATUS_LABELS = {
    "pending": "Chưa thanh toán",
    "success": "Đã thanh toán",
    "failed": "Thanh toán thất bại",
    "refunded": "Đã hoàn tiền",
}


def _money(value: Any) -> str:
    amount = Decimal(str(value))
    return f"{amount:,.0f} VND"


def _text(value: Any) -> str:
    """Escape &, <, > để chữ từ DB không làm hỏng markup của Paragraph."""
    return escape("" if value is None else str(value))


def _datetime(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(_VN_TZ)
        return f"{value:%d/%m/%Y %H:%M}"
    return _text(value)


def _label(mapping: dict[str, str], value: Any) -> str:
    return mapping.get(str(value), str(value))


def _base_table_style(header_bg: str = "#1f2937") -> list[tuple]:
    return [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]


def render_invoice(order: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                            title=f"Hóa đơn {order['order_code']}", author="TBookStore")
    story: list[Any] = [
        Paragraph("TBookStore — Hóa đơn bán hàng", _TITLE_STYLE),
        Spacer(1, 0.5 * cm),
        Paragraph(f"Mã đơn hàng: <b>{_text(order['order_code'])}</b>", _NORMAL_STYLE),
        Paragraph(f"Ngày đặt: {_datetime(order['created_at'])}", _NORMAL_STYLE),
        Paragraph(f"Trạng thái: {_label(ORDER_STATUS_LABELS, order['status'])}", _NORMAL_STYLE),
    ]

    address = order.get("address")
    if address:
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph("Địa chỉ giao hàng:", _HEADING_STYLE))
        story.append(Paragraph(f"{_text(address['recipient_name'])} — {_text(address['phone'])}", _NORMAL_STYLE))
        line_parts = [address.get("line1"), address.get("ward"), address.get("district"), address.get("province")]
        story.append(Paragraph(_text(", ".join(p for p in line_parts if p)), _NORMAL_STYLE))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph("Chi tiết sản phẩm:", _HEADING_STYLE))

    # Tên sách / SKU dùng Paragraph để tự xuống dòng trong ô thay vì tràn sang cột bên.
    table_data: list[list[Any]] = [["Sản phẩm", "SKU", "SL", "Đơn giá", "Thành tiền"]]
    for item in order.get("items") or []:
        table_data.append([
            Paragraph(_text(item["product_name"]), _CELL_STYLE),
            Paragraph(_text(item["sku"]), _CELL_STYLE),
            str(item["quantity"]),
            _money(item["unit_price"]),
            _money(item["line_total"]),
        ])

    col_widths = [6.4 * cm, 3.2 * cm, 1.1 * cm, 2.6 * cm, 2.6 * cm]   # tổng 15,9 cm
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle(_base_table_style() + [("ALIGN", (2, 0), (-1, -1), "RIGHT")]))
    story.append(table)

    story.append(Spacer(1, 0.5 * cm))
    summary_data = [
        ["Tạm tính", _money(order["subtotal"])],
        ["Giảm giá", _money(order["discount_amount"])],
        ["Phí vận chuyển", _money(order["shipping_fee"])],
        ["Tổng cộng", _money(order["total_amount"])],
    ]
    summary_table = Table(summary_data, colWidths=[_CONTENT_WIDTH - 3.2 * cm, 3.2 * cm])
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.black),
            ]
        )
    )
    story.append(summary_table)

    payment = order.get("payment")
    if payment:
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(f"Phương thức thanh toán: {_label(PAYMENT_METHOD_LABELS, payment['method'])}", _NORMAL_STYLE))
        story.append(
            Paragraph(
                f"Tình trạng thanh toán: {_label(PAYMENT_STATUS_LABELS, payment['status'])} ({_money(payment['amount'])})",
                _NORMAL_STYLE,
            )
        )

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph("Cảm ơn quý khách đã mua sách tại TBookStore!", _NORMAL_STYLE))

    doc.build(story)
    return buffer.getvalue()


def render_revenue_report(rows: list[dict[str, Any]], date_from: datetime, date_to: datetime) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm,
                            title="Báo cáo doanh thu", author="TBookStore")
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
        report_date = row["report_date"]
        if hasattr(report_date, "strftime"):
            report_date = report_date.strftime("%d/%m/%Y")
        table_data.append([str(report_date), str(row["orders_count"]), _money(row["revenue"])])
        total_orders += row["orders_count"]
        total_revenue += Decimal(str(row["revenue"]))
    table_data.append(["Tổng cộng", str(total_orders), _money(total_revenue)])

    table = Table(table_data, colWidths=[5.9 * cm, 4.5 * cm, 5.5 * cm], repeatRows=1)
    table.setStyle(
        TableStyle(
            _base_table_style()
            + [
                ("FONTNAME", (0, -1), (-1, -1), FONT_BOLD),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    story.append(table)

    doc.build(story)
    return buffer.getvalue()
