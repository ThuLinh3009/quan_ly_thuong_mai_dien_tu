# Kịch bản test nhanh — luồng mua hàng

Một lượt mua hàng trọn vẹn, từ lúc khách xem sách tới khi được hoàn tiền: **29 request, chạy khoảng 4 giây**.

```
Đăng nhập → Xem sách → Giỏ hàng → Đặt hàng (COD) → Nhân viên xử lý đơn → Khách nhận hàng → Đánh giá → Hoàn tiền
```

Collection riêng: [`docs/TBookStore_LuongMuaHang.postman_collection.json`](TBookStore_LuongMuaHang.postman_collection.json) (không ảnh hưởng collection đầy đủ `TBookStore.postman_collection.json`).

---

## Chuẩn bị (1 lần)

1. Backend đang chạy: `docker compose up -d`, PostgreSQL trên máy đang chạy. Kiểm tra: mở `http://localhost:5080/health` thấy `{"status":"ok"}`.
2. Postman → **Import** → chọn `docs/TBookStore_LuongMuaHang.postman_collection.json`. Bên trái hiện collection **"TBookStore — Test nhanh luồng mua hàng"** với 8 folder.

Không cần chuẩn bị dữ liệu: collection dùng tài khoản mẫu `customer@tbookstore.vn` và `staff@tbookstore.vn`, **tự chọn** 1 sách còn ít nhất 2 cuốn, **tự lấy** địa chỉ mặc định của khách (chưa có thì tự tạo).

## Cách chạy

| Cách | Làm gì |
|---|---|
| **Chạy cả luồng 1 lần** | Chuột phải collection → **Run collection** → **Run**. Kết quả: 29 request, 81 kiểm tra đều xanh |
| **Đi từng bước** (để quan sát, demo) | Mở lần lượt từng request từ trên xuống → **Send** → xem Body + tab **Test Results** |
| **Dòng lệnh** | `postman collection run docs/TBookStore_LuongMuaHang.postman_collection.json` |

Mỗi lần chạy tạo **1 đơn mới**, nên chạy lại bao nhiêu lần cũng được. Khi đi từng bước, phải đi **đúng thứ tự**: mỗi bước lưu id (sách, đơn, dòng hàng…) vào biến `{{qn_…}}` cho bước sau.

---

## Các bước

Token: **K** = khách (`customer@`), **NV** = nhân viên (`staff@`), **—** = không cần đăng nhập. Collection tự gắn đúng token cho từng request.

### 1. Đăng nhập

| # | Request | Token | Kết quả đúng |
|---|---|---|---|
| 1.1 | Khách đăng nhập — `POST /auth/login` | — | 200, lưu token khách |
| 1.2 | Nhân viên đăng nhập — `POST /auth/login` | — | 200, lưu token nhân viên |

### 2. Khách xem hàng

| # | Request | Token | Kết quả đúng |
|---|---|---|---|
| 2.1 | Xem danh sách sách đang bán — `GET /products?sort_by=name` | — | Danh sách sách, tất cả `is_active = true` |
| 2.2 | Xem chi tiết sách — `GET /products/{id}` | — | Chọn được 1 biến thể còn ≥ 2 cuốn. Tên sách được chọn hiện ngay trong Test Results, vd *"Chọn: 10 Vạn Câu Hỏi Vì Sao — Bìa mềm, tồn 24"*. Sách hết hàng: chạy Runner tự thử sách kế tiếp; đi từng bước thì bấm Send lại |
| 2.3 | Xem điểm đánh giá — `GET /reviews/product/{id}/summary` | — | `average_rating`, `review_count` (ghi lại số lượt để so ở bước 7.4) |
| 2.4 | Xem gợi ý sách tương tự — `GET /products/{id}/recommendations` | — | ≤ 5 sách, không có chính sách đang xem |

### 3. Giỏ hàng

| # | Request | Token | Kết quả đúng |
|---|---|---|---|
| 3.1 | Làm trống giỏ — `DELETE /cart` | K | 204 (bắt đầu từ giỏ trống) |
| 3.2 | Thêm 2 cuốn vào giỏ — `POST /cart/items` | K | 201, giỏ có đúng sách đã chọn, số lượng 2 |
| 3.3 | Xem giỏ — `GET /cart` | K | `subtotal` = 2 × đơn giá |

### 4. Đặt hàng

| # | Request | Token | Kết quả đúng |
|---|---|---|---|
| 4.1 | Xem trước đơn — `GET /orders/checkout/preview` | K | Phí ship 30.000; tổng = tạm tính − giảm giá + ship. Chưa tạo đơn |
| 4.2 | Đặt hàng COD — `POST /orders/checkout` | K | 201: đơn `pending`, thanh toán `cod`, **tổng tiền đúng bằng lúc xem trước**, mã đơn dạng `ORD-YYYYMMDD-id` |
| 4.3 | Giỏ trống sau khi đặt — `GET /cart` | K | `items` rỗng |
| 4.4 | Tồn kho đã trừ — `GET /products/{id}` | — | Tồn kho = trước khi mua − 2 |
| 4.5 | Khách xem đơn vừa đặt — `GET /orders/{id}` | K | `pending`, 1 dòng hàng, 1 dòng lịch sử, thanh toán `pending` |

### 5. Nhân viên xử lý đơn

| # | Request | Token | Kết quả đúng |
|---|---|---|---|
| 5.1 | Khách thử tự xác nhận đơn — `PATCH /orders/{id}/status` | K | **403**: khách chỉ được hủy đơn của mình |
| 5.2 | Nhân viên xem đơn chờ xử lý — `GET /orders/admin?status=pending` | NV | Có đơn vừa đặt |
| 5.3 | Xác nhận đơn → `confirmed` | NV | 200 |
| 5.4 | Giao cho vận chuyển → `shipping` | NV | 200 |
| 5.5 | Đã giao → `delivered` | NV | 200 |
| 5.6 | Chuyển sai luồng `delivered → confirmed` | NV | **409** "Invalid transition" |

### 6. Khách nhận hàng

| # | Request | Token | Kết quả đúng |
|---|---|---|---|
| 6.1 | Theo dõi đơn — `GET /orders/{id}` | K | `delivered`, lịch sử đủ 4 bước `pending > confirmed > shipping > delivered` |
| 6.2 | Tải hóa đơn PDF — `GET /orders/{id}/invoice` | K | File PDF (trong Postman: mũi tên cạnh Send → **Send and Download**) |

### 7. Đánh giá

| # | Request | Token | Kết quả đúng |
|---|---|---|---|
| 7.1 | Sách chờ đánh giá — `GET /reviews/reviewable` | K | Có sách của đơn vừa nhận |
| 7.2 | Đánh giá 5 sao — `POST /reviews` | K | 201, trả về `id` |
| 7.3 | Đánh giá lần 2 cùng sách — `POST /reviews` | K | **409**: mỗi dòng hàng chỉ đánh giá 1 lần |
| 7.4 | Điểm đánh giá đã cập nhật — `GET /reviews/product/{id}/summary` | — | `review_count` tăng đúng 1 so với bước 2.3 |

### 8. Trả hàng, hoàn tiền

| # | Request | Token | Kết quả đúng |
|---|---|---|---|
| 8.1 | Khách gửi yêu cầu hoàn tiền — `POST /refunds` | K | 201, `requested` |
| 8.2 | Nhân viên duyệt — `POST /refunds/{id}/process` `{"approve": true}` | NV | 200, `refunded` |
| 8.3 | Khách xem lại đơn — `GET /orders/{id}` | K | Thanh toán của đơn = `refunded` |

---

## Xem lại trong database (pgAdmin)

Mã đơn vừa tạo nằm trong response của bước 4.2 (`id`, `order_code`). Mở [`docs/sql/KIEM_TRA_SAU_KHI_GOI_API.sql`](sql/KIEM_TRA_SAU_KHI_GOI_API.sql), đổi id đơn ở mục **D1–D5** rồi chạy để thấy: tiền đơn khớp, các dòng hàng, tồn kho, lịch sử 4 trạng thái, thanh toán, đánh giá (mục F), hoàn tiền (mục E).

## Lưu ý — lỗi nghiệp vụ đã biết (chưa sửa)

Kịch bản này **không kiểm tra** 2 điểm dưới đây vì code hiện tại còn sai, xem trong DB sẽ thấy:
- Sau bước 5.5 (giao đơn COD thành công), thanh toán của đơn vẫn `pending` — lẽ ra là `success` (lỗi A2).
- Chuyển sang `shipping` / `delivered` không tạo bản ghi trong bảng `shipments` (lỗi A3).
