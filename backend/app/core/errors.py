"""Exception nghiệp vụ dùng chung + đăng ký exception handler cho FastAPI.

Mọi exception (kể cả lỗi nghiệp vụ 4xx và lỗi hệ thống 500 chưa lường trước)
đều đi qua đây để: (1) luôn trả JSON {"detail": ...} nhất quán cho client,
(2) được ghi log — lỗi hệ thống ghi vào logs/error.log kèm traceback đầy đủ
để tiện tra cứu khi có sự cố.
"""
from __future__ import annotations

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class ValidationAppError(AppError):
    status_code = 422


class ForbiddenError(AppError):
    status_code = 403


class UnauthorizedError(AppError):
    status_code = 401


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        # Lỗi nghiệp vụ (400/401/403/404/409/422...) là chuyện bình thường của API,
        # log ở mức warning, không cần traceback, chỉ để tiện audit khi cần tra lại.
        logger.warning(
            "app_error",
            method=request.method,
            path=request.url.path,
            status_code=exc.status_code,
            detail=exc.detail,
        )
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Lỗi hệ thống thật sự (bug, DB down, ...) -> ghi đầy đủ traceback vào
        # logs/error.log để dev tra cứu, trả về client thông điệp chung chung
        # (không lộ chi tiết nội bộ/stack trace ra ngoài).
        logger.error(
            "unhandled_exception",
            method=request.method,
            path=request.url.path,
            exc_info=exc,
        )
        return JSONResponse(status_code=500, content={"detail": "Đã có lỗi hệ thống, vui lòng thử lại sau."})
