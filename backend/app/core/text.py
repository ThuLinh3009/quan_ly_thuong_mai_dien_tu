"""Tiện ích xử lý chuỗi dùng chung (sinh slug từ tên tiếng Việt có dấu)."""
from __future__ import annotations

import re
import unicodedata


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text or "item"
