# TBookStore — Đặc tả nghiệp vụ (SRS)

Đề tài: Quản lý thương mại điện tử (E-Commerce) — hệ thống bán sách trực tuyến.
Tham chiếu: `database/schema.sql`, `database/functions.sql`.

## A. Vai trò & quyền hạn (RBAC)

| Vai trò | Quyền |
|---|---|
| **Admin** | Toàn quyền: danh mục/sản phẩm/NCC, quản lý nhân viên (tạo/sửa/khóa Staff), cấu hình khuyến mãi/flash sale, xem mọi báo cáo, duyệt trả hàng/hoàn tiền, audit log |
| **Staff** | Quản lý sản phẩm/tồn kho trong phạm vi được giao, tạo phiếu nhập kho, xử lý đơn hàng (xác nhận → cập nhật vận chuyển), xem báo cáo theo đơn mình xử lý |
| **Customer** | Duyệt/tìm sách, giỏ hàng, đặt hàng, thanh toán, theo dõi đơn, gửi yêu cầu trả hàng, đánh giá sách đã mua |

## B. Danh mục sản phẩm, tồn kho, biến thể

1. `categories` có cấu trúc cây (`parent_id`), không giới hạn cứng số cấp nhưng khuyến nghị tối đa 2 cấp cho UI đơn giản.
2. Mỗi `products` bắt buộc thuộc 1 category, `sku` duy nhất toàn hệ thống.
3. Một sách có thể có nhiều `product_variants` (bìa cứng/bìa mềm/ebook...), mỗi variant có `sku` riêng; giá bán = `products.base_price + product_variants.price_adjustment`.
4. Tồn kho quản lý ở **cấp variant** (1 variant ↔ 1 dòng `inventories`), không quản lý ở cấp product.
5. Nhập kho theo lô (`import_lots` gắn 1 supplier) → `restock_from_import()` cộng dồn vào `inventories.quantity_on_hand`.
6. Xóa category/product dùng soft-delete (`deleted_at`) — không xóa cứng, để không phá vỡ lịch sử đơn hàng cũ đã tham chiếu.
7. `reorder_level`: ngưỡng cảnh báo tồn kho thấp, hiển thị dashboard Staff/Admin (Sprint 4 có thể tự động hoá gửi mail cảnh báo qua Celery — chưa cài trong bản hiện tại).
8. `quantity_reserved` dùng để giữ chỗ trong lúc checkout — **giới hạn hiện tại**: `place_order()` trừ thẳng vào `quantity_on_hand` ngay khi đặt hàng thành công, chưa có bước "giữ giỏ hàng N phút" trước khi thanh toán xong.

## C. Giỏ hàng, đặt hàng, thanh toán

1. Mỗi Customer có đúng 1 `carts` (`UNIQUE(user_id)`).
2. `add_to_cart()`: nếu variant đã có trong giỏ → cộng dồn số lượng. Giá được **chụp (snapshot)** tại thời điểm thêm — sản phẩm đổi giá sau đó không ảnh hưởng dòng đã có trong giỏ cho tới khi khách thêm lại.
3. `place_order()` (checkout):
   - Bắt buộc có `address_id` đã lưu trước (từ `addresses`).
   - Khóa (`FOR UPDATE`) và kiểm tra tồn kho **từng dòng** trong giỏ trước khi trừ tiền — thiếu hàng bất kỳ dòng nào → rollback toàn bộ, báo rõ variant nào thiếu.
   - Áp mã khuyến mãi nếu có (xem mục D).
   - Tính: `subtotal` → trừ `discount_amount` → cộng `shipping_fee` (cố định demo, hiện = 30.000đ) = `total_amount`.
   - **Snapshot** `product_name_snapshot`/`sku_snapshot` vào `order_items` — lịch sử đơn không đổi dù sau này sản phẩm bị đổi tên/xóa.
   - Trừ tồn kho ngay khi đơn tạo thành công.
   - Tạo `payments` trạng thái `pending`, `method` = `cod` hoặc `simulated_gateway`.
   - **Giả lập gateway**: sau khi `payments` ở trạng thái pending, một bước riêng (thủ công demo hoặc job) cập nhật `status` thành `success`/`failed`. Payment fail **không** tự hủy đơn — Staff xử lý thủ công (huỷ đơn qua `update_order_status` → tự hoàn kho).
   - Xoá sạch `cart_items` sau khi đặt hàng thành công.
4. `order_code` sinh tự động dạng `ORD-YYYYMMDDHHMMSS-<user_id>`.

## D. Voucher/khuyến mãi, Flash sale

1. `promotions.type` = `percentage` | `fixed_amount` | `flash_sale`.
2. `percentage`/`fixed_amount`: khách nhập `code` lúc checkout — hệ thống kiểm tra còn hiệu lực (`starts_at`/`ends_at`), đạt `min_order_amount`, chưa vượt `usage_limit` tổng và `per_user_limit` (bảng `promotion_usages`). `max_discount_amount` là trần giảm khi type = percentage.
3. `flash_sale`: gắn với danh sách sản phẩm cụ thể (`flash_sale_items`), mỗi dòng có `flash_price` + `quantity_limit` riêng — khi `quantity_sold` chạm `quantity_limit` thì dừng áp giá flash cho variant đó dù promotion vẫn còn hạn.

   > ⚠️ **Việc cần làm thêm**: `place_order()` hiện chỉ xử lý voucher qua `code`; phần trừ `quantity_sold` cho flash sale khi đặt hàng **chưa được cài đặt** — cần bổ sung logic (kiểm tra variant có đang flash sale active không, ưu tiên `flash_price` thay `unit_price_snapshot`, tăng `quantity_sold`) trước khi đưa vào Sprint 3 demo.

4. `promotion_usages` ghi lại mỗi lần 1 user dùng 1 promotion cho 1 order — vừa để enforce `per_user_limit`, vừa làm dữ liệu báo cáo hiệu quả khuyến mãi.

## E. Vận chuyển, trạng thái đơn, trả hàng/hoàn tiền

1. Trạng thái đơn hàng đi **một chiều**, không nhảy cóc (đã enforce cứng trong `update_order_status()`):
   - `pending → confirmed → shipping → delivered`
   - `pending → cancelled`, `confirmed → cancelled` (không huỷ được khi đã `shipping`/`delivered`)
2. Mỗi lần đổi trạng thái ghi 1 dòng `order_status_history` (ai đổi, lúc nào, ghi chú) — đây cũng chính là audit log nghiệp vụ theo yêu cầu chung của đề bài.
3. Staff xác nhận đơn (`pending→confirmed`) coi như xác nhận đủ hàng để giao — không có bước duyệt lại tồn kho (đã trừ từ lúc đặt hàng).
4. Huỷ đơn (`→cancelled`): tự động hoàn tồn kho đúng số lượng trong `order_items` — xử lý ngay trong `update_order_status()`.
5. `shipments`: khởi tạo khi đơn chuyển `shipping`; `carrier`/`tracking_code` do Staff nhập; `delivered_at` set khi đơn về `delivered`.
6. `refund_requests`: Customer gửi yêu cầu (kèm `reason`) sau khi đơn đã `delivered` → Staff/Admin duyệt (`approved`/`rejected`) → nếu approved, xử lý hoàn tiền (giả lập), set `payments.status='refunded'` và `refund_requests.status='refunded'`.
7. `reviews` chỉ tạo được khi `order_item` thuộc order có `status='delivered'` và đúng user đã mua (enforce cứng trong `submit_review()`); 1 `order_item` chỉ review được **đúng 1 lần** (`UNIQUE(order_item_id)`).

## F. Báo cáo: doanh thu, top sản phẩm

1. Doanh thu hiện tính trên mọi `orders` có `status <> 'cancelled'` (kể cả đơn đang `pending`).

   > ⚠️ **Cần làm rõ**: có nên chỉ tính doanh thu khi `payments.status='success'` (doanh thu thực thu) thay vì mọi đơn chưa huỷ (doanh thu dự kiến)? Nên chốt với đề bài/GV trước khi hoàn thiện `get_revenue_report`.

2. `get_revenue_report(from, to)`: doanh thu + số đơn theo từng ngày trong khoảng.
3. `get_top_selling_books(from, to, limit)`: xếp hạng theo tổng số lượng bán, kèm doanh thu từng sách.
4. README có nêu "doanh thu theo nhân viên xử lý đơn" (dựa cột `orders.handled_by`) nhưng **chưa có function riêng** — cần bổ sung `get_revenue_by_staff(from, to)` nếu muốn đưa vào dashboard.
5. Cache Redis cho danh mục/báo cáo theo yêu cầu NFR — invalidate khi có đơn mới hoặc thay đổi tồn kho.

## G. Tìm kiếm, lọc, phân trang, đánh giá

1. `search_books()`: full-text search (`search_vector`, cấu hình `simple` do Postgres không có config tiếng Việt sẵn) + lọc category/khoảng giá + phân trang (`limit`/`offset`), trả kèm `total_count` để FE tính số trang.
2. `reviews`: `rating` 1–5 bắt buộc, `comment` tuỳ chọn, `is_approved` mặc định `true` (hiện tự động hiển thị ngay — có thể đổi sang chế độ Admin duyệt thủ công nếu cần kiểm duyệt nội dung).

## H. Gợi ý sách (mở rộng — đã thống nhất bổ sung ngoài đề)

- `get_book_recommendations()`: ưu tiên "khách mua cùng" (co-occurrence trong `order_items` cùng đơn hàng), bổ sung thêm "cùng danh mục" nếu chưa đủ số lượng yêu cầu.

## Tổng hợp việc còn thiếu để hoàn thiện nghiệp vụ (checklist kỹ thuật)

- [ ] Trừ `flash_sale_items.quantity_sold` + áp `flash_price` trong `place_order()`
- [ ] Chốt cách tính doanh thu (theo đơn hay theo payment thành công) trước khi hoàn thiện báo cáo
- [ ] Thêm `get_revenue_by_staff(from, to)` nếu cần báo cáo theo nhân viên
- [ ] Cơ chế callback cập nhật `payments.status` khi "gateway giả lập" trả kết quả (webhook giả lập hoặc endpoint riêng)
- [ ] Cơ chế giữ chỗ tồn kho (`quantity_reserved`) nếu muốn tránh oversell khi nhiều khách checkout cùng lúc trước khi thanh toán xong
