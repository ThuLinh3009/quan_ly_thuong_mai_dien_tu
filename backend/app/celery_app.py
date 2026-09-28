"""Celery app — hàng đợi tác vụ nền cho gửi mail xác nhận đơn hàng và xuất
báo cáo doanh thu lớn (Sprint 4, mục 42), dùng chung Redis với cache/session.

Chạy worker: celery -A app.celery_app worker --loglevel=info
(Windows: thêm --pool=solo vì Celery prefork không chạy được trên Windows.)
"""
from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "tbookstore",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.email_tasks", "app.tasks.report_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    task_track_started=True,
    result_expires=3600,
)
