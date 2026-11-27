-- =====================================================================
-- TEST TỪNG THỦ TỤC (function) — mỗi thủ tục 1 câu gọi với id thật trong DB
--
-- Mở trong pgAdmin: chuột phải tbookstore -> Query Tool -> 📁 Open File.
--
-- [ĐỌC] Hàm chỉ đọc dữ liệu: bôi đen 1 câu SELECT -> F5. Chạy thoải mái.
--
-- [GHI] Hàm ghi dữ liệu nằm trong khối BEGIN ... ROLLBACK để thử xong thì hủy:
--   1. Bôi đen từ BEGIN đến câu kiểm tra ngay trên ROLLBACK -> F5
--      (pgAdmin hiện kết quả câu cuối = dữ liệu sau khi hàm chạy)
--   2. Bôi đen ROLLBACK -> F5   (hủy thay đổi, DB trở lại như cũ)
--   Muốn LƯU THẬT thì chạy COMMIT thay cho ROLLBACK.
--   Quên ROLLBACK thì khi đóng tab pgAdmin sẽ hỏi Commit/Rollback -> chọn Rollback.
--
-- Id dùng trong file (có sẵn sau khi nạp seed_realistic):
--   khách customer@tbookstore.vn = 3 · nhân viên staff@ = 2, ha.tran@ = 4 · admin = 1
--   sách 3 "Tôi Thấy Hoa Vàng Trên Cỏ Xanh": biến thể 4 (bìa mềm), 5 (bìa cứng)
--   danh mục 1 "Văn học" · NCC 3 "Nhã Nam" · đơn 1880..1884 · hoàn tiền 16
--   Dữ liệu rác do Postman tạo (dùng cho sửa/xóa): danh mục 16, NCC 13, sách 116, 121
-- =====================================================================


-- =====================================================================
-- 1. SÁCH  (/api/v1/products)
-- =====================================================================

-- [ĐỌC] GET /products?keyword=kim&sort_by=base_price&sort_dir=asc
--   tham số: từ khóa, id danh mục, giá từ, giá đến, đang bán, sắp theo, chiều, limit, offset
SELECT * FROM search_books('kim', NULL, NULL, NULL, TRUE, 'base_price', 'asc', 20, 0);

-- [ĐỌC] GET /products?category_id=3&min_price=50000&max_price=100000
SELECT * FROM search_books(NULL, 3, 50000, 100000, TRUE, 'base_price', 'asc', 20, 0);

-- [ĐỌC] GET /products/3   (cột variants = danh sách biến thể kèm tồn kho)
SELECT * FROM get_book_by_id(3);

-- [ĐỌC] GET /products/3/recommendations?limit=6
SELECT * FROM get_book_recommendations(3, 6);

-- [ĐỌC] GET /products/variants/4 (dùng nội bộ khi sửa biến thể)
SELECT * FROM get_variant_by_id(4);

-- [ĐỌC] Giá bán thực tế của 1 biến thể (có flash sale thì lấy giá flash)
SELECT get_effective_unit_price(4);

-- [ĐỌC] Kiểm tra trùng trước khi tạo (true = đã có)
SELECT product_sku_exists('TBS-VN-0001'),
       product_slug_exists('toi-thay-hoa-vang-tren-co-xanh'),
       variant_sku_exists('TBS-VN-0001-BM');

-- [GHI] POST /products  (tạo sách + biến thể + tồn kho)
BEGIN;
SELECT create_product(1, 'TEST-SKU-01', 'Sách thử nghiệm', 'sach-thu-nghiem', 'Tác giả A', 'NXB Trẻ', NULL, 'Mô tả', NULL, 99000, TRUE);
SELECT * FROM create_variant((SELECT max(id) FROM products), 'Bìa mềm', 'TEST-SKU-01-BM', 0, TRUE);
SELECT create_inventory_for_variant((SELECT max(id) FROM product_variants), 20, 5);
SELECT * FROM get_book_by_id((SELECT max(id) FROM products));
ROLLBACK;

-- [GHI] PUT /products/121  (giữ nguyên các cột khác, chỉ đổi mô tả + giá)
BEGIN;
SELECT update_product(p.id, p.category_id, p.name, p.slug, p.author, p.publisher, p.isbn,
                      'Mô tả đã sửa', p.cover_image_url, 88000, p.is_active)
FROM products p WHERE p.id = 121;
SELECT id, name, description, base_price, updated_at FROM products WHERE id = 121;
ROLLBACK;

-- [GHI] DELETE /products/116  (xóa mềm)
BEGIN;
SELECT soft_delete_product(116);
SELECT id, name, is_active, deleted_at FROM products WHERE id = 116;
ROLLBACK;

-- [GHI] PUT /products/variants/5  (đổi tên + phụ phí bìa cứng)
BEGIN;
SELECT * FROM update_variant(5, 'Bìa cứng', 45000, TRUE);
SELECT get_effective_unit_price(5);
ROLLBACK;

-- [GHI] PATCH /products/variants/5/deactivate
BEGIN;
SELECT * FROM set_variant_active(5, FALSE);
SELECT get_effective_unit_price(5);        -- NULL = không bán được nữa
ROLLBACK;

-- [GHI] PUT /products/variants/4 {"reorder_level": 15}  (ngưỡng cảnh báo tồn kho)
BEGIN;
SELECT update_inventory_reorder_level(4, 15);
SELECT * FROM inventories WHERE product_variant_id = 4;
ROLLBACK;


-- =====================================================================
-- 2. DANH MỤC  (/api/v1/categories)
-- =====================================================================

-- [ĐỌC] GET /categories?limit=20
SELECT * FROM list_categories(NULL, NULL, NULL, 20, 0);

-- [ĐỌC] GET /categories?parent_id=1   (danh mục con của "Văn học")
SELECT * FROM list_categories(NULL, 1, NULL, 20, 0);

-- [ĐỌC] GET /categories?keyword=thiếu nhi
SELECT * FROM list_categories('thiếu nhi', NULL, NULL, 20, 0);

-- [ĐỌC] GET /categories/1
SELECT * FROM get_category_by_id(1);

-- [ĐỌC] Slug đã tồn tại chưa (tham số 2 = id được loại trừ khi đang sửa chính nó)
SELECT category_slug_exists('van-hoc'), category_slug_exists('van-hoc', 1);

-- [GHI] POST /categories
BEGIN;
SELECT * FROM create_category('Danh mục thử', 'danh-muc-thu', 1, TRUE);
SELECT * FROM list_categories(NULL, 1, NULL, 20, 0);
ROLLBACK;

-- [GHI] PUT /categories/16
BEGIN;
SELECT * FROM update_category(16, 'Danh mục đã sửa', 'danh-muc-da-sua', NULL, TRUE);
SELECT * FROM get_category_by_id(16);
ROLLBACK;

-- [GHI] DELETE /categories/16  (xóa mềm -> get_category_by_id trả 0 dòng)
BEGIN;
SELECT soft_delete_category(16);
SELECT * FROM get_category_by_id(16);
ROLLBACK;


-- =====================================================================
-- 3. NHÀ CUNG CẤP  (/api/v1/suppliers)
-- =====================================================================

-- [ĐỌC] GET /suppliers?keyword=nhã nam
SELECT * FROM list_suppliers('nhã nam', NULL, 20, 0);

-- [ĐỌC] GET /suppliers?is_active=false
SELECT * FROM list_suppliers(NULL, FALSE, 20, 0);

-- [ĐỌC] GET /suppliers/3
SELECT * FROM get_supplier_by_id(3);

-- [GHI] POST /suppliers
BEGIN;
SELECT * FROM create_supplier('NXB Thử Nghiệm', '0281234567', 'nxb@test.vn', 'TP.HCM', TRUE);
SELECT * FROM list_suppliers('thử nghiệm', NULL, 20, 0);
ROLLBACK;

-- [GHI] PUT /suppliers/13
BEGIN;
SELECT * FROM update_supplier(13, 'NXB Test', '0287654321', 'test@nxb.vn', 'Hà Nội', TRUE);
SELECT * FROM get_supplier_by_id(13);
ROLLBACK;

-- [GHI] DELETE /suppliers/13  (ngừng hợp tác: is_active = false)
BEGIN;
SELECT * FROM set_supplier_active(13, FALSE);
SELECT * FROM get_supplier_by_id(13);
ROLLBACK;


-- =====================================================================
-- 4. NHẬP KHO  (/api/v1/import-lots)
-- =====================================================================

-- [ĐỌC] GET /import-lots?limit=10
SELECT * FROM list_import_lots(NULL, 10, 0);

-- [ĐỌC] GET /import-lots?supplier_id=3
SELECT * FROM list_import_lots(3, 20, 0);

-- [ĐỌC] GET /import-lots/1   (cột items = các dòng nhập)
SELECT * FROM get_import_lot_by_id(1);

-- [GHI] POST /import-lots  (tạo lô -> thêm dòng nhập -> cộng tồn kho)
--   Xem tồn kho biến thể 4 TRƯỚC:
SELECT product_variant_id, quantity_on_hand FROM inventories WHERE product_variant_id = 4;
BEGIN;
SELECT * FROM create_import_lot(3, 2);                                   -- NCC 3, người nhập id 2
SELECT add_import_receipt_items((SELECT max(id) FROM import_lots),
                                ARRAY[4], ARRAY[50], ARRAY[60000]::numeric[]);  -- nhập 50 cuốn biến thể 4
SELECT restock_from_import((SELECT max(id) FROM import_lots));
SELECT product_variant_id, quantity_on_hand FROM inventories WHERE product_variant_id = 4;  -- SAU: +50
ROLLBACK;


-- =====================================================================
-- 5. KHUYẾN MÃI  (/api/v1/promotions)
-- =====================================================================

-- [ĐỌC] GET /promotions/flash-sales/active
SELECT * FROM get_active_flash_sales(20);

-- [ĐỌC] GET /promotions?type=percentage&is_active=true
SELECT * FROM list_promotions('percentage', TRUE, 50, 0);

-- [ĐỌC] GET /promotions/1
SELECT * FROM get_promotion_by_id(1);

-- [ĐỌC] GET /promotions/18/flash-sale-items
SELECT * FROM list_flash_sale_items(18);

-- [ĐỌC] Mã voucher đã tồn tại chưa
SELECT promotion_code_exists('WELCOME50K');

-- [ĐỌC] Kiểm tra voucher dùng được không (mã, id khách, tạm tính) — lỗi = không dùng được
SELECT * FROM find_valid_promotion('WELCOME50K', 3, 300000);

-- [ĐỌC] Số tiền được giảm của voucher cho 1 tạm tính
SELECT calculate_discount(p, 300000) FROM promotions p WHERE p.code = 'WELCOME50K';

-- [GHI] POST /promotions
BEGIN;
SELECT * FROM create_promotion('TEST10', 'percentage', 10, 100000, 30000,
                               now(), now() + interval '7 days', 100, 1, TRUE);
SELECT * FROM list_promotions('percentage', TRUE, 50, 0);
ROLLBACK;

-- [GHI] PUT /promotions/19
BEGIN;
SELECT * FROM update_promotion(19, 12, 50000, NULL, now(), now() + interval '30 days', 200, 1, TRUE);
ROLLBACK;

-- [GHI] POST /promotions/19/deactivate  (activate: đổi FALSE thành TRUE)
BEGIN;
SELECT * FROM set_promotion_active(19, FALSE);
ROLLBACK;

-- [GHI] POST /promotions/18/flash-sale-items  (biến thể 4 giá flash 90.000, tối đa 10 cuốn)
BEGIN;
SELECT * FROM add_flash_sale_item(18, 4, 90000, 10);
SELECT get_effective_unit_price(4);       -- giá bán giờ là 90.000
ROLLBACK;


-- =====================================================================
-- 6. ĐỊA CHỈ  (/api/v1/addresses) — khách id 3
-- =====================================================================

-- [ĐỌC] GET /addresses
SELECT * FROM list_addresses_for_user(3);

-- [ĐỌC] 1 địa chỉ
SELECT * FROM get_address_by_id(212);

-- [GHI] POST /addresses
BEGIN;
SELECT * FROM create_address(3, 'Nguyễn Văn B', '0901234567', '10 Lê Lợi', 'Phường Bến Nghé', 'Quận 1', 'TP.HCM', FALSE);
SELECT * FROM list_addresses_for_user(3);
ROLLBACK;

-- [GHI] POST /addresses/212/default
BEGIN;
SELECT set_default_address(212, 3);
SELECT id, is_default FROM list_addresses_for_user(3);
ROLLBACK;


-- =====================================================================
-- 7. GIỎ HÀNG  (/api/v1/cart) — khách id 3
-- =====================================================================

-- [ĐỌC] GET /cart
SELECT * FROM get_cart(3);

-- [ĐỌC] Tổng tiền giỏ (tham số là id GIỎ, không phải id khách)
SELECT get_cart_total((SELECT id FROM carts WHERE user_id = 3));

-- [GHI] POST /cart/items -> PUT /cart/items/4 -> DELETE /cart/items/4 -> DELETE /cart
BEGIN;
SELECT add_to_cart(3, 4, 2);                  -- thêm 2 cuốn biến thể 4
SELECT add_to_cart(3, 64, 1);                 -- thêm 1 cuốn "Đắc Nhân Tâm"
SELECT update_cart_item_quantity(3, 4, 3);    -- sửa biến thể 4 thành 3 cuốn
SELECT remove_cart_item(3, 64);               -- bỏ "Đắc Nhân Tâm"
SELECT * FROM get_cart(3);
ROLLBACK;

BEGIN;
SELECT add_to_cart(3, 4, 2);
SELECT clear_cart(3);                         -- xóa cả giỏ
SELECT * FROM get_cart(3);
ROLLBACK;


-- =====================================================================
-- 8. ĐẶT HÀNG, ĐƠN HÀNG  (/api/v1/orders)
-- =====================================================================

-- [ĐỌC] GET /orders?status=pending   (đơn của khách 3)
SELECT * FROM list_orders_for_user(3, 'pending', 20, 0);

-- [ĐỌC] GET /orders/admin?status=shipping
SELECT * FROM list_orders_admin('shipping', NULL, NULL, NULL, 20, 0);

-- [ĐỌC] GET /orders/admin?user_id=3&date_from=...&date_to=...
SELECT * FROM list_orders_admin(NULL, 3, '2026-11-01', '2026-11-30', 50, 0);

-- [ĐỌC] GET /orders/1880   (address, items, payment, status_history là JSON)
SELECT * FROM get_order_detail(1880);

-- [GHI] GET /orders/checkout/preview  +  POST /orders/checkout
BEGIN;
SELECT add_to_cart(3, 4, 2);
SELECT * FROM preview_checkout(3);                       -- xem trước, chưa có voucher
SELECT * FROM preview_checkout(3, 'WELCOME50K');         -- xem trước với voucher
SELECT place_order(3, 212, 'cod', 'WELCOME50K');         -- đặt hàng, trả về id đơn mới
SELECT * FROM get_order_detail((SELECT max(id) FROM orders));
ROLLBACK;

-- [GHI] PATCH /orders/1882/status {"status":"shipping"}
BEGIN;
SELECT update_order_status(1882, 'shipping', 2, 'Đã bàn giao GHN');
SELECT * FROM order_status_history WHERE order_id = 1882 ORDER BY id;
ROLLBACK;

-- [GHI] PATCH /orders/1884/status {"status":"cancelled"}  (khách hủy -> hoàn tồn kho)
BEGIN;
SELECT update_order_status(1884, 'cancelled', 3, 'Đặt nhầm');
SELECT oi.product_variant_id, oi.quantity, i.quantity_on_hand
FROM order_items oi JOIN inventories i ON i.product_variant_id = oi.product_variant_id
WHERE oi.order_id = 1884;
ROLLBACK;

-- [GHI] POST /orders/1883/payment/simulate {"success": true}
BEGIN;
SELECT * FROM simulate_payment_gateway(1883, TRUE, 3);
ROLLBACK;


-- =====================================================================
-- 9. ĐÁNH GIÁ  (/api/v1/reviews)
-- =====================================================================

-- [ĐỌC] GET /reviews/reviewable   (sách khách 3 đã nhận, chưa đánh giá)
SELECT * FROM list_reviewable_order_items(3);

-- [ĐỌC] GET /reviews/product/3
SELECT * FROM list_reviews_for_product(3, 10, 0);

-- [ĐỌC] GET /reviews/product/3/summary
SELECT * FROM get_product_rating_summary(3);

-- [GHI] POST /reviews  (dòng hàng 3254 thuộc đơn 1880 đã giao)
BEGIN;
SELECT submit_review(3254, 3, 5::smallint, 'Sách rất hay');
SELECT * FROM reviews ORDER BY id DESC LIMIT 1;
ROLLBACK;


-- =====================================================================
-- 10. HOÀN TIỀN  (/api/v1/refunds)
-- =====================================================================

-- [ĐỌC] GET /refunds/admin?status=requested
SELECT * FROM list_refund_requests('requested', NULL, 20, 0);

-- [ĐỌC] GET /refunds   (của khách 3)
SELECT * FROM list_refund_requests(NULL, 3, 20, 0);

-- [ĐỌC] GET /refunds/16
SELECT * FROM get_refund_request_by_id(16);

-- [GHI] POST /refunds  (đơn 1880 đã giao)
BEGIN;
SELECT * FROM create_refund_request(1880, 3, 'Sách bị lỗi in');
ROLLBACK;

-- [GHI] POST /refunds/16/process {"approve": true}   (false = từ chối)
BEGIN;
SELECT * FROM process_refund_request(16, TRUE, 2);
SELECT r.id, r.status, p.status AS payment_status
FROM refund_requests r JOIN payments p ON p.order_id = r.order_id WHERE r.id = 16;
ROLLBACK;


-- =====================================================================
-- 11. THỐNG KÊ  (/api/v1/statistics)
-- =====================================================================

-- [ĐỌC] GET /statistics/top-selling-books
SELECT * FROM get_top_selling_books('2026-06-01', '2026-11-28', 10);

-- [ĐỌC] GET /statistics/revenue-report
SELECT * FROM get_revenue_report('2026-11-01', '2026-11-28');

-- [ĐỌC] GET /statistics/dashboard
SELECT * FROM get_dashboard_summary('2026-06-01', '2026-11-28');


-- =====================================================================
-- 12. NHÂN VIÊN, ĐĂNG NHẬP  (/api/v1/employees, /api/v1/auth)
-- =====================================================================

-- [ĐỌC] GET /employees?is_active=true
SELECT * FROM list_staff(NULL, TRUE, 20, 0);

-- [ĐỌC] Tìm user (dùng khi đăng nhập / GET /auth/me / GET /employees/4)
SELECT * FROM get_user_by_email('customer@tbookstore.vn');
SELECT * FROM get_user_by_id(4);

-- [GHI] POST /auth/register, POST /employees  (role: 'customer' / 'staff')
BEGIN;
SELECT * FROM create_user('nv_thu@tbookstore.vn', 'hash', 'Nhân Viên Thử', '0909000000', 'staff');
SELECT * FROM list_staff('thử', NULL, 20, 0);
ROLLBACK;

-- [GHI] PUT /employees/4
BEGIN;
SELECT * FROM update_staff(4, 'Trần Thị Thu Hà', '0912345678');
ROLLBACK;

-- [GHI] PATCH /employees/4/lock  (unlock: đổi FALSE thành TRUE)
BEGIN;
SELECT * FROM set_staff_active(4, FALSE);
SELECT revoke_all_refresh_tokens(4);          -- khóa thì API thu hồi luôn mọi phiên đăng nhập
ROLLBACK;

-- [GHI] DELETE /employees/7  (xóa mềm -> get_user_by_id trả 0 dòng)
BEGIN;
SELECT soft_delete_staff(7);
SELECT * FROM get_user_by_id(7);
ROLLBACK;

-- [GHI] Refresh token: login tạo -> refresh kiểm tra -> logout thu hồi -> logout-all
BEGIN;
SELECT create_refresh_token(3, 'token_thu', now() + interval '7 days');
SELECT * FROM get_valid_refresh_token('token_thu');      -- 1 dòng = còn hiệu lực
SELECT revoke_refresh_token('token_thu');                -- POST /auth/logout
SELECT * FROM get_valid_refresh_token('token_thu');      -- 0 dòng = đã thu hồi
ROLLBACK;


-- =====================================================================
-- 13. NHẬT KÝ THAO TÁC (audit) — gọi tự động sau mỗi thao tác ghi của admin/staff
-- =====================================================================
BEGIN;
SELECT record_audit(1, 'update', 'product', 3, '{"base_price": 125000}', '{"base_price": 130000}');
SELECT * FROM audit_logs ORDER BY id DESC LIMIT 1;
ROLLBACK;

-- set_updated_at: là TRIGGER, không gọi trực tiếp được. Nó tự chạy khi UPDATE
-- các bảng users, products, carts, orders và đặt updated_at = thời điểm sửa.
BEGIN;
UPDATE products SET name = name WHERE id = 3;
SELECT id, updated_at FROM products WHERE id = 3;        -- updated_at = bây giờ
ROLLBACK;
