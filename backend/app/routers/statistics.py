from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import require_roles
from app.schemas.statistics import DashboardSummaryOut, RevenueReportItemOut, TopSellingBookOut
from app.services import pdf_service, statistics_service

router = APIRouter(prefix="/statistics", tags=["statistics"])

_staff_admin = require_roles("admin", "staff")


@router.get("/top-selling-books", response_model=list[TopSellingBookOut])
async def top_selling_books(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    limit: int = Query(default=10, ge=1, le=100),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    return await statistics_service.top_selling_books(conn, date_from=date_from, date_to=date_to, limit=limit)


@router.get("/revenue-report", response_model=list[RevenueReportItemOut])
async def revenue_report(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    return await statistics_service.revenue_report(conn, date_from=date_from, date_to=date_to)


@router.get("/revenue-report/pdf", response_class=Response)
async def revenue_report_pdf(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    rows = await statistics_service.revenue_report(conn, date_from=date_from, date_to=date_to)
    pdf_bytes = pdf_service.render_revenue_report(rows, date_from, date_to)
    filename = f"revenue-report-{date_from:%Y%m%d}-{date_to:%Y%m%d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/dashboard", response_model=DashboardSummaryOut)
async def dashboard_summary(
    date_from: datetime = Query(...),
    date_to: datetime = Query(...),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    return await statistics_service.dashboard_summary(conn, date_from=date_from, date_to=date_to)
