import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.core import database
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.redis import close_redis, open_redis
from app.routers import auth, categories, employees, health, import_lots, products, suppliers

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.open_pool()
    await open_redis()
    logger.info("app_startup")
    yield
    logger.info("app_shutdown")
    await close_redis()
    await database.close_pool()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Ghi lại mọi request (method/path/status/thời gian xử lý) vào logs/app.log
    — hữu ích để xem bối cảnh xung quanh 1 lỗi khi tra logs/error.log."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    log = logger.warning if response.status_code >= 500 else logger.info
    log(
        "request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response


register_exception_handlers(app)

# --- API versioning ---------------------------------------------------------
# /health không versioning (health check là hạ tầng, quy ước chung không gắn
# theo phiên bản API — load balancer/monitoring luôn gọi 1 đường dẫn cố định).
app.include_router(health.router)

API_V1_PREFIX = "/api/v1"
_versioned_routers = (auth.router, categories.router, suppliers.router, products.router, employees.router, import_lots.router)


def _legacy_operation_id(route: APIRoute) -> str:
    # Tránh trùng operationId với route /api/v1 tương ứng khi generate OpenAPI schema
    return f"legacy_{route.name}"


for _router in _versioned_routers:
    # Đường dẫn chuẩn từ giờ trở đi: /api/v1/...
    app.include_router(_router, prefix=API_V1_PREFIX)
    # Giữ nguyên đường dẫn cũ (không prefix) chạy song song để không phá vỡ
    # client/Postman collection đã tích hợp trước khi có versioning. Đánh dấu
    # deprecated=True để Swagger hiển thị rõ đây là đường cũ, nên chuyển sang
    # /api/v1/... — khi có breaking change thật (v2) thì bỏ nhánh legacy này.
    app.include_router(_router, deprecated=True, generate_unique_id_function=_legacy_operation_id)
