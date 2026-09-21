# 📚 Quản lý thương mại điện tử (E-Commerce) 

- **Sinh viên:** Đoàn Thị Thu Linh — MSSV `12423020`
- **Hình thức thực hiện:** Cá nhân
- **Đề tài:** Hệ thống quản lý cửa hàng bán sách TbookStore

---

## 1. Giới thiệu

TBookStore mô phỏng nghiệp vụ của một cửa hàng sách có chủ shop thuê nhân viên bán hàng, phục vụ khách mua sách online: quản lý danh mục sách, tồn kho theo lô nhập, giỏ hàng, đặt hàng, khuyến mãi/flash sale, báo cáo doanh thu, và các yêu cầu nền tảng bắt buộc của môn học (xác thực, phân quyền, audit log, cache, bảo mật, kiểm thử, container hoá).

Dự án kế thừa schema và ý tưởng nghiệp vụ từ một prototype trước đó (`bookstore-management-express-address` — Node.js/Express/MySQL/EJS) và được viết lại hoàn toàn trên stack theo yêu cầu đề bài, tách riêng Backend (Web API) và Frontend (SPA).

## 2. Vai trò người dùng (RBAC)

| Vai trò | Mô tả |
|---|---|
| **Admin** | Chủ cửa hàng — toàn quyền: sản phẩm, khuyến mãi, quản lý nhân viên, báo cáo tổng, cấu hình hệ thống, audit log |
| **Staff** | Nhân viên — quản lý sản phẩm/tồn kho, nhập kho, xử lý đơn hàng (xác nhận, cập nhật vận chuyển), xem báo cáo theo ca |
| **Customer** | Khách hàng — duyệt sách, giỏ hàng, đặt hàng, thanh toán, theo dõi đơn, đánh giá sách |

## 3. Tính năng chính

- **Xác thực & phân quyền:** đăng ký/đăng nhập, JWT (access + refresh token), RBAC 3 vai trò theo màn hình & hành động
- **Danh mục & tồn kho:** CRUD sách (thuộc tính, thể loại, nhà cung cấp), tìm kiếm/lọc/sắp xếp/phân trang, nhập kho theo lô
- **Giỏ hàng & đặt hàng:** giỏ hàng, checkout với gateway thanh toán giả lập, trạng thái đơn hàng (`Pending → Confirmed → Shipping → Delivered/Cancelled`), lịch sử trạng thái
- **Khuyến mãi:** voucher theo %/số tiền cố định, flash sale có giới hạn số lượng
- **Sau bán hàng:** trả hàng/hoàn tiền, đánh giá sách (chỉ khi đơn đã giao)
- **Báo cáo:** doanh thu theo ngày/tháng, top sách bán chạy, doanh thu theo nhân viên xử lý đơn
- **Nền tảng & vận hành:** audit log, soft-delete, import/export Excel, xuất hoá đơn/báo cáo PDF, hàng đợi tác vụ nền (email, báo cáo lớn), cache Redis, health check, logging có cấu trúc
- **Chất lượng & bảo mật:** Swagger/OpenAPI, Postman collection, unit & integration test, chống SQLi/XSS/CSRF, rate limit, CORS, Docker Compose, CI cơ bản

## 4. Kiến trúc & Công nghệ

| Thành phần | Công nghệ |
|---|---|
| Backend API | FastAPI (Python 3.12) chạy trên Uvicorn |
| Validation / DTO | Pydantic v2 |
| Data access | psycopg 3 (SQL thuần, gọi function PostgreSQL) |
| Cơ sở dữ liệu | PostgreSQL |
| Frontend | AngularJS (SPA, gọi API qua JWT) |
| Cache | Redis |
| Job nền | Celery (broker Redis) |
| Xuất PDF | ReportLab |
| Logging | structlog |
| Container hoá | Docker Compose (`api` + `postgres` + `redis` + `mailhog`) |
| Test | pytest + httpx (unit + integration) |

Frontend và Backend tách rời hoàn toàn: Backend chỉ cung cấp REST API (Swagger UI/OpenAPI do FastAPI tự sinh), Frontend là ứng dụng AngularJS độc lập gọi API qua HTTP + JWT interceptor.

## 5. Cấu trúc thư mục

```
TBookStore/
├── backend/
│   ├── app/
│   │   ├── main.py                # Khởi tạo FastAPI, đăng ký router, middleware
│   │   ├── routers/               # Endpoint theo module (auth, books, cart, orders...)
│   │   ├── services/              # Business logic
│   │   ├── repositories/          # Truy cập DB bằng psycopg, gọi function PostgreSQL
│   │   ├── schemas/               # Pydantic models (request/response DTO, enums)
│   │   ├── core/                  # Cấu hình, DB pool, JWT/RBAC, Redis, Celery, PDF, logging
│   │   └── scripts/               # migrate.py: chạy schema.sql, functions.sql, seed.sql
│   ├── tests/                     # Unit & integration tests (pytest)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── app/                   # AngularJS modules, controllers, services
│       ├── views/                 # Templates theo role: admin/ staff/ customer/
│       └── assets/                # CSS, hình ảnh
├── database/
│   ├── schema.sql                 # Script tạo bảng (PostgreSQL)
│   ├── migrations/                # Thay đổi bảng đánh số (001_*.sql...), chạy 1 lần mỗi file
│   ├── functions.sql              # 12 function nghiệp vụ (PostgreSQL), chạy lại mỗi lần migrate
│   └── seed.sql                   # Dữ liệu mẫu (≥ 2.000 bản ghi)
├── docs/
│   ├── SRS.md
│   ├── ERD.png
│   └── TBookStore.postman_collection.json
├── docker-compose.yml
├── .env.example
└── README.md
```

## 6. Yêu cầu hệ thống

- [Python 3.12+](https://www.python.org/downloads/)
- [Docker](https://www.docker.com/) & Docker Compose
- Node.js ≥ 18 (nếu cần build/serve Frontend riêng khi phát triển)
- PostgreSQL client (pgAdmin / DBeaver / psql) — tuỳ chọn, để xem dữ liệu

## 7. Cài đặt & chạy dự án

```bash
# 1. Clone repository
git clone https://github.com/<username>/TBookStore.git
cd TBookStore

# 2. Tạo file cấu hình môi trường
cp .env.example .env
# Chỉnh các biến: DB connection string, JWT secret, Redis, SMTP (Mailhog)...

# 3. Khởi động toàn bộ hạ tầng (API + PostgreSQL + Redis + Mailhog)
docker-compose up -d --build

# 4. Khởi tạo schema + seed dữ liệu mẫu
docker exec -it tbookstore-api python -m app.scripts.migrate --seed

# 5. Truy cập
# API & Swagger:   http://localhost:8000/docs   (OpenAPI JSON: /openapi.json)
# Frontend:        http://localhost:4200
# Mailhog (email test): http://localhost:8025
```

Tài khoản mặc định sau khi seed (đổi mật khẩu ngay khi triển khai thật):

| Vai trò | Email/Username | Mật khẩu |
|---|---|---|
| Admin | admin@tbookstore.vn | `Admin@123` |
| Staff | staff@tbookstore.vn | `Staff@123` |
| Customer | customer@tbookstore.vn | `Customer@123` |

> Dùng đuôi `.vn` (không phải `.local`/`.test`) vì thư viện validate email (`pydantic[email]`) coi các TLD đặc biệt đó là special-use domain và từ chối ngay khi validate request.

### 7.1. API versioning

Toàn bộ API (trừ `/health`, `/health/db` — health check không versioning theo quy ước chung) được mount ở **`/api/v1/...`**, ví dụ `http://localhost:8000/api/v1/products`.

Đường dẫn cũ không có prefix (`/products`, `/categories`...) **vẫn chạy song song**, đánh dấu `deprecated` trong Swagger (`/docs`) để biết cần chuyển sang `/api/v1/...` — không phá vỡ client/Postman đã tích hợp trước khi có versioning. Khi cần một phiên bản API mới có breaking change thật sự, thêm router mới mount ở `/api/v2/...` trong `backend/app/main.py`, giữ nguyên `/api/v1` không đổi cho client cũ.

## 8. Kiểm thử

```bash
cd backend
pip install -r requirements.txt
pytest --cov=app --cov-report=term-missing
```

Mục tiêu coverage: 30–40%, ưu tiên luồng đặt hàng và thanh toán.

## 9. Tài liệu

- [`docs/SRS.md`](docs/SRS.md) — tài liệu yêu cầu phần mềm
- [`docs/ERD.png`](docs/ERD.png) — sơ đồ thực thể quan hệ
- [`docs/TBookStore.postman_collection.json`](docs/TBookStore.postman_collection.json) — bộ test API bằng Postman
- Video demo: *(cập nhật link sau khi quay)*

## 10. Lộ trình phát triển

Dự án triển khai trong 4 sprint (1 tuần/sprint), làm cá nhân:

| Sprint | Nội dung chính |
|---|---|
| Sprint 1 | Nền tảng: setup FastAPI + psycopg, JWT, RBAC, CRUD danh mục, Swagger, Docker khung |
| Sprint 2 | Danh mục sách, quản lý nhân viên, nhập kho theo lô, audit log, cache Redis |
| Sprint 3 | Giỏ hàng, checkout, đơn hàng & trạng thái, khuyến mãi/flash sale, đánh giá |
| Sprint 4 | Báo cáo, xuất PDF, job nền, test, bảo mật, Docker hoàn chỉnh, tài liệu & demo |

## 11. Ghi nhận

Schema và một số ý tưởng nghiệp vụ được tham khảo từ prototype cá nhân trước đó (`bookstore-management-express-address`), được viết lại toàn bộ trên stack FastAPI + PostgreSQL + AngularJS theo yêu cầu môn học.

## 12. Giấy phép

Dự án phục vụ mục đích học tập trong khuôn khổ môn Lập trình Web API.
