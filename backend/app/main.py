import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

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

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(employees.router)
app.include_router(import_lots.router)
