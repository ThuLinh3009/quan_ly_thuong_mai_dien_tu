from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import database
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.redis import close_redis, open_redis
from app.routers import auth, categories, employees, health, import_lots, products, suppliers


@asynccontextmanager
async def lifespan(_: FastAPI):
    await database.open_pool()
    await open_redis()
    yield
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

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(suppliers.router)
app.include_router(products.router)
app.include_router(employees.router)
app.include_router(import_lots.router)
