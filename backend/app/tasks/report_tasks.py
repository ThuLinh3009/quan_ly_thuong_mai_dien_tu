"""Xuất báo cáo doanh thu lớn chạy nền qua Celery (Sprint 4, mục 42) — báo cáo
khoảng thời gian dài có thể tốn vài giây tổng hợp + render PDF, không nên chặn
request API.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import structlog

from app.celery_app import celery_app
from app.core.database import get_sync_connection
from app.services import pdf_service

logger = structlog.get_logger(__name__)

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


@celery_app.task(name="generate_revenue_report_pdf")
def generate_revenue_report_pdf(date_from_iso: str, date_to_iso: str) -> str:
    date_from = datetime.fromisoformat(date_from_iso)
    date_to = datetime.fromisoformat(date_to_iso)

    with get_sync_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM get_revenue_report(%s, %s)", (date_from, date_to)
        ).fetchall()

    pdf_bytes = pdf_service.render_revenue_report(rows, date_from, date_to)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"revenue-report-{date_from:%Y%m%d}-{date_to:%Y%m%d}-{datetime.now():%H%M%S}.pdf"
    file_path = REPORTS_DIR / filename
    file_path.write_bytes(pdf_bytes)

    logger.info("generate_revenue_report_pdf_done", file=str(file_path))
    return str(file_path)
