"""Sinh bộ dữ liệu giống thực tế để test: ~110 đầu sách có thật, khách hàng
tên/địa chỉ Việt Nam, và khoảng 6 tháng hoạt động bán hàng được mô phỏng theo
đúng thứ tự thời gian.

Khác với seed_bulk.py (sinh số lượng lớn, dữ liệu ngẫu nhiên rời rạc), script
này giữ mọi con số khớp nhau như khi chạy thật:
  - Tồn kho = tổng nhập theo lô - tổng bán + hàng của đơn bị hủy.
  - Lô nhập được tạo khi tồn xuống dưới mức đặt hàng lại (sáng thứ Hai, thứ Năm).
  - Đơn hàng đi qua đúng các bước update_order_status() cho phép, mỗi bước có
    dòng order_status_history với thời điểm và người thao tác.
  - Mã giảm giá áp đúng điều kiện find_valid_promotion() (hạn dùng, đơn tối
    thiểu, giới hạn lượt) và tính tiền giống calculate_discount().
  - Đánh giá chỉ có trên đơn đã giao; hoàn tiền chỉ có trên đơn đã giao.
  - Số đơn mỗi ngày tăng dần theo thời gian, đông hơn cuối tuần, ngày lương và
    các ngày sale (9.9, 10.10, 11.11, 20/10...).

Tài khoản customer@tbookstore.vn có sẵn vài đơn ở trạng thái "đang chờ thao
tác" để test ngay trên Postman (xem phần in ra cuối khi chạy).

Dùng:
  python -m app.scripts.seed_realistic             # ghi vào DB
  python -m app.scripts.seed_realistic --dry-run   # chạy thử rồi rollback
Tùy chọn: --days 180 --customers 160 --orders-per-day 8 --seed 2026

Chỉ chạy được 1 lần trên mỗi DB: nếu đã có sản phẩm SKU "TBS-..." thì dừng.
Mọi thứ nằm trong 1 transaction, lỗi giữa chừng thì không ghi gì cả.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import unicodedata
import zlib
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

import psycopg

from app.core.config import get_settings
from app.core.security import hash_password
from app.scripts import realistic_data as D

VN = timezone(timedelta(hours=7))
SHIPPING_FEE = 30000  # place_order() cộng cố định 30.000đ
SKU_PREFIX = "TBS-"
CUSTOMER_PASSWORD = "Customer@123"
STAFF_PASSWORD = "Staff@123"

GATEWAY_NOTE = "Thanh toan thanh cong (gia lap gateway)"  # giống hệt note của simulate_payment_gateway()
CREATED_NOTE = "Don hang duoc tao"  # giống hệt note của place_order()

# Trọng số đặt hàng theo giờ trong ngày (0h..23h)
HOUR_WEIGHTS = [1, 0.5, 0.3, 0.2, 0.2, 0.4, 1, 2, 3, 4, 5, 6, 7, 5, 4, 4, 4, 4, 5, 6, 8, 9, 8, 4]

# (mã, (tháng, ngày bắt đầu), (tháng, ngày kết thúc), loại, giá trị, đơn tối thiểu,
#  giảm tối đa, tổng lượt, lượt/khách, hệ số lượng đơn, danh mục được đẩy)
EVENTS = [
    ("QUOCTEPN83", (3, 6), (3, 8), "percentage", 20, 200000, 80000, 300, 1, 1.4, None),
    ("GIAIPHONG305", (4, 28), (5, 1), "fixed_amount", 30000, 199000, None, 400, 1, 1.2, None),
    ("SALE55", (5, 5), (5, 5), "percentage", 5, 150000, 50000, 300, 1, 1.8, None),
    ("THIEUNHI16", (5, 30), (6, 1), "percentage", 16, 150000, 60000, 300, 1, 1.5, ("thieu-nhi", "truyen-tranh")),
    ("SALE66", (6, 6), (6, 6), "percentage", 6, 150000, 60000, 300, 1, 1.8, None),
    ("SALE77", (7, 7), (7, 7), "percentage", 7, 150000, 70000, 300, 1, 1.8, None),
    ("BACKTOSCHOOL", (8, 15), (9, 10), "percentage", 15, 150000, 60000, 500, 2, 1.3, ("ngoai-ngu", "thieu-nhi")),
    ("QUOCKHANH29", (8, 29), (9, 2), "fixed_amount", 29000, 199000, None, 400, 1, 1.3, None),
    ("SALE99", (9, 9), (9, 9), "percentage", 9, 199000, 90000, 300, 1, 2.2, None),
    ("SALE1010", (10, 10), (10, 10), "percentage", 10, 199000, 100000, 300, 1, 2.2, None),
    ("PHUNU2010", (10, 18), (10, 20), "percentage", 20, 200000, 80000, 300, 1, 1.6, None),
    ("SALE1111", (11, 11), (11, 11), "percentage", 11, 300000, 111000, 500, 1, 3.5, None),
    ("SALE1212", (12, 12), (12, 12), "percentage", 12, 300000, 120000, 500, 1, 2.5, None),
    ("NOEL2512", (12, 20), (12, 25), "fixed_amount", 50000, 300000, None, 400, 1, 1.3, None),
]
FLASH_SALE_DAYS = {(9, 9), (10, 10), (11, 11), (12, 12)}


# ---------------------------------------------------------------------------
# Tiện ích
# ---------------------------------------------------------------------------
def strip_accents(text: str) -> str:
    text = text.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def slugify(text: str) -> str:
    out = "".join(c if c.isalnum() else "-" for c in strip_accents(text).lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def money(x) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def round_to(x: float, step: int) -> int:
    return int(round(x / step) * step)


def poisson(lam: float, rng: random.Random) -> int:
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def isbn13(rng: random.Random) -> str:
    digits = "978604" + "".join(str(rng.randint(0, 9)) for _ in range(6))
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    return digits + str((10 - total % 10) % 10)


def at(day: date, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute, second), tzinfo=VN)


def in_work_hours(t: datetime, rng: random.Random, start: int = 8, end: int = 21) -> datetime:
    """Dời thời điểm thao tác của nhân viên vào giờ làm việc."""
    if start <= t.hour < end:
        return t
    day = t.date() if t.hour < start else t.date() + timedelta(days=1)
    return at(day, start) + timedelta(minutes=rng.randint(5, 100))


# ---------------------------------------------------------------------------
# Mô hình trong bộ nhớ
# ---------------------------------------------------------------------------
@dataclass
class Variant:
    id: int
    sku: str
    product_name: str
    variant_name: str
    category: str
    price: int
    supplier_id: int
    pop: float
    is_default: bool
    available_from: datetime
    on_hand: int
    reorder_level: int
    target: int
    cost_ratio: float
    discontinued: bool = False
    stocked: bool = False
    last_move: datetime | None = None

    @property
    def label(self) -> str:
        return f"{self.product_name} ({self.variant_name})"

    def pick_weight(self) -> float:
        return self.pop ** 1.6 * (1.0 if self.is_default else 0.35)


@dataclass
class Customer:
    id: int
    name: str
    joined: datetime
    weight: float
    addresses: list  # [(address_id, is_big_city)]
    fav: tuple
    orders: int = 0
    is_demo: bool = False


@dataclass
class Promo:
    id: int
    code: str | None
    kind: str  # welcome | freeship | vip | event | flash | upcoming | inactive
    type: str
    value: Decimal
    min_order: Decimal
    max_discount: Decimal | None
    starts: datetime
    ends: datetime
    usage_limit: int | None
    per_user: int | None
    active: bool = True
    multiplier: float = 1.0
    boost: tuple | None = None
    used: int = 0
    by_user: dict = field(default_factory=dict)
    flash_items: dict = field(default_factory=dict)  # variant_id -> [fsi_id, price, limit, sold]

    def running(self, t: datetime) -> bool:
        return self.active and self.starts <= t <= self.ends

    def usable(self, t: datetime, user_id: int, subtotal: Decimal) -> bool:
        return (
            self.code is not None and self.running(t) and subtotal >= self.min_order
            and (self.usage_limit is None or self.used < self.usage_limit)
            and (self.per_user is None or self.by_user.get(user_id, 0) < self.per_user)
        )

    def discount(self, subtotal: Decimal) -> Decimal:
        d = subtotal * self.value / 100 if self.type == "percentage" else self.value
        if self.max_discount is not None:
            d = min(d, self.max_discount)
        return money(min(d, subtotal))


# ---------------------------------------------------------------------------
# Bộ sinh dữ liệu
# ---------------------------------------------------------------------------
class Seeder:
    def __init__(self, conn: psycopg.Connection, args: argparse.Namespace) -> None:
        self.conn = conn
        self.args = args
        self.rng = random.Random(args.seed)
        self.now = datetime.now(VN).replace(microsecond=0)
        self.start_day = (self.now - timedelta(days=args.days)).date()
        self.start = at(self.start_day, 0)
        self.variants: list[Variant] = []
        self.customers: list[Customer] = []
        self.promos: list[Promo] = []
        self.staff_ids: list[int] = []
        self.admin_id: int | None = None
        self.category_ids: dict[str, int] = {}
        self.supplier_ids: dict[str, int] = {}
        self.counts: dict[str, int] = {}

    # -- tiện ích ghi DB ----------------------------------------------------
    def q(self, sql: str, params=None):
        return self.conn.execute(sql, params)

    def bump(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    def progress(self, t: datetime) -> float:
        return min(1.0, max(0.0, (t - self.start) / (self.now - self.start)))

    # -- 1. danh mục, nhà cung cấp, nhân viên ------------------------------
    def seed_reference_data(self) -> None:
        for slug, name, _parent in D.CATEGORIES:
            self.q("INSERT INTO categories (name, slug) VALUES (%s, %s) ON CONFLICT (slug) DO NOTHING", (name, slug))
        self.category_ids = dict(self.q("SELECT slug, id FROM categories").fetchall())
        for slug, _name, parent in D.CATEGORIES:
            if parent:
                self.q("UPDATE categories SET parent_id = %s WHERE slug = %s AND parent_id IS NULL",
                       (self.category_ids[parent], slug))

        for name, phone, email, address in D.SUPPLIERS:
            row = self.q("SELECT id FROM suppliers WHERE name = %s", (name,)).fetchone()
            if row is None:
                row = self.q(
                    "INSERT INTO suppliers (name, contact_phone, email, address) VALUES (%s, %s, %s, %s) RETURNING id",
                    (name, phone, email, address),
                ).fetchone()
                self.bump("suppliers")
            self.supplier_ids[name] = row[0]

        staff_hash = hash_password(STAFF_PASSWORD)
        for full_name, email, phone, active in D.STAFF:
            created = self.start - timedelta(days=self.rng.randint(30, 400))
            inserted = self.q(
                "INSERT INTO users (email, password_hash, full_name, phone, role, is_active, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, 'staff', %s, %s, %s) ON CONFLICT (email) DO NOTHING RETURNING id",
                (email, staff_hash, full_name, phone, active, created, created),
            ).fetchone()
            if inserted:
                self.bump("staff")
        self.staff_ids = [r[0] for r in self.q(
            "SELECT id FROM users WHERE role = 'staff' AND is_active AND deleted_at IS NULL ORDER BY id").fetchall()]
        admin = self.q("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()
        self.admin_id = admin[0] if admin else self.staff_ids[0]
        if not self.staff_ids:
            raise SystemExit("Không có tài khoản staff nào đang hoạt động")

    # -- 2. sách -------------------------------------------------------------
    def seed_catalog(self) -> None:
        rng = self.rng
        used_slugs = {r[0] for r in self.q("SELECT slug FROM products").fetchall()}
        seq_by_cat: dict[str, int] = {}
        supplier_cost = {name: rng.uniform(0.55, 0.68) for name in self.supplier_ids}

        for (cat, title, author, publisher, supplier, price, pop, extras, desc, is_new) in D.BOOKS:
            seq_by_cat[cat] = seq_by_cat.get(cat, 0) + 1
            code = f"{SKU_PREFIX}{D.CATEGORY_CODE[cat]}-{seq_by_cat[cat]:04d}"
            slug = slugify(title)
            if slug in used_slugs:
                slug = f"{slug}-{slugify(author)}"
            used_slugs.add(slug)

            if is_new:
                created = at((self.now - timedelta(days=rng.randint(12, 60))).date(), 8)
            else:
                created = self.start - timedelta(days=rng.randint(30, 500), hours=rng.randint(0, 23))
            product_id = self.q(
                """
                INSERT INTO products (category_id, sku, name, slug, author, publisher, isbn, description,
                                      base_price, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                """,
                (self.category_ids[cat], code, title, slug, author, publisher, isbn13(rng), desc,
                 price, created, created),
            ).fetchone()[0]
            self.bump("products")

            available = max(created, at(self.start_day, 8))
            for idx, (vname, adj) in enumerate([("Bìa mềm", 0)] + list(extras)):
                suffix = {"Bìa mềm": "BM", "Bìa cứng": "BC"}.get(vname, "DB")
                variant_id = self.q(
                    "INSERT INTO product_variants (product_id, variant_name, sku, price_adjustment) "
                    "VALUES (%s, %s, %s, %s) RETURNING id",
                    (product_id, vname, f"{code}-{suffix}", adj),
                ).fetchone()[0]
                self.bump("variants")
                vpop = pop if idx == 0 else max(1.0, pop * 0.5)
                self.variants.append(Variant(
                    id=variant_id, sku=f"{code}-{suffix}", product_name=title, variant_name=vname, category=cat,
                    price=price + adj, supplier_id=self.supplier_ids[supplier], pop=pop, is_default=idx == 0,
                    available_from=available, on_hand=0,
                    reorder_level=max(5, round(vpop * 2) + 3), target=round_to(20 + vpop * 6, 10),
                    cost_ratio=supplier_cost[supplier],
                ))

        # Vài đầu sách ít bán bị nhà cung cấp ngừng phát hành: không nhập lại,
        # nhập lần đầu rất ít -> cuối kỳ còn rất ít hoặc hết hàng (để test lỗi hết hàng).
        slow = [v for v in self.variants if v.is_default and v.pop <= 2]
        for v in rng.sample(slow, k=min(3, len(slow))):
            v.discontinued = True
            v.target = 4

        # Sách đã có từ seed.sql: đưa vào mô phỏng với tồn kho hiện tại.
        for sku, (supplier, pop) in D.EXISTING_PRODUCTS.items():
            rows = self.q(
                """
                SELECT pv.id, pv.sku, p.name, pv.variant_name, c.slug, p.base_price + pv.price_adjustment,
                       COALESCE(i.quantity_on_hand, 0), pv.price_adjustment = 0
                FROM products p JOIN product_variants pv ON pv.product_id = p.id
                JOIN categories c ON c.id = p.category_id
                LEFT JOIN inventories i ON i.product_variant_id = pv.id
                WHERE p.sku = %s AND pv.is_active AND p.deleted_at IS NULL
                """,
                (sku,),
            ).fetchall()
            for vid, vsku, pname, vname, cat, vprice, on_hand, is_default in rows:
                vpop = pop if is_default else max(1.0, pop * 0.5)
                self.variants.append(Variant(
                    id=vid, sku=vsku, product_name=pname, variant_name=vname, category=cat, price=int(vprice),
                    supplier_id=self.supplier_ids[supplier], pop=pop, is_default=is_default,
                    available_from=self.start, on_hand=on_hand, stocked=True,
                    reorder_level=max(5, round(vpop * 2) + 3), target=round_to(20 + vpop * 6, 10),
                    cost_ratio=supplier_cost[supplier],
                ))
                self.q("INSERT INTO inventories (product_variant_id) VALUES (%s) ON CONFLICT DO NOTHING", (vid,))

        self.q(
            "INSERT INTO inventories (product_variant_id, quantity_on_hand, reorder_level, updated_at) "
            "SELECT pv.id, 0, 0, %s FROM product_variants pv WHERE pv.sku LIKE %s",
            (self.start, f"{SKU_PREFIX}%"),
        )

    # -- 3. khách hàng ------------------------------------------------------
    def _person(self) -> tuple[str, str, str, int]:
        rng = self.rng
        surname = rng.choices([s for s, _ in D.SURNAMES], weights=[w for _, w in D.SURNAMES])[0]
        if rng.random() < 0.55:  # khách mua sách nữ nhiều hơn một chút
            middle, given = rng.choice(D.MIDDLE_FEMALE), rng.choice(D.GIVEN_FEMALE)
        else:
            middle, given = rng.choice(D.MIDDLE_MALE), rng.choice(D.GIVEN_MALE)
        birth_year = rng.choices(range(1972, 2008), weights=[1 + max(0, y - 1985) for y in range(1972, 2008)])[0]
        return surname, middle, given, birth_year

    def _email(self, surname: str, middle: str, given: str, year: int, used: set) -> str:
        s, m, g = (strip_accents(x).lower().replace(" ", "") for x in (surname, middle, given))
        rng = self.rng
        local = rng.choice([
            f"{g}.{s}{year % 100:02d}", f"{s}{m}{g}{rng.randint(1, 999)}", f"{g}{s}{year}",
            f"{g}_{s}", f"{s}.{g}{m[0]}", f"{g}{m[0]}{s}{rng.randint(10, 99)}",
        ])
        email = f"{local}@{rng.choice(D.EMAIL_DOMAINS)}"
        while email in used:
            email = f"{local}{rng.randint(1, 9999)}@{rng.choice(D.EMAIL_DOMAINS)}"
        used.add(email)
        return email

    def _phone(self, used: set) -> str:
        while True:
            phone = self.rng.choice(D.PHONE_PREFIXES) + f"{self.rng.randint(0, 9999999):07d}"
            if phone not in used:
                used.add(phone)
                return phone

    def _address_line(self, province: str) -> str:
        rng = self.rng
        _w, _wards, streets, buildings, big = D.PROVINCES[province]
        street = rng.choice(streets)
        num = rng.choice([rng.randint(1, 99), rng.randint(1, 350), rng.randint(100, 999)])
        r = rng.random()
        if big and buildings and r < 0.2:
            return f"Căn {rng.choice('ABCS')}{rng.randint(1, 6)}-{rng.randint(2, 35):02d}{rng.randint(1, 20):02d}, {rng.choice(buildings)}"
        if province == "Hà Nội" and r < 0.55:
            if rng.random() < 0.4:
                return f"Số {rng.randint(1, 60)} ngách {rng.randint(1, 120)}/{rng.randint(2, 90)} {street}"
            return f"Số {rng.randint(1, 80)} ngõ {rng.randint(2, 300)} {street}"
        if province == "TP. Hồ Chí Minh" and r < 0.5:
            if rng.random() < 0.3:
                return f"{num}/{rng.randint(1, 60)}/{rng.randint(1, 30)} {street}"
            return f"{num}/{rng.randint(1, 120)} {street}"
        if r < 0.75:
            return f"{num} {street}"
        return f"{num}/{rng.randint(1, 40)} {street}"

    def _insert_address(self, user_id: int, name: str, phone: str, province: str,
                        default: bool, created: datetime, office: bool = False) -> tuple[int, bool]:
        rng = self.rng
        _w, wards, streets, _b, big = D.PROVINCES[province]
        line1 = self._address_line(province)
        if office and province in D.OFFICE_BUILDINGS:
            line1 = f"Tầng {rng.randint(3, 40)}, {rng.choice(D.OFFICE_BUILDINGS[province])}"
        address_id = self.q(
            "INSERT INTO addresses (user_id, recipient_name, phone, line1, ward, district, province, is_default, created_at) "
            "VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, %s) RETURNING id",
            (user_id, name, phone, line1, rng.choice(wards), province, default, created),
        ).fetchone()[0]
        self.bump("addresses")
        return address_id, big

    def _pick_province(self) -> str:
        names = list(D.PROVINCES)
        return self.rng.choices(names, weights=[D.PROVINCES[n][0] for n in names])[0]

    def seed_customers(self) -> None:
        rng = self.rng
        used_emails = {r[0] for r in self.q("SELECT email FROM users").fetchall()}
        used_phones = {r[0] for r in self.q("SELECT phone FROM users WHERE phone IS NOT NULL").fetchall()}
        pw_hash = hash_password(CUSTOMER_PASSWORD)
        cats = sorted({v.category for v in self.variants})

        for i in range(self.args.customers):
            surname, middle, given, year = self._person()
            full_name = f"{surname} {middle} {given}"
            email = self._email(surname, middle, given, year, used_emails)
            phone = self._phone(used_phones)
            if rng.random() < 0.25:
                joined = self.start - timedelta(days=rng.randint(5, 330), minutes=rng.randint(0, 1439))
            else:
                joined = self.start + (self.now - self.start) * (rng.random() ** 0.7)
            joined = joined.replace(microsecond=0)
            # Khoảng 10% chỉ đăng ký mà không mua; 2 người trong số đó bị khóa tài khoản
            buyer = rng.random() > 0.10
            active = buyer or rng.random() > 0.25
            user_id = self.q(
                "INSERT INTO users (email, password_hash, full_name, phone, role, is_active, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, 'customer', %s, %s, %s) RETURNING id",
                (email, pw_hash, full_name, phone, active, joined, joined),
            ).fetchone()[0]
            self.bump("customers")

            province = self._pick_province()
            addresses = [self._insert_address(user_id, full_name, phone, province, True, joined)]
            if rng.random() < 0.25:
                created = joined + timedelta(days=rng.randint(1, 60))
                if province in D.OFFICE_BUILDINGS and rng.random() < 0.6:
                    addresses.append(self._insert_address(user_id, full_name, phone, province, False, created, office=True))
                else:  # gửi sách về cho bố mẹ ở quê
                    s2, m2, g2, _ = self._person()
                    addresses.append(self._insert_address(
                        user_id, f"{s2} {m2} {g2}", self._phone(used_phones), self._pick_province(), False, created))

            weight = rng.lognormvariate(0, 0.9) if buyer else 0.0
            self.customers.append(Customer(user_id, full_name, joined, weight, addresses, tuple(rng.sample(cats, 2))))

        # Tài khoản demo có sẵn: khách quen, mua đều
        demo = self.q("SELECT id, full_name, phone, created_at FROM users WHERE email = 'customer@tbookstore.vn'").fetchone()
        if demo:
            demo_id, demo_name, demo_phone, _created = demo
            existing = self.q("SELECT id, province FROM addresses WHERE user_id = %s ORDER BY is_default DESC, id",
                              (demo_id,)).fetchall()
            addresses = [(aid, D.PROVINCES.get(p, (0, [], [], [], False))[4]) for aid, p in existing]
            if not addresses:
                phone = demo_phone or "0900000003"
                addresses = [
                    self._insert_address(demo_id, demo_name, phone, "Hà Nội", True, self.start),
                    self._insert_address(demo_id, demo_name, phone, "Hà Nội", False, self.start, office=True),
                ]
            self.customers.append(Customer(demo_id, demo_name, self.start - timedelta(days=60), 2.5, addresses,
                                           ("ky-nang-song", "van-hoc-nuoc-ngoai"), is_demo=True))

    # -- 4. khuyến mãi -------------------------------------------------------
    def _insert_promo(self, p: Promo) -> Promo:
        p.id = self.q(
            """
            INSERT INTO promotions (code, type, value, min_order_amount, max_discount_amount, starts_at, ends_at,
                                    usage_limit, per_user_limit, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (p.code, p.type, p.value, p.min_order, p.max_discount, p.starts, p.ends,
             p.usage_limit, p.per_user, p.active),
        ).fetchone()[0]
        self.promos.append(p)
        self.bump("promotions")
        return p

    def _add_flash_items(self, promo: Promo, count: int, limit_range: tuple[int, int]) -> None:
        rng = self.rng
        pool = [v for v in self.variants if v.is_default and v.pop >= 4 and v.available_from <= promo.starts]
        for v in rng.sample(pool, k=min(count, len(pool))):
            flash_price = max(1000, round_to(v.price * rng.uniform(0.6, 0.75), 1000) - 1000)
            limit = rng.randint(*limit_range)
            fsi_id = self.q(
                "INSERT INTO flash_sale_items (promotion_id, product_variant_id, flash_price, quantity_limit) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (promo.id, v.id, flash_price, limit),
            ).fetchone()[0]
            promo.flash_items[v.id] = [fsi_id, flash_price, limit, 0]
            self.bump("flash_sale_items")

    def seed_promotions(self) -> None:
        rng = self.rng
        far = self.now + timedelta(days=365)
        self._insert_promo(Promo(0, "WELCOME50K", "welcome", "fixed_amount", Decimal(50000), Decimal(199000), None,
                                 self.start - timedelta(days=90), far, None, 1))
        self._insert_promo(Promo(0, "FREESHIP30K", "freeship", "fixed_amount", Decimal(30000), Decimal(250000), None,
                                 self.start, self.now + timedelta(days=60), 3000, 5))
        self._insert_promo(Promo(0, "VIP100K", "vip", "fixed_amount", Decimal(100000), Decimal(500000), None,
                                 self.start, self.now + timedelta(days=30), 1000, 1))
        self._insert_promo(Promo(0, "TAMNGUNG10", "inactive", "percentage", Decimal(10), Decimal(0), Decimal(50000),
                                 self.start, self.now + timedelta(days=30), None, None, active=False))
        self._insert_promo(Promo(0, "SACHMOI15", "upcoming", "percentage", Decimal(15), Decimal(150000), Decimal(70000),
                                 at((self.now + timedelta(days=5)).date(), 0),
                                 at((self.now + timedelta(days=12)).date(), 23, 59, 59), 300, 1))

        seen = set()
        for year in sorted({self.start.year, self.now.year}):
            for code, (m1, d1), (m2, d2), ptype, value, min_order, max_d, ulimit, per_user, mult, boost in EVENTS:
                starts, ends = at(date(year, m1, d1), 0), at(date(year, m2, d2), 23, 59, 59)
                if ends < self.start or starts > self.now or code in seen:
                    continue
                seen.add(code)
                self._insert_promo(Promo(0, code, "event", ptype, Decimal(value), Decimal(min_order),
                                         Decimal(max_d) if max_d else None, starts, ends, ulimit, per_user,
                                         multiplier=mult, boost=boost))
                if (m1, d1) in FLASH_SALE_DAYS:
                    flash = self._insert_promo(Promo(0, None, "flash", "flash_sale", Decimal(30), Decimal(0), None,
                                                     starts, ends, None, None, multiplier=1.0))
                    self._add_flash_items(flash, 8, (30, 60))

        # Black Friday sắp tới (nếu trong vòng 45 ngày) -> mã "chưa bắt đầu" để test
        nov1 = date(self.now.year, 11, 1)
        thanksgiving = nov1 + timedelta(days=(3 - nov1.weekday()) % 7 + 21)
        bf = at(thanksgiving + timedelta(days=1), 0)
        if self.now < bf <= self.now + timedelta(days=45):
            self._insert_promo(Promo(0, f"BLACKFRIDAY{self.now.year % 100}", "upcoming", "percentage", Decimal(25),
                                     Decimal(300000), Decimal(150000), bf, bf + timedelta(days=3, hours=23, minutes=59),
                                     800, 1))

        # Flash sale đang chạy lúc này
        current = self._insert_promo(Promo(0, None, "flash", "flash_sale", Decimal(30), Decimal(0), None,
                                           at((self.now - timedelta(days=1)).date(), 0),
                                           at((self.now + timedelta(days=5)).date(), 23, 59, 59), None, None,
                                           multiplier=1.2))
        self._add_flash_items(current, 6, (50, 80))

    # -- 5. nhập kho --------------------------------------------------------
    def restock(self, day: date, initial: bool) -> None:
        rng = self.rng
        restock_day = initial or day.weekday() in (0, 3)
        lot_time = at(day, 8 if initial else 9, rng.randint(0, 40))
        if lot_time > self.now:
            return
        by_supplier: dict[int, list[tuple[Variant, int]]] = {}
        for v in self.variants:
            if v.available_from.date() > day:
                continue
            if not v.stocked:
                qty = v.target
            elif restock_day and not v.discontinued and v.on_hand <= v.reorder_level:
                qty = round_to(max(v.target - v.on_hand, 10), 10)
            else:
                continue
            by_supplier.setdefault(v.supplier_id, []).append((v, qty))

        for offset, (supplier_id, items) in enumerate(sorted(by_supplier.items())):
            imported_at = lot_time + timedelta(minutes=offset * 7, seconds=rng.randint(0, 59))
            lot_code = f"LOT-{imported_at:%Y%m%d%H%M%S}-{supplier_id}"
            creator = self.admin_id if initial else rng.choice(self.staff_ids)
            lot_id = self.q(
                "INSERT INTO import_lots (supplier_id, lot_code, imported_at, created_by) VALUES (%s, %s, %s, %s) RETURNING id",
                (supplier_id, lot_code, imported_at, creator),
            ).fetchone()[0]
            drift = 1 + 0.04 * self.progress(imported_at)
            with self.conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO import_receipt_items (import_lot_id, product_variant_id, quantity, unit_cost) "
                    "VALUES (%s, %s, %s, %s)",
                    [(lot_id, v.id, qty, round_to(v.price * v.cost_ratio * drift, 500)) for v, qty in items],
                )
            self.q(
                "INSERT INTO audit_logs (user_id, action, entity_type, entity_id, new_value, created_at) "
                "VALUES (%s, 'create', 'import_lot', %s, %s, %s)",
                (creator, lot_id, json.dumps({"lot_code": lot_code, "items": len(items)}), imported_at),
            )
            for v, qty in items:
                v.on_hand += qty
                v.stocked = True
                v.last_move = imported_at
            self.bump("import_lots")
            self.bump("import_items", len(items))

    # -- 6. đơn hàng --------------------------------------------------------
    def effective_price(self, v: Variant, t: datetime) -> tuple[int, list | None]:
        best = None
        for p in self.promos:
            if p.kind == "flash" and p.running(t) and v.id in p.flash_items:
                item = p.flash_items[v.id]
                if item[3] < item[2] and (best is None or item[1] < best[1]):
                    best = item
        return (best[1], best) if best else (v.price, None)

    def day_rate(self, day: date) -> float:
        rate = self.args.orders_per_day * (0.75 + 0.6 * self.progress(at(day, 12)))
        if day.weekday() >= 5:
            rate *= 1.25
        if day.day <= 5 or day.day >= 25:
            rate *= 1.12  # quanh ngày nhận lương
        noon = at(day, 12)
        for p in self.promos:
            if p.kind in ("event", "flash") and p.starts <= noon <= p.ends:
                rate *= p.multiplier
        return rate

    def pick_lines(self, t: datetime, cust: Customer) -> list[tuple[Variant, int, int, list | None]]:
        rng = self.rng
        boosts = set()
        for p in self.promos:
            if p.kind == "event" and p.boost and p.running(t):
                boosts.update(p.boost)
        flash_ids = {vid for p in self.promos if p.kind == "flash" and p.running(t) for vid in p.flash_items}
        pool, weights = [], []
        for v in self.variants:
            if v.on_hand <= 0 or v.available_from > t:
                continue
            w = v.pick_weight()
            if v.category in cust.fav:
                w *= 2.5
            if v.category in boosts:
                w *= 2.5
            if v.id in flash_ids:
                w *= 3
            pool.append(v)
            weights.append(w)
        if not pool:
            return []
        n_lines = rng.choices([1, 2, 3, 4], weights=[50, 30, 13, 7])[0]
        chosen: list[Variant] = []
        for _ in range(n_lines * 3):
            v = rng.choices(pool, weights=weights)[0]
            if v not in chosen and all(c.product_name != v.product_name for c in chosen):
                chosen.append(v)
            if len(chosen) >= n_lines:
                break
        lines = []
        for v in chosen:
            if v.category == "truyen-tranh":
                qty = rng.choices([1, 2, 3], weights=[60, 25, 15])[0]
            else:
                qty = rng.choices([1, 2, 3], weights=[88, 10, 2])[0]
            price, flash = self.effective_price(v, t)
            if flash:
                qty = min(qty, flash[2] - flash[3])
            qty = min(qty, v.on_hand)
            if qty > 0:
                lines.append((v, qty, price, flash))
        return lines

    def choose_promo(self, t: datetime, cust: Customer, subtotal: Decimal) -> Promo | None:
        rng = self.rng
        usable = [p for p in self.promos if p.usable(t, cust.id, subtotal)]
        by_kind = {}
        for p in usable:
            by_kind.setdefault(p.kind, []).append(p)
        if cust.orders == 0 and "welcome" in by_kind and rng.random() < 0.75:
            return by_kind["welcome"][0]
        if "event" in by_kind and rng.random() < 0.65:
            return max(by_kind["event"], key=lambda p: p.discount(subtotal))
        if "vip" in by_kind and rng.random() < 0.4:
            return by_kind["vip"][0]
        if "freeship" in by_kind and rng.random() < 0.3:
            return by_kind["freeship"][0]
        return None

    def tracking_code(self, carrier: str) -> str:
        rng = self.rng
        alnum = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        if carrier == "GHN":
            return "G" + "".join(rng.choice(alnum) for _ in range(7))
        if carrier == "GHTK":
            return f"S{rng.randint(10**8, 10**9 - 1)}"
        if carrier == "Viettel Post":
            return f"{rng.randint(10**11, 10**12 - 1)}"
        if carrier == "J&T Express":
            return f"8{rng.randint(10**10, 10**11 - 1)}"
        return "NVVN" + "".join(rng.choice(alnum) for _ in range(10))

    def build_timeline(self, t: datetime, cust: Customer, method: str, big_city: bool, plan: dict | None) -> dict:
        """Tính trước toàn bộ vòng đời đơn rồi cắt ở thời điểm hiện tại."""
        rng = self.rng
        plan = plan or {}
        staff = rng.choice(self.staff_ids)
        carrier = rng.choice(D.CARRIERS)
        code = self.tracking_code(carrier)
        events = [(t, None, "pending", cust.id, CREATED_NOTE)]
        pay = {"status": "pending", "paid_at": None, "ref": None}
        confirm_t = None

        outcome = plan.get("outcome")
        if outcome is None:
            r = rng.random()
            if method == "simulated_gateway":
                outcome = "pay_fail" if r < 0.07 else "normal"
            else:
                outcome = "customer_cancel" if r < 0.04 else "staff_cancel" if r < 0.065 else "normal"

        if method == "simulated_gateway" and not plan.get("no_payment"):
            pay_t = t + timedelta(minutes=rng.randint(1, 6), seconds=rng.randint(0, 59))
            if pay_t <= self.now:
                pay["ref"] = f"SIM-{pay_t:%Y%m%d%H%M%S}-{{order_id}}"
                if outcome == "pay_fail":
                    pay["status"] = "failed"
                else:
                    pay.update(status="success", paid_at=pay_t)
                    confirm_t = pay_t
                    events.append((pay_t, "pending", "confirmed", cust.id, GATEWAY_NOTE))
            if outcome == "pay_fail":
                cancel_t = in_work_hours(t + timedelta(hours=rng.uniform(24, 30)), rng)
                events.append((cancel_t, "pending", "cancelled", staff, D.PAYMENT_FAIL_CANCEL_NOTE))
        elif method == "cod":
            if outcome == "customer_cancel":
                events.append((t + timedelta(hours=rng.uniform(0.2, 10)), "pending", "cancelled", cust.id,
                               rng.choice(D.CUSTOMER_CANCEL_NOTES)))
            elif outcome == "staff_cancel":
                events.append((in_work_hours(t + timedelta(hours=rng.uniform(3, 26)), rng), "pending", "cancelled",
                               staff, rng.choice(D.STAFF_CANCEL_NOTES)))
            else:
                confirm_t = plan.get("confirm_at") or in_work_hours(t + timedelta(hours=rng.uniform(0.3, 3)), rng)
                events.append((confirm_t, "pending", "confirmed", staff, "Đã gọi điện xác nhận đơn với khách"))

        ship_t = deliver_t = None
        if confirm_t is not None and outcome == "normal":
            ship_t = plan.get("ship_at") or in_work_hours(confirm_t + timedelta(hours=rng.uniform(5, 28)), rng, 8, 18)
            events.append((ship_t, "confirmed", "shipping", staff, f"Bàn giao {carrier}, mã vận đơn {code}"))
            days = rng.uniform(1, 2.5) if big_city else rng.uniform(2, 5)
            deliver_t = plan.get("deliver_at") or max(
                ship_t + timedelta(hours=12),
                at((ship_t + timedelta(days=days)).date(), rng.randint(8, 19), rng.randint(0, 59)),
            )
            events.append((deliver_t, "shipping", "delivered", staff, f"{carrier} xác nhận giao thành công"))

        stop = plan.get("stop_at")
        kept = []
        for ev in sorted(events, key=lambda e: e[0]):
            if ev[0] > self.now:
                break
            kept.append(ev)
            if stop and ev[2] == stop:
                break
        status = kept[-1][2]
        if method == "cod" and status == "delivered":
            pay.update(status="success", paid_at=kept[-1][0])

        shipment = None
        reached = {e[2] for e in kept}
        if "confirmed" in reached and status != "cancelled":
            ship_status = {"confirmed": "preparing", "shipping": "in_transit", "delivered": "delivered"}[status]
            shipment = {
                "carrier": carrier, "code": code, "status": ship_status,
                "shipped_at": ship_t if status in ("shipping", "delivered") else None,
                "delivered_at": kept[-1][0] if status == "delivered" else None,
            }
        handled = next((e[3] for e in kept if e[3] in self.staff_ids), None)
        return {"events": kept, "status": status, "pay": pay, "shipment": shipment, "handled_by": handled,
                "updated_at": kept[-1][0]}

    def create_order(self, t: datetime, cust: Customer, lines, plan: dict | None = None, after_sales: bool = True):
        rng = self.rng
        plan = plan or {}
        subtotal = money(sum(price * qty for _v, qty, price, _f in lines))
        promo = None if plan.get("no_promo") else self.choose_promo(t, cust, subtotal)
        discount = promo.discount(subtotal) if promo else money(0)
        total = subtotal - discount + SHIPPING_FEE
        method = plan.get("method") or ("simulated_gateway" if rng.random() < 0.4 else "cod")
        address_id, big = cust.addresses[0] if len(cust.addresses) == 1 or rng.random() < 0.85 else rng.choice(cust.addresses[1:])
        tl = self.build_timeline(t, cust, method, big, plan)

        order_id = self.q("SELECT nextval(pg_get_serial_sequence('orders', 'id'))").fetchone()[0]
        order_code = f"ORD-{t:%Y%m%d}-{order_id}"
        self.q(
            """
            INSERT INTO orders (id, order_code, user_id, address_id, status, subtotal, discount_amount, shipping_fee,
                                total_amount, handled_by, created_at, updated_at)
            OVERRIDING SYSTEM VALUE VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (order_id, order_code, cust.id, address_id, tl["status"], subtotal, discount, SHIPPING_FEE, total,
             tl["handled_by"], t, tl["updated_at"]),
        )
        items = []
        for v, qty, price, flash in lines:
            item_id = self.q(
                """
                INSERT INTO order_items (order_id, product_variant_id, product_name_snapshot, sku_snapshot, quantity,
                                         unit_price, discount_amount, line_total)
                VALUES (%s, %s, %s, %s, %s, %s, 0, %s) RETURNING id
                """,
                (order_id, v.id, v.label, v.sku, qty, price, price * qty),
            ).fetchone()[0]
            items.append((item_id, v, qty, price))
            v.on_hand -= qty
            v.last_move = t
            if flash:
                flash[3] += qty

        with self.conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO order_status_history (order_id, from_status, to_status, changed_by, note, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                [(order_id, frm, to, by, note, when) for when, frm, to, by, note in tl["events"]],
            )
        pay = tl["pay"]
        self.q(
            "INSERT INTO payments (order_id, method, status, amount, transaction_ref, created_at, paid_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (order_id, method, pay["status"], total, pay["ref"].format(order_id=order_id) if pay["ref"] else None,
             t, pay["paid_at"]),
        )
        if tl["shipment"]:
            s = tl["shipment"]
            self.q(
                "INSERT INTO shipments (order_id, carrier, tracking_code, status, shipped_at, delivered_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (order_id, s["carrier"], s["code"], s["status"], s["shipped_at"], s["delivered_at"]),
            )
        if promo:
            self.q("INSERT INTO promotion_usages (promotion_id, user_id, order_id, used_at) VALUES (%s, %s, %s, %s)",
                   (promo.id, cust.id, order_id, t))
            promo.used += 1
            promo.by_user[cust.id] = promo.by_user.get(cust.id, 0) + 1
            self.bump("promotion_usages")

        if tl["status"] == "cancelled":  # update_order_status() trả hàng về kho khi hủy
            cancel_t = tl["updated_at"]
            for _iid, v, qty, _p in items:
                v.on_hand += qty
                v.last_move = max(v.last_move or cancel_t, cancel_t)

        cust.orders += 1
        self.bump("orders")
        self.bump(f"orders_{tl['status']}")
        if tl["status"] == "delivered" and after_sales:
            self.after_sales(order_id, cust, items, total, tl["updated_at"])
        return order_id, order_code, tl["status"]

    def after_sales(self, order_id: int, cust: Customer, items, total: Decimal, delivered_at: datetime) -> None:
        rng = self.rng
        # Hoàn tiền (~3% đơn đã giao)
        if rng.random() < 0.03:
            requested = delivered_at + timedelta(hours=rng.uniform(6, 120))
            if requested <= self.now:
                reason, scope = rng.choice(D.REFUND_REASONS)
                if scope == "item":
                    _iid, _v, qty, price = rng.choice(items)
                    amount = money(price * qty)
                else:
                    amount = total
                processed = requested + timedelta(hours=rng.uniform(12, 60))
                status, by, when = "requested", None, None
                if processed <= self.now and rng.random() < 0.9:
                    status = "refunded" if rng.random() < 0.7 else "rejected"
                    by, when = rng.choice(self.staff_ids), processed
                self.q(
                    "INSERT INTO refund_requests (order_id, reason, status, refund_amount, requested_at, processed_by, processed_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (order_id, reason, status, amount, requested, by, when),
                )
                if status == "refunded":
                    self.q("UPDATE payments SET status = 'refunded' WHERE order_id = %s", (order_id,))
                self.bump(f"refunds_{status}")

        # Đánh giá (~32% dòng hàng của đơn đã giao)
        for item_id, v, _qty, _price in items:
            if rng.random() > 0.32:
                continue
            created = delivered_at + timedelta(hours=rng.uniform(8, 300))
            if created > self.now:
                continue
            approved = True
            if rng.random() < 0.01:
                rating, comment, approved = 5, D.SPAM_REVIEW, False
            else:
                quality = zlib.crc32(v.product_name.encode()) % 3  # mỗi đầu sách có "chất lượng" ổn định
                weights = [[3, 3, 8, 26, 60], [3, 4, 10, 30, 53], [6, 8, 14, 30, 42]][quality]
                rating = rng.choices([1, 2, 3, 4, 5], weights=weights)[0]
                r = rng.random()
                if r < 0.22:
                    comment = None
                elif r < 0.45 and rating >= 4 and v.category in D.CATEGORY_REVIEW_COMMENTS:
                    comment = rng.choice(D.CATEGORY_REVIEW_COMMENTS[v.category])
                else:
                    comment = rng.choice(D.REVIEW_COMMENTS[rating])
            product_id = self.q("SELECT product_id FROM product_variants WHERE id = %s", (v.id,)).fetchone()[0]
            self.q(
                "INSERT INTO reviews (product_id, user_id, order_item_id, rating, comment, is_approved, created_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (product_id, cust.id, item_id, rating, comment, approved, created),
            )
            self.bump("reviews")

    def simulate(self) -> None:
        rng = self.rng
        day = self.start_day
        first = True
        while day <= self.now.date():
            self.restock(day, initial=first)
            first = False
            n = poisson(self.day_rate(day), rng)
            hour_w = list(HOUR_WEIGHTS)
            if any(p.kind == "flash" and p.starts.date() == day for p in self.promos):
                hour_w[0] *= 6  # săn sale lúc 0h
            times = sorted(
                at(day, rng.choices(range(24), weights=hour_w)[0], rng.randint(0, 59), rng.randint(0, 59))
                for _ in range(n)
            )
            for t in times:
                if t > self.now - timedelta(minutes=5):
                    continue
                eligible = [c for c in self.customers if c.weight > 0 and c.joined <= t and not c.is_demo]
                if not eligible:
                    continue
                weights = [c.weight * (4 if c.orders == 0 and (t - c.joined).days < 3 else 1) for c in eligible]
                if any(c.is_demo for c in self.customers) and rng.random() < 0.012:
                    cust = next(c for c in self.customers if c.is_demo)
                else:
                    cust = rng.choices(eligible, weights=weights)[0]
                lines = self.pick_lines(t, cust)
                if lines:
                    self.create_order(t, cust, lines)
            day += timedelta(days=1)

    # -- 7. kịch bản test cho tài khoản demo --------------------------------
    def demo_scenarios(self) -> list[tuple[str, str, str]]:
        demo = next((c for c in self.customers if c.is_demo), None)
        if demo is None:
            return []
        rng = self.rng
        popular = sorted((v for v in self.variants if v.is_default and v.on_hand > 5), key=lambda v: -v.pop)[:12]

        def lines(k: int):
            picked = rng.sample(popular, k=k)
            return [(v, 1, v.price, None) for v in picked]

        n = self.now
        plans = [
            ("Đã giao hôm qua, chưa đánh giá: test POST /reviews và POST /refunds", n - timedelta(days=4),
             {"method": "cod", "outcome": "normal", "confirm_at": n - timedelta(days=4) + timedelta(hours=2),
              "ship_at": n - timedelta(days=3), "deliver_at": n - timedelta(days=1)}),
            ("Đang giao: staff test chuyển sang delivered", n - timedelta(days=2),
             {"method": "cod", "outcome": "normal", "confirm_at": n - timedelta(days=2) + timedelta(hours=1),
              "ship_at": n - timedelta(days=1), "stop_at": "shipping"}),
            ("Đã xác nhận: staff test chuyển sang shipping hoặc hủy", n - timedelta(hours=20),
             {"method": "cod", "outcome": "normal", "confirm_at": n - timedelta(hours=18), "stop_at": "confirmed"}),
            ("Chờ thanh toán online: test POST /orders/{id}/payment/simulate", n - timedelta(minutes=25),
             {"method": "simulated_gateway", "no_payment": True, "stop_at": "pending"}),
            ("COD chờ xác nhận: test khách tự hủy đơn", n - timedelta(hours=2),
             {"method": "cod", "outcome": "normal", "confirm_at": n + timedelta(hours=1)}),
        ]
        result = []
        for title, t, plan in plans:
            plan["no_promo"] = True
            _oid, code, status = self.create_order(t, demo, lines(rng.randint(1, 2)), plan, after_sales=False)
            result.append((code, status, title))
        return result

    def seed_open_refunds(self, k: int = 4) -> None:
        """Vài yêu cầu hoàn tiền mới gửi, chưa ai xử lý -> staff test POST /refunds/{id}/process."""
        rng = self.rng
        rows = self.q(
            """
            SELECT o.id, o.total_amount, o.updated_at FROM orders o JOIN users u ON u.id = o.user_id
            WHERE o.status = 'delivered' AND u.email <> 'customer@tbookstore.vn'
              AND o.updated_at BETWEEN %s AND %s
              AND NOT EXISTS (SELECT 1 FROM refund_requests r WHERE r.order_id = o.id)
            ORDER BY o.id
            """,
            (self.now - timedelta(days=7), self.now - timedelta(hours=6)),
        ).fetchall()
        for order_id, total, delivered_at in rng.sample(rows, k=min(k, len(rows))):
            reason, scope = rng.choice(D.REFUND_REASONS)
            amount = total
            if scope == "item":
                lines = self.q("SELECT line_total FROM order_items WHERE order_id = %s ORDER BY id", (order_id,)).fetchall()
                amount = rng.choice(lines)[0]
            requested = delivered_at + (self.now - delivered_at) * rng.uniform(0.3, 0.9)
            self.q("INSERT INTO refund_requests (order_id, reason, refund_amount, requested_at) VALUES (%s, %s, %s, %s)",
                   (order_id, reason, amount, requested))
            self.bump("refunds_requested")

    # -- 8. giỏ hàng đang dở -------------------------------------------------
    def seed_carts(self) -> None:
        rng = self.rng
        active = [v for v in self.variants if v.on_hand > 0]
        buyers = [c for c in self.customers if c.weight > 0 and not c.is_demo]
        demo = [c for c in self.customers if c.is_demo]
        for cust in rng.sample(buyers, k=min(25, len(buyers))) + demo:
            updated = self.now - timedelta(hours=rng.uniform(0.5, 240))
            cart_id = self.q(
                "INSERT INTO carts (user_id, created_at, updated_at) VALUES (%s, %s, %s) "
                "ON CONFLICT (user_id) DO NOTHING RETURNING id",
                (cust.id, updated - timedelta(days=rng.randint(0, 20)), updated),
            ).fetchone()
            if cart_id is None:
                continue
            for v in rng.sample(active, k=rng.randint(1, 3)):
                price, _flash = self.effective_price(v, self.now)
                self.q(
                    "INSERT INTO cart_items (cart_id, product_variant_id, quantity, unit_price_snapshot) "
                    "VALUES (%s, %s, %s, %s)",
                    (cart_id[0], v.id, rng.choice([1, 1, 1, 2]), price),
                )
            self.bump("carts")

    # -- 9. ghi số liệu cuối kỳ --------------------------------------------
    def finalize(self) -> None:
        with self.conn.cursor() as cur:
            cur.executemany(
                "UPDATE inventories SET quantity_on_hand = %s, reorder_level = %s, updated_at = %s "
                "WHERE product_variant_id = %s",
                [(v.on_hand, v.reorder_level, v.last_move or self.start, v.id) for v in self.variants],
            )
            for p in self.promos:
                for fsi_id, _price, _limit, sold in p.flash_items.values():
                    cur.execute("UPDATE flash_sale_items SET quantity_sold = %s WHERE id = %s", (sold, fsi_id))
        # VIP100K: đặt giới hạn đúng bằng số lượt đã dùng -> dùng tiếp sẽ báo hết lượt
        vip = next(p for p in self.promos if p.kind == "vip")
        if vip.used:
            self.q("UPDATE promotions SET usage_limit = %s WHERE id = %s", (vip.used, vip.id))
        negative = [v.sku for v in self.variants if v.on_hand < 0]
        if negative:
            raise RuntimeError(f"Tồn kho âm, dừng lại: {negative}")

    def run(self) -> list[tuple[str, str, str]]:
        self.seed_reference_data()
        self.seed_catalog()
        self.seed_customers()
        self.seed_promotions()
        self.simulate()
        scenarios = self.demo_scenarios()
        self.seed_open_refunds()
        self.seed_carts()
        self.finalize()
        return scenarios


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--days", type=int, default=180, help="số ngày lịch sử bán hàng (mặc định 180)")
    parser.add_argument("--customers", type=int, default=160, help="số khách hàng sinh thêm (mặc định 160)")
    parser.add_argument("--orders-per-day", type=float, default=8, help="số đơn trung bình mỗi ngày (mặc định 8)")
    parser.add_argument("--seed", type=int, default=2026, help="seed ngẫu nhiên, cùng seed cho cùng dữ liệu")
    parser.add_argument("--dry-run", action="store_true", help="chạy thử rồi rollback, không ghi gì")
    args = parser.parse_args()

    with psycopg.connect(get_settings().database_url) as conn:
        if conn.execute("SELECT 1 FROM products WHERE sku LIKE %s LIMIT 1", (f"{SKU_PREFIX}%",)).fetchone():
            print("DB đã có dữ liệu seed_realistic (sản phẩm SKU TBS-...), không chạy lại.")
            return 0
        seeder = Seeder(conn, args)
        scenarios = seeder.run()
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()

    c = seeder.counts
    print(f"Khoảng thời gian: {seeder.start_day:%d/%m/%Y} → {seeder.now:%d/%m/%Y %H:%M}")
    print(f"Sách: {c.get('products', 0)} đầu sách, {c.get('variants', 0)} phiên bản · "
          f"Nhà cung cấp mới: {c.get('suppliers', 0)} · Lô nhập: {c.get('import_lots', 0)} ({c.get('import_items', 0)} dòng)")
    print(f"Khách hàng: {c.get('customers', 0)} ({c.get('addresses', 0)} địa chỉ) · Nhân viên mới: {c.get('staff', 0)}")
    print(f"Đơn hàng: {c.get('orders', 0)} — "
          + ", ".join(f"{s} {c.get('orders_' + s, 0)}" for s in ("delivered", "shipping", "confirmed", "pending", "cancelled")))
    print(f"Khuyến mãi: {c.get('promotions', 0)} (dùng {c.get('promotion_usages', 0)} lượt) · "
          f"Flash sale items: {c.get('flash_sale_items', 0)}")
    print(f"Đánh giá: {c.get('reviews', 0)} · Hoàn tiền: "
          + ", ".join(f"{s} {c.get('refunds_' + s, 0)}" for s in ("requested", "refunded", "rejected")))
    print(f"Giỏ hàng đang dở: {c.get('carts', 0)}")
    if scenarios:
        print("\nĐơn để test với customer@tbookstore.vn / Customer@123:")
        for code, status, title in scenarios:
            print(f"  {code:<22} {status:<10} {title}")
    print(f"\nMật khẩu: khách hàng mới {CUSTOMER_PASSWORD} · nhân viên mới {STAFF_PASSWORD}")
    print("Đã rollback (--dry-run), DB không đổi." if args.dry_run else "Xong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
