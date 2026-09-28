"""Gửi mail nền qua Celery (Sprint 4, mục 42) — tách khỏi request checkout để
không làm chậm response API khi SMTP chậm/lỗi.
"""
from __future__ import annotations

import smtplib
import structlog
from email.message import EmailMessage

from app.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import get_sync_connection

logger = structlog.get_logger(__name__)


def _send_email(*, to_email: str, subject: str, body: str) -> None:
    settings = get_settings()
    message = EmailMessage()
    message["From"] = "no-reply@tbookstore.vn"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.send_message(message)


@celery_app.task(name="send_order_confirmation_email", bind=True, max_retries=3, default_retry_delay=30)
def send_order_confirmation_email(self, order_id: int) -> None:
    with get_sync_connection() as conn:
        order = conn.execute("SELECT * FROM get_order_detail(%s)", (order_id,)).fetchone()
        if order is None:
            logger.warning("send_order_confirmation_email_order_not_found", order_id=order_id)
            return

        user = conn.execute("SELECT * FROM get_user_by_id(%s)", (order["user_id"],)).fetchone()
        if user is None:
            logger.warning("send_order_confirmation_email_user_not_found", order_id=order_id)
            return

    body = (
        f"Chào {user['full_name']},\n\n"
        f"Đơn hàng {order['order_code']} của bạn đã được ghi nhận.\n"
        f"Tổng tiền: {order['total_amount']:,.0f} VND\n"
        f"Trạng thái: {order['status']}\n\n"
        "Cảm ơn bạn đã mua sắm tại TBookStore."
    )

    try:
        _send_email(to_email=user["email"], subject=f"Xác nhận đơn hàng {order['order_code']}", body=body)
    except Exception as exc:  # noqa: BLE001 - SMTP tạm thời lỗi thì retry, không làm crash worker
        logger.warning("send_order_confirmation_email_failed", order_id=order_id, error=str(exc))
        raise self.retry(exc=exc) from exc
