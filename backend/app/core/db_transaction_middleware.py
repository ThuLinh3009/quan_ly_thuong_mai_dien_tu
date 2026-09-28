"""ASGI middleware quản lý 1 connection/transaction riêng cho mỗi HTTP
request, commit/rollback TRƯỚC KHI response được gửi thật ra client.

Lý do cần middleware này thay vì để `Depends(get_conn)` (dependency-with-yield)
tự commit: FastAPI chỉ chạy code sau `yield` của 1 dependency SAU KHI
`await response(scope, receive, send)` đã chạy xong (xem
fastapi/routing.py::get_request_handler — AsyncExitStack bọc dependency chỉ
đóng SAU dòng gửi response). Nghĩa là nếu để get_conn() tự
commit trong lúc dọn dẹp, việc commit luôn xảy ra SAU KHI client đã nhận được
response. Với 2 request liên tiếp rất sát nhau từ cùng 1 client (vd: thêm sách
vào giỏ hàng rồi bấm checkout ngay), request sau hoàn toàn có thể bắt đầu và
đọc DB TRƯỚC KHI request trước kịp commit — gây lỗi ngẫu nhiên kiểu "giỏ hàng
trống" dù request thêm giỏ hàng trước đó đã trả về 200 OK. Bug này được phát
hiện khi test luồng checkout thực tế (rapid add-to-cart -> checkout).

Middleware này KHÔNG dùng BaseHTTPMiddleware (chạy app trong background task
qua stream, không đảm bảo thứ tự commit-trước-khi-gửi) mà tự buffer message
gửi đi: chạy toàn bộ request, đợi commit/rollback xong (dựa theo status code
cuối cùng) rồi mới forward các message đã buffer ra send() thật.
"""
from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import database

# /health/db KHONG duoc mien tru: no cung dung Depends(get_conn) nen van can
# scope["db_conn"] duoc middleware nay mo san.
_EXEMPT_PATHS = {"/health"}


class DBTransactionMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in _EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        assert database.pool is not None, "Database pool chưa được khởi tạo"
        async with database.pool.connection() as conn:
            scope["db_conn"] = conn
            messages: list[Message] = []

            async def buffering_send(message: Message) -> None:
                messages.append(message)

            await self.app(scope, receive, buffering_send)

            status = 200
            for message in messages:
                if message["type"] == "http.response.start":
                    status = message["status"]
                    break

            # Loi nghiep vu (AppError -> 4xx) da duoc rout/xu ly THANH RESPONSE
            # o tang duoi (wrap_app_handling_exceptions trong route), khong con
            # la exception Python nua khi toi day — phai tu kiem tra status
            # code de quyet dinh commit hay rollback, khong the dua vao try/except.
            if status >= 400:
                await conn.rollback()
            else:
                await conn.commit()

            for message in messages:
                await send(message)
