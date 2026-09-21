from typing import Any

from fastapi import APIRouter, Depends, Query
from psycopg import AsyncConnection

from app.core.database import get_conn
from app.core.deps import require_roles
from app.schemas.common import Page
from app.schemas.import_lot import ImportLotCreate, ImportLotOut
from app.services import import_service

router = APIRouter(prefix="/import-lots", tags=["import-lots"])

_staff_admin = require_roles("admin", "staff")


@router.get("", response_model=Page[ImportLotOut])
async def list_import_lots(
    supplier_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    return await import_service.list_import_lots(conn, supplier_id=supplier_id, limit=limit, offset=offset)


@router.get("/{lot_id}", response_model=ImportLotOut)
async def get_import_lot(
    lot_id: int,
    conn: AsyncConnection = Depends(get_conn),
    _current_user: dict[str, Any] = Depends(_staff_admin),
):
    return await import_service.get_import_lot(conn, lot_id)


@router.post("", response_model=ImportLotOut, status_code=201)
async def create_import_lot(
    data: ImportLotCreate,
    conn: AsyncConnection = Depends(get_conn),
    current_user: dict[str, Any] = Depends(_staff_admin),
):
    return await import_service.create_import_lot(conn, data, current_user)
