"""Sinh dữ liệu mẫu số lượng lớn (Sprint 4, mục 52 — mục tiêu ≥2.000 bản ghi)
để có đủ dữ liệu demo cho tìm kiếm/phân trang/thống kê/báo cáo.

Idempotent: kiểm tra số sản phẩm hiện có, chỉ sinh thêm phần còn thiếu để đạt
--products (mặc định 2000); chạy lại nhiều lần không tạo trùng vì SKU sinh
tuần tự dựa trên id lớn nhất hiện có.

Dùng: python -m app.scripts.seed_bulk [--products 2000] [--customers 40] [--orders 150]
Lưu ý: script insert thẳng bằng SQL (không qua function nghiệp vụ) vì đây là
script quản trị sinh dữ liệu hàng loạt, không phải luồng nghiệp vụ của app —
insert hàng loạt qua psycopg.Cursor.executemany() cho nhanh, khác với
repositories/*.py (luôn gọi function DB) dùng trong request API.
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import datetime, timedelta, timezone

import psycopg

from app.core.config import get_settings
from app.core.security import hash_password

CATEGORIES = [
    ("Văn học", "van-hoc"),
    ("Kinh tế", "kinh-te"),
    ("Thiếu nhi", "thieu-nhi"),
    ("Kỹ năng sống", "ky-nang-song"),
    ("Trinh thám", "trinh-tham"),
    ("Khoa học viễn tưởng", "khoa-hoc-vien-tuong"),
    ("Lịch sử", "lich-su"),
    ("Tâm lý học", "tam-ly-hoc"),
    ("Ngoại ngữ", "ngoai-ngu"),
    ("Giáo trình", "giao-trinh"),
    ("Truyện tranh", "truyen-tranh"),
    ("Tôn giáo - Triết học", "ton-giao-triet-hoc"),
]

SUPPLIERS = [
    ("NXB Kim Đồng", "0243100001", "lienhe@kimdong.vn", "55 Quang Trung, Hà Nội"),
    ("NXB Trẻ", "0283100002", "lienhe@nxbtre.com.vn", "161B Lý Chính Thắng, TP.HCM"),
    ("NXB Văn Học", "0243100003", "lienhe@nxbvanhoc.vn", "18 Nguyễn Trường Tộ, Hà Nội"),
    ("Nhã Nam", "0243100004", "lienhe@nhanam.vn", "59 Đỗ Quang, Hà Nội"),
    ("First News - Trí Việt", "0283100005", "lienhe@firstnews.com.vn", "11H Nguyễn Thị Minh Khai, TP.HCM"),
    ("Alpha Books", "0243100006", "lienhe@alphabooks.vn", "176 Thái Hà, Hà Nội"),
]

AUTHORS = [
    "Nguyễn Nhật Ánh", "Tô Hoài", "Vũ Trọng Phụng", "Nam Cao", "Ngô Tất Tố",
    "Paulo Coelho", "Haruki Murakami", "Dale Carnegie", "Yuval Noah Harari",
    "Agatha Christie", "Stephen King", "J.K. Rowling", "Nguyễn Ngọc Tư",
    "Marc Levy", "Higashino Keigo", "Napoleon Hill", "Robin Sharma",
    "Nguyễn Nhật Minh", "Trang Hạ", "Đặng Thùy Trâm",
]

TITLE_PART_A = [
    "Bí Mật", "Hành Trình", "Giấc Mơ", "Ánh Sáng", "Con Đường", "Lời Hứa",
    "Ngày Mai", "Mùa Xuân", "Câu Chuyện", "Thế Giới", "Ký Ức", "Hơi Thở",
    "Bến Bờ", "Cánh Cửa", "Vết Sẹo", "Dòng Sông", "Tiếng Vọng", "Nốt Nhạc",
    "Bầu Trời", "Ngọn Lửa",
]
TITLE_PART_B = [
    "Của Chúng Ta", "Không Tên", "Cuối Cùng", "Đầu Tiên", "Mùa Hạ", "Tuổi Trẻ",
    "Hạnh Phúc", "Yêu Thương", "Sau Cơn Mưa", "Nơi Xa", "Không Ngủ", "Thầm Lặng",
    "Trong Đêm", "Giữa Phố", "Đã Mất", "Chưa Kể", "Bên Kia", "Không Lời",
    "Xa Xôi", "Trở Về",
]

VARIANT_NAMES = ["Bìa mềm", "Bìa cứng", "Tái bản"]
ORDER_STATUSES = ["pending", "confirmed", "shipping", "delivered", "delivered", "delivered", "cancelled"]
PAYMENT_METHODS = ["cod", "simulated_gateway"]


def _rand_price() -> int:
    return random.choice([45000, 59000, 68000, 75000, 89000, 99000, 120000, 145000, 165000, 199000])


def seed_categories(conn: psycopg.Connection) -> dict[str, int]:
    ids: dict[str, int] = {}
    for name, slug in CATEGORIES:
        row = conn.execute(
            """
            INSERT INTO categories (name, slug) VALUES (%s, %s)
            ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            (name, slug),
        ).fetchone()
        ids[slug] = row[0]
    return ids


def seed_suppliers(conn: psycopg.Connection) -> list[int]:
    ids = []
    for name, phone, email, address in SUPPLIERS:
        row = conn.execute(
            """
            INSERT INTO suppliers (name, contact_phone, email, address)
            SELECT %s, %s, %s, %s
            WHERE NOT EXISTS (SELECT 1 FROM suppliers WHERE name = %s)
            RETURNING id
            """,
            (name, phone, email, address, name),
        ).fetchone()
        if row is None:
            row = conn.execute("SELECT id FROM suppliers WHERE name = %s", (name,)).fetchone()
        ids.append(row[0])
    return ids


def seed_products(conn: psycopg.Connection, category_ids: list[int], target: int) -> None:
    existing = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if existing >= target:
        print(f"products: đã có {existing} >= {target}, bỏ qua")
        return

    next_seq = conn.execute(
        "SELECT COALESCE(MAX(NULLIF(regexp_replace(sku, '\\D', '', 'g'), '')::BIGINT), 0) FROM products WHERE sku LIKE 'SEED-%%'"
    ).fetchone()[0]
    next_seq = int(next_seq) + 1

    to_create = target - existing
    print(f"products: sinh thêm {to_create} sản phẩm (bắt đầu từ SEED-{next_seq:06d})")

    used_titles: set[str] = set()
    batch = 0
    for i in range(to_create):
        seq = next_seq + i
        sku = f"SEED-{seq:06d}"

        title = f"{random.choice(TITLE_PART_A)} {random.choice(TITLE_PART_B)}"
        if title in used_titles:
            title = f"{title} {seq}"
        used_titles.add(title)

        slug = f"{sku.lower()}-{title.lower()}"
        slug = "".join(ch if ch.isalnum() else "-" for ch in slug)
        while "--" in slug:
            slug = slug.replace("--", "-")

        category_id = random.choice(category_ids)
        author = random.choice(AUTHORS)
        base_price = _rand_price()

        row = conn.execute(
            """
            INSERT INTO products (category_id, sku, name, slug, author, publisher, base_price, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (category_id, sku, title, slug, author, random.choice(["NXB Kim Đồng", "NXB Trẻ", "Nhã Nam"]),
             base_price, f"{title} — tiểu thuyết của {author}."),
        ).fetchone()
        product_id = row[0]

        variant_count = random.choice([1, 1, 2])
        for v in range(variant_count):
            variant_name = VARIANT_NAMES[v % len(VARIANT_NAMES)]
            price_adjustment = 0 if v == 0 else random.choice([15000, 20000, 30000])
            variant_row = conn.execute(
                """
                INSERT INTO product_variants (product_id, variant_name, sku, price_adjustment)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (product_id, variant_name, f"{sku}-{v + 1}", price_adjustment),
            ).fetchone()
            conn.execute(
                "INSERT INTO inventories (product_variant_id, quantity_on_hand, reorder_level) VALUES (%s, %s, %s)",
                (variant_row[0], random.randint(20, 300), 10),
            )

        batch += 1
        if batch % 200 == 0:
            conn.commit()
            print(f"  ... đã tạo {batch}/{to_create}")

    conn.commit()
    print(f"products: hoàn tất, tổng cộng {existing + to_create}")


def seed_customers(conn: psycopg.Connection, target: int) -> list[int]:
    existing_ids = [
        r[0] for r in conn.execute("SELECT id FROM users WHERE role = 'customer'").fetchall()
    ]
    if len(existing_ids) >= target:
        print(f"customers: đã có {len(existing_ids)} >= {target}, bỏ qua tạo mới")
        return existing_ids

    to_create = target - len(existing_ids)
    print(f"customers: sinh thêm {to_create} khách hàng")
    password_hash = hash_password("Customer@123")
    new_ids = []
    for i in range(to_create):
        idx = len(existing_ids) + i + 1
        email = f"seed.customer{idx}@tbookstore.vn"
        row = conn.execute(
            """
            INSERT INTO users (email, password_hash, full_name, phone, role)
            VALUES (%s, %s, %s, %s, 'customer')
            ON CONFLICT (email) DO NOTHING
            RETURNING id
            """,
            (email, password_hash, f"Khách hàng mẫu {idx}", f"09{idx:08d}"),
        ).fetchone()
        if row is None:
            continue
        user_id = row[0]
        new_ids.append(user_id)
        conn.execute(
            """
            INSERT INTO addresses (user_id, recipient_name, phone, line1, province, is_default)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            """,
            (user_id, f"Khách hàng mẫu {idx}", f"09{idx:08d}", f"Số {idx} đường Demo", "Hà Nội"),
        )
    conn.commit()
    return existing_ids + new_ids


def seed_orders(conn: psycopg.Connection, customer_ids: list[int], target: int) -> None:
    existing = conn.execute("SELECT COUNT(*) FROM orders WHERE order_code LIKE 'SEED-ORD-%%'").fetchone()[0]
    if existing >= target or not customer_ids:
        print(f"orders: đã có {existing} >= {target} (hoặc không có khách hàng), bỏ qua")
        return

    variants = conn.execute(
        "SELECT pv.id, p.base_price + pv.price_adjustment AS price, p.name, pv.variant_name, pv.sku "
        "FROM product_variants pv JOIN products p ON p.id = pv.product_id LIMIT 500"
    ).fetchall()
    if not variants:
        print("orders: chưa có product_variants, bỏ qua")
        return

    address_by_user = {
        r[0]: r[1]
        for r in conn.execute("SELECT DISTINCT ON (user_id) user_id, id FROM addresses ORDER BY user_id, id").fetchall()
    }

    to_create = target - existing
    print(f"orders: sinh thêm {to_create} đơn hàng lịch sử")
    now = datetime.now(timezone.utc)

    for i in range(to_create):
        user_id = random.choice(customer_ids)
        address_id = address_by_user.get(user_id)
        if address_id is None:
            continue

        created_at = now - timedelta(days=random.randint(0, 90), hours=random.randint(0, 23))
        status = random.choice(ORDER_STATUSES)
        order_code = f"SEED-ORD-{existing + i + 1:06d}"

        items = random.sample(variants, k=random.randint(1, 3))
        subtotal = sum(item[1] * random.randint(1, 3) for item in items)
        shipping_fee = 30000
        total_amount = subtotal + shipping_fee

        order_row = conn.execute(
            """
            INSERT INTO orders (order_code, user_id, address_id, status, subtotal, discount_amount,
                                 shipping_fee, total_amount, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s)
            RETURNING id
            """,
            (order_code, user_id, address_id, status, subtotal, shipping_fee, total_amount, created_at, created_at),
        ).fetchone()
        order_id = order_row[0]

        for variant_id, price, name, variant_name, sku in items:
            qty = random.randint(1, 3)
            conn.execute(
                """
                INSERT INTO order_items (order_id, product_variant_id, product_name_snapshot, sku_snapshot,
                                          quantity, unit_price, discount_amount, line_total)
                VALUES (%s, %s, %s, %s, %s, %s, 0, %s)
                """,
                (order_id, variant_id, f"{name} ({variant_name})", sku, qty, price, price * qty),
            )

        payment_status = "success" if status in ("confirmed", "shipping", "delivered") else (
            "failed" if status == "cancelled" else "pending"
        )
        conn.execute(
            """
            INSERT INTO payments (order_id, method, status, amount, paid_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (order_id, random.choice(PAYMENT_METHODS), payment_status, total_amount,
             created_at if payment_status == "success" else None),
        )
        conn.execute(
            "INSERT INTO order_status_history (order_id, from_status, to_status, note, created_at) "
            "VALUES (%s, NULL, %s, 'Seed data', %s)",
            (order_id, status, created_at),
        )

        if (i + 1) % 200 == 0:
            conn.commit()
            print(f"  ... đã tạo {i + 1}/{to_create}")

    conn.commit()
    print("orders: hoàn tất")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--products", type=int, default=2000)
    parser.add_argument("--customers", type=int, default=40)
    parser.add_argument("--orders", type=int, default=150)
    args = parser.parse_args()

    random.seed(42)

    with psycopg.connect(get_settings().database_url) as conn:
        categories = seed_categories(conn)
        conn.commit()
        seed_suppliers(conn)
        conn.commit()

        seed_products(conn, list(categories.values()), args.products)
        customer_ids = seed_customers(conn, args.customers)
        seed_orders(conn, customer_ids, args.orders)

    print("Xong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
