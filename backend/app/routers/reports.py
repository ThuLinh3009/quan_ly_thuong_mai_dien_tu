"""Xuất báo cáo lớn chạy nền qua Celery (Sprint 4, mục 42) — trigger tác vụ rồi
poll trạng thái/tải file, thay vì chặn request chờ render PDF xong."""
from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from app.celery_app import celery_app
from app.core.deps import require_roles
from app.core.errors import NotFoundError, ValidationAppError
from app.schemas.report import ReportRequest, ReportStatusOut, ReportTaskOut

router = APIRouter(prefix="/reports", tags=["reports"])

_staff_admin = require_roles("admin", "staff")


@router.post("/revenue/async", response_model=ReportTaskOut, status_code=202)
async def trigger_revenue_report(
    data: ReportRequest,
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    from app.tasks.report_tasks import generate_revenue_report_pdf

    task = generate_revenue_report_pdf.delay(data.date_from.isoformat(), data.date_to.isoformat())
    return ReportTaskOut(task_id=task.id)


@router.get("/revenue/async/{task_id}", response_model=ReportStatusOut)
async def get_report_status(
    task_id: str,
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    result = AsyncResult(task_id, app=celery_app)
    return ReportStatusOut(task_id=task_id, status=result.status, ready=result.ready())


@router.get("/revenue/async/{task_id}/download", response_class=FileResponse)
async def download_report(
    task_id: str,
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    result = AsyncResult(task_id, app=celery_app)
    if not result.ready():
        raise ValidationAppError(f"Báo cáo task={task_id} chưa xử lý xong (trạng thái: {result.status})")
    if result.failed():
        raise ValidationAppError(f"Báo cáo task={task_id} xử lý thất bại")

    file_path = result.get()
    if not file_path:
        raise NotFoundError(f"Không tìm thấy file báo cáo cho task={task_id}")
    return FileResponse(file_path, media_type="application/pdf", filename=file_path.split("/")[-1].split("\\")[-1])
