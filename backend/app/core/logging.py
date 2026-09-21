"""Cấu hình logging tập trung: vừa in ra stdout (xem qua `docker compose logs`),
vừa ghi ra file có xoay vòng để quản lý lỗi mà không cần đào log của Docker.

  logs/app.log    - toàn bộ log (INFO trở lên), JSON mỗi dòng
  logs/error.log  - chỉ ERROR trở lên (kèm traceback đầy đủ), dễ soi khi có sự cố

Dùng structlog làm lớp API ghi log (`structlog.get_logger(...)`) nhưng render ra
qua handler của `logging` chuẩn, nên log của uvicorn/fastapi cũng tự động đi qua
cùng 2 file trên thay vì chỉ nằm rải rác ở console.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

import structlog

# app/core/logging.py -> app/core -> app -> root (repo backend/ khi chạy local,
# hoặc /code khi chạy trong container) -> logs/
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"

_MAX_BYTES = 10 * 1024 * 1024  # 10MB mỗi file, giữ 5 bản cũ -> tối đa ~50MB/loại
_BACKUP_COUNT = 5

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    _configured = True

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=False),
        foreign_pre_chain=shared_processors,
    )
    file_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(ensure_ascii=False),
        foreign_pre_chain=shared_processors,
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)

    app_file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "app.log", maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    app_file_handler.setFormatter(file_formatter)

    error_file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "error.log", maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8"
    )
    error_file_handler.setFormatter(file_formatter)
    error_file_handler.setLevel(logging.ERROR)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [console_handler, app_file_handler, error_file_handler]

    # Log của uvicorn (access log, lỗi khởi động...) đi qua cùng handler ở trên
    # thay vì tự in riêng theo format mặc định của nó.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers = []
        uv_logger.propagate = True
