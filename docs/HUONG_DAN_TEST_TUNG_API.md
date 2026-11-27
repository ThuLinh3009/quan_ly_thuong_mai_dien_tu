# Hướng dẫn test từng API bằng tay (trừ đăng ký và tạo mới)

Test lần lượt từng API trên **dữ liệu có sẵn** trong DB (đã nạp `seed_realistic`), không cần tạo mới gì. Mỗi API ghi rõ: gọi bằng tài khoản nào, gửi gì, kết quả đúng là gì, và (với API ghi dữ liệu) kiểm tra lại trong pgAdmin.

**Không có trong hướng dẫn này** (là API đăng ký / tạo mới): `POST /auth/register`, `POST /categories`, `POST /suppliers`, `POST /products`, `POST /products/{id}/variants`, `POST /products/import-excel`, `POST /employees`, `POST /import-lots`, `POST /addresses`, `POST /promotions`, `POST /promotions/{id}/flash-sale-items`, `POST /orders/checkout`, `POST /refunds`, `POST /reviews`. Các API này đã có test tự động trong Postman collection.

> Id trong hướng dẫn (đơn 1880–1884, sách 3, yêu cầu hoàn tiền 16…) đúng với DB vừa nạp `seed_realistic`. Nạp lại DB thì id vẫn giống, vì seed cố định (`--seed 2026`).
> API có dấu ⚠️ **ghi dữ liệu và chỉ chạy được 1 lần** (vd đơn đã giao thì không giao lại được). Muốn test lại từ đầu: làm lại DB theo README mục 7.

---

## 0. Chuẩn bị

1. Backend đang chạy, gọi qua API Gateway: **`http://localhost:5080`**.
2. Import [`TBookStore.postman_collection.json`](TBookStore.postman_collection.json) vào Postman.
3. Lấy token: mở folder **01. Auth**, bấm Send lần lượt 3 request:
   - `Login - Admin` → lưu vào biến `{{access_token}}`
   - `Login - Staff` → `{{staff_access_token}}`
   - `Login - Customer` → `{{customer_access_token}}`
4. Với mỗi API dưới đây: tạo request mới (`Ctrl+N` → HTTP), dán URL, chọn method, rồi:
   - Cột **Token** = `admin` / `staff` / `customer`: tab **Authorization** → **Bearer Token** → điền `{{access_token}}` / `{{staff_access_token}}` / `{{customer_access_token}}`.
   - Cột **Token** = `—`: không cần token (Authorization → **No Auth**).
   - Có **Body**: tab **Body** → **raw** → **JSON**, dán nội dung.
5. Token hết hạn sau 30 phút → API trả **401** → chạy lại request Login tương ứng.
6. Kiểm tra DB sau khi gọi API: trong pgAdmin mở Query Tool → 📁 Open File → [`docs/sql/KIEM_TRA_SAU_KHI_GOI_API.sql`](sql/KIEM_TRA_SAU_KHI_GOI_API.sql). File chia mục theo API (tồn kho, giỏ hàng, đơn hàng, hoàn tiền…): sửa id ở dòng `<-- ĐỔI`, bôi đen câu SELECT, nhấn F5. Chạy 1 lần **trước** và 1 lần **sau** khi gọi API để so sánh.
7. Muốn gọi thẳng thủ tục (function) đứng sau mỗi API để xem output: mở [`docs/sql/TEST_TUNG_THU_TUC.sql`](sql/TEST_TUNG_THU_TUC.sql) — mỗi thủ tục 1 câu, ghi rõ ứng với API nào.

| Tài khoản | Email | Mật khẩu |
|---|---|---|
| Admin | `admin@tbookstore.vn` | `Admin@123` |
| Staff | `staff@tbookstore.vn` | `Staff@123` |
| Customer | `customer@tbookstore.vn` | `Customer@123` |

Mã lỗi hay gặp: **401** chưa đăng nhập/token hết hạn · **403** sai quyền · **404** không tìm thấy · **409** sai nghiệp vụ (trùng, sai trạng thái…) · **422** dữ liệu gửi lên sai định dạng · **429** gọi quá nhanh.

---

## 1. Health check

| # | Method + URL | Token | Kết quả đúng |
|---|---|---|---|
| 1.1 | `GET http://localhost:5080/gateway/health` | — | 200 `{"status":"ok","service":"gateway"}` (gateway sống) |
| 1.2 | `GET http://localhost:5080/health` | — | 200 `{"status":"ok"}` (FastAPI sống) |
| 1.3 | `GET http://localhost:5080/health/db` | — | 200 `{"status":"ok","db":1}` (kết nối được PostgreSQL) |
| 1.4 | `GET http://localhost:5080/products` (thiếu `/api/v1`) | — | **404** từ gateway: đường dẫn không public |

---

## 2. Auth

| # | Method + URL | Token | Body | Kết quả đúng |
|---|---|---|---|---|
| 2.1 | `POST http://localhost:5080/api/v1/auth/login` | — | `{"email":"customer@tbookstore.vn","password":"Customer@123"}` | 200, có `access_token`, `refresh_token`. **Copy `refresh_token`** để dùng ở 2.4–2.6 |
| 2.2 | như 2.1, sai mật khẩu `"Sai@123"` | — | | **401** "Email hoặc mật khẩu không đúng" |
| 2.3 | `GET http://localhost:5080/api/v1/auth/me` | customer | | 200, `email` = customer@…, `role` = `customer`, **không có** `password_hash` |
| 2.4 | `POST http://localhost:5080/api/v1/auth/refresh` | — | `{"refresh_token":"<dán refresh_token ở 2.1>"}` | 200, cặp token **mới** |
| 2.5 | gửi lại y hệt 2.4 (token cũ) | — | | **401** "đã bị thu hồi" (mỗi refresh token chỉ dùng 1 lần) |
| 2.6 | `POST http://localhost:5080/api/v1/auth/logout` | — | `{"refresh_token":"<refresh_token MỚI ở 2.4>"}` | 204. Gọi refresh bằng token đó → 401 |
| 2.7 | `POST http://localhost:5080/api/v1/auth/logout-all` | customer | | 204: thu hồi mọi refresh token của khách. Access token đang dùng vẫn chạy tới khi hết hạn |
| 2.8 | `POST http://localhost:5080/api/v1/auth/logout-all` | — | | **401** |

Kiểm tra DB (sau 2.7):
```sql
SELECT id, revoked_at FROM refresh_tokens WHERE user_id = 3 ORDER BY id DESC LIMIT 5;  -- đều có revoked_at
```

> Sau 2.7, chạy lại `Login - Customer` trong collection để có token mới cho các phần sau.

---

## 3. Danh mục (Categories)

Ghi/xóa chỉ **admin**. Xem thì ai cũng được.

| # | Method + URL | Token | Body | Kết quả đúng |
|---|---|---|---|---|
| 3.1 | `GET http://localhost:5080/api/v1/categories?limit=20&offset=0` | — | | 200, `items` sắp theo tên, có `total` |
| 3.2 | `GET http://localhost:5080/api/v1/categories?parent_id=1` | — | | Chỉ danh mục con của "Văn học" (Văn học Việt Nam, Văn học nước ngoài…) |
| 3.3 | `GET http://localhost:5080/api/v1/categories?keyword=thiếu nhi` | — | | Có "Thiếu nhi" |
| 3.4 | `GET http://localhost:5080/api/v1/categories/1` | — | | 200, `name` = "Văn học" |
| 3.5 | `GET http://localhost:5080/api/v1/categories/999999` | — | | **404** |
| 3.6 ⚠️ | `PUT http://localhost:5080/api/v1/categories/16` | admin | `{"name":"Danh mục test đã sửa"}` | 200, tên mới (16 là danh mục do Postman tạo) |
| 3.7 | `PUT http://localhost:5080/api/v1/categories/16` | staff | `{"name":"x"}` | **403** (staff không sửa được danh mục) |
| 3.8 | `PUT http://localhost:5080/api/v1/categories/16` | admin | `{"slug":"van-hoc"}` | **409** slug đã tồn tại |
| 3.9 ⚠️ | `DELETE http://localhost:5080/api/v1/categories/16` | admin | | 204 (xóa mềm) → gọi lại 3.4 với id 16 → **404** |

```sql
SELECT id, name, deleted_at FROM categories WHERE id = 16;   -- deleted_at có giá trị
SELECT * FROM audit_logs WHERE entity_type = 'category' ORDER BY id DESC LIMIT 3;  -- có dòng update, delete
```

---

## 4. Nhà cung cấp (Suppliers)

Xem: admin/staff. Sửa/ngưng: **admin**.

| # | Method + URL | Token | Body | Kết quả đúng |
|---|---|---|---|---|
| 4.1 | `GET http://localhost:5080/api/v1/suppliers?limit=20` | staff | | 200 |
| 4.2 | như 4.1 | customer | | **403** |
| 4.3 | `GET http://localhost:5080/api/v1/suppliers?keyword=Nhã Nam` | admin | | Có "Nhã Nam" |
| 4.4 | `GET http://localhost:5080/api/v1/suppliers/3` | admin | | 200, "Nhã Nam" |
| 4.5 ⚠️ | `PUT http://localhost:5080/api/v1/suppliers/13` | admin | `{"contact_phone":"0281234567","address":"TP.HCM"}` | 200 (13 = "NXB Test" do Postman tạo) |
| 4.6 ⚠️ | `DELETE http://localhost:5080/api/v1/suppliers/13` | admin | | 200, `is_active` = `false` (không xóa hẳn vì còn lô nhập tham chiếu) |
| 4.7 | `GET http://localhost:5080/api/v1/suppliers?is_active=false` | admin | | Có id 13 |

---

## 5. Sách (Products) và biến thể (Variants)

Xem: ai cũng được (khách chỉ thấy sách đang bán). Sửa/xóa: admin/staff.

| # | Method + URL | Token | Body | Kết quả đúng |
|---|---|---|---|---|
| 5.1 | `GET http://localhost:5080/api/v1/products?limit=20&offset=0&sort_by=created_at&sort_dir=desc` | — | | 200, khoảng 115–120 sách (`total`) |
| 5.2 | `GET http://localhost:5080/api/v1/products?keyword=nguyễn nhật ánh` | — | | Các sách của Nguyễn Nhật Ánh |
| 5.3 | `GET http://localhost:5080/api/v1/products?category_id=3&min_price=50000&max_price=100000&sort_by=base_price&sort_dir=asc` | — | | 6 sách Thiếu nhi, giá từ 55.000 đến 98.000, tăng dần |
| 5.4 | `GET http://localhost:5080/api/v1/products?limit=101` | — | | **422** (limit tối đa 100) |
| 5.5 | `GET http://localhost:5080/api/v1/products/3` | — | | 200, "Tôi Thấy Hoa Vàng Trên Cỏ Xanh", 2 biến thể (Bìa mềm id 4, Bìa cứng id 5) kèm tồn kho |
| 5.6 | `GET http://localhost:5080/api/v1/products/3/recommendations?limit=6` | — | | 200, tối đa 6 sách, `reason` = `bought_together` (mua cùng) đứng trước `same_category` |
| 5.7 | `GET http://localhost:5080/api/v1/products/3/recommendations?limit=50` | — | | **422** (limit tối đa 20) |
| 5.8 ⚠️ | `PUT http://localhost:5080/api/v1/products/121` | staff | `{"base_price":99000,"description":"Đã sửa giá"}` | 200, giá mới (121 = "Sách Test Postman") |
| 5.9 | `PUT http://localhost:5080/api/v1/products/121` | staff | `{"base_price":-1}` | **422** |
| 5.10 | `PUT http://localhost:5080/api/v1/products/121` | customer | `{"base_price":1}` | **403** |
| 5.11 ⚠️ | `PUT http://localhost:5080/api/v1/products/121` | admin | `{"is_active":false}` | 200 → gọi `GET /products/121` **không token** → **404** (khách không thấy sách ẩn); gọi bằng token admin → vẫn thấy |
| 5.12 | `GET http://localhost:5080/api/v1/products?is_active=false` | admin | | Có sách 121 |
| 5.13 ⚠️ | `PUT http://localhost:5080/api/v1/products/variants/4` | staff | `{"reorder_level":15}` | 200 (ngưỡng cảnh báo tồn kho của Bìa mềm sách 3) |
| 5.14 ⚠️ | `PATCH http://localhost:5080/api/v1/products/variants/5/deactivate` | staff | | 200, `is_active` = `false`. Thêm biến thể 5 vào giỏ (mục 9) → **409** |
| 5.15 ⚠️ | `PUT http://localhost:5080/api/v1/products/variants/5` | staff | `{"is_active":true}` | Bật lại biến thể 5 |
| 5.16 ⚠️ | `DELETE http://localhost:5080/api/v1/products/116` | staff | | 204 → `GET /products/116` → **404**; `GET /products/116/recommendations` → **404** |

```sql
SELECT id, name, base_price, is_active, deleted_at FROM products WHERE id IN (116, 121);
SELECT product_variant_id, quantity_on_hand, reorder_level FROM inventories WHERE product_variant_id IN (4, 5);
```

---

## 6. Nhân viên (Employees) — chỉ admin

| # | Method + URL | Token | Body | Kết quả đúng |
|---|---|---|---|---|
| 6.1 | `GET http://localhost:5080/api/v1/employees?limit=20` | admin | | 200, danh sách staff (không có `password_hash`) |
| 6.2 | như 6.1 | staff | | **403** |
| 6.3 | `GET http://localhost:5080/api/v1/employees?is_active=true&keyword=tran` | admin | | Nhân viên đang làm, tên có "tran" |
| 6.4 | `GET http://localhost:5080/api/v1/employees/4` | admin | | 200, `ha.tran@tbookstore.vn` |
| 6.5 ⚠️ | `PUT http://localhost:5080/api/v1/employees/4` | admin | `{"phone":"0912345678"}` | 200, số điện thoại mới |
| 6.6 ⚠️ | `PATCH http://localhost:5080/api/v1/employees/4/lock` | admin | | 200, `is_active` = `false`. Đăng nhập `ha.tran@tbookstore.vn` / `Staff@123` → **401** "Tài khoản đã bị khóa" |
| 6.7 ⚠️ | `PATCH http://localhost:5080/api/v1/employees/4/unlock` | admin | | 200, `is_active` = `true`, đăng nhập lại được |
| 6.8 ⚠️ | `DELETE http://localhost:5080/api/v1/employees/7` | admin | | 204 (7 = `bao.vo@`, nhân viên đã nghỉ, đang bị khóa) → `GET /employees/7` → **404**. Trong pgAdmin dòng vẫn còn, chỉ có thêm `deleted_at` (xóa mềm) |
| 6.9 | `GET http://localhost:5080/api/v1/employees/183` | admin | | **404**: nhân viên do Postman tạo rồi xóa mềm. pgAdmin vẫn thấy dòng 183 vì đọc thẳng bảng, API thì bỏ qua dòng có `deleted_at` |

```sql
SELECT id, email, is_active, deleted_at FROM users WHERE id IN (4, 7);
-- Danh sách nhân viên đúng như API thấy (bỏ dòng đã xóa mềm):
SELECT id, email, full_name, is_active FROM users WHERE role = 'staff' AND deleted_at IS NULL ORDER BY id;
SELECT action, entity_id, created_at FROM audit_logs WHERE entity_type = 'staff' ORDER BY id DESC LIMIT 5;
-- khóa nhân viên => mọi refresh token của người đó bị thu hồi:
SELECT count(*) FILTER (WHERE revoked_at IS NULL) AS con_hieu_luc FROM refresh_tokens WHERE user_id = 4;  -- 0 sau khi khóa
```

---

## 7. Lô nhập kho (Import lots) — admin/staff

| # | Method + URL | Token | Kết quả đúng |
|---|---|---|---|
| 7.1 | `GET http://localhost:5080/api/v1/import-lots?limit=10` | staff | 200, lô mới nhất trước, có `lot_code` |
| 7.2 | `GET http://localhost:5080/api/v1/import-lots?supplier_id=3` | staff | Chỉ lô của Nhã Nam |
| 7.3 | `GET http://localhost:5080/api/v1/import-lots/1` | staff | 200, kèm các dòng nhập (sách, số lượng, giá nhập) |
| 7.4 | `GET http://localhost:5080/api/v1/import-lots/1` | customer | **403** |

---

## 8. Địa chỉ (Addresses) — customer

| # | Method + URL | Token | Kết quả đúng |
|---|---|---|---|
| 8.1 | `GET http://localhost:5080/api/v1/addresses` | customer | 200, các địa chỉ của khách, đúng 1 địa chỉ `is_default = true` |
| 8.2 ⚠️ | `POST http://localhost:5080/api/v1/addresses/212/default` | customer | 204 → gọi lại 8.1: địa chỉ 212 thành mặc định, các địa chỉ khác `false` |
| 8.3 | `POST http://localhost:5080/api/v1/addresses/1/default` | customer | **404** (địa chỉ của người khác) |
| 8.4 | `GET http://localhost:5080/api/v1/addresses` | admin | **403** |

---

## 9. Giỏ hàng (Cart) — customer

> Nếu vừa chạy cả Postman collection, giỏ của `customer@` có thể còn hàng: gọi 9.9 (xóa giỏ) trước. 9.1 chỉ **thêm sách vào giỏ** (không tạo dữ liệu mới), cần có để test các API giỏ còn lại và xem trước đơn (10.1).

| # | Method + URL | Token | Body | Kết quả đúng |
|---|---|---|---|---|
| 9.1 | `POST http://localhost:5080/api/v1/cart/items` | customer | `{"product_variant_id":4,"quantity":2}` | 201, giỏ có Bìa mềm "Tôi Thấy Hoa Vàng…" × 2 (125.000/cuốn), `subtotal` = 250.000 |
| 9.2 | `POST http://localhost:5080/api/v1/cart/items` | customer | `{"product_variant_id":64,"quantity":1}` | Thêm "Đắc Nhân Tâm" |
| 9.3 | `GET http://localhost:5080/api/v1/cart` | customer | | 2 dòng, `subtotal` = tổng `line_total` các dòng |
| 9.4 | `PUT http://localhost:5080/api/v1/cart/items/4` | customer | `{"quantity":3}` | Số lượng thành 3, `subtotal` đổi theo |
| 9.5 | `PUT http://localhost:5080/api/v1/cart/items/4` | customer | `{"quantity":9999}` | **200**: giỏ hàng *cho phép* vượt tồn kho (thiết kế: tồn kho chỉ khóa và kiểm tra lúc đặt hàng — đặt hàng với giỏ này sẽ bị **409** "Insufficient stock") |
| 9.5b | `PUT http://localhost:5080/api/v1/cart/items/4` | customer | `{"quantity":3}` | Trả về 3 cuốn để test tiếp |
| 9.6 | `POST http://localhost:5080/api/v1/cart/items` | customer | `{"product_variant_id":4,"quantity":0}` | **422** |
| 9.7 | `DELETE http://localhost:5080/api/v1/cart/items/64` | customer | | Còn 1 dòng |
| 9.8 | `GET http://localhost:5080/api/v1/cart` | admin | | **403** (chỉ khách có giỏ) |

Để lại giỏ (sách 4 × 3) để test mục 10.1, rồi mới làm 9.9:

| 9.9 | `DELETE http://localhost:5080/api/v1/cart` | customer | | 204, giỏ trống |
|---|---|---|---|---|

---

## 10. Đơn hàng (Orders)

Đơn có sẵn của `customer@tbookstore.vn`:

| Đơn | Mã | Trạng thái | Thanh toán | Dùng để test |
|---|---|---|---|---|
| 1880 | ORD-20261123-1880 | delivered | COD | Xem chi tiết, hóa đơn PDF, đánh giá |
| 1881 | ORD-20261125-1881 | shipping | COD | Staff chuyển sang delivered |
| 1882 | ORD-20261127-1882 | confirmed | COD | Staff chuyển sang shipping |
| 1883 | ORD-20261127-1883 | pending | Online (giả lập) | Thanh toán giả lập |
| 1884 | ORD-20261127-1884 | pending | COD | Khách tự hủy |

Quy tắc chuyển trạng thái: `pending → confirmed | cancelled`, `confirmed → shipping | cancelled`, `shipping → delivered`. Đơn `delivered`/`cancelled` không đổi được nữa. Khách chỉ được **hủy** đơn của mình.

| # | Method + URL | Token | Body | Kết quả đúng |
|---|---|---|---|---|
| 10.1 | `GET http://localhost:5080/api/v1/orders/checkout/preview` | customer | | 200 (giỏ đang có 3 cuốn × 125.000): `subtotal` 375.000, `shipping_fee` 30.000, `discount_amount` 0, `total_amount` 405.000. Không tạo đơn |
| 10.2 | `GET http://localhost:5080/api/v1/orders/checkout/preview?promotion_code=WELCOME50K` | customer | | `discount_amount` = 50.000 (tạm tính ≥ 199.000), `total_amount` = 355.000 |
| 10.3 | `GET http://localhost:5080/api/v1/orders/checkout/preview?promotion_code=TAMNGUNG10` | customer | | **409** "invalid or expired" (mã đã bị tắt) |
| 10.4 | `GET http://localhost:5080/api/v1/orders/checkout/preview?promotion_code=SALE66` | customer | | **409** "invalid or expired" (mã chỉ áp dụng ngày 6/6) |
| 10.5 | `GET http://localhost:5080/api/v1/orders?limit=10` | customer | | Chỉ đơn của chính khách, mới nhất trước |
| 10.6 | `GET http://localhost:5080/api/v1/orders?status=pending` | customer | | 1883, 1884 |
| 10.7 | `GET http://localhost:5080/api/v1/orders/admin?status=shipping&limit=50` | staff | | Mọi đơn đang giao của mọi khách |
| 10.8 | `GET http://localhost:5080/api/v1/orders/admin?user_id=3&date_from=2026-11-01T00:00:00Z&date_to=2026-11-30T00:00:00Z` | admin | | Chỉ đơn tháng 11 của khách id 3 (`customer@`), có 1880–1884 |
| 10.9 | `GET http://localhost:5080/api/v1/orders/admin` | customer | | **403** |
| 10.10 | `GET http://localhost:5080/api/v1/orders/1880` | customer | | 200, chi tiết: các dòng hàng, địa chỉ, thanh toán, lịch sử trạng thái |
| 10.11 | `GET http://localhost:5080/api/v1/orders/1` | customer | | **404** (đơn của khách khác) |
| 10.12 | `GET http://localhost:5080/api/v1/orders/1880/invoice` | customer | | 200, file PDF hóa đơn (Postman: **Send and Download** để lưu file) |
| 10.13 ⚠️ | `PATCH http://localhost:5080/api/v1/orders/1882/status` | staff | `{"status":"shipping","note":"Đã bàn giao GHN"}` | 200, `status` = `shipping`, lịch sử thêm 1 dòng |
| 10.14 ⚠️ | `PATCH http://localhost:5080/api/v1/orders/1881/status` | staff | `{"status":"delivered"}` | 200, `delivered` |
| 10.15 | `PATCH http://localhost:5080/api/v1/orders/1880/status` | staff | `{"status":"pending"}` | **409** "Invalid transition from delivered to pending" |
| 10.16 | `PATCH http://localhost:5080/api/v1/orders/1884/status` | customer | `{"status":"confirmed"}` | **403** khách chỉ được hủy |
| 10.17 ⚠️ | `PATCH http://localhost:5080/api/v1/orders/1884/status` | customer | `{"status":"cancelled","note":"Đặt nhầm"}` | 200, `cancelled`; tồn kho các sách trong đơn được **cộng lại** |
| 10.18 ⚠️ | `POST http://localhost:5080/api/v1/orders/1883/payment/simulate` | customer | `{"success":true}` | 200, thanh toán `success` |
| 10.19 | gửi lại 10.18 | customer | | **409** "has no pending payment" (đã thanh toán rồi) |
| 10.20 | `POST http://localhost:5080/api/v1/orders/1880/payment/simulate` | customer | `{"success":true}` | **422** đơn COD không dùng cổng thanh toán giả lập |

```sql
-- Lịch sử trạng thái của các đơn vừa đổi
SELECT order_id, from_status, to_status, note, created_at FROM order_status_history
WHERE order_id IN (1881, 1882, 1884) ORDER BY order_id, created_at;
-- Thanh toán
SELECT order_id, method, status, paid_at FROM payments WHERE order_id BETWEEN 1880 AND 1884;
-- Tồn kho trước/sau khi hủy 1884: chạy câu này TRƯỚC và SAU bước 10.17
SELECT oi.product_variant_id, oi.quantity, i.quantity_on_hand
FROM order_items oi JOIN inventories i ON i.product_variant_id = oi.product_variant_id
WHERE oi.order_id = 1884;
```

> **Lỗi đã biết (chưa sửa):** sau 10.14 (giao COD) thanh toán 1881 vẫn `pending` thay vì `success`; sau 10.17 (hủy) thanh toán 1884 vẫn `pending`; chuyển sang shipping/delivered không tạo bản ghi `shipments`. Đây là các lỗi A1–A3 trong danh sách việc cần làm.

---

## 11. Khuyến mãi (Promotions)

Xem flash sale đang chạy: ai cũng được. Còn lại: **admin**.

| # | Method + URL | Token | Body | Kết quả đúng |
|---|---|---|---|---|
| 11.1 | `GET http://localhost:5080/api/v1/promotions/flash-sales/active?limit=10` | — | | 200, sách đang flash sale (khuyến mãi 18, tới 02/12): giá gốc, `flash_price`, số đã bán / giới hạn |
| 11.2 | `GET http://localhost:5080/api/v1/promotions?limit=50` | admin | | 200, voucher + flash sale |
| 11.3 | `GET http://localhost:5080/api/v1/promotions?type=percentage&is_active=true` | admin | | Chỉ voucher % đang bật |
| 11.4 | `GET http://localhost:5080/api/v1/promotions?limit=10` | staff | | **403** |
| 11.5 | `GET http://localhost:5080/api/v1/promotions/1` | admin | | 200, `WELCOME50K`, giảm 50.000, đơn tối thiểu 199.000 |
| 11.6 | `GET http://localhost:5080/api/v1/promotions/999999` | admin | | **404** |
| 11.7 ⚠️ | `PUT http://localhost:5080/api/v1/promotions/19` | admin | `{"value":12,"usage_limit":100}` | 200 (19 = voucher do Postman tạo) |
| 11.8 | `PUT http://localhost:5080/api/v1/promotions/19` | admin | `{"starts_at":"2026-12-31T00:00:00Z","ends_at":"2026-12-01T00:00:00Z"}` | **409** "ends_at phải sau starts_at" |
| 11.9 ⚠️ | `POST http://localhost:5080/api/v1/promotions/19/deactivate` | admin | | 200, `is_active` = `false` |
| 11.10 ⚠️ | `POST http://localhost:5080/api/v1/promotions/19/activate` | admin | | 200, `is_active` = `true` |
| 11.11 | `GET http://localhost:5080/api/v1/promotions/18/flash-sale-items` | admin | | Các sách trong đợt flash sale 18 |

---

## 12. Hoàn tiền (Refunds)

| # | Method + URL | Token | Body | Kết quả đúng |
|---|---|---|---|---|
| 12.1 | `GET http://localhost:5080/api/v1/refunds?limit=10` | customer | | Chỉ yêu cầu hoàn tiền của chính khách |
| 12.2 | `GET http://localhost:5080/api/v1/refunds/admin?status=requested` | staff | | 10 yêu cầu đang chờ duyệt (có id 16, 30, 39, 43…) |
| 12.3 | `GET http://localhost:5080/api/v1/refunds/admin` | customer | | **403** |
| 12.4 | `GET http://localhost:5080/api/v1/refunds/16` | staff | | 200, chi tiết yêu cầu + đơn ORD-20260719-374 |
| 12.5 | `GET http://localhost:5080/api/v1/refunds/16` | customer | | **404** (không phải yêu cầu của khách này) |
| 12.6 ⚠️ | `POST http://localhost:5080/api/v1/refunds/16/process` | staff | `{"approve":true}` | 200, `status` = `refunded`; thanh toán của đơn thành `refunded` |
| 12.7 ⚠️ | `POST http://localhost:5080/api/v1/refunds/30/process` | staff | `{"approve":false}` | 200, `status` = `rejected` |
| 12.8 | gửi lại 12.6 | staff | | **409** yêu cầu đã xử lý |

```sql
SELECT r.id, r.status, p.status AS payment_status
FROM refund_requests r JOIN payments p ON p.order_id = r.order_id WHERE r.id IN (16, 30);
```

---

## 13. Đánh giá (Reviews)

| # | Method + URL | Token | Kết quả đúng |
|---|---|---|---|
| 13.1 | `GET http://localhost:5080/api/v1/reviews/reviewable` | customer | Các dòng hàng **đã giao, chưa đánh giá**, mới nhất trước: đầu danh sách là 2 sách của đơn 1880 (Rừng Na Uy, Doraemon Truyện Ngắn - Tập 1) |
| 13.2 | `GET http://localhost:5080/api/v1/reviews/reviewable` | staff | **403** |
| 13.3 | `GET http://localhost:5080/api/v1/reviews/product/3?limit=10` | — | `total` = 44 đánh giá của "Tôi Thấy Hoa Vàng…", có số sao, nội dung, tên người đánh giá |
| 13.4 | `GET http://localhost:5080/api/v1/reviews/product/3/summary` | — | `{"average_rating": 4.3, "review_count": 44}` |

---

## 14. Thống kê và báo cáo — admin/staff

Tham số ngày dạng `2026-06-01T00:00:00Z` (chữ `Z` cuối = giờ UTC; **không dùng `+07:00`** trên URL vì dấu `+` bị hiểu thành dấu cách).

| # | Method + URL | Token | Kết quả đúng |
|---|---|---|---|
| 14.1 | `GET http://localhost:5080/api/v1/statistics/dashboard?date_from=2026-06-01T00:00:00Z&date_to=2026-11-28T00:00:00Z` | admin | Tổng đơn, doanh thu, đơn chờ xử lý, khách mới |
| 14.2 | `GET http://localhost:5080/api/v1/statistics/top-selling-books?date_from=2026-06-01T00:00:00Z&date_to=2026-11-28T00:00:00Z&limit=10` | staff | 10 sách bán chạy, **giảm dần** theo số lượng |
| 14.3 | `GET http://localhost:5080/api/v1/statistics/revenue-report?date_from=2026-11-01T00:00:00Z&date_to=2026-11-28T00:00:00Z` | admin | Doanh thu + số đơn theo từng ngày; ngày 11/11 cao nhất (28 đơn, ~8,3 triệu) |
| 14.4 | `GET http://localhost:5080/api/v1/statistics/revenue-report/pdf?date_from=2026-11-01T00:00:00Z&date_to=2026-11-28T00:00:00Z` | admin | File PDF báo cáo (Send and Download) |
| 14.5 | `GET http://localhost:5080/api/v1/statistics/dashboard` | admin | **422** thiếu `date_from`, `date_to` |
| 14.6 | 14.1 | customer | **403** |
| 14.7 | `POST http://localhost:5080/api/v1/reports/revenue/async` · Body `{"date_from":"2026-06-01T00:00:00Z","date_to":"2026-11-28T00:00:00Z"}` | admin | **202**, trả `task_id` (Celery xử lý nền). Copy `task_id` |
| 14.8 | `GET http://localhost:5080/api/v1/reports/revenue/async/<task_id>` | admin | `status`: `PENDING`/`STARTED` (`ready: false`) → `SUCCESS` (`ready: true`) sau vài giây |
| 14.9 | `GET http://localhost:5080/api/v1/reports/revenue/async/<task_id>/download` | admin | Khi `SUCCESS`: file PDF. Khi chưa xong: **422** |

Đối chiếu số liệu với SQL (pgAdmin):
```sql
-- Top bán chạy: so với 14.2
SELECT p.name, sum(oi.quantity) AS sl
FROM order_items oi
JOIN orders o ON o.id = oi.order_id
JOIN product_variants pv ON pv.id = oi.product_variant_id
JOIN products p ON p.id = pv.product_id
WHERE o.status <> 'cancelled' AND o.created_at >= '2026-06-01' AND o.created_at < '2026-11-28'
GROUP BY p.name ORDER BY sl DESC LIMIT 10;
```

> **Lưu ý về doanh thu (lỗi A4, chưa sửa):** hiện doanh thu cộng mọi đơn chưa hủy, kể cả đơn chờ xử lý và đơn đã hoàn tiền.

---

## 15. Gateway và rate limit

| # | Thao tác | Kết quả đúng |
|---|---|---|
| 15.1 | Gửi bất kỳ request nào, mở tab **Headers** của response | Có `X-Request-ID`; tra được trong `gateway/logs/access.log` |
| 15.2 | Gửi request có header `X-Request-ID: test-123` | Response trả lại đúng `X-Request-ID: test-123` |
| 15.3 | Đăng nhập sai mật khẩu 11 lần trong 1 phút | Lần thứ 11 → **429** |
| 15.4 | `GET http://localhost:8000/health` | Không kết nối được: FastAPI không mở cổng ra ngoài, phải đi qua gateway 5080 |
