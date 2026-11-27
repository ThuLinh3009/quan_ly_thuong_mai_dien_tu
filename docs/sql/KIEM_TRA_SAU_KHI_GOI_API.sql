-- =====================================================================
-- KIỂM TRA DB SAU KHI GỌI API (TBookStore)
--
-- Cách dùng trong pgAdmin:
--   1. Chuột phải database tbookstore -> Query Tool -> nút 📁 (Open File)
--      -> chọn file này.
--   2. Tìm mục ứng với API vừa gọi (Ctrl+F theo tên API, vd "cart/items").
--   3. Sửa con số ở dòng có chú thích  <-- ĐỔI  (id sách, id đơn...).
--   4. BÔI ĐEN đúng câu SELECT của mục đó rồi nhấn F5.
--      (Không bôi đen thì pgAdmin chạy cả file và chỉ hiện kết quả câu cuối.)
--
-- Mẹo so sánh TRƯỚC / SAU:
--   chạy câu kiểm tra 1 lần TRƯỚC khi gọi API (ghi lại số), gọi API trong
--   Postman, rồi chạy lại câu đó SAU -> so 2 kết quả.
--
-- File chỉ có SELECT, chạy bao nhiêu lần cũng không làm đổi dữ liệu.
-- Mọi bảng có xóa mềm (products, categories, users) đều lọc
-- deleted_at IS NULL khi cần giống những gì API thấy.
-- =====================================================================


-- ---------------------------------------------------------------------
-- A. TỒN KHO CỦA 1 BIẾN THỂ SÁCH
--    Dùng sau: POST /import-lots (nhập kho, cộng tồn)
--              POST /orders/checkout (đặt hàng, trừ tồn)
--              PATCH /orders/{id}/status = cancelled (hủy, cộng lại tồn)
--              PUT /products/variants/{id} (đổi reorder_level, is_active)
-- ---------------------------------------------------------------------
WITH p AS (SELECT 4::bigint AS variant_id)                 -- <-- ĐỔI id biến thể
SELECT pv.id            AS variant_id,
       pr.name          AS sach,
       pv.variant_name,
       pv.sku,
       pv.is_active     AS bien_the_dang_ban,
       i.quantity_on_hand AS ton_kho,
       i.reorder_level  AS nguong_canh_bao,
       i.updated_at     AS cap_nhat_luc
FROM p
JOIN product_variants pv ON pv.id = p.variant_id
JOIN products pr        ON pr.id = pv.product_id
JOIN inventories i      ON i.product_variant_id = pv.id;

-- A2. Tồn kho mọi biến thể của 1 cuốn sách (theo id sách)
WITH p AS (SELECT 3::bigint AS product_id)                 -- <-- ĐỔI id sách
SELECT pv.id AS variant_id, pv.variant_name, pv.sku, pv.is_active,
       i.quantity_on_hand AS ton_kho, i.reorder_level
FROM p
JOIN product_variants pv ON pv.product_id = p.product_id
JOIN inventories i       ON i.product_variant_id = pv.id
ORDER BY pv.id;


-- ---------------------------------------------------------------------
-- B. NHẬP KHO — POST /api/v1/import-lots
--    Lô mới nhất + từng dòng nhập + tồn kho hiện tại của sách trong lô.
--    Đúng khi: ton_kho_hien_tai tăng đúng bằng so_luong_nhap so với trước.
-- ---------------------------------------------------------------------
SELECT l.id AS lot_id, l.lot_code, s.name AS nha_cung_cap, l.imported_at,
       ri.product_variant_id, pv.sku, ri.quantity AS so_luong_nhap, ri.unit_cost AS gia_nhap,
       i.quantity_on_hand AS ton_kho_hien_tai
FROM import_lots l
JOIN suppliers s              ON s.id = l.supplier_id
JOIN import_receipt_items ri  ON ri.import_lot_id = l.id
JOIN product_variants pv      ON pv.id = ri.product_variant_id
JOIN inventories i            ON i.product_variant_id = ri.product_variant_id
WHERE l.id = (SELECT max(id) FROM import_lots)            -- lô mới nhất; hoặc thay bằng: l.id = 55
ORDER BY ri.id;


-- ---------------------------------------------------------------------
-- C. GIỎ HÀNG — POST /cart/items, PUT /cart/items/{id}, DELETE /cart/items/{id}, DELETE /cart
--    Đúng khi: thêm cùng sách 2 lần thì số lượng CỘNG DỒN (không ra 2 dòng);
--    tong_dong = so_luong x gia_chup; giỏ trống sau DELETE /cart.
-- ---------------------------------------------------------------------
WITH p AS (SELECT 'customer@tbookstore.vn'::text AS email) -- <-- ĐỔI email khách
SELECT c.id AS cart_id, ci.product_variant_id, pr.name AS sach, pv.variant_name,
       ci.quantity AS so_luong, ci.unit_price_snapshot AS gia_chup,
       ci.quantity * ci.unit_price_snapshot AS tong_dong,
       i.quantity_on_hand AS ton_kho,
       c.updated_at
FROM p
JOIN users u            ON u.email = p.email
JOIN carts c            ON c.user_id = u.id
JOIN cart_items ci      ON ci.cart_id = c.id
JOIN product_variants pv ON pv.id = ci.product_variant_id
JOIN products pr        ON pr.id = pv.product_id
JOIN inventories i      ON i.product_variant_id = pv.id
ORDER BY ci.id;


-- ---------------------------------------------------------------------
-- D. ĐƠN HÀNG — checkout, đổi trạng thái, thanh toán giả lập, hủy đơn
--    Chạy lần lượt D1..D5 với cùng id đơn.
-- ---------------------------------------------------------------------

-- D0. Đơn mới nhất của 1 khách (lấy id đơn vừa tạo bằng POST /orders/checkout)
WITH p AS (SELECT 'customer@tbookstore.vn'::text AS email) -- <-- ĐỔI email khách
SELECT o.id, o.order_code, o.status, o.total_amount, o.created_at
FROM p JOIN users u ON u.email = p.email
JOIN orders o ON o.user_id = u.id
ORDER BY o.id DESC
LIMIT 5;

-- D1. Thông tin đơn: tiền phải khớp  tong_cong = tam_tinh - giam_gia + phi_ship
WITH p AS (SELECT 1880::bigint AS order_id)                -- <-- ĐỔI id đơn
SELECT o.id, o.order_code, u.email, o.status,
       o.subtotal AS tam_tinh, o.discount_amount AS giam_gia, o.shipping_fee AS phi_ship,
       o.total_amount AS tong_cong,
       (o.subtotal - o.discount_amount + o.shipping_fee = o.total_amount) AS tien_khop,
       o.created_at, o.updated_at
FROM p JOIN orders o ON o.id = p.order_id
JOIN users u ON u.id = o.user_id;

-- D2. Các dòng hàng + tồn kho hiện tại (so trước/sau khi đặt hoặc hủy)
WITH p AS (SELECT 1880::bigint AS order_id)                -- <-- ĐỔI id đơn
SELECT oi.product_variant_id, oi.product_name_snapshot AS sach, oi.sku_snapshot,
       oi.quantity AS so_luong, oi.unit_price AS don_gia, oi.discount_amount, oi.line_total,
       i.quantity_on_hand AS ton_kho_hien_tai
FROM p JOIN order_items oi ON oi.order_id = p.order_id
JOIN inventories i ON i.product_variant_id = oi.product_variant_id
ORDER BY oi.id;

-- D3. Thanh toán của đơn
--     simulate success=true -> status 'success' + paid_at; COD giao xong lẽ ra 'success';
--     hủy đơn -> lẽ ra 'failed'/'refunded'  (2 dòng cuối là lỗi đã biết A1/A2, chưa sửa)
WITH p AS (SELECT 1880::bigint AS order_id)                -- <-- ĐỔI id đơn
SELECT pay.method, pay.status, pay.amount, pay.transaction_ref, pay.created_at, pay.paid_at
FROM p JOIN payments pay ON pay.order_id = p.order_id;

-- D4. Lịch sử trạng thái: mỗi lần PATCH /orders/{id}/status thêm 1 dòng
WITH p AS (SELECT 1880::bigint AS order_id)                -- <-- ĐỔI id đơn
SELECT h.from_status, h.to_status, u.email AS nguoi_doi, h.note, h.created_at
FROM p JOIN order_status_history h ON h.order_id = p.order_id
LEFT JOIN users u ON u.id = h.changed_by
ORDER BY h.created_at;

-- D5. Vận chuyển + khuyến mãi đã dùng cho đơn
--     (shipments trống với đơn tạo qua API là lỗi đã biết A3)
WITH p AS (SELECT 1880::bigint AS order_id)                -- <-- ĐỔI id đơn
SELECT 'shipment' AS loai, s.carrier AS chi_tiet, s.status::text AS trang_thai, s.shipped_at AS thoi_gian
FROM p JOIN shipments s ON s.order_id = p.order_id
UNION ALL
SELECT 'khuyen_mai', coalesce(pr.code, 'flash sale #' || pr.id), pr.type::text, pu.used_at
FROM p JOIN promotion_usages pu ON pu.order_id = p.order_id
JOIN promotions pr ON pr.id = pu.promotion_id;


-- ---------------------------------------------------------------------
-- E. HOÀN TIỀN — POST /refunds, POST /refunds/{id}/process
--    Duyệt (approve=true) -> refund 'refunded' + payment 'refunded'; từ chối -> 'rejected'
-- ---------------------------------------------------------------------
WITH p AS (SELECT 16::bigint AS refund_id)                 -- <-- ĐỔI id yêu cầu hoàn tiền
SELECT r.id, o.order_code, r.status AS trang_thai_hoan, r.refund_amount, r.reason,
       pay.status AS trang_thai_thanh_toan,
       u.email AS nguoi_xu_ly, r.requested_at, r.processed_at
FROM p JOIN refund_requests r ON r.id = p.refund_id
JOIN orders o ON o.id = r.order_id
JOIN payments pay ON pay.order_id = o.id
LEFT JOIN users u ON u.id = r.processed_by;


-- ---------------------------------------------------------------------
-- F. ĐÁNH GIÁ — POST /reviews
--    5 đánh giá mới nhất của 1 sách + điểm trung bình (so với GET /reviews/product/{id}/summary)
-- ---------------------------------------------------------------------
WITH p AS (SELECT 3::bigint AS product_id)                 -- <-- ĐỔI id sách
SELECT r.id, u.full_name, r.rating, r.comment, r.order_item_id, r.created_at,
       round(avg(r.rating) OVER (), 2) AS diem_tb,
       count(*) OVER ()               AS so_danh_gia
FROM p JOIN reviews r ON r.product_id = p.product_id AND r.is_approved
JOIN users u ON u.id = r.user_id
ORDER BY r.created_at DESC
LIMIT 5;


-- ---------------------------------------------------------------------
-- G. SÁCH / DANH MỤC / NHÀ CUNG CẤP — PUT, DELETE (xóa mềm), deactivate
--    Xóa mềm: dòng vẫn còn, cột deleted_at có giá trị -> API trả 404.
-- ---------------------------------------------------------------------
SELECT 'product' AS loai, id, name, is_active, deleted_at, updated_at
FROM products WHERE id = 121                               -- <-- ĐỔI id sách
UNION ALL
SELECT 'category', id, name, is_active, deleted_at, NULL
FROM categories WHERE id = 16                              -- <-- ĐỔI id danh mục
UNION ALL
SELECT 'supplier', id, name, is_active, NULL, NULL
FROM suppliers WHERE id = 13;                              -- <-- ĐỔI id nhà cung cấp


-- ---------------------------------------------------------------------
-- H. NHÂN VIÊN — PUT, lock, unlock, DELETE /employees/{id}; logout, logout-all
--    Khóa nhân viên -> is_active=false VÀ mọi refresh token bị thu hồi (con_hieu_luc = 0)
-- ---------------------------------------------------------------------
WITH p AS (SELECT 4::bigint AS user_id)                    -- <-- ĐỔI id user
SELECT u.id, u.email, u.full_name, u.phone, u.role, u.is_active, u.deleted_at,
       count(t.id) FILTER (WHERE t.revoked_at IS NULL AND t.expires_at > now()) AS token_con_hieu_luc,
       count(t.id) FILTER (WHERE t.revoked_at IS NOT NULL)                      AS token_da_thu_hoi
FROM p JOIN users u ON u.id = p.user_id
LEFT JOIN refresh_tokens t ON t.user_id = u.id
GROUP BY u.id;

-- H2. Danh sách nhân viên đúng như API /employees thấy
SELECT id, email, full_name, is_active
FROM users
WHERE role = 'staff' AND deleted_at IS NULL
ORDER BY id;


-- ---------------------------------------------------------------------
-- I. KHUYẾN MÃI — PUT, activate/deactivate, flash sale
-- ---------------------------------------------------------------------
WITH p AS (SELECT 19::bigint AS promotion_id)              -- <-- ĐỔI id khuyến mãi
SELECT pr.id, pr.code, pr.type, pr.value, pr.min_order_amount, pr.max_discount_amount,
       pr.starts_at, pr.ends_at, pr.usage_limit, pr.per_user_limit, pr.is_active,
       (SELECT count(*) FROM promotion_usages pu WHERE pu.promotion_id = pr.id) AS da_dung
FROM p JOIN promotions pr ON pr.id = p.promotion_id;

-- I2. Sách trong 1 đợt flash sale: đã bán / giới hạn
WITH p AS (SELECT 18::bigint AS promotion_id)              -- <-- ĐỔI id đợt flash sale
SELECT f.product_variant_id, pv.sku, f.flash_price, f.quantity_sold, f.quantity_limit
FROM p JOIN flash_sale_items f ON f.promotion_id = p.promotion_id
JOIN product_variants pv ON pv.id = f.product_variant_id
ORDER BY f.id;


-- ---------------------------------------------------------------------
-- J. ĐỊA CHỈ — POST /addresses/{id}/default
--    Đúng khi: mỗi khách chỉ có đúng 1 địa chỉ is_default = true
-- ---------------------------------------------------------------------
WITH p AS (SELECT 'customer@tbookstore.vn'::text AS email) -- <-- ĐỔI email khách
SELECT a.id, a.recipient_name, a.phone, a.line1, a.ward, a.province, a.is_default
FROM p JOIN users u ON u.email = p.email
JOIN addresses a ON a.user_id = u.id
ORDER BY a.is_default DESC, a.id;


-- ---------------------------------------------------------------------
-- K. AUDIT LOG — mọi thao tác ghi của admin/staff (sửa sách, khóa nhân viên...)
--    20 thao tác mới nhất: ai làm, làm gì, trên đối tượng nào, giá trị cũ/mới
-- ---------------------------------------------------------------------
SELECT a.created_at, u.email AS nguoi_thao_tac, a.action, a.entity_type, a.entity_id,
       a.old_value, a.new_value
FROM audit_logs a
LEFT JOIN users u ON u.id = a.user_id
ORDER BY a.id DESC
LIMIT 20;
