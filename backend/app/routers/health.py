from fastapi import APIRouter, Depends

from app.core.database import get_conn

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(conn=Depends(get_conn)):
    cur = await conn.execute("SELECT 1 AS ok")
    row = await cur.fetchone()
    return {"status": "ok", "db": row["ok"]}
