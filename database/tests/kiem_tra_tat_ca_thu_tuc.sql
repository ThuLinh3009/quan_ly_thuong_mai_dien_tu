-- =====================================================================
-- KIỂM TRA OUTPUT TẤT CẢ CÁC THỦ TỤC (function PostgreSQL) — TBookStore
--
-- CÁCH CHẠY
--   pgAdmin : chuột phải database tbookstore -> Query Tool -> 📁 Open File
--             -> chọn file này -> nhấn F5 (chạy CẢ file, không cần bôi đen).
--             Kết quả là bảng ở tab Data Output: mỗi dòng 1 ca kiểm tra.
--   psql    : psql -h localhost -U tbookstore -d tbookstore -f database/tests/kiem_tra_tat_ca_thu_tuc.sql
--
-- HOẠT ĐỘNG
--   * Tự tạo dữ liệu test riêng (tên/email/SKU có hậu tố thời gian, không đụng
--     dữ liệu có sẵn) bằng chính các function, rồi chạy trọn luồng nghiệp vụ:
--     danh mục -> sách -> nhập kho -> khuyến mãi -> giỏ hàng -> đặt hàng ->
--     thanh toán -> giao hàng -> đánh giá -> hoàn tiền -> thống kê.
--   * Mỗi ca so output của function với kết quả đúng mong đợi -> PASS/FAIL,
--     cột chi_tiet ghi giá trị thực tế để dò lỗi.
--   * Cuối cùng HOÀN TÁC toàn bộ dữ liệu test (DB giữ nguyên như trước khi
--     chạy). Chạy bao nhiêu lần cũng được, trên DB nào cũng được.
--   * Lưu ý: id tự tăng (sequence) không hoàn tác được trong PostgreSQL, nên
--     mỗi lần chạy, id của bản ghi thật tạo sau đó sẽ nhảy cóc vài số
--     (vd đơn tiếp theo là 1915 thay vì 1912). Dữ liệu không bị ảnh hưởng.
--   * Dòng "Độ phủ" báo FAIL nếu có function trong DB chưa được kiểm tra.
--   * Nhóm "Lỗi đã biết" là các lỗi nghiệp vụ A1–A3 chưa sửa: hiện FAIL,
--     sửa xong sẽ tự chuyển PASS.
-- =====================================================================

SET client_min_messages = warning;   -- ẩn NOTICE "does not exist, skipping"
DROP TABLE IF EXISTS fn_test_results CASCADE;
CREATE TEMP TABLE fn_test_results (
    stt      INT,
    nhom     TEXT,
    ham      TEXT,
    kiem_tra TEXT,
    ket_qua  TEXT,
    chi_tiet TEXT
);

-- Tạo 1 dòng kết quả. p_ok NULL được coi là FAIL (vd so sánh với giá trị NULL).
CREATE OR REPLACE FUNCTION pg_temp.chk(p_nhom TEXT, p_ham TEXT, p_kiem_tra TEXT, p_ok BOOLEAN, p_chi_tiet TEXT DEFAULT NULL)
RETURNS fn_test_results LANGUAGE sql AS $f$
    SELECT NULL::INT, p_nhom, p_ham, p_kiem_tra,
           CASE WHEN coalesce(p_ok, FALSE) THEN 'PASS' ELSE 'FAIL' END, p_chi_tiet;
$f$;

-- Chạy 1 câu SQL mà ta MONG ĐỢI bị lỗi; trả về thông báo lỗi (NULL nếu không lỗi).
-- Thay đổi của câu bị lỗi được tự hoàn tác.
CREATE OR REPLACE FUNCTION pg_temp.expect_error(p_sql TEXT)
RETURNS TEXT LANGUAGE plpgsql AS $f$
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    RETURN SQLERRM;
END;
$f$;


DO $test$
DECLARE
    r        fn_test_results[] := '{}';
    v_sfx    TEXT := to_char(clock_timestamp(), 'YYMMDDHH24MISSMS');
    v_err    TEXT;
    v_bool   BOOLEAN;
    v_num    NUMERIC;
    v_int    BIGINT;
    v_txt    TEXT;
    v_ts     TIMESTAMPTZ;
    v_json   JSON;
    rec      RECORD;
    v_promo_row promotions%ROWTYPE;
    -- dữ liệu test
    v_admin BIGINT; v_staff BIGINT; v_staff2 BIGINT; v_cust BIGINT; v_cust2 BIGINT;
    v_cat BIGINT; v_cat_child BIGINT; v_sup BIGINT;
    v_prod_a BIGINT; v_prod_b BIGINT; v_prod_c BIGINT; v_prod_d BIGINT;
    v_a1 BIGINT; v_a2 BIGINT; v_b1 BIGINT; v_c1 BIGINT;
    v_lot BIGINT;
    v_pct BIGINT; v_fix BIGINT; v_old BIGINT; v_flash BIGINT;
    v_pct_code TEXT; v_fix_code TEXT; v_old_code TEXT;
    v_addr1 BIGINT; v_addr2 BIGINT; v_addr_other BIGINT;
    v_cart BIGINT;
    v_order1 BIGINT; v_order2 BIGINT; v_order3 BIGINT;
    v_oi_a BIGINT; v_oi_b BIGINT; v_oi_o2 BIGINT;
    v_refund BIGINT; v_refund2 BIGINT;
BEGIN
  BEGIN  -- khối test: toàn bộ thay đổi trong khối này được hoàn tác ở cuối

    -- =================================================================
    -- 1. NGƯỜI DÙNG, NHÂN VIÊN, TOKEN, AUDIT
    -- =================================================================
    BEGIN
        SELECT u.id INTO v_admin FROM create_user('fntest_admin_' || v_sfx || '@test.local', 'hash', 'FN Admin', NULL, 'admin') u;
        SELECT u.id INTO v_staff FROM create_user('fntest_staff_' || v_sfx || '@test.local', 'hash', 'FN Nhân Viên', '0900000001', 'staff') u;
        SELECT u.id INTO v_staff2 FROM create_user('fntest_staff2_' || v_sfx || '@test.local', 'hash', 'FN Nhân Viên 2', NULL, 'staff') u;
        SELECT u.id, u.role, u.is_active INTO rec
        FROM create_user('fntest_cust_' || v_sfx || '@test.local', 'hash', 'FN Khách Hàng', '0900000002', 'customer') u;
        v_cust := rec.id;
        r := r || pg_temp.chk('1. Người dùng', 'create_user', 'Tạo khách: role customer, đang hoạt động',
                              rec.role = 'customer' AND rec.is_active, format('id=%s role=%s', rec.id, rec.role));
        SELECT u.id INTO v_cust2 FROM create_user('fntest_cust2_' || v_sfx || '@test.local', 'hash', 'FN Khách 2', NULL, 'customer') u;

        v_err := pg_temp.expect_error(format('SELECT * FROM create_user(%L, %L, %L, NULL, %L)',
                 'fntest_cust_' || v_sfx || '@test.local', 'x', 'Trùng', 'customer'));
        r := r || pg_temp.chk('1. Người dùng', 'create_user', 'Email trùng bị chặn', v_err ILIKE '%duplicate%', v_err);

        SELECT u.id INTO v_int FROM get_user_by_email('fntest_staff_' || v_sfx || '@test.local') u;
        r := r || pg_temp.chk('1. Người dùng', 'get_user_by_email', 'Tìm đúng user theo email', v_int = v_staff, format('id=%s', v_int));

        SELECT u.email INTO v_txt FROM get_user_by_id(v_cust) u;
        r := r || pg_temp.chk('1. Người dùng', 'get_user_by_id', 'Tìm đúng user theo id', v_txt = 'fntest_cust_' || v_sfx || '@test.local', v_txt);

        SELECT count(*), bool_and(s.role = 'staff') INTO v_int, v_bool FROM list_staff(v_sfx, NULL, 50, 0) s;
        r := r || pg_temp.chk('1. Người dùng', 'list_staff', 'Chỉ liệt kê nhân viên (không lẫn khách/admin)',
                              v_int = 2 AND v_bool, format('%s dòng', v_int));

        SELECT s.full_name, s.phone INTO rec FROM update_staff(v_staff, 'FN Nhân Viên Đã Sửa', '0911111111') s;
        r := r || pg_temp.chk('1. Người dùng', 'update_staff', 'Sửa tên + số điện thoại',
                              rec.full_name = 'FN Nhân Viên Đã Sửa' AND rec.phone = '0911111111', format('%s / %s', rec.full_name, rec.phone));
        SELECT count(*) INTO v_int FROM update_staff(v_cust, 'Hack', NULL);
        r := r || pg_temp.chk('1. Người dùng', 'update_staff', 'Không sửa được tài khoản khách qua API nhân viên', v_int = 0, format('%s dòng bị sửa', v_int));

        SELECT s.is_active INTO v_bool FROM set_staff_active(v_staff, FALSE) s;
        r := r || pg_temp.chk('1. Người dùng', 'set_staff_active', 'Khóa nhân viên', v_bool = FALSE, format('is_active=%s', v_bool));
        SELECT s.is_active INTO v_bool FROM set_staff_active(v_staff, TRUE) s;
        r := r || pg_temp.chk('1. Người dùng', 'set_staff_active', 'Mở khóa nhân viên', v_bool = TRUE, format('is_active=%s', v_bool));

        v_bool := soft_delete_staff(v_staff2);
        SELECT count(*) INTO v_int FROM get_user_by_id(v_staff2);
        r := r || pg_temp.chk('1. Người dùng', 'soft_delete_staff', 'Xóa mềm: trả true, sau đó không tìm thấy',
                              v_bool AND v_int = 0, format('ket_qua=%s, tim_thay=%s', v_bool, v_int));
        r := r || pg_temp.chk('1. Người dùng', 'soft_delete_staff', 'Xóa lần 2 / xóa tài khoản khách -> false',
                              NOT soft_delete_staff(v_staff2) AND NOT soft_delete_staff(v_cust));

        PERFORM create_refresh_token(v_cust, 'fntest_h1_' || v_sfx, now() + interval '1 day');
        PERFORM create_refresh_token(v_cust, 'fntest_h2_' || v_sfx, now() + interval '1 day');
        PERFORM create_refresh_token(v_cust, 'fntest_h3_' || v_sfx, now() - interval '1 second');
        SELECT count(*) INTO v_int FROM get_valid_refresh_token('fntest_h1_' || v_sfx);
        r := r || pg_temp.chk('1. Token', 'create_refresh_token, get_valid_refresh_token', 'Token mới tạo hợp lệ', v_int = 1);
        SELECT count(*) INTO v_int FROM get_valid_refresh_token('fntest_h3_' || v_sfx);
        r := r || pg_temp.chk('1. Token', 'get_valid_refresh_token', 'Token hết hạn bị loại', v_int = 0);
        PERFORM revoke_refresh_token('fntest_h1_' || v_sfx);
        SELECT count(*) INTO v_int FROM get_valid_refresh_token('fntest_h1_' || v_sfx);
        r := r || pg_temp.chk('1. Token', 'revoke_refresh_token', 'Logout: token bị thu hồi', v_int = 0);
        PERFORM revoke_all_refresh_tokens(v_cust);
        SELECT count(*) INTO v_int FROM refresh_tokens WHERE user_id = v_cust AND revoked_at IS NULL;
        r := r || pg_temp.chk('1. Token', 'revoke_all_refresh_tokens', 'Logout-all: không còn token nào chưa thu hồi', v_int = 0, format('còn %s', v_int));

        PERFORM record_audit(v_admin, 'test', 'fn_test', 123, '{"a":1}'::jsonb, '{"a":2}'::jsonb);
        SELECT count(*) INTO v_int FROM audit_logs
        WHERE user_id = v_admin AND entity_type = 'fn_test' AND entity_id = 123 AND new_value->>'a' = '2';
        r := r || pg_temp.chk('1. Audit', 'record_audit', 'Ghi 1 dòng audit với giá trị cũ/mới', v_int = 1);

        SELECT u.id, u.updated_at INTO rec FROM users u WHERE u.updated_at < now() ORDER BY u.id LIMIT 1;
        IF rec.id IS NULL THEN
            r := r || ROW(NULL, '1. Trigger', 'set_updated_at', 'UPDATE tự cập nhật updated_at', 'SKIP', 'không có dòng cũ để thử')::fn_test_results;
        ELSE
            UPDATE users SET full_name = full_name WHERE id = rec.id;
            SELECT updated_at INTO v_ts FROM users WHERE id = rec.id;
            r := r || pg_temp.chk('1. Trigger', 'set_updated_at', 'UPDATE tự cập nhật updated_at = now()',
                                  v_ts = now() AND rec.updated_at < now(), format('%s -> %s', rec.updated_at, v_ts));
        END IF;
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 1', 'Mục 1 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 2. DANH MỤC
    -- =================================================================
    BEGIN
        SELECT c.id INTO v_cat FROM create_category('FN Danh Mục ' || v_sfx, 'fn-dm-' || v_sfx, NULL, TRUE) c;
        SELECT c.id, c.parent_id INTO rec FROM create_category('FN Danh Mục Con ' || v_sfx, 'fn-dm-con-' || v_sfx, v_cat, TRUE) c;
        v_cat_child := rec.id;
        r := r || pg_temp.chk('2. Danh mục', 'create_category', 'Tạo danh mục con trỏ đúng danh mục cha', rec.parent_id = v_cat);

        r := r || pg_temp.chk('2. Danh mục', 'category_slug_exists', 'Slug đã có -> true; loại trừ chính nó -> false; slug lạ -> false',
                              category_slug_exists('fn-dm-' || v_sfx)
                              AND NOT category_slug_exists('fn-dm-' || v_sfx, v_cat)
                              AND NOT category_slug_exists('khong-co-' || v_sfx));

        SELECT c.name, c.parent_id INTO rec FROM get_category_by_id(v_cat_child) c;
        r := r || pg_temp.chk('2. Danh mục', 'get_category_by_id', 'Lấy đúng tên + danh mục cha',
                              rec.name = 'FN Danh Mục Con ' || v_sfx AND rec.parent_id = v_cat, rec.name);

        SELECT count(*), max(c.total_count) INTO v_int, v_num FROM list_categories(v_sfx, NULL, NULL, 50, 0) c;
        r := r || pg_temp.chk('2. Danh mục', 'list_categories', 'Tìm theo từ khóa: 2 danh mục, total_count = 2', v_int = 2 AND v_num = 2);
        SELECT count(*) INTO v_int FROM list_categories(NULL, v_cat, NULL, 50, 0);
        r := r || pg_temp.chk('2. Danh mục', 'list_categories', 'Lọc theo parent_id: 1 danh mục con', v_int = 1);

        SELECT c.name, c.is_active INTO rec FROM update_category(v_cat_child, 'FN Con Đã Sửa ' || v_sfx, 'fn-con-sua-' || v_sfx, v_cat, FALSE) c;
        r := r || pg_temp.chk('2. Danh mục', 'update_category', 'Sửa tên + ẩn danh mục', rec.name LIKE 'FN Con Đã Sửa%' AND NOT rec.is_active);

        v_bool := soft_delete_category(v_cat_child);
        SELECT count(*) INTO v_int FROM get_category_by_id(v_cat_child);
        r := r || pg_temp.chk('2. Danh mục', 'soft_delete_category', 'Xóa mềm: true, sau đó không tìm thấy, slug được giải phóng',
                              v_bool AND v_int = 0 AND NOT category_slug_exists('fn-con-sua-' || v_sfx) AND NOT soft_delete_category(v_cat_child));
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 2', 'Mục 2 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 3. NHÀ CUNG CẤP
    -- =================================================================
    BEGIN
        SELECT s.id, s.is_active INTO rec FROM create_supplier('FN NCC ' || v_sfx, '0281111111', 'ncc@test.local', 'HCM', TRUE) s;
        v_sup := rec.id;
        r := r || pg_temp.chk('3. Nhà cung cấp', 'create_supplier', 'Tạo nhà cung cấp đang hoạt động', rec.is_active);

        SELECT s.name INTO v_txt FROM get_supplier_by_id(v_sup) s;
        r := r || pg_temp.chk('3. Nhà cung cấp', 'get_supplier_by_id', 'Lấy đúng theo id', v_txt = 'FN NCC ' || v_sfx, v_txt);

        SELECT s.contact_phone INTO v_txt FROM update_supplier(v_sup, 'FN NCC ' || v_sfx, '0289999999', 'ncc@test.local', 'Hà Nội', TRUE) s;
        r := r || pg_temp.chk('3. Nhà cung cấp', 'update_supplier', 'Sửa số điện thoại', v_txt = '0289999999', v_txt);

        SELECT s.is_active INTO v_bool FROM set_supplier_active(v_sup, FALSE) s;
        SELECT count(*) INTO v_int FROM list_suppliers(v_sfx, FALSE, 50, 0);
        r := r || pg_temp.chk('3. Nhà cung cấp', 'set_supplier_active, list_suppliers', 'Ngừng hợp tác -> có trong danh sách is_active=false',
                              v_bool = FALSE AND v_int = 1);
        PERFORM set_supplier_active(v_sup, TRUE);
        SELECT count(*) INTO v_int FROM list_suppliers(v_sfx, TRUE, 50, 0);
        r := r || pg_temp.chk('3. Nhà cung cấp', 'list_suppliers', 'Lọc theo từ khóa + đang hoạt động', v_int = 1);
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 3', 'Mục 3 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 4. SÁCH, BIẾN THỂ, TỒN KHO
    --    A 100.000 (bìa mềm A1 +0, bìa cứng A2 +30.000) · B 50.000 · C 80.000 · D (để xóa)
    -- =================================================================
    BEGIN
        r := r || pg_temp.chk('4. Sách', 'product_sku_exists, product_slug_exists', 'SKU/slug chưa có -> false',
                              NOT product_sku_exists('FNTEST-A-' || v_sfx) AND NOT product_slug_exists('fntest-a-' || v_sfx));
        v_prod_a := create_product(v_cat, 'FNTEST-A-' || v_sfx, 'Sách A fntest' || v_sfx, 'fntest-a-' || v_sfx, 'Tác Giả FN', 'NXB FN', NULL, 'Mô tả', NULL, 100000, TRUE);
        v_prod_b := create_product(v_cat, 'FNTEST-B-' || v_sfx, 'Sách B fntest' || v_sfx, 'fntest-b-' || v_sfx, 'Tác Giả FN', 'NXB FN', NULL, NULL, NULL, 50000, TRUE);
        v_prod_c := create_product(v_cat, 'FNTEST-C-' || v_sfx, 'Sách C fntest' || v_sfx, 'fntest-c-' || v_sfx, 'Tác Giả FN', 'NXB FN', NULL, NULL, NULL, 80000, TRUE);
        v_prod_d := create_product(v_cat, 'FNTEST-D-' || v_sfx, 'Sách D fntest' || v_sfx, 'fntest-d-' || v_sfx, NULL, NULL, NULL, NULL, NULL, 60000, TRUE);
        r := r || pg_temp.chk('4. Sách', 'create_product', 'Tạo sách trả về id', v_prod_a IS NOT NULL, format('id=%s', v_prod_a));
        r := r || pg_temp.chk('4. Sách', 'product_sku_exists, product_slug_exists', 'Sau khi tạo -> true',
                              product_sku_exists('FNTEST-A-' || v_sfx) AND product_slug_exists('fntest-a-' || v_sfx));

        r := r || pg_temp.chk('4. Biến thể', 'variant_sku_exists', 'SKU biến thể chưa có -> false', NOT variant_sku_exists('FNTEST-A1-' || v_sfx));
        SELECT v.id INTO v_a1 FROM create_variant(v_prod_a, 'Bìa mềm', 'FNTEST-A1-' || v_sfx, 0, TRUE) v;
        SELECT v.id INTO v_a2 FROM create_variant(v_prod_a, 'Bìa cứng', 'FNTEST-A2-' || v_sfx, 30000, TRUE) v;
        SELECT v.id INTO v_b1 FROM create_variant(v_prod_b, 'Bìa mềm', 'FNTEST-B1-' || v_sfx, 0, TRUE) v;
        SELECT v.id INTO v_c1 FROM create_variant(v_prod_c, 'Bìa mềm', 'FNTEST-C1-' || v_sfx, 0, TRUE) v;
        r := r || pg_temp.chk('4. Biến thể', 'create_variant, variant_sku_exists', 'Tạo biến thể -> SKU tồn tại', variant_sku_exists('FNTEST-A1-' || v_sfx));

        PERFORM create_inventory_for_variant(v_a1, 10, 5);
        PERFORM create_inventory_for_variant(v_a2, 5, 2);
        PERFORM create_inventory_for_variant(v_b1, 20, 5);
        PERFORM create_inventory_for_variant(v_c1, 3, 1);
        PERFORM create_inventory_for_variant(v_c1, 4, 1);   -- gọi lại: ghi đè (upsert)
        SELECT quantity_on_hand INTO v_int FROM inventories WHERE product_variant_id = v_c1;
        r := r || pg_temp.chk('4. Tồn kho', 'create_inventory_for_variant', 'Tạo tồn kho; gọi lại thì ghi đè số lượng', v_int = 4, format('C1 tồn=%s', v_int));

        PERFORM update_inventory_reorder_level(v_a1, 7);
        SELECT reorder_level INTO v_int FROM inventories WHERE product_variant_id = v_a1;
        r := r || pg_temp.chk('4. Tồn kho', 'update_inventory_reorder_level', 'Đổi ngưỡng cảnh báo tồn kho', v_int = 7, format('reorder=%s', v_int));

        SELECT v.price_adjustment INTO v_num FROM get_variant_by_id(v_a2) v;
        r := r || pg_temp.chk('4. Biến thể', 'get_variant_by_id', 'Lấy đúng phụ phí bìa cứng', v_num = 30000, v_num::text);

        SELECT v.variant_name, v.price_adjustment INTO rec FROM update_variant(v_a2, 'Bìa cứng đặc biệt', 40000, TRUE) v;
        r := r || pg_temp.chk('4. Biến thể', 'update_variant', 'Sửa tên + phụ phí',
                              rec.variant_name = 'Bìa cứng đặc biệt' AND rec.price_adjustment = 40000);

        SELECT v.is_active INTO v_bool FROM set_variant_active(v_a2, FALSE) v;
        v_num := get_effective_unit_price(v_a2);
        r := r || pg_temp.chk('4. Biến thể', 'set_variant_active, get_effective_unit_price', 'Ngừng bán biến thể -> không có giá bán',
                              v_bool = FALSE AND v_num IS NULL, format('giá=%s', v_num));
        PERFORM set_variant_active(v_a2, TRUE);
        r := r || pg_temp.chk('4. Giá', 'get_effective_unit_price', 'Giá = giá sách + phụ phí (100.000 + 40.000)',
                              get_effective_unit_price(v_a2) = 140000, get_effective_unit_price(v_a2)::text);

        SELECT b.name, b.category_id, b.variants INTO rec FROM get_book_by_id(v_prod_a) b;
        SELECT (v->>'quantity_on_hand')::int INTO v_int FROM json_array_elements(rec.variants) v WHERE (v->>'id')::bigint = v_a1;
        r := r || pg_temp.chk('4. Sách', 'get_book_by_id', 'Chi tiết sách: 2 biến thể, kèm tồn kho (A1 = 10)',
                              rec.category_id = v_cat AND json_array_length(rec.variants) = 2 AND v_int = 10,
                              format('%s biến thể, A1 tồn %s', json_array_length(rec.variants), v_int));

        SELECT count(*) INTO v_int FROM search_books('fntest' || v_sfx, NULL, NULL, NULL, TRUE, 'created_at', 'desc', 20, 0);
        r := r || pg_temp.chk('4. Tìm kiếm', 'search_books', 'Tìm theo từ khóa: 4 sách A, B, C, D', v_int = 4, format('%s sách', v_int));
        SELECT string_agg(s.base_price::int::text, ',' ORDER BY ord) INTO v_txt
        FROM search_books('fntest' || v_sfx, v_cat, 55000, 100000, TRUE, 'base_price', 'asc', 20, 0) WITH ORDINALITY AS s(id, sku, name, author, base_price, cover_image_url, is_active, created_at, category_id, category_name, total_count, ord);
        r := r || pg_temp.chk('4. Tìm kiếm', 'search_books', 'Lọc danh mục + giá 55k–100k, sắp giá tăng: 60k, 80k, 100k',
                              v_txt = '60000,80000,100000', v_txt);

        v_bool := update_product(v_prod_a, v_cat, 'Sách A fntest' || v_sfx, 'fntest-a-' || v_sfx, 'Tác Giả FN', 'NXB Mới', NULL, 'Mô tả mới', NULL, 100000, TRUE);
        SELECT publisher INTO v_txt FROM products WHERE id = v_prod_a;
        r := r || pg_temp.chk('4. Sách', 'update_product', 'Sửa nhà xuất bản -> true', v_bool AND v_txt = 'NXB Mới', v_txt);

        v_bool := soft_delete_product(v_prod_d);
        SELECT count(*) INTO v_int FROM get_book_by_id(v_prod_d);
        r := r || pg_temp.chk('4. Sách', 'soft_delete_product', 'Xóa mềm: true, không xem được, xóa lại -> false',
                              v_bool AND v_int = 0 AND NOT soft_delete_product(v_prod_d));
        r := r || pg_temp.chk('4. Sách', 'update_product', 'Sửa sách đã xóa -> false',
                              NOT update_product(v_prod_d, v_cat, 'x', 'fntest-d-' || v_sfx, NULL, NULL, NULL, NULL, NULL, 1, TRUE));
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 4', 'Mục 4 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 5. NHẬP KHO: A1 +50 (tồn 10 -> 60), B1 +30 (20 -> 50)
    -- =================================================================
    BEGIN
        SELECT l.id, l.lot_code INTO rec FROM create_import_lot(v_sup, v_staff) l;
        v_lot := rec.id;
        r := r || pg_temp.chk('5. Nhập kho', 'create_import_lot', 'Tạo lô, mã dạng LOT-...', rec.lot_code LIKE 'LOT-%', rec.lot_code);

        PERFORM add_import_receipt_items(v_lot, ARRAY[v_a1, v_b1], ARRAY[50, 30], ARRAY[60000, 30000]::numeric[]);
        SELECT l.supplier_name, l.items INTO rec FROM get_import_lot_by_id(v_lot) l;
        r := r || pg_temp.chk('5. Nhập kho', 'add_import_receipt_items, get_import_lot_by_id', 'Lô có 2 dòng nhập, đúng nhà cung cấp',
                              json_array_length(rec.items) = 2 AND rec.supplier_name = 'FN NCC ' || v_sfx,
                              format('%s dòng', json_array_length(rec.items)));

        SELECT count(*) INTO v_int FROM list_import_lots(v_sup, 20, 0);
        r := r || pg_temp.chk('5. Nhập kho', 'list_import_lots', 'Lọc theo nhà cung cấp: 1 lô', v_int = 1);

        PERFORM restock_from_import(v_lot);
        SELECT string_agg(quantity_on_hand::text, ',' ORDER BY product_variant_id) INTO v_txt
        FROM inventories WHERE product_variant_id IN (v_a1, v_b1);
        r := r || pg_temp.chk('5. Nhập kho', 'restock_from_import', 'Cộng tồn kho: A1 10+50 = 60, B1 20+30 = 50', v_txt = '60,50', v_txt);
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 5', 'Mục 5 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 6. KHUYẾN MÃI
    --    PCT: giảm 10%, tối đa 20.000, đơn từ 100.000, mỗi khách 1 lần
    --    FIX: giảm 50.000, đơn từ 500.000 · OLD: đã hết hạn · FLASH: B1 còn 35.000
    -- =================================================================
    BEGIN
        v_pct_code := 'FNPCT' || v_sfx; v_fix_code := 'FNFIX' || v_sfx; v_old_code := 'FNOLD' || v_sfx;
        r := r || pg_temp.chk('6. Khuyến mãi', 'promotion_code_exists', 'Mã chưa có -> false', NOT promotion_code_exists(v_pct_code));
        SELECT p.id INTO v_pct FROM create_promotion(v_pct_code, 'percentage', 10, 100000, 20000, now() - interval '1 day', now() + interval '1 day', 100, 1, TRUE) p;
        SELECT p.id INTO v_fix FROM create_promotion(v_fix_code, 'fixed_amount', 50000, 500000, NULL, now() - interval '1 day', now() + interval '1 day', NULL, NULL, TRUE) p;
        SELECT p.id INTO v_old FROM create_promotion(v_old_code, 'percentage', 10, 0, NULL, now() - interval '10 day', now() - interval '5 day', NULL, NULL, TRUE) p;
        SELECT p.id INTO v_flash FROM create_promotion(NULL, 'flash_sale', 30, 0, NULL, now() - interval '1 hour', now() + interval '1 day', NULL, NULL, TRUE) p;
        r := r || pg_temp.chk('6. Khuyến mãi', 'create_promotion, promotion_code_exists', 'Tạo voucher -> mã tồn tại', promotion_code_exists(v_pct_code));

        SELECT p.value, p.max_discount_amount INTO rec FROM get_promotion_by_id(v_pct) p;
        r := r || pg_temp.chk('6. Khuyến mãi', 'get_promotion_by_id', 'Đúng giá trị 10%, tối đa 20.000', rec.value = 10 AND rec.max_discount_amount = 20000);

        r := r || pg_temp.chk('6. Khuyến mãi', 'list_promotions', 'Lọc theo loại percentage + đang bật có voucher PCT',
                              EXISTS (SELECT 1 FROM list_promotions('percentage', TRUE, 1000, 0) p WHERE p.id = v_pct)
                              AND NOT EXISTS (SELECT 1 FROM list_promotions('percentage', TRUE, 1000, 0) p WHERE p.id = v_fix));

        SELECT p.usage_limit INTO v_int FROM update_promotion(v_pct, 10, 100000, 20000, now() - interval '1 day', now() + interval '1 day', 50, 1, TRUE) p;
        r := r || pg_temp.chk('6. Khuyến mãi', 'update_promotion', 'Đổi giới hạn lượt dùng 100 -> 50', v_int = 50, format('usage_limit=%s', v_int));
        v_err := pg_temp.expect_error(format('SELECT * FROM update_promotion(%s, 10, 0, NULL, now(), now() - interval ''1 day'', NULL, NULL, TRUE)', v_pct));
        r := r || pg_temp.chk('6. Khuyến mãi', 'update_promotion', 'Ngày kết thúc trước ngày bắt đầu bị chặn', v_err ILIKE '%promotions_check%', v_err);

        SELECT p.is_active INTO v_bool FROM set_promotion_active(v_fix, FALSE) p;
        v_err := pg_temp.expect_error(format('SELECT find_valid_promotion(%L, %s, 999999)', v_fix_code, v_cust));
        r := r || pg_temp.chk('6. Khuyến mãi', 'set_promotion_active, find_valid_promotion', 'Tắt voucher -> không dùng được',
                              v_bool = FALSE AND v_err ILIKE '%invalid or expired%', v_err);
        PERFORM set_promotion_active(v_fix, TRUE);

        v_err := pg_temp.expect_error(format('SELECT find_valid_promotion(%L, %s, 999999)', v_old_code, v_cust));
        r := r || pg_temp.chk('6. Khuyến mãi', 'find_valid_promotion', 'Voucher hết hạn bị chặn', v_err ILIKE '%invalid or expired%', v_err);
        v_err := pg_temp.expect_error(format('SELECT find_valid_promotion(%L, %s, 100000)', v_fix_code, v_cust));
        r := r || pg_temp.chk('6. Khuyến mãi', 'find_valid_promotion', 'Chưa đạt giá trị đơn tối thiểu bị chặn', v_err ILIKE '%minimum amount%', v_err);
        v_promo_row := find_valid_promotion(v_pct_code, v_cust, 200000);
        r := r || pg_temp.chk('6. Khuyến mãi', 'find_valid_promotion', 'Voucher hợp lệ -> trả đúng khuyến mãi', v_promo_row.id = v_pct);

        r := r || pg_temp.chk('6. Khuyến mãi', 'calculate_discount', '10% của 100.000 = 10.000', calculate_discount(v_promo_row, 100000) = 10000);
        r := r || pg_temp.chk('6. Khuyến mãi', 'calculate_discount', '10% của 300.000 = 30.000 -> bị chặn trần 20.000', calculate_discount(v_promo_row, 300000) = 20000);
        SELECT * INTO v_promo_row FROM promotions WHERE id = v_fix;
        r := r || pg_temp.chk('6. Khuyến mãi', 'calculate_discount', 'Giảm 50.000 cho đơn 30.000 -> chỉ giảm 30.000 (không âm)', calculate_discount(v_promo_row, 30000) = 30000);

        SELECT f.flash_price INTO v_num FROM add_flash_sale_item(v_flash, v_b1, 35000, 5) f;
        r := r || pg_temp.chk('6. Flash sale', 'add_flash_sale_item', 'Thêm B1 vào flash sale giá 35.000', v_num = 35000);
        SELECT count(*), max(f.product_name) INTO v_int, v_txt FROM list_flash_sale_items(v_flash) f;
        r := r || pg_temp.chk('6. Flash sale', 'list_flash_sale_items', 'Đợt flash sale có 1 sách (B)', v_int = 1 AND v_txt LIKE 'Sách B%', v_txt);
        SELECT f.flash_price INTO v_num FROM get_active_flash_sales(1000) f WHERE f.product_variant_id = v_b1;
        r := r || pg_temp.chk('6. Flash sale', 'get_active_flash_sales', 'B1 xuất hiện trong flash sale đang chạy', v_num = 35000);
        r := r || pg_temp.chk('6. Giá', 'get_effective_unit_price', 'B1 đang flash sale -> giá 35.000 thay vì 50.000; A1 = 100.000',
                              get_effective_unit_price(v_b1) = 35000 AND get_effective_unit_price(v_a1) = 100000);
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 6', 'Mục 6 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 7. ĐỊA CHỈ
    -- =================================================================
    BEGIN
        SELECT a.id INTO v_addr1 FROM create_address(v_cust, 'FN Người Nhận', '0900000002', '1 Đường Test', 'P1', 'Q1', 'TP.HCM', TRUE) a;
        SELECT a.id, a.is_default INTO rec FROM create_address(v_cust, 'FN Người Nhận', '0900000002', '2 Đường Test', 'P2', 'Q2', 'TP.HCM', TRUE) a;
        v_addr2 := rec.id;
        SELECT a.is_default INTO v_bool FROM get_address_by_id(v_addr1) a;
        r := r || pg_temp.chk('7. Địa chỉ', 'create_address, get_address_by_id', 'Thêm địa chỉ mặc định mới -> địa chỉ cũ hết mặc định',
                              rec.is_default AND v_bool = FALSE);
        SELECT a.id INTO v_int FROM list_addresses_for_user(v_cust) a LIMIT 1;
        r := r || pg_temp.chk('7. Địa chỉ', 'list_addresses_for_user', 'Địa chỉ mặc định đứng đầu danh sách', v_int = v_addr2);

        v_bool := set_default_address(v_addr1, v_cust);
        SELECT count(*) FILTER (WHERE is_default) INTO v_int FROM addresses WHERE user_id = v_cust;
        r := r || pg_temp.chk('7. Địa chỉ', 'set_default_address', 'Đặt địa chỉ 1 làm mặc định -> chỉ đúng 1 địa chỉ mặc định',
                              v_bool AND v_int = 1 AND (SELECT is_default FROM addresses WHERE id = v_addr1));
        SELECT a.id INTO v_addr_other FROM create_address(v_cust2, 'FN Khách 2', '0900000003', '3 Đường Test', NULL, NULL, 'Hà Nội', TRUE) a;
        r := r || pg_temp.chk('7. Địa chỉ', 'set_default_address', 'Không đặt được địa chỉ của người khác', NOT set_default_address(v_addr_other, v_cust));
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 7', 'Mục 7 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 8. GIỎ HÀNG
    -- =================================================================
    BEGIN
        SELECT g.cart_id, g.subtotal INTO rec FROM get_cart(v_cust) g;
        r := r || pg_temp.chk('8. Giỏ hàng', 'get_cart', 'Khách chưa có giỏ -> giỏ rỗng, tạm tính 0', rec.cart_id IS NULL AND rec.subtotal = 0);

        PERFORM add_to_cart(v_cust, v_a1, 2);
        PERFORM add_to_cart(v_cust, v_a1, 1);
        SELECT id INTO v_cart FROM carts WHERE user_id = v_cust;
        SELECT quantity INTO v_int FROM cart_items WHERE cart_id = v_cart AND product_variant_id = v_a1;
        r := r || pg_temp.chk('8. Giỏ hàng', 'add_to_cart', 'Thêm cùng sách 2 lần -> cộng dồn 2 + 1 = 3 (1 dòng)', v_int = 3,
                              format('số lượng=%s, số dòng=%s', v_int, (SELECT count(*) FROM cart_items WHERE cart_id = v_cart)));
        PERFORM add_to_cart(v_cust, v_b1, 1);
        SELECT unit_price_snapshot INTO v_num FROM cart_items WHERE cart_id = v_cart AND product_variant_id = v_b1;
        r := r || pg_temp.chk('8. Giỏ hàng', 'add_to_cart', 'Chụp giá tại lúc thêm: B1 theo giá flash 35.000', v_num = 35000, v_num::text);

        v_err := pg_temp.expect_error(format('SELECT add_to_cart(%s, %s, 0)', v_cust, v_a1));
        r := r || pg_temp.chk('8. Giỏ hàng', 'add_to_cart', 'Số lượng 0 bị chặn', v_err ILIKE '%Quantity must be positive%', v_err);
        v_err := pg_temp.expect_error(format('SELECT add_to_cart(%s, -1, 1)', v_cust));
        r := r || pg_temp.chk('8. Giỏ hàng', 'add_to_cart', 'Biến thể không tồn tại bị chặn', v_err ILIKE '%not found or inactive%', v_err);

        r := r || pg_temp.chk('8. Giỏ hàng', 'get_cart_total', 'Tổng = 3 x 100.000 + 35.000 = 335.000', get_cart_total(v_cart) = 335000, get_cart_total(v_cart)::text);

        v_bool := update_cart_item_quantity(v_cust, v_a1, 2);
        SELECT g.subtotal, json_array_length(g.items) INTO rec FROM get_cart(v_cust) g;
        r := r || pg_temp.chk('8. Giỏ hàng', 'update_cart_item_quantity, get_cart', 'Sửa A1 còn 2 -> 2 dòng, tạm tính 235.000',
                              v_bool AND rec.subtotal = 235000 AND rec.json_array_length = 2, format('tạm tính=%s', rec.subtotal));
        v_err := pg_temp.expect_error(format('SELECT update_cart_item_quantity(%s, %s, 0)', v_cust, v_a1));
        r := r || pg_temp.chk('8. Giỏ hàng', 'update_cart_item_quantity', 'Sửa về 0 bị chặn', v_err ILIKE '%Quantity must be positive%', v_err);
        r := r || pg_temp.chk('8. Giỏ hàng', 'update_cart_item_quantity', 'Sửa sách không có trong giỏ -> false', NOT update_cart_item_quantity(v_cust, v_c1, 1));

        v_bool := remove_cart_item(v_cust, v_b1);
        r := r || pg_temp.chk('8. Giỏ hàng', 'remove_cart_item', 'Xóa 1 dòng -> true; xóa lại -> false', v_bool AND NOT remove_cart_item(v_cust, v_b1));
        PERFORM add_to_cart(v_cust, v_b1, 1);   -- giỏ để đặt đơn 1: A1 x2 + B1 x1 = 235.000

        PERFORM add_to_cart(v_cust2, v_c1, 1);
        PERFORM clear_cart(v_cust2);
        SELECT g.subtotal, json_array_length(g.items) INTO rec FROM get_cart(v_cust2) g;
        r := r || pg_temp.chk('8. Giỏ hàng', 'clear_cart', 'Xóa cả giỏ -> giỏ rỗng', rec.subtotal = 0 AND rec.json_array_length = 0);
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 8', 'Mục 8 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 9. ĐẶT HÀNG
    --    Đơn 1: COD, voucher PCT  (A1 x2 + B1 x1)   = 235.000 - 20.000 + 30.000 = 245.000
    --    Đơn 2: thanh toán online (A1 x1)           = 100.000 + 30.000            = 130.000
    --    Đơn 3: COD, sẽ bị hủy    (C1 x2)
    -- =================================================================
    BEGIN
        SELECT * INTO rec FROM preview_checkout(v_cust);
        r := r || pg_temp.chk('9. Đặt hàng', 'preview_checkout', 'Xem trước: 235.000 + ship 30.000 = 265.000',
                              rec.subtotal = 235000 AND rec.discount_amount = 0 AND rec.shipping_fee = 30000 AND rec.total_amount = 265000,
                              format('%s - %s + %s = %s', rec.subtotal, rec.discount_amount, rec.shipping_fee, rec.total_amount));
        SELECT * INTO rec FROM preview_checkout(v_cust, v_pct_code);
        r := r || pg_temp.chk('9. Đặt hàng', 'preview_checkout', 'Với voucher 10% (tối đa 20.000): giảm 20.000, tổng 245.000',
                              rec.discount_amount = 20000 AND rec.total_amount = 245000, format('giảm %s, tổng %s', rec.discount_amount, rec.total_amount));
        v_err := pg_temp.expect_error(format('SELECT * FROM preview_checkout(%s)', v_cust2));
        r := r || pg_temp.chk('9. Đặt hàng', 'preview_checkout', 'Giỏ rỗng bị chặn', v_err ILIKE '%Cart is empty%', v_err);

        v_err := pg_temp.expect_error(format('SELECT place_order(%s, %s, ''cod'')', v_cust, v_addr_other));
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Dùng địa chỉ của người khác bị chặn', v_err ILIKE '%does not belong%', v_err);
        PERFORM add_to_cart(v_cust2, v_c1, 10);   -- C1 chỉ còn 4
        v_err := pg_temp.expect_error(format('SELECT place_order(%s, %s, ''cod'')', v_cust2, v_addr_other));
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Vượt tồn kho bị chặn (giỏ 10, kho 4)', v_err ILIKE '%Insufficient stock%', v_err);
        PERFORM clear_cart(v_cust2);

        v_order1 := place_order(v_cust, v_addr1, 'cod', v_pct_code);
        SELECT * INTO rec FROM orders WHERE id = v_order1;
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Đơn 1: tiền đúng 235.000 - 20.000 + 30.000 = 245.000, trạng thái pending',
                              rec.subtotal = 235000 AND rec.discount_amount = 20000 AND rec.shipping_fee = 30000
                              AND rec.total_amount = 245000 AND rec.status = 'pending',
                              format('%s - %s + %s = %s (%s)', rec.subtotal, rec.discount_amount, rec.shipping_fee, rec.total_amount, rec.status));
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Mã đơn dạng ORD-YYYYMMDD-id',
                              rec.order_code = 'ORD-' || to_char(now(), 'YYYYMMDD') || '-' || v_order1, rec.order_code);
        SELECT count(*), sum(line_total) INTO v_int, v_num FROM order_items WHERE order_id = v_order1;
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', '2 dòng hàng, tổng các dòng = tạm tính', v_int = 2 AND v_num = 235000, format('%s dòng, %s', v_int, v_num));
        SELECT string_agg(quantity_on_hand::text, ',' ORDER BY product_variant_id) INTO v_txt
        FROM inventories WHERE product_variant_id IN (v_a1, v_b1);
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Trừ tồn kho: A1 60-2 = 58, B1 50-1 = 49', v_txt = '58,49', v_txt);
        SELECT quantity_sold INTO v_int FROM flash_sale_items WHERE promotion_id = v_flash AND product_variant_id = v_b1;
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Flash sale: số đã bán của B1 tăng lên 1', v_int = 1);
        SELECT status::text || '/' || method::text || '/' || amount INTO v_txt FROM payments WHERE order_id = v_order1;
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Tạo thanh toán pending, COD, số tiền 245.000', v_txt = 'pending/cod/245000.00', v_txt);
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Ghi lịch sử trạng thái đầu tiên + lượt dùng voucher + làm trống giỏ',
                              (SELECT count(*) FROM order_status_history WHERE order_id = v_order1 AND to_status = 'pending') = 1
                              AND (SELECT count(*) FROM promotion_usages WHERE order_id = v_order1 AND promotion_id = v_pct) = 1
                              AND get_cart_total(v_cart) = 0);
        v_err := pg_temp.expect_error(format('SELECT place_order(%s, %s, ''cod'')', v_cust, v_addr1));
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Đặt tiếp khi giỏ rỗng bị chặn', v_err ILIKE '%Cart is empty%', v_err);

        PERFORM add_to_cart(v_cust, v_a1, 1);
        v_err := pg_temp.expect_error(format('SELECT * FROM preview_checkout(%s, %L)', v_cust, v_pct_code));
        r := r || pg_temp.chk('9. Đặt hàng', 'find_valid_promotion', 'Voucher giới hạn 1 lần/khách: lần 2 bị chặn', v_err ILIKE '%limit reached for this user%', v_err);
        v_order2 := place_order(v_cust, v_addr1, 'simulated_gateway');
        SELECT total_amount INTO v_num FROM orders WHERE id = v_order2;
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Đơn 2 (online): 100.000 + 30.000 = 130.000', v_num = 130000, v_num::text);

        PERFORM add_to_cart(v_cust, v_c1, 2);
        v_order3 := place_order(v_cust, v_addr1, 'cod');
        SELECT quantity_on_hand INTO v_int FROM inventories WHERE product_variant_id = v_c1;
        r := r || pg_temp.chk('9. Đặt hàng', 'place_order', 'Đơn 3: trừ tồn C1 4 - 2 = 2', v_int = 2, format('C1 tồn=%s', v_int));

        SELECT d.order_code, json_array_length(d.items) AS n_items, d.payment->>'method' AS method,
               json_array_length(d.status_history) AS n_hist, d.address->>'line1' AS line1 INTO rec
        FROM get_order_detail(v_order1) d;
        r := r || pg_temp.chk('9. Đơn hàng', 'get_order_detail', 'Chi tiết đơn: 2 dòng hàng, thanh toán COD, 1 dòng lịch sử, có địa chỉ',
                              rec.n_items = 2 AND rec.method = 'cod' AND rec.n_hist = 1 AND rec.line1 = '1 Đường Test',
                              format('%s dòng, %s, lịch sử %s, %s', rec.n_items, rec.method, rec.n_hist, rec.line1));
        SELECT count(*), max(o.total_count) INTO v_int, v_num FROM list_orders_for_user(v_cust, NULL, 20, 0) o;
        r := r || pg_temp.chk('9. Đơn hàng', 'list_orders_for_user', 'Khách có đúng 3 đơn', v_int = 3 AND v_num = 3);
        SELECT count(*) INTO v_int FROM list_orders_admin('pending', v_cust, now(), now(), 20, 0);
        r := r || pg_temp.chk('9. Đơn hàng', 'list_orders_admin', 'Lọc trạng thái + khách + khoảng ngày: 3 đơn pending', v_int = 3);
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 9', 'Mục 9 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 10. THANH TOÁN VÀ TRẠNG THÁI ĐƠN
    -- =================================================================
    BEGIN
        SELECT * INTO rec FROM simulate_payment_gateway(v_order2, TRUE, v_cust);
        r := r || pg_temp.chk('10. Thanh toán', 'simulate_payment_gateway', 'Thanh toán online thành công -> payment success, đơn tự sang confirmed',
                              rec.payment_status = 'success' AND rec.order_status = 'confirmed' AND rec.transaction_ref LIKE 'SIM-%',
                              format('%s / %s / %s', rec.payment_status, rec.order_status, rec.transaction_ref));
        v_err := pg_temp.expect_error(format('SELECT * FROM simulate_payment_gateway(%s, true)', v_order2));
        r := r || pg_temp.chk('10. Thanh toán', 'simulate_payment_gateway', 'Thanh toán lần 2 bị chặn', v_err ILIKE '%no pending payment%', v_err);

        v_err := pg_temp.expect_error(format('SELECT update_order_status(%s, ''delivered'', %s)', v_order1, v_staff));
        r := r || pg_temp.chk('10. Trạng thái', 'update_order_status', 'Nhảy cóc pending -> delivered bị chặn', v_err ILIKE '%Invalid transition%', v_err);
        PERFORM update_order_status(v_order1, 'confirmed', v_staff, 'Xác nhận');
        PERFORM update_order_status(v_order1, 'shipping', v_staff, 'Giao cho GHN');
        r := r || pg_temp.chk('Lỗi đã biết', 'update_order_status', '[A3] Chuyển sang shipping phải tạo bản ghi shipments',
                              EXISTS (SELECT 1 FROM shipments WHERE order_id = v_order1),
                              format('%s bản ghi shipments', (SELECT count(*) FROM shipments WHERE order_id = v_order1)));
        PERFORM update_order_status(v_order1, 'delivered', v_staff, 'Đã giao');
        SELECT string_agg(coalesce(from_status::text, '∅') || '>' || to_status, ' ' ORDER BY id) INTO v_txt
        FROM order_status_history WHERE order_id = v_order1;
        r := r || pg_temp.chk('10. Trạng thái', 'update_order_status', 'pending -> confirmed -> shipping -> delivered, mỗi bước 1 dòng lịch sử',
                              (SELECT status FROM orders WHERE id = v_order1) = 'delivered'
                              AND v_txt = '∅>pending pending>confirmed confirmed>shipping shipping>delivered', v_txt);
        SELECT status::text INTO v_txt FROM payments WHERE order_id = v_order1;
        r := r || pg_temp.chk('Lỗi đã biết', 'update_order_status', '[A2] Đơn COD giao xong -> thanh toán phải là success', v_txt = 'success', format('payment=%s', v_txt));
        v_err := pg_temp.expect_error(format('SELECT update_order_status(%s, ''cancelled'', %s)', v_order1, v_staff));
        r := r || pg_temp.chk('10. Trạng thái', 'update_order_status', 'Hủy đơn đã giao bị chặn', v_err ILIKE '%Invalid transition%', v_err);

        PERFORM update_order_status(v_order3, 'cancelled', v_cust, 'Khách hủy');
        SELECT quantity_on_hand INTO v_int FROM inventories WHERE product_variant_id = v_c1;
        r := r || pg_temp.chk('10. Trạng thái', 'update_order_status', 'Hủy đơn 3 -> hoàn tồn C1 2 + 2 = 4', v_int = 4, format('C1 tồn=%s', v_int));
        SELECT status::text INTO v_txt FROM payments WHERE order_id = v_order3;
        r := r || pg_temp.chk('Lỗi đã biết', 'update_order_status', '[A1] Hủy đơn -> thanh toán không được còn pending', v_txt <> 'pending', format('payment=%s', v_txt));
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 10', 'Mục 10 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 11. ĐÁNH GIÁ VÀ GỢI Ý SÁCH
    -- =================================================================
    BEGIN
        SELECT id INTO v_oi_a FROM order_items WHERE order_id = v_order1 AND product_variant_id = v_a1;
        SELECT id INTO v_oi_b FROM order_items WHERE order_id = v_order1 AND product_variant_id = v_b1;
        SELECT id INTO v_oi_o2 FROM order_items WHERE order_id = v_order2;
        SELECT count(*) FILTER (WHERE x.order_id = v_order1), count(*) FILTER (WHERE x.order_id <> v_order1) INTO v_int, v_num
        FROM list_reviewable_order_items(v_cust) x;
        r := r || pg_temp.chk('11. Đánh giá', 'list_reviewable_order_items', 'Chỉ 2 sách của đơn đã giao được đánh giá (đơn chưa giao thì không)',
                              v_int = 2 AND v_num = 0, format('đơn 1: %s, đơn khác: %s', v_int, v_num));

        v_int := submit_review(v_oi_a, v_cust, 5::smallint, 'Sách rất hay');
        SELECT product_id INTO v_num FROM reviews WHERE id = v_int;
        r := r || pg_temp.chk('11. Đánh giá', 'submit_review', 'Đánh giá sách đã mua -> gắn đúng sách A', v_num = v_prod_a);
        PERFORM submit_review(v_oi_b, v_cust, 3::smallint, NULL);
        v_err := pg_temp.expect_error(format('SELECT submit_review(%s, %s, 4::smallint)', v_oi_a, v_cust));
        r := r || pg_temp.chk('11. Đánh giá', 'submit_review', 'Đánh giá 2 lần cùng 1 dòng hàng bị chặn', v_err ILIKE '%already been reviewed%', v_err);
        v_err := pg_temp.expect_error(format('SELECT submit_review(%s, %s, 4::smallint)', v_oi_o2, v_cust));
        r := r || pg_temp.chk('11. Đánh giá', 'submit_review', 'Đơn chưa giao bị chặn', v_err ILIKE '%not eligible%', v_err);
        v_err := pg_temp.expect_error(format('SELECT submit_review(%s, %s, 4::smallint)', v_oi_a, v_cust2));
        r := r || pg_temp.chk('11. Đánh giá', 'submit_review', 'Người không mua bị chặn', v_err ILIKE '%not eligible%', v_err);

        SELECT count(*), max(x.full_name) INTO v_int, v_txt FROM list_reviews_for_product(v_prod_a, 20, 0) x;
        r := r || pg_temp.chk('11. Đánh giá', 'list_reviews_for_product', '1 đánh giá, kèm tên người viết', v_int = 1 AND v_txt = 'FN Khách Hàng', v_txt);
        SELECT * INTO rec FROM get_product_rating_summary(v_prod_b);
        r := r || pg_temp.chk('11. Đánh giá', 'get_product_rating_summary', 'Sách B: 1 lượt, trung bình 3.00', rec.review_count = 1 AND rec.average_rating = 3,
                              format('%s lượt, %s sao', rec.review_count, rec.average_rating));
        SELECT * INTO rec FROM get_product_rating_summary(v_prod_c);
        r := r || pg_temp.chk('11. Đánh giá', 'get_product_rating_summary', 'Sách chưa có đánh giá -> 0 lượt, 0 sao', rec.review_count = 0 AND rec.average_rating = 0);

        SELECT string_agg(x.product_id::text || ':' || x.reason, ' ' ORDER BY ord) INTO v_txt
        FROM get_book_recommendations(v_prod_a, 8) WITH ORDINALITY AS x(product_id, product_name, base_price, reason, ord);
        r := r || pg_temp.chk('11. Gợi ý', 'get_book_recommendations', 'Sách A: B (mua cùng đơn) trước, C (cùng danh mục) sau; không có D đã xóa',
                              v_txt = v_prod_b || ':bought_together ' || v_prod_c || ':same_category', v_txt);
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 11', 'Mục 11 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 12. HOÀN TIỀN
    -- =================================================================
    BEGIN
        v_err := pg_temp.expect_error(format('SELECT * FROM create_refund_request(%s, %s, ''x'')', v_order2, v_cust));
        r := r || pg_temp.chk('12. Hoàn tiền', 'create_refund_request', 'Đơn chưa giao bị chặn', v_err ILIKE '%Only delivered%', v_err);
        v_err := pg_temp.expect_error(format('SELECT * FROM create_refund_request(%s, %s, ''x'')', v_order1, v_cust2));
        r := r || pg_temp.chk('12. Hoàn tiền', 'create_refund_request', 'Đơn của người khác bị chặn', v_err ILIKE '%not found for user%', v_err);

        SELECT x.id, x.status, x.refund_amount INTO rec FROM create_refund_request(v_order1, v_cust, 'Sách bị lỗi in') x;
        v_refund := rec.id;
        r := r || pg_temp.chk('12. Hoàn tiền', 'create_refund_request', 'Tạo yêu cầu: requested, số tiền = tổng đơn 245.000',
                              rec.status = 'requested' AND rec.refund_amount = 245000, format('%s, %s', rec.status, rec.refund_amount));
        v_err := pg_temp.expect_error(format('SELECT * FROM create_refund_request(%s, %s, ''x'')', v_order1, v_cust));
        r := r || pg_temp.chk('12. Hoàn tiền', 'create_refund_request', 'Gửi yêu cầu thứ 2 cho cùng đơn bị chặn', v_err ILIKE '%already has an active%', v_err);

        SELECT count(*) INTO v_int FROM list_refund_requests('requested', v_cust, 20, 0);
        r := r || pg_temp.chk('12. Hoàn tiền', 'list_refund_requests', 'Lọc trạng thái + khách: 1 yêu cầu', v_int = 1);
        SELECT x.order_code INTO v_txt FROM get_refund_request_by_id(v_refund) x;
        r := r || pg_temp.chk('12. Hoàn tiền', 'get_refund_request_by_id', 'Kèm đúng mã đơn', v_txt = (SELECT order_code FROM orders WHERE id = v_order1), v_txt);

        SELECT x.status, x.processed_at INTO rec FROM process_refund_request(v_refund, TRUE, v_staff) x;
        SELECT status::text INTO v_txt FROM payments WHERE order_id = v_order1;
        r := r || pg_temp.chk('12. Hoàn tiền', 'process_refund_request', 'Duyệt -> refunded, thanh toán của đơn -> refunded',
                              rec.status = 'refunded' AND rec.processed_at IS NOT NULL AND v_txt = 'refunded', format('%s / payment=%s', rec.status, v_txt));
        v_err := pg_temp.expect_error(format('SELECT * FROM process_refund_request(%s, true, %s)', v_refund, v_staff));
        r := r || pg_temp.chk('12. Hoàn tiền', 'process_refund_request', 'Duyệt lại yêu cầu đã xử lý bị chặn', v_err ILIKE '%already processed%', v_err);

        PERFORM update_order_status(v_order2, 'shipping', v_staff);
        PERFORM update_order_status(v_order2, 'delivered', v_staff);
        SELECT x.id INTO v_refund2 FROM create_refund_request(v_order2, v_cust, 'Đổi ý', 50000) x;
        SELECT x.status INTO v_txt FROM process_refund_request(v_refund2, FALSE, v_staff) x;
        r := r || pg_temp.chk('12. Hoàn tiền', 'process_refund_request', 'Từ chối -> rejected, thanh toán vẫn success',
                              v_txt = 'rejected' AND (SELECT status FROM payments WHERE order_id = v_order2) = 'success',
                              format('%s / payment=%s', v_txt, (SELECT status FROM payments WHERE order_id = v_order2)));
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 12', 'Mục 12 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 13. THỐNG KÊ — khoảng thời gian [now(), now()] = chỉ các đơn test
    --     (mọi đơn test có created_at = thời điểm bắt đầu giao dịch)
    --     Đơn 1 (245.000) + đơn 2 (130.000) tính; đơn 3 đã hủy không tính.
    -- =================================================================
    BEGIN
        SELECT string_agg(format('%s:%s:%s', x.product_id, x.total_quantity_sold, x.total_revenue::int), ' ' ORDER BY ord) INTO v_txt
        FROM get_top_selling_books(now(), now(), 10) WITH ORDINALITY AS x(product_id, product_name, total_quantity_sold, total_revenue, ord);
        r := r || pg_temp.chk('13. Thống kê', 'get_top_selling_books', 'A bán 3 cuốn (300.000) đứng trước B 1 cuốn (35.000); C (đơn hủy) không tính',
                              v_txt = format('%s:3:300000 %s:1:35000', v_prod_a, v_prod_b), v_txt);
        SELECT count(*), sum(x.revenue) INTO v_int, v_num FROM get_revenue_report(now(), now()) x;
        r := r || pg_temp.chk('13. Thống kê', 'get_revenue_report', '1 ngày, doanh thu 245.000 + 130.000 = 375.000', v_int = 1 AND v_num = 375000, format('%s ngày, %s', v_int, v_num));
        SELECT * INTO rec FROM get_dashboard_summary(now(), now());
        r := r || pg_temp.chk('13. Thống kê', 'get_dashboard_summary', '2 đơn, 375.000, 2 khách mới',
                              rec.total_orders = 2 AND rec.total_revenue = 375000 AND rec.new_customers = 2 AND rec.pending_orders >= 0,
                              format('%s đơn, %s, %s khách mới', rec.total_orders, rec.total_revenue, rec.new_customers));
    EXCEPTION WHEN OTHERS THEN
        r := r || pg_temp.chk('LỖI', 'mục 13', 'Mục 13 dừng giữa chừng', FALSE, SQLERRM);
    END;

    -- =================================================================
    -- 14. ĐỘ PHỦ: function nào trong DB chưa có ca kiểm tra -> FAIL
    -- =================================================================
    SELECT string_agg(p.proname, ', ' ORDER BY p.proname) INTO v_txt
    FROM pg_proc p
    WHERE p.pronamespace = 'public'::regnamespace
      AND p.proname NOT IN (SELECT trim(f) FROM unnest(r) x, unnest(string_to_array(x.ham, ',')) f);
    r := r || pg_temp.chk('14. Độ phủ', '(tất cả)',
                          format('Mọi function trong DB đều được kiểm tra (%s function)',
                                 (SELECT count(*) FROM pg_proc WHERE pronamespace = 'public'::regnamespace)),
                          v_txt IS NULL, coalesce('Chưa kiểm tra: ' || v_txt, 'đủ'));

    -- Hoàn tác toàn bộ dữ liệu test
    RAISE EXCEPTION USING ERRCODE = 'TBT01', MESSAGE = 'hoan tac du lieu test';
  EXCEPTION WHEN SQLSTATE 'TBT01' THEN
    NULL;
  END;

  INSERT INTO fn_test_results
  SELECT x.ord::int, x.nhom, x.ham, x.kiem_tra, x.ket_qua, x.chi_tiet
  FROM unnest(r) WITH ORDINALITY AS x(stt, nhom, ham, kiem_tra, ket_qua, chi_tiet, ord);
END
$test$;

-- Xác nhận dữ liệu test đã được hoàn tác
INSERT INTO fn_test_results
SELECT (SELECT max(stt) + 1 FROM fn_test_results), '15. Hoàn tác', '(tất cả)', 'Không còn dữ liệu test nào trong DB',
       CASE WHEN n = 0 THEN 'PASS' ELSE 'FAIL' END, format('%s user test còn sót', n)
FROM (SELECT count(*) AS n FROM users WHERE email LIKE 'fntest\_%@test.local') s;

RESET client_min_messages;

-- KẾT QUẢ (dòng 0 = tổng kết)
SELECT 0 AS stt,
       format('%s/%s PASS', count(*) FILTER (WHERE ket_qua = 'PASS'), count(*)) AS ket_qua,
       'TỔNG KẾT' AS nhom,
       format('%s function', (SELECT count(*) FROM pg_proc WHERE pronamespace = 'public'::regnamespace)) AS ham,
       format('%s FAIL (trong đó %s lỗi đã biết A1–A3), %s SKIP',
              count(*) FILTER (WHERE ket_qua = 'FAIL'),
              count(*) FILTER (WHERE ket_qua = 'FAIL' AND nhom = 'Lỗi đã biết'),
              count(*) FILTER (WHERE ket_qua = 'SKIP')) AS kiem_tra,
       NULL AS chi_tiet
FROM fn_test_results
UNION ALL
SELECT stt, ket_qua, nhom, ham, kiem_tra, chi_tiet FROM fn_test_results
ORDER BY stt;
