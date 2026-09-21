from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.core.audit import record_audit
from app.core.cache import CATEGORY_PREFIX, get_json, invalidate_prefix, set_json
from app.core.errors import ConflictError, NotFoundError
from app.core.text import slugify
from app.repositories import category_repo
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.common import Page


async def create_category(conn: AsyncConnection, data: CategoryCreate, current_user: dict[str, Any]) -> dict[str, Any]:
    slug = slugify(data.slug or data.name)
    if await category_repo.get_by_slug(conn, slug) is not None:
        raise ConflictError(f"Slug '{slug}' đã tồn tại")
    if data.parent_id is not None and await category_repo.get_by_id(conn, data.parent_id) is None:
        raise NotFoundError(f"Không tìm thấy category cha id={data.parent_id}")

    category = await category_repo.create(
        conn, name=data.name, slug=slug, parent_id=data.parent_id, is_active=data.is_active
    )
    await record_audit(
        conn,
        user_id=current_user["id"],
        action="create",
        entity_type="category",
        entity_id=category["id"],
        new_value=category,
    )
    await invalidate_prefix(CATEGORY_PREFIX)
    return category


async def list_categories(
    conn: AsyncConnection,
    *,
    keyword: str | None,
    parent_id: int | None,
    is_active: bool | None,
    limit: int,
    offset: int,
) -> Page:
    cache_key = f"{CATEGORY_PREFIX}:list:{keyword}:{parent_id}:{is_active}:{limit}:{offset}"
    cached = await get_json(cache_key)
    if cached is not None:
        return Page(**cached)

    rows, total = await category_repo.list_categories(
        conn, keyword=keyword, parent_id=parent_id, is_active=is_active, limit=limit, offset=offset
    )
    # loại field total_count (chỉ dùng nội bộ để tính total) khỏi từng item trả về
    items = [{k: v for k, v in row.items() if k != "total_count"} for row in rows]
    page = Page(items=items, total=total, limit=limit, offset=offset)
    await set_json(cache_key, page.model_dump())
    return page


async def get_category(conn: AsyncConnection, category_id: int) -> dict[str, Any]:
    category = await category_repo.get_by_id(conn, category_id)
    if category is None:
        raise NotFoundError(f"Không tìm thấy category id={category_id}")
    return category


async def update_category(
    conn: AsyncConnection, category_id: int, data: CategoryUpdate, current_user: dict[str, Any]
) -> dict[str, Any]:
    old = await get_category(conn, category_id)

    fields: dict[str, Any] = {}
    if data.name is not None:
        fields["name"] = data.name
    if data.slug is not None:
        fields["slug"] = slugify(data.slug)
    elif data.name is not None:
        fields["slug"] = slugify(data.name)
    if data.parent_id is not None:
        if data.parent_id == category_id:
            raise ConflictError("Category không thể là cha của chính nó")
        if await category_repo.get_by_id(conn, data.parent_id) is None:
            raise NotFoundError(f"Không tìm thấy category cha id={data.parent_id}")
        fields["parent_id"] = data.parent_id
    if data.is_active is not None:
        fields["is_active"] = data.is_active

    if "slug" in fields and fields["slug"] != old["slug"]:
        existing = await category_repo.get_by_slug(conn, fields["slug"])
        if existing is not None and existing["id"] != category_id:
            raise ConflictError(f"Slug '{fields['slug']}' đã tồn tại")

    updated = await category_repo.update(conn, category_id, fields)
    assert updated is not None
    await record_audit(
        conn,
        user_id=current_user["id"],
        action="update",
        entity_type="category",
        entity_id=category_id,
        old_value=old,
        new_value=updated,
    )
    await invalidate_prefix(CATEGORY_PREFIX)
    return updated


async def delete_category(conn: AsyncConnection, category_id: int, current_user: dict[str, Any]) -> None:
    old = await get_category(conn, category_id)
    deleted = await category_repo.soft_delete(conn, category_id)
    if not deleted:
        raise NotFoundError(f"Không tìm thấy category id={category_id}")
    await record_audit(
        conn,
        user_id=current_user["id"],
        action="delete",
        entity_type="category",
        entity_id=category_id,
        old_value=old,
    )
    await invalidate_prefix(CATEGORY_PREFIX)
