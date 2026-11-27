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
| Data access | psycopg 3 — **không viết SQL trong Python**, mọi đọc/ghi đều gọi function PostgreSQL định nghĩa sẵn trong `database/functions.sql` (xem mục 5.1) |
| Cơ sở dữ liệu | PostgreSQL |
| Frontend | AngularJS (SPA, gọi API qua JWT) |
| Cache | Redis |
| Job nền | Celery (broker Redis) |
| Xuất PDF | ReportLab |
| Logging | structlog |
| API Gateway | Nginx (`gateway/nginx.conf`) — cổng vào duy nhất, xem mục 7.2 |
| Container hoá | Docker Compose (`gateway` + `api` + `celery-worker` + `redis` + `mailhog`); PostgreSQL cài trên máy (cổng 5432), `postgres` trong Docker chỉ còn là tuỳ chọn (profile `docker-db`) |
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
│   ├── functions.sql              # 83 function (PostgreSQL), chạy lại mỗi lần migrate — xem mục 5.1
│   └── seed.sql                   # Dữ liệu mẫu (≥ 2.000 bản ghi)
├── docs/
│   ├── SRS.md
│   ├── ERD.png
│   └── TBookStore.postman_collection.json
├── docker-compose.yml
└── README.md
```

### 5.1. Quy ước truy cập dữ liệu — mọi đọc/ghi đều qua function PostgreSQL

`backend/app/repositories/*.py` **không được viết câu SQL trực tiếp** (không
`INSERT/UPDATE/SELECT ... FROM <table>` trong Python) — mỗi hàm repository chỉ
gọi 1 function tương ứng trong `database/functions.sql`, ví dụ:

```python
# backend/app/repositories/category_repo.py
async def create(conn, *, name, slug, parent_id, is_active):
    cur = await conn.execute(
        "SELECT * FROM create_category(%s, %s, %s, %s)", (name, slug, parent_id, is_active)
    )
    ...
```

Lý do: toàn bộ logic đọc/ghi nằm tập trung ở 1 chỗ (`functions.sql`) — sửa
nghiệp vụ chỉ sửa 1 file, không phải lục từng file Python; đồng thời có thể
gọi lại các function này từ nơi khác (script, tool khác) ngoài FastAPI mà vẫn
đảm bảo đúng logic.

Quy tắc khi thêm tính năng mới (Sprint 3/4 trở đi):
- **CRUD đơn giản** (insert/update/select 1-2 bảng, không cần khóa transaction
  phức tạp): viết 1 function SQL/PLpgSQL tương ứng trong `functions.sql`,
  service gọi qua repository như trên.
- **Nghiệp vụ nhiều bảng/nhiều bước cần atomic** (đặt hàng, thanh toán, trừ
  tồn kho...): bắt buộc viết PLpgSQL function xử lý trọn vẹn trong 1
  transaction (xem ví dụ `place_order()`, `restock_from_import()`).
- Hàm `UPDATE` không tự "chỉ sửa field được gửi" bằng SQL động — nhận đủ giá
  trị cuối cùng. Việc merge "field cũ + field client gửi (`exclude_unset`)"
  làm ở tầng **service** (Python), trước khi gọi repository — xem
  `category_service.update_category()` làm ví dụ mẫu.
- Function đổi kiểu trả về (thêm/bớt cột) phải `DROP FUNCTION IF EXISTS` trước
  `CREATE OR REPLACE` cùng chữ ký cũ (Postgres không cho đổi return type khi
  `CREATE OR REPLACE`).

## 6. Yêu cầu hệ thống

- [Python 3.12+](https://www.python.org/downloads/)
- [Docker](https://www.docker.com/) & Docker Compose
- Node.js ≥ 18 (nếu cần build/serve Frontend riêng khi phát triển)
- [PostgreSQL](https://www.postgresql.org/download/) cài trên máy (bản 16+, cổng 5432) — bộ cài Windows có sẵn **pgAdmin 4** và **SQL Shell (psql)** để xem dữ liệu

## 7. Cài đặt & chạy dự án

**Cơ sở dữ liệu chạy ngoài Docker** (PostgreSQL cài trên máy). Các container `api` và `celery-worker` kết nối ra máy host qua `host.docker.internal:5432`, nên pgAdmin trên máy và API luôn thấy **cùng một dữ liệu**. Tạo user + database một lần (bằng tài khoản `postgres` trong pgAdmin hoặc SQL Shell):

```sql
CREATE ROLE tbookstore LOGIN PASSWORD 'tbookstore';
CREATE DATABASE tbookstore OWNER tbookstore;
```

```bash
# 1. Clone repository
git clone https://github.com/<username>/TBookStore.git
cd TBookStore

# 2. Tạo file .env ở thư mục gốc (không đưa lên git) với các biến:
#    DATABASE_URL=postgresql://tbookstore:<mật khẩu>@localhost:5432/tbookstore
#    REDIS_URL=redis://localhost:6379/0
#    JWT_SECRET=<chuỗi ngẫu nhiên dài>
#    SMTP_HOST=localhost
#    SMTP_PORT=1025
#    RATE_LIMIT_PER_MINUTE=300
#    (Thiếu biến nào thì backend dùng giá trị mặc định trong backend/app/core/config.py)

# 3. Khởi động hạ tầng (Gateway + API + Celery + Redis + Mailhog; DB là PostgreSQL trên máy)
docker compose up -d --build

# 4. Khởi tạo schema + function + 3 tài khoản mẫu (chạy lại an toàn: chỉ cập nhật function)
docker exec -it tbookstore-api python -m app.scripts.migrate --seed

# 5. (Tuỳ chọn) Nạp dữ liệu bán hàng thực tế: ~113 đầu sách, 160 khách, ~1.900 đơn
#    trong 6 tháng, đánh giá, hoàn tiền, khuyến mãi. Chỉ chạy 1 lần trên DB vừa migrate.
docker exec -it tbookstore-api python -m app.scripts.seed_realistic

# 6. Truy cập
# API (qua gateway): http://localhost:5080/api/v1/...
# Swagger:           http://localhost:5080/docs   (OpenAPI JSON: /openapi.json)
# Frontend:        http://localhost:4200
# Mailhog (email test): http://localhost:8025
# Xem dữ liệu:       pgAdmin -> PostgreSQL -> Databases -> tbookstore (localhost:5432)
```

Làm lại DB từ đầu (xoá toàn bộ dữ liệu của database `tbookstore`, không ảnh hưởng database khác):

```bash
psql -h localhost -U tbookstore -d tbookstore -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker exec -it tbookstore-api python -m app.scripts.migrate --seed
docker exec -it tbookstore-api python -m app.scripts.seed_realistic
docker exec tbookstore-redis sh -c "redis-cli --scan --pattern 'cache:*' | xargs -r redis-cli del"
```

> Muốn chạy PostgreSQL trong Docker thay vì trên máy: `docker compose --profile docker-db up -d postgres` (cổng host 5433) và đổi `DATABASE_URL` của `api` + `celery-worker` trong `docker-compose.yml` về `postgresql://tbookstore:tbookstore@postgres:5432/tbookstore`.

Tài khoản mặc định sau khi seed (đổi mật khẩu ngay khi triển khai thật):

| Vai trò | Email/Username | Mật khẩu |
|---|---|---|
| Admin | admin@tbookstore.vn | `Admin@123` |
| Staff | staff@tbookstore.vn | `Staff@123` |
| Customer | customer@tbookstore.vn | `Customer@123` |

> Dùng đuôi `.vn` (không phải `.local`/`.test`) vì thư viện validate email (`pydantic[email]`) coi các TLD đặc biệt đó là special-use domain và từ chối ngay khi validate request.

### 7.1. API versioning

Toàn bộ API (trừ `/health`, `/health/db` — health check không versioning theo quy ước chung) được mount ở **`/api/v1/...`**, ví dụ `http://localhost:5080/api/v1/products`.

Đường dẫn cũ không có prefix (`/products`, `/categories`...) **vẫn chạy song song bên trong FastAPI** (API Gateway không mở các đường dẫn này ra ngoài — xem mục 7.2), đánh dấu `deprecated` trong Swagger (`/docs`) để biết cần chuyển sang `/api/v1/...` — không phá vỡ client/Postman đã tích hợp trước khi có versioning. Khi cần một phiên bản API mới có breaking change thật sự, thêm router mới mount ở `/api/v2/...` trong `backend/app/main.py`, giữ nguyên `/api/v1` không đổi cho client cũ.

### 7.2. API Gateway (Nginx)

Client **không gọi thẳng FastAPI**: service `api` chỉ `expose` cổng 8000 trong Docker network, mọi request đi qua service `gateway` (Nginx) ở **http://localhost:5080** (cổng host 5080 → cổng 80 trong container Nginx; đổi bằng biến `GATEWAY_PORT`, vd `GATEWAY_PORT=8080 docker compose up -d`). Cấu hình: [`gateway/nginx.conf`](gateway/nginx.conf).

```
Client ──► Gateway :5080 ──► /api/v1/*                    → FastAPI api:8000
                        ├──► /docs, /redoc, /openapi.json → FastAPI (Swagger)
                        ├──► /health, /health/db          → FastAPI
                        ├──► /gateway/health              → Gateway tự trả lời
                        └──► đường dẫn khác               → 404 JSON
```

| Gateway làm gì | Chi tiết |
|---|---|
| Định tuyến | Chỉ mở `/api/v1/*`, tài liệu API và health check; còn lại trả 404 |
| Rate limit theo IP | API: 50 req/s (burst 100) — chặn flood; `/auth/login`: 30 lần/phút (burst 10). FastAPI vẫn giữ rate limit nghiệp vụ (300 req/phút — đổi bằng `RATE_LIMIT_PER_MINUTE`; login 10 lần/phút) phía sau |
| Giới hạn body | Tối đa 10 MB (đủ cho file Excel import), vượt → 413 |
| Request ID | Mỗi response có header `X-Request-ID` (dùng lại giá trị client gửi nếu có), cùng mã được chuyển cho backend |
| IP thật của client | Gắn `X-Real-IP`/`X-Forwarded-For`; Uvicorn chạy `--proxy-headers` nên `request.client.host` là IP client, không phải IP gateway |
| Header bảo mật | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`; ẩn version Nginx |
| Access log JSON | `gateway/logs/access.log` và `docker compose logs gateway` (thời gian, request_id, IP, status, thời gian xử lý của backend…) |
| Lỗi do gateway sinh ra | 404/413/429/502 trả JSON `{"detail": ...}` giống FastAPI; lỗi của FastAPI (401, 403, 409…) đi thẳng qua không bị sửa |

Kiểm tra nhanh:

```bash
curl http://localhost:5080/gateway/health        # {"status":"ok","service":"gateway"}
curl -i http://localhost:5080/api/v1/categories  # xem header X-Request-ID
docker compose logs -f gateway              # log từng request
```

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
- [`docs/TBookStore.postman_collection.json`](docs/TBookStore.postman_collection.json) — bộ test API bằng Postman (131 request, 334 assertion)
- [`docs/HUONG_DAN_TEST_API_POSTMAN.md`](docs/HUONG_DAN_TEST_API_POSTMAN.md) — hướng dẫn test API bằng Postman: import collection, token, biến id, danh sách đầy đủ API theo role
- [`docs/KICH_BAN_TEST_NHANH_MUA_HANG.md`](docs/KICH_BAN_TEST_NHANH_MUA_HANG.md) + [`docs/TBookStore_LuongMuaHang.postman_collection.json`](docs/TBookStore_LuongMuaHang.postman_collection.json) — test nhanh luồng mua hàng: xem sách → giỏ → đặt hàng → xử lý đơn → đánh giá → hoàn tiền (29 request)
- [`docs/HUONG_DAN_TEST_TUNG_API.md`](docs/HUONG_DAN_TEST_TUNG_API.md) — test tay từng API trên dữ liệu `seed_realistic` (id thật, kết quả đúng, SQL kiểm tra)
- [`docs/sql/KIEM_TRA_SAU_KHI_GOI_API.sql`](docs/sql/KIEM_TRA_SAU_KHI_GOI_API.sql) — câu SQL xem dữ liệu thay đổi sau khi gọi API
- [`docs/sql/TEST_TUNG_THU_TUC.sql`](docs/sql/TEST_TUNG_THU_TUC.sql) — gọi thử từng thủ tục PostgreSQL với id thật
- [`database/tests/kiem_tra_tat_ca_thu_tuc.sql`](database/tests/kiem_tra_tat_ca_thu_tuc.sql) — tự kiểm tra cả 84 thủ tục (PASS/FAIL), tự hoàn tác dữ liệu test
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
