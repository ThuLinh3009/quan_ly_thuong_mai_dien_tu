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
| Backend API | .NET 8 (ASP.NET Core Web API) |
| Data access | Dapper |
| Cơ sở dữ liệu | SQL Server |
| Frontend | AngularJS (SPA, gọi API qua JWT) |
| Cache | Redis |
| Job nền | Hangfire |
| Xuất PDF | QuestPDF |
| Logging | Serilog |
| Container hoá | Docker Compose (`api` + `sqlserver` + `redis` + `mailhog`) |
| Test | xUnit (unit + integration) |

Frontend và Backend tách rời hoàn toàn: Backend chỉ cung cấp REST API (có Swagger), Frontend là ứng dụng AngularJS độc lập gọi API qua HTTP + JWT interceptor.

## 5. Cấu trúc thư mục

```
TBookStore/
├── backend/
│   ├── TBookStore.Api/            # Controllers, DI, Swagger, cấu hình
│   ├── TBookStore.Application/    # Services, business logic
│   ├── TBookStore.Infrastructure/ # Dapper repositories, Redis, Hangfire, QuestPDF
│   ├── TBookStore.Domain/         # Entities, DTOs, enums
│   └── TBookStore.Tests/          # Unit & integration tests
├── frontend/
│   └── src/
│       ├── app/                   # AngularJS modules, controllers, services
│       ├── views/                 # Templates theo role: admin/ staff/ customer/
│       └── assets/                # CSS, hình ảnh
├── database/
│   ├── schema.sql                 # Script tạo bảng (SQL Server)
│   └── seed.sql                   # Dữ liệu mẫu (≥ 2.000 bản ghi)
├── docs/
│   ├── SRS.md
│   ├── ERD.png
│   └── TBookStore.postman_collection.json
├── docker-compose.yml
└── README.md
```

## 6. Yêu cầu hệ thống

- [.NET 8 SDK](https://dotnet.microsoft.com/download)
- [Docker](https://www.docker.com/) & Docker Compose
- Node.js ≥ 18 (nếu cần build/serve Frontend riêng khi phát triển)
- SQL Server client (Azure Data Studio / SSMS) — tuỳ chọn, để xem dữ liệu

## 7. Cài đặt & chạy dự án

```bash
# 1. Clone repository
git clone https://github.com/<username>/TBookStore.git
cd TBookStore

# 2. Tạo file cấu hình môi trường
cp .env.example .env
# Chỉnh các biến: DB connection string, JWT secret, Redis, SMTP (Mailhog)...

# 3. Khởi động toàn bộ hạ tầng (API + SQL Server + Redis + Mailhog)
docker-compose up -d --build

# 4. Khởi tạo schema + seed dữ liệu mẫu
docker exec -it tbookstore-api dotnet run --project TBookStore.Api -- migrate --seed

# 5. Truy cập
# API & Swagger:   http://localhost:5000/swagger
# Frontend:        http://localhost:4200
# Mailhog (email test): http://localhost:8025
```

Tài khoản mặc định sau khi seed (đổi mật khẩu ngay khi triển khai thật):

| Vai trò | Email/Username | Mật khẩu |
|---|---|---|
| Admin | admin@tbookstore.local | `Admin@123` |
| Staff | staff@tbookstore.local | `Staff@123` |
| Customer | customer@tbookstore.local | `Customer@123` |

## 8. Kiểm thử

```bash
cd backend
dotnet test /p:CollectCoverage=true
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
| Sprint 1 | Nền tảng: setup .NET 8 + Dapper, JWT, RBAC, CRUD danh mục, Swagger, Docker khung |
| Sprint 2 | Danh mục sách, quản lý nhân viên, nhập kho theo lô, audit log, cache Redis |
| Sprint 3 | Giỏ hàng, checkout, đơn hàng & trạng thái, khuyến mãi/flash sale, đánh giá |
| Sprint 4 | Báo cáo, xuất PDF, job nền, test, bảo mật, Docker hoàn chỉnh, tài liệu & demo |

## 11. Ghi nhận

Schema và một số ý tưởng nghiệp vụ được tham khảo từ prototype cá nhân trước đó (`bookstore-management-express-address`), được viết lại toàn bộ trên stack .NET 8 + Dapper + AngularJS theo yêu cầu môn học.

## 12. Giấy phép

Dự án phục vụ mục đích học tập trong khuôn khổ môn Lập trình Web API.
