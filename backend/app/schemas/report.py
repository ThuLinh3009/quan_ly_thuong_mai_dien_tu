from datetime import datetime

from pydantic import BaseModel


class ReportRequest(BaseModel):
    date_from: datetime
    date_to: datetime


class ReportTaskOut(BaseModel):
    task_id: str


class ReportStatusOut(BaseModel):
    task_id: str
    status: str
    ready: bool
