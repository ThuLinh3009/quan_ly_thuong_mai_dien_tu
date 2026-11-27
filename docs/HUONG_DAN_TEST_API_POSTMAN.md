# Hướng dẫn test API TBookStore bằng Postman (dành cho người mới)

Tài liệu này dành cho người **không rành backend** — làm theo từng bước, copy nguyên link/body đã viết sẵn, không cần hiểu code.

> 📌 Project đã có sẵn 1 bộ **Postman Collection hoàn chỉnh** tại [`docs/TBookStore.postman_collection.json`](TBookStore.postman_collection.json) — đã điền sẵn URL, body, và cả script tự động lưu token khi đăng nhập. **Cách nhanh nhất là import file đó** (xem Phần 2). Tài liệu này vừa hướng dẫn cách dùng file đó, vừa viết sẵn toàn bộ link + body dưới dạng văn bản để bạn đọc/copy tay nếu muốn tạo request riêng.

---

## 0. Vài khái niệm cần biết trước (đọc 2 phút)

- **Method**: mỗi request có 1 "động từ" đi kèm —
  - `GET` = xem/lấy dữ liệu (không đổi gì trong hệ thống)
  - `POST` = tạo mới
  - `PUT` = sửa toàn bộ
  - `PATCH` = sửa một phần (ví dụ đổi trạng thái)
  - `DELETE` = xoá (hệ thống này xoá mềm — dữ liệu không mất hẳn)
- **Role (vai trò)**: hệ thống có 3 role — `admin` (quản trị), `staff` (nhân viên), `customer` (khách hàng). Mỗi API chỉ cho 1 hoặc vài role gọi, gọi sai role sẽ bị từ chối (lỗi 403).
- **Token (JWT)**: sau khi đăng nhập, server trả về 1 chuỗi ký tự dài gọi là `access_token` — đây là "thẻ ra vào" chứng minh bạn đã đăng nhập và role gì. Mọi request cần đăng nhập phải đính kèm token này trong header `Authorization: Bearer <token>`.
- **Mã lỗi (status code)** cần nhớ:
  | Mã | Ý nghĩa |
  |---|---|
  | 200 / 201 / 204 | Thành công (201 = tạo mới thành công, 204 = thành công nhưng không có nội dung trả về) |
  | 401 | Chưa đăng nhập / token sai hoặc hết hạn |
  | 403 | Đã đăng nhập nhưng **không đúng role** để gọi API này |
  | 404 | Không tìm thấy dữ liệu (id sai, hoặc không phải của bạn) |
  | 422 | Dữ liệu gửi lên sai định dạng (thiếu field, sai kiểu...) |
  | 429 | Gọi quá nhiều request trong thời gian ngắn (rate limit) |
  | 500 | Lỗi hệ thống |

  Khi lỗi, server luôn trả JSON dạng `{"detail": "lý do lỗi bằng tiếng Việt"}` — đọc `detail` là biết nguyên nhân.

---

## 1. Chuẩn bị môi trường

### 1.1. Cài Postman
Tải tại https://www.postman.com/downloads/ — cài xong mở lên, không cần tạo tài khoản (chọn "Skip and go to the app" nếu có hỏi).

### 1.2. Khởi động backend
Đảm bảo **PostgreSQL trên máy** đang chạy (Windows: service `postgresql-x64-18`, cổng 5432) — DB không chạy trong Docker. Mở terminal tại thư mục gốc project (`D:\phat-trien-web`) và chạy:

```bash
docker compose up -d --build
docker exec -it tbookstore-api python -m app.scripts.migrate --seed
```

Lệnh đầu khởi động hạ tầng (API Gateway + API + Celery + Redis + Mailhog). Lệnh sau tạo bảng và chèn **dữ liệu mẫu** (3 tài khoản admin/staff/customer + vài sản phẩm mẫu) — bạn sẽ dùng các tài khoản này để test ngay dưới đây. Nếu DB đã nạp `seed_realistic` thì có thêm 113 đầu sách, 160 khách, ~1.900 đơn (xem README mục 7).

Xem dữ liệu trực tiếp: mở **pgAdmin 4** → PostgreSQL 18 → Databases → `tbookstore` → Schemas → public → Tables (chuột phải bảng → View/Edit Data). Đây đúng là DB mà API đang dùng.

### 1.3. Kiểm tra server đã sống chưa
Mở Postman, tạo request mới:
```
GET http://localhost:5080/health
```
Nhấn **Send** → nếu thấy `{"status": "ok"}` là server đã chạy tốt. Có thể xem toàn bộ danh sách API trực quan (Swagger) tại: http://localhost:5080/docs

> **Mọi request đều đi qua API Gateway (Nginx) ở `http://localhost:5080`** — FastAPI không còn mở cổng 8000 ra ngoài (xem README mục 7.2).
> - `GET http://localhost:5080/gateway/health` → `{"status":"ok","service":"gateway"}`: gateway sống (không cần backend).
> - Mỗi response có header **`X-Request-ID`** (tab *Headers* trong Postman) — dùng mã này để tra dòng log tương ứng trong `gateway/logs/access.log`.
> - Đường dẫn cũ không có `/api/v1` (vd `/products`) bị gateway trả **404**.
> - Gửi quá dồn dập → gateway trả **429** `"Quá nhiều yêu cầu tới API Gateway..."`; backend tắt → **502**.
> - Collection ghi thẳng URL `http://localhost:5080/api/v1/...` (không dùng biến). Nếu bạn đã import bản cũ (có `{{api_url}}`/`{{base_url}}` hoặc `localhost:8000`), xóa collection cũ rồi import lại.

### 1.4. Tài khoản mẫu có sẵn sau khi seed

| Role | Email | Password |
|---|---|---|
| Admin | `admin@tbookstore.vn` | `Admin@123` |
| Staff | `staff@tbookstore.vn` | `Staff@123` |
| Customer | `customer@tbookstore.vn` | `Customer@123` |

### 1.5. Sản phẩm mẫu có sẵn (để test giỏ hàng/đặt hàng ngay, không cần tạo mới)

| product_id | Tên sách | variant_id | Biến thể | Giá |
|---|---|---|---|---|
| 1 | Số Đỏ | 1 | Bìa mềm | 85.000đ |
| 1 | Số Đỏ | 2 | Bìa cứng | 115.000đ |
| 2 | Nhà Giả Kim | 3 | Bìa mềm | 79.000đ |

> ⚠️ Các id trên đúng khi DB **vừa seed lần đầu** trên database rỗng. Nếu bạn đã tạo/xoá thêm dữ liệu trước đó, hãy gọi `GET /products` để xem id thực tế rồi thay vào các ví dụ bên dưới.
>
> DB đã nạp **`seed_realistic`** (113 đầu sách, ~1.900 đơn) có thêm dữ liệu dựng sẵn để test tay: sách 3 "Tôi Thấy Hoa Vàng Trên Cỏ Xanh" (biến thể 4, 5), 5 đơn mẫu **1880–1884** của `customer@` ở đủ các trạng thái, yêu cầu hoàn tiền đang chờ duyệt (16, 30…). Danh sách đầy đủ id và cách test từng API trên dữ liệu này: [HUONG_DAN_TEST_TUNG_API.md](HUONG_DAN_TEST_TUNG_API.md).

Tất cả URL trong tài liệu này dùng tiền tố chuẩn **`/api/v1`**, ví dụ đầy đủ: `http://localhost:5080/api/v1/products`.

---

## 2. Cách nhanh nhất: Import bộ Postman Collection có sẵn

1. Mở Postman → nút **Import** (góc trên trái) → **Choose Files** → chọn file [`docs/TBookStore.postman_collection.json`](TBookStore.postman_collection.json) trong project.
2. Sau khi import, bên trái sẽ xuất hiện collection **"TBookStore API"** với các folder chia sẵn theo chức năng (Auth, Categories, Products, Cart, Checkout & Orders, Refunds, Statistics...). Mỗi request trong đó **đã điền sẵn URL và Body mẫu**.
3. Collection có các biến dùng chung (xem bằng cách click vào tên collection → tab **Variables**):
   - (URL không dùng biến: mọi request ghi thẳng `http://localhost:5080/api/v1/...`)
   - `access_token` — token của **Admin** (tự lưu sau khi login)
   - `staff_access_token` — token của **Staff**
   - `customer_access_token` — token của **Customer**
4. **Lấy token trước khi test gì khác** — mở folder **Auth**, chạy theo thứ tự (nhấn **Send** từng request):
   - `Login - Admin` → tự động lưu token admin vào biến `access_token`
   - `Login - Staff` → tự động lưu vào `staff_access_token`
   - `Login - Customer` → tự động lưu vào `customer_access_token`

   (Mỗi request này có sẵn 1 đoạn script nhỏ ở tab "Tests" tự động chạy sau khi nhận response, tự lấy `access_token` trả về và lưu vào biến — bạn không cần copy/paste token bằng tay.)
5. Sau khi có token: các request dành cho **Admin/Staff** (danh mục, sản phẩm, nhân viên, nhập kho, thống kê...) tự dùng `{{access_token}}` (token Admin) làm mặc định. Các request dành cho **Customer** (giỏ hàng, địa chỉ, đặt hàng...) đã tự gắn sẵn `{{customer_access_token}}`. Bạn chỉ cần bấm **Send**, không cần tự gắn header Authorization.
6. Muốn test 1 API bằng role khác với role mặc định của request đó? Mở tab **Authorization** của request → chọn **Bearer Token** → đổi giá trị thành `{{staff_access_token}}` hoặc `{{customer_access_token}}` tương ứng. **Không** bấm *Edit in Parent* (sẽ đổi token của cả collection).

### 2.0. Biến id nối giữa các request — đọc trước khi bấm Send lẻ từng request

Nhiều URL/body dùng biến thay vì số cố định, vd `GET .../suppliers/{{supplier_id}}`, `"address_id": "{{address_id}}"`. Collection được viết thành **kịch bản chạy nối tiếp**: request "Create…" lưu id vừa tạo vào biến, các request sau dùng lại biến đó. Nhờ vậy chạy cả collection chỉ sửa/xóa **dữ liệu do chính nó tạo**, không đụng dữ liệu thật.

| Biến | Được gán bởi request |
|---|---|
| `{{category_id}}` | 02 · Create category (admin) |
| `{{supplier_id}}` | 03 · Create supplier (admin) |
| `{{product_id}}`, `{{variant_id}}` | 04 · Create product + variant |
| `{{staff_id}}` | 05 · Create staff |
| `{{address_id}}` | 07 · Create address |
| `{{promotion_id}}`, `{{voucher_code}}`, `{{flash_promotion_id}}` | 08 · Create voucher / Create flash sale promotion |
| `{{order_id}}`, `{{cod_order_id}}` | 10 · Checkout (simulated gateway) / Checkout (COD) |
| `{{refund_request_id}}` | 12 · Create refund request |

Khi **bấm Send lẻ** 1 request ở giữa:
- Rê chuột lên `{{tên_biến}}` để xem giá trị hiện tại. Biến chưa có giá trị (hoặc vẫn là giá trị mặc định `1`) nghĩa là chưa chạy request "Create…" tương ứng → chạy request đó trước.
- ⚠️ Cẩn thận với request **sửa/xóa**: nếu biến vẫn là `1`, request sẽ tác động lên dữ liệu thật có id 1 (vd *Delete category* xóa danh mục "Văn học").
- Các request **checkout** tự lấy địa chỉ mặc định của khách khi `{{address_id}}` trống (script ở tab *Scripts → Pre-request*), chỉ cần đã chạy `Login - Customer`.
- Cách đỡ nhớ thứ tự nhất: chuột phải 1 folder → **Run folder** — Postman chạy các request trong folder đúng thứ tự từ trên xuống.
- Muốn test 1 id cụ thể: sửa thẳng số trong ô URL (vd `.../suppliers/3`) rồi Send, **không bấm Save**; hoặc đổi *Current value* của biến ở tab **Variables** của collection.

### 2.1. Chạy toàn bộ collection tự động (Postman CLI hoặc Collection Runner)

Mọi request trong collection đều có **assertion** (tab "Tests"): kiểm tra status code, dữ liệu trả về và quy tắc nghiệp vụ (giá flash sale, voucher, tồn kho sau nhập/bán/hủy, chuyển trạng thái đơn...). Collection còn có các **ca âm**: không có token → 401, sai quyền → 403, trùng dữ liệu → 409, dữ liệu sai → 422. Các request được sắp thứ tự để chạy liền một lượt từ trên xuống.

**Chạy bằng Postman CLI** (từ thư mục gốc repo, backend đang chạy, gọi qua API Gateway ở `http://localhost:5080`):

```
postman collection run docs/TBookStore.postman_collection.json
```

- Đổi cổng gateway (biến `GATEWAY_PORT`, mặc định 5080): mở collection bằng VS Code, Find & Replace `http://localhost:5080/` → `http://localhost:<cổng mới>/`.
- Lưu kết quả lại để xem sau (PowerShell). `--output` của Postman CLI bắt buộc `postman login`, nên dùng cách ghi ra file:
  ```
  New-Item -ItemType Directory -Force test-reports | Out-Null
  postman collection run docs/TBookStore.postman_collection.json | Tee-Object "test-reports/run-$(Get-Date -Format yyyyMMdd-HHmmss).txt"
  ```
- Cuối kết quả có bảng tổng `assertions | executed | failed`, và danh sách từng assertion fail kèm body response.

**Chạy trong app Postman**: chuột phải collection → **Run collection** → **Run**.

Lưu ý:
- DB cần có 3 tài khoản mẫu trong `database/seed.sql` (admin/staff/customer). Nếu bước login fail, collection tự dừng để tránh hàng loạt lỗi 401 dây chuyền.
- Dữ liệu tạo mới (email, SKU, mã voucher, ngày khuyến mãi) sinh theo thời gian chạy, nên chạy lại nhiều lần không bị trùng. Chạy được cả trên DB chỉ có seed mẫu và DB đã nạp `seed_realistic`.
- Collection có 131 request (334 assertion), dưới rate limit **300 request/phút/IP** (biến `RATE_LIMIT_PER_MINUTE`). Chạy liên tiếp 3 lần trong cùng 1 phút sẽ gặp 429: đợi 1 phút rồi chạy lại.
- Request *Import products from Excel* dùng file mẫu `docs/postman_import_products_sample.xlsx`. Lần đầu tạo 2 sách, các lần sau báo trùng SKU ở cột `failed`; cả hai đều được test chấp nhận. Trong app Postman, nếu không tìm thấy file thì chọn lại ở tab Body.
- Request *Download async report* cần Celery worker đang chạy. Nếu worker chưa xử lý xong, API trả 422 và test cũng chấp nhận.

### 2.2. Kiểm tra kết quả trong database (pgAdmin)

Gọi API xong, muốn xem dữ liệu trong DB đã đổi đúng chưa (tồn kho, tiền đơn hàng, lịch sử trạng thái…): mở pgAdmin → chuột phải database `tbookstore` → **Query Tool** → 📁 **Open File**:

| File | Dùng khi |
|---|---|
| [`docs/sql/KIEM_TRA_SAU_KHI_GOI_API.sql`](sql/KIEM_TRA_SAU_KHI_GOI_API.sql) | Gọi API xong, xem bảng dữ liệu thay đổi đúng chưa. Chia mục theo API; sửa id ở dòng `<-- ĐỔI`, bôi đen 1 câu → F5. Chạy 1 lần **trước** và 1 lần **sau** khi gọi API để so sánh |
| [`docs/sql/TEST_TUNG_THU_TUC.sql`](sql/TEST_TUNG_THU_TUC.sql) | Gọi thẳng từng thủ tục (function) với id thật, xem output — mỗi thủ tục 1 câu, kèm API tương ứng |
| [`database/tests/kiem_tra_tat_ca_thu_tuc.sql`](../database/tests/kiem_tra_tat_ca_thu_tuc.sql) | Chạy cả file (F5): tự kiểm tra 84 thủ tục, ra bảng PASS/FAIL, xong tự hoàn tác dữ liệu test |

Lưu ý khi so pgAdmin với API: bảng `users`, `products`, `categories` **xóa mềm** (dòng vẫn còn, cột `deleted_at` có giá trị) — pgAdmin vẫn thấy, API thì trả 404. Thêm `WHERE deleted_at IS NULL` để thấy đúng như API.

Nếu bạn chỉ cần cách này thì có thể dừng ở đây. Phần 3 dưới đây là **tài liệu tham khảo đầy đủ từng API** (phòng khi bạn muốn tự tạo request tay, hoặc muốn hiểu API nào cần gửi gì).

---

## 3. Cách gắn token thủ công (nếu không dùng collection có sẵn)

Nếu bạn tự tạo request mới trong Postman (không import collection):

1. Tab **Authorization** của request → **Auth Type** chọn **Bearer Token** → ô **Token** dán access_token vừa lấy được từ bước Login.
2. Hoặc thêm header thủ công: Key = `Authorization`, Value = `Bearer <access_token>` (chú ý có khoảng trắng sau "Bearer").
3. Với request có Body, vào tab **Body** → chọn **raw** → chọn định dạng **JSON** (dropdown bên phải) → dán JSON mẫu.

---

## 4. DANH SÁCH ĐẦY ĐỦ API — chia theo quyền (role)

Ký hiệu dùng bên dưới: `{token-admin}`, `{token-staff}`, `{token-customer}` = access_token lấy được sau khi login role tương ứng ở Phần 1.4.

### 4.1. Không cần đăng nhập (Public — ai gọi cũng được)

#### Đăng ký tài khoản khách hàng
```
POST http://localhost:5080/api/v1/auth/register
```
Body:
```json
{
  "email": "customer1@tbookstore.vn",
  "password": "Customer@123",
  "full_name": "Khach Hang A",
  "phone": "0911111111"
}
```
Ghi chú: tài khoản tạo qua đây luôn mang role `customer`. Muốn có tài khoản `staff`/`admin` phải dùng API tạo nhân viên (mục 4.5) hoặc tài khoản seed sẵn.

#### Đăng nhập
```
POST http://localhost:5080/api/v1/auth/login
```
Body:
```json
{
  "email": "admin@tbookstore.vn",
  "password": "Admin@123"
}
```
Response trả về `access_token` (dùng cho các request khác) và `refresh_token` (dùng để xin token mới khi access_token hết hạn).

#### Làm mới token
```
POST http://localhost:5080/api/v1/auth/refresh
```
Body:
```json
{
  "refresh_token": "<refresh_token lấy được lúc login>"
}
```

#### Đăng xuất
```
POST http://localhost:5080/api/v1/auth/logout
```
Body:
```json
{
  "refresh_token": "<refresh_token lấy được lúc login>"
}
```
Trả về 204 (không có nội dung) — refresh_token này sẽ không dùng lại được nữa.

#### Xem danh sách danh mục sách
```
GET http://localhost:5080/api/v1/categories?limit=20&offset=0
```
Query params tuỳ chọn: `keyword` (tìm theo tên), `parent_id`, `is_active`.

#### Xem chi tiết 1 danh mục
```
GET http://localhost:5080/api/v1/categories/1
```

#### Xem danh sách sản phẩm (sách)
```
GET http://localhost:5080/api/v1/products?limit=20&offset=0&sort_by=created_at&sort_dir=desc
```
Query params tuỳ chọn: `keyword` (tìm tên/tác giả/mô tả), `category_id`, `min_price`, `max_price`, `sort_by` (`name`|`base_price`|`created_at`), `sort_dir` (`asc`|`desc`), `limit` (1–100), `offset`.

Ví dụ lọc sách Thiếu nhi giá 50–100 nghìn, rẻ trước:
```
GET http://localhost:5080/api/v1/products?category_id=3&min_price=50000&max_price=100000&sort_by=base_price&sort_dir=asc
```

#### Xem chi tiết 1 sản phẩm (gồm cả các biến thể)
```
GET http://localhost:5080/api/v1/products/1
```

#### Gợi ý sách (trang chi tiết sách: "Khách cũng mua")
```
GET http://localhost:5080/api/v1/products/3/recommendations?limit=8
```
Trả về tối đa `limit` (1–20, mặc định 8) sách, mỗi sách có `reason`:
- `bought_together` — hay được mua cùng đơn với sách đang xem (xếp trước, nhiều đơn mua cùng hơn xếp trên)
- `same_category` — cùng danh mục, bù thêm khi chưa đủ số lượng

Chỉ gợi ý sách đang bán (không có sách đã xóa/ẩn). Sách đang xem không tồn tại hoặc đã xóa → 404.

#### Xem khu vực Flash Sale đang diễn ra (trang chủ)
```
GET http://localhost:5080/api/v1/promotions/flash-sales/active?limit=20
```

#### Xem đánh giá của 1 sản phẩm
```
GET http://localhost:5080/api/v1/reviews/product/1?limit=20&offset=0
```

#### Xem điểm đánh giá trung bình của 1 sản phẩm
```
GET http://localhost:5080/api/v1/reviews/product/1/summary
```

#### Kiểm tra server / kết nối database
```
GET http://localhost:5080/health
GET http://localhost:5080/health/db
```

---

### 4.2. Cần đăng nhập (bất kỳ role nào — chỉ cần có token hợp lệ)

Header bắt buộc cho tất cả API ở mục này: `Authorization: Bearer {token-bất kỳ role}`

#### Xem thông tin tài khoản đang đăng nhập
```
GET http://localhost:5080/api/v1/auth/me
```

#### Đăng xuất khỏi mọi thiết bị
```
POST http://localhost:5080/api/v1/auth/logout-all
```
Không cần body. Trả về 204 — thu hồi **toàn bộ** refresh token của chính người đang đăng nhập (mọi máy/trình duyệt đã đăng nhập đều không xin được token mới nữa). Access token đang cầm vẫn dùng được tới khi hết hạn (tối đa 30 phút) vì JWT không thu hồi được.

Khi admin **khóa** hoặc **xóa** 1 nhân viên (mục 4.5), hệ thống cũng tự thu hồi mọi refresh token của nhân viên đó.

#### Xem chi tiết 1 đơn hàng
```
GET http://localhost:5080/api/v1/orders/1
```
Lưu ý: Customer chỉ xem được đơn **của chính mình** (xem đơn người khác sẽ bị trả lỗi 404 như không tồn tại); Admin/Staff xem được mọi đơn.

#### Đổi trạng thái đơn hàng
```
PATCH http://localhost:5080/api/v1/orders/1/status
```
Body:
```json
{
  "status": "cancelled",
  "note": "Khách đổi ý không mua nữa"
}
```
Lưu ý quan trọng — **quyền theo role khác nhau trên cùng 1 API này**:
- `status` hợp lệ: `pending` → `confirmed` → `shipping` → `delivered`, hoặc huỷ `pending`/`confirmed` → `cancelled`. Không nhảy cóc, không lùi lại.
- **Customer**: chỉ được đổi đơn **của chính mình** và chỉ được chuyển sang `cancelled` (không tự xác nhận/giao hàng được).
- **Staff/Admin**: đổi được trạng thái bất kỳ đơn nào, sang bất kỳ bước hợp lệ tiếp theo (`confirmed`, `shipping`, `delivered`, `cancelled`).
- Huỷ đơn sẽ tự động hoàn lại số lượng tồn kho.

#### Giả lập kết quả cổng thanh toán (dùng khi checkout với `payment_method = simulated_gateway`)
```
POST http://localhost:5080/api/v1/orders/1/payment/simulate
```
Body (thanh toán thành công):
```json
{
  "success": true
}
```
Body (thanh toán thất bại):
```json
{
  "success": false
}
```

#### Tải hoá đơn PDF của 1 đơn hàng
```
GET http://localhost:5080/api/v1/orders/1/invoice
```
Trong Postman: Send xong, ở phần response chọn **Save Response → Save to a file** để lưu file PDF ra xem (vì đây không phải JSON mà là file PDF).

#### Xem chi tiết 1 yêu cầu trả hàng/hoàn tiền
```
GET http://localhost:5080/api/v1/refunds/1
```
Lưu ý: Customer chỉ xem được yêu cầu của chính mình; Admin/Staff xem được tất cả.

---

### 4.3. Chỉ dành cho Customer

Header bắt buộc: `Authorization: Bearer {token-customer}`

#### Địa chỉ giao hàng

Xem danh sách địa chỉ đã lưu:
```
GET http://localhost:5080/api/v1/addresses
```

Thêm địa chỉ mới:
```
POST http://localhost:5080/api/v1/addresses
```
Body:
```json
{
  "recipient_name": "Khach Hang A",
  "phone": "0911111111",
  "line1": "123 Đường Nguyễn Trãi",
  "ward": "Phường 7",
  "district": "Quận 5",
  "province": "TP. Hồ Chí Minh",
  "is_default": true
}
```

Đặt 1 địa chỉ làm mặc định (thay `1` bằng `address_id` thực tế):
```
POST http://localhost:5080/api/v1/addresses/1/default
```
(Không cần Body, trả về 204.)

#### Giỏ hàng

Xem giỏ hàng hiện tại:
```
GET http://localhost:5080/api/v1/cart
```

Thêm sản phẩm vào giỏ (dùng `variant_id` xem ở mục 1.5):
```
POST http://localhost:5080/api/v1/cart/items
```
Body:
```json
{
  "product_variant_id": 1,
  "quantity": 2
}
```

Sửa số lượng 1 dòng trong giỏ (thay `1` cuối URL bằng `variant_id`):
```
PUT http://localhost:5080/api/v1/cart/items/1
```
Body:
```json
{
  "quantity": 3
}
```

Xoá 1 dòng khỏi giỏ:
```
DELETE http://localhost:5080/api/v1/cart/items/1
```

Xoá trống toàn bộ giỏ hàng:
```
DELETE http://localhost:5080/api/v1/cart
```

#### Đặt hàng (Checkout)

Xem trước tổng tiền (chưa tạo đơn, chưa trừ kho) — có thể thử kèm mã giảm giá:
```
GET http://localhost:5080/api/v1/orders/checkout/preview?promotion_code=SALE10
```
(Bỏ `?promotion_code=...` nếu không dùng mã.)

Đặt hàng thật — thanh toán khi nhận hàng (COD):
```
POST http://localhost:5080/api/v1/orders/checkout
```
Body:
```json
{
  "address_id": 1,
  "payment_method": "cod"
}
```

Đặt hàng thật — thanh toán qua cổng giả lập (sau đó phải gọi API "Giả lập kết quả cổng thanh toán" ở mục 4.2 để xác nhận thành công/thất bại):
```
POST http://localhost:5080/api/v1/orders/checkout
```
Body:
```json
{
  "address_id": 1,
  "payment_method": "simulated_gateway",
  "promotion_code": "SALE10"
}
```
(`promotion_code` là tuỳ chọn — bỏ field này nếu không dùng mã giảm giá.)

Xem danh sách đơn hàng của chính mình:
```
GET http://localhost:5080/api/v1/orders?limit=20&offset=0
```
Query tuỳ chọn: `status` (`pending`|`confirmed`|`shipping`|`delivered`|`cancelled`).

#### Trả hàng / hoàn tiền

Gửi yêu cầu trả hàng (chỉ gửi được khi đơn đã ở trạng thái `delivered`):
```
POST http://localhost:5080/api/v1/refunds
```
Body:
```json
{
  "order_id": 1,
  "reason": "Sách bị rách bìa khi nhận hàng"
}
```

Xem danh sách yêu cầu trả hàng của mình:
```
GET http://localhost:5080/api/v1/refunds?limit=20&offset=0
```

#### Đánh giá sách

Xem các sản phẩm đã mua, đã nhận hàng, đủ điều kiện để đánh giá:
```
GET http://localhost:5080/api/v1/reviews/reviewable
```
(Response trả về `order_item_id` — dùng giá trị này ở bước dưới.)

Gửi đánh giá (thay `order_item_id` bằng giá trị lấy ở trên):
```
POST http://localhost:5080/api/v1/reviews
```
Body:
```json
{
  "order_item_id": 1,
  "rating": 5,
  "comment": "Sách hay, giao hàng nhanh!"
}
```
`rating` từ 1-5, `comment` tuỳ chọn. Mỗi sản phẩm trong đơn chỉ đánh giá được **1 lần**.

---

### 4.4. Chỉ dành cho Staff + Admin (cả 2 role đều gọi được)

Header bắt buộc: `Authorization: Bearer {token-staff}` hoặc `{token-admin}`

#### Nhà cung cấp (xem)

```
GET http://localhost:5080/api/v1/suppliers?limit=20&offset=0
GET http://localhost:5080/api/v1/suppliers/1
```

#### Sản phẩm (tạo/sửa/xoá) — Admin và Staff đều làm được

Tạo sách mới (kèm luôn biến thể đầu tiên):
```
POST http://localhost:5080/api/v1/products
```
Body:
```json
{
  "category_id": 1,
  "sku": "SACH-100",
  "name": "Dế Mèn Phiêu Lưu Ký",
  "author": "Tô Hoài",
  "publisher": "NXB Kim Đồng",
  "description": "Truyện thiếu nhi kinh điển Việt Nam.",
  "base_price": 65000,
  "variants": [
    {
      "variant_name": "Bìa mềm",
      "sku": "SACH-100-BM",
      "price_adjustment": 0,
      "initial_quantity": 50,
      "reorder_level": 5
    }
  ]
}
```

Sửa thông tin sách (chỉ cần gửi field muốn đổi, thay `1` bằng `product_id`):
```
PUT http://localhost:5080/api/v1/products/1
```
Body:
```json
{
  "base_price": 90000,
  "description": "Mô tả mới cập nhật."
}
```

Xoá (ẩn) sách — soft-delete:
```
DELETE http://localhost:5080/api/v1/products/1
```

Thêm biến thể mới cho 1 sách đã có (thay `1` bằng `product_id`):
```
POST http://localhost:5080/api/v1/products/1/variants
```
Body:
```json
{
  "variant_name": "Ebook",
  "sku": "SACH-100-EB",
  "price_adjustment": -20000,
  "initial_quantity": 9999,
  "reorder_level": 0
}
```

Sửa 1 biến thể (thay `1` bằng `variant_id`):
```
PUT http://localhost:5080/api/v1/products/variants/1
```
Body:
```json
{
  "variant_name": "Bìa mềm (tái bản)",
  "price_adjustment": 5000
}
```

Ngừng kinh doanh 1 biến thể:
```
PATCH http://localhost:5080/api/v1/products/variants/1/deactivate
```
(Không cần Body.)

Import sách từ file Excel:
```
POST http://localhost:5080/api/v1/products/import-excel
```
Trong Postman: tab **Body** → chọn **form-data** → key = `file`, type chọn **File** → chọn file `.xlsx` từ máy.

#### Nhập kho theo lô

Xem danh sách lô nhập:
```
GET http://localhost:5080/api/v1/import-lots?limit=20&offset=0
```

Tạo phiếu nhập kho mới (tự động cộng tồn kho cho các biến thể bên trong):
```
POST http://localhost:5080/api/v1/import-lots
```
Body:
```json
{
  "supplier_id": 1,
  "items": [
    {
      "product_variant_id": 1,
      "quantity": 50,
      "unit_cost": 40000
    },
    {
      "product_variant_id": 2,
      "quantity": 20,
      "unit_cost": 60000
    }
  ]
}
```

Xem chi tiết 1 lô nhập:
```
GET http://localhost:5080/api/v1/import-lots/1
```

#### Quản lý đơn hàng (xem tất cả, không chỉ đơn của mình)

```
GET http://localhost:5080/api/v1/orders/admin?limit=20&offset=0
```
Query tuỳ chọn: `status`, `user_id`, `date_from`, `date_to` (định dạng ISO, ví dụ `2026-01-01T00:00:00`).

Đổi trạng thái / huỷ đơn: dùng chung API ở mục 4.2 (`PATCH /orders/{id}/status`), nhưng với token Staff/Admin thì đổi được sang **bất kỳ** trạng thái hợp lệ tiếp theo (không bị giới hạn chỉ huỷ như Customer).

#### Trả hàng / hoàn tiền — duyệt yêu cầu

Xem tất cả yêu cầu trả hàng của mọi khách:
```
GET http://localhost:5080/api/v1/refunds/admin?limit=20&offset=0
```
Query tuỳ chọn: `status` (`requested`|`approved`|`rejected`|`refunded`).

Duyệt hoặc từ chối 1 yêu cầu (thay `1` bằng `request_id`):
```
POST http://localhost:5080/api/v1/refunds/1/process
```
Body (duyệt):
```json
{
  "approve": true
}
```
Body (từ chối):
```json
{
  "approve": false
}
```

#### Thống kê & báo cáo

Top sách bán chạy trong khoảng thời gian:
```
GET http://localhost:5080/api/v1/statistics/top-selling-books?date_from=2026-01-01T00:00:00&date_to=2026-12-31T23:59:59&limit=10
```

Báo cáo doanh thu theo ngày:
```
GET http://localhost:5080/api/v1/statistics/revenue-report?date_from=2026-01-01T00:00:00&date_to=2026-12-31T23:59:59
```

Xuất báo cáo doanh thu dạng PDF (tải trực tiếp — trong Postman dùng "Save Response → Save to a file"):
```
GET http://localhost:5080/api/v1/statistics/revenue-report/pdf?date_from=2026-01-01T00:00:00&date_to=2026-12-31T23:59:59
```

Tổng quan dashboard (tổng đơn, tổng doanh thu, đơn đang chờ, khách hàng mới):
```
GET http://localhost:5080/api/v1/statistics/dashboard?date_from=2026-01-01T00:00:00&date_to=2026-12-31T23:59:59
```

Xuất báo cáo doanh thu PDF **chạy nền** (dùng khi báo cáo lớn, không muốn chờ) — 3 bước:

1. Kích hoạt tác vụ:
```
POST http://localhost:5080/api/v1/reports/revenue/async
```
Body:
```json
{
  "date_from": "2026-01-01T00:00:00",
  "date_to": "2026-12-31T23:59:59"
}
```
Response trả về `task_id`, dùng cho 2 bước sau.

2. Kiểm tra tác vụ đã xử lý xong chưa (thay `<task_id>` bằng giá trị ở trên):
```
GET http://localhost:5080/api/v1/reports/revenue/async/<task_id>
```
Khi `ready = true` thì qua bước 3.

3. Tải file PDF kết quả:
```
GET http://localhost:5080/api/v1/reports/revenue/async/<task_id>/download
```

---

### 4.5. Chỉ dành cho Admin

Header bắt buộc: `Authorization: Bearer {token-admin}`

#### Danh mục sách (tạo/sửa/xoá)

Tạo danh mục mới:
```
POST http://localhost:5080/api/v1/categories
```
Body:
```json
{
  "name": "Sách Giáo Khoa",
  "is_active": true
}
```
(`slug` và `parent_id` là tuỳ chọn — bỏ qua thì hệ thống tự sinh `slug` từ `name`.)

Sửa danh mục (thay `1` bằng `category_id`):
```
PUT http://localhost:5080/api/v1/categories/1
```
Body:
```json
{
  "name": "Sách Giáo Khoa (cập nhật)",
  "is_active": true
}
```

Xoá (ẩn) danh mục — soft-delete:
```
DELETE http://localhost:5080/api/v1/categories/1
```

#### Nhà cung cấp (tạo/sửa/ngừng hợp tác)

Tạo nhà cung cấp mới:
```
POST http://localhost:5080/api/v1/suppliers
```
Body:
```json
{
  "name": "NXB Giáo Dục Việt Nam",
  "contact_phone": "0243123999",
  "email": "lienhe@nxbgd.vn",
  "address": "81 Trần Thái Tông, Hà Nội",
  "is_active": true
}
```

Sửa nhà cung cấp (thay `1` bằng `supplier_id`):
```
PUT http://localhost:5080/api/v1/suppliers/1
```
Body:
```json
{
  "contact_phone": "0243999999"
}
```

Ngừng hợp tác với nhà cung cấp:
```
DELETE http://localhost:5080/api/v1/suppliers/1
```

#### Quản lý nhân viên (Staff)

Xem danh sách nhân viên:
```
GET http://localhost:5080/api/v1/employees?limit=20&offset=0
```

Tạo nhân viên mới:
```
POST http://localhost:5080/api/v1/employees
```
Body:
```json
{
  "email": "staff2@tbookstore.vn",
  "password": "Staff@123",
  "full_name": "Nguyễn Văn B",
  "phone": "0922222222"
}
```

Sửa thông tin nhân viên (thay `1` bằng `staff_id`):
```
PUT http://localhost:5080/api/v1/employees/1
```
Body:
```json
{
  "full_name": "Nguyễn Văn B (đã cập nhật)",
  "phone": "0933333333"
}
```

Khoá / mở khoá tài khoản nhân viên:
```
PATCH http://localhost:5080/api/v1/employees/1/lock
PATCH http://localhost:5080/api/v1/employees/1/unlock
```
(Không cần Body.)

Xoá (ẩn) nhân viên:
```
DELETE http://localhost:5080/api/v1/employees/1
```

#### Khuyến mãi — Mã giảm giá (Voucher)

Tạo mã giảm giá theo phần trăm:
```
POST http://localhost:5080/api/v1/promotions
```
Body:
```json
{
  "code": "SALE10",
  "type": "percentage",
  "value": 10,
  "min_order_amount": 100000,
  "max_discount_amount": 50000,
  "starts_at": "2026-01-01T00:00:00",
  "ends_at": "2026-12-31T23:59:59",
  "usage_limit": 100,
  "per_user_limit": 1,
  "is_active": true
}
```

Tạo mã giảm giá theo số tiền cố định:
```
POST http://localhost:5080/api/v1/promotions
```
Body:
```json
{
  "code": "GIAM20K",
  "type": "fixed_amount",
  "value": 20000,
  "min_order_amount": 150000,
  "starts_at": "2026-01-01T00:00:00",
  "ends_at": "2026-12-31T23:59:59",
  "is_active": true
}
```

Xem danh sách khuyến mãi:
```
GET http://localhost:5080/api/v1/promotions?limit=20&offset=0
```
Query tuỳ chọn: `type` (`percentage`|`fixed_amount`|`flash_sale`), `is_active`.

Sửa khuyến mãi (thay `1` bằng `promotion_id`):
```
PUT http://localhost:5080/api/v1/promotions/1
```
Body:
```json
{
  "value": 15,
  "ends_at": "2026-06-30T23:59:59"
}
```

Tạm ngừng / kích hoạt lại khuyến mãi:
```
POST http://localhost:5080/api/v1/promotions/1/deactivate
POST http://localhost:5080/api/v1/promotions/1/activate
```
(Không cần Body.)

#### Khuyến mãi — Flash Sale

Bước 1 — Tạo 1 promotion loại `flash_sale`:
```
POST http://localhost:5080/api/v1/promotions
```
Body:
```json
{
  "type": "flash_sale",
  "value": 1,
  "starts_at": "2026-01-01T00:00:00",
  "ends_at": "2026-01-31T23:59:59",
  "is_active": true
}
```
(Lấy `id` trả về trong response, dùng cho bước 2. `code` để trống vì flash sale không cần nhập mã.)

Bước 2 — Thêm sản phẩm vào chương trình flash sale (thay `1` bằng `promotion_id` ở bước 1):
```
POST http://localhost:5080/api/v1/promotions/1/flash-sale-items
```
Body:
```json
{
  "product_variant_id": 1,
  "flash_price": 59000,
  "quantity_limit": 30
}
```

Xem danh sách sản phẩm trong 1 chương trình flash sale:
```
GET http://localhost:5080/api/v1/promotions/1/flash-sale-items
```

---

## 5. Kịch bản test toàn trình (gợi ý thứ tự demo đầy đủ)

Làm theo đúng thứ tự dưới, chuyển đổi token theo đúng role ghi chú ở mỗi bước:

1. **[Public]** `POST /auth/register` — tạo thêm 1 khách hàng mới (hoặc dùng luôn tài khoản `customer@tbookstore.vn` có sẵn).
2. **[Public]** `POST /auth/login` với customer → lấy `access_token` của Customer.
3. **[Customer]** `GET /products` — xem danh sách sách đang bán.
4. **[Customer]** `POST /cart/items` — thêm sách vào giỏ (`product_variant_id=1`, `quantity=2`).
5. **[Customer]** `POST /addresses` — thêm địa chỉ nhận hàng.
6. **[Customer]** `GET /orders/checkout/preview` — xem trước tổng tiền.
7. **[Customer]** `POST /orders/checkout` với `payment_method="cod"` — đặt hàng, lấy `id` đơn hàng trả về.
8. **[Public]** `POST /auth/login` với admin/staff → lấy `access_token` khác.
9. **[Staff/Admin]** `GET /orders/admin` — thấy đơn vừa đặt ở trạng thái `pending`.
10. **[Staff/Admin]** `PATCH /orders/{id}/status` → `{"status": "confirmed"}`.
11. **[Staff/Admin]** `PATCH /orders/{id}/status` → `{"status": "shipping"}`.
12. **[Staff/Admin]** `PATCH /orders/{id}/status` → `{"status": "delivered"}`.
13. **[Customer]** `GET /reviews/reviewable` — thấy sản phẩm vừa nhận, đủ điều kiện đánh giá.
14. **[Customer]** `POST /reviews` — gửi đánh giá 5 sao.
15. **[Customer]** `POST /refunds` — gửi yêu cầu trả hàng cho đơn vừa nhận (nếu muốn test luồng hoàn tiền).
16. **[Staff/Admin]** `GET /refunds/admin` rồi `POST /refunds/{id}/process` → `{"approve": true}`.
17. **[Staff/Admin]** `GET /statistics/dashboard?date_from=...&date_to=...` — xem số liệu tổng quan đã cập nhật.

---

## 6. Vài lỗi hay gặp khi mới test

- **401 "Thiếu access token"**: quên gắn header `Authorization: Bearer <token>`, hoặc token đã hết hạn — login lại để lấy token mới.
- **403 "Yêu cầu role thuộc (...)"**: đang dùng token role không đủ quyền — kiểm tra lại đang dùng token Customer/Staff/Admin có đúng không.
- **404** khi xem đơn hàng/yêu cầu trả hàng của người khác: đúng thiết kế — Customer chỉ xem được dữ liệu của chính mình.
- **404 nhưng pgAdmin vẫn thấy dòng đó**: bản ghi đã bị **xóa mềm** (cột `deleted_at` có giá trị) — API bỏ qua các dòng này. Ngoài ra `GET /employees/{id}` chỉ trả tài khoản có `role = 'staff'`; id của khách hàng sẽ ra 404.
- **409 "Address 1 does not belong to user 3"** khi checkout: biến `{{address_id}}` chưa có địa chỉ của khách → chạy `07. Addresses / Create address` (hoặc xóa trắng *Current value* của `address_id` để request tự lấy địa chỉ mặc định). Xem mục 2.0.
- **Đúng mã lỗi nhưng sai lý do**: luôn đọc `detail` và tab **Test Results**, không chỉ nhìn status. Vd checkout trả 409 do địa chỉ sai thay vì do thiếu hàng — test *Báo thiếu hàng* sẽ fail.
- **422**: body gửi sai định dạng — so lại với JSON mẫu trong tài liệu này, chú ý đừng để thiếu dấu `,` hoặc gửi chữ vào field số.
- **429 "Too Many Requests"**: gọi quá nhanh — API chung giới hạn 300 request/phút/IP, API đăng nhập giới hạn chặt hơn (10 lần/phút/IP) để chống dò mật khẩu. Đợi 1 phút rồi thử lại.
- Gọi mà không thấy phản hồi gì / lỗi kết nối: kiểm tra lại `docker compose up -d` đã chạy chưa (`docker ps` phải thấy `tbookstore-gateway` và `tbookstore-api` đang `Up`), và đang gọi đúng cổng **5080** (cổng 80 và 8000 không còn dùng).
- **502 "API Gateway không kết nối được tới backend"**: gateway sống nhưng container `api` đang tắt hoặc khởi động lại → `docker compose ps`, `docker compose logs api`.
- **500 "Đã có lỗi hệ thống"** ở mọi API có đụng DB: PostgreSQL trên máy (service `postgresql-x64-18`) đang tắt → bật lại service rồi `docker compose restart api celery-worker`.
