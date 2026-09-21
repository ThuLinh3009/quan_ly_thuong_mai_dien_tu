-- ============================================================
-- TBookStore — dữ liệu mẫu để test Postman (Sprint 1-2)
-- Chạy qua: python -m app.scripts.migrate --seed
-- Idempotent: dùng ON CONFLICT DO NOTHING nên chạy lại nhiều lần vẫn an toàn.
-- ============================================================

-- Tài khoản mẫu (mật khẩu bcrypt, hash tạo sẵn — KHÔNG dùng cho production)
--   admin@tbookstore.vn     / Admin@123
--   staff@tbookstore.vn     / Staff@123
--   customer@tbookstore.vn  / Customer@123
-- Lưu ý: dùng đuôi .vn (không phải .local/.test) vì email-validator (pydantic EmailStr)
-- coi .local/.test là special-use domain và từ chối ngay ở bước validate request.
INSERT INTO users (email, password_hash, full_name, phone, role) VALUES
    ('admin@tbookstore.vn', '$2b$10$1epn4Ignb7F5csJQWAlAqeknLI0bOlXpVF8e8nzgPPHKX6cjhulnW', 'Quan tri vien', '0900000001', 'admin'),
    ('staff@tbookstore.vn', '$2b$10$u4egbpefnzVirFERpEOLmuJK7GCufGDXomFQU1c39sBvXfQs3VodG', 'Nhan vien Demo', '0900000002', 'staff'),
    ('customer@tbookstore.vn', '$2b$10$/cZhF87b.2m5jUig9Q6BUevsUIjCL4eMSGKIRDOOYuCjR0S35bU/m', 'Khach Hang Demo', '0900000003', 'customer')
ON CONFLICT (email) DO NOTHING;

-- Danh mục
INSERT INTO categories (name, slug, is_active) VALUES
    ('Văn học', 'van-hoc', TRUE),
    ('Kinh tế', 'kinh-te', TRUE),
    ('Thiếu nhi', 'thieu-nhi', TRUE)
ON CONFLICT (slug) DO NOTHING;

-- Nhà cung cấp
INSERT INTO suppliers (name, contact_phone, email, address, is_active) VALUES
    ('NXB Kim Đồng', '0243123456', 'lienhe@kimdong.vn', '55 Quang Trung, Hà Nội', TRUE),
    ('NXB Trẻ', '0283123456', 'lienhe@nxbtre.com.vn', '161B Lý Chính Thắng, TP.HCM', TRUE)
ON CONFLICT DO NOTHING;

-- Sản phẩm mẫu + biến thể + tồn kho
DO $$
DECLARE
    v_cat_van_hoc  BIGINT;
    v_cat_kinh_te  BIGINT;
    v_product_id   BIGINT;
    v_variant_id   BIGINT;
BEGIN
    SELECT id INTO v_cat_van_hoc FROM categories WHERE slug = 'van-hoc';
    SELECT id INTO v_cat_kinh_te FROM categories WHERE slug = 'kinh-te';

    IF NOT EXISTS (SELECT 1 FROM products WHERE sku = 'SACH-001') THEN
        INSERT INTO products (category_id, sku, name, slug, author, publisher, base_price, description)
        VALUES (v_cat_van_hoc, 'SACH-001', 'Số Đỏ', 'so-do', 'Vũ Trọng Phụng', 'NXB Văn Học', 85000,
                'Tiểu thuyết trào phúng kinh điển của văn học Việt Nam.')
        RETURNING id INTO v_product_id;

        INSERT INTO product_variants (product_id, variant_name, sku, price_adjustment)
        VALUES (v_product_id, 'Bìa mềm', 'SACH-001-BM', 0)
        RETURNING id INTO v_variant_id;
        INSERT INTO inventories (product_variant_id, quantity_on_hand, reorder_level)
        VALUES (v_variant_id, 100, 10);

        INSERT INTO product_variants (product_id, variant_name, sku, price_adjustment)
        VALUES (v_product_id, 'Bìa cứng', 'SACH-001-BC', 30000)
        RETURNING id INTO v_variant_id;
        INSERT INTO inventories (product_variant_id, quantity_on_hand, reorder_level)
        VALUES (v_variant_id, 40, 5);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM products WHERE sku = 'SACH-002') THEN
        INSERT INTO products (category_id, sku, name, slug, author, publisher, base_price, description)
        VALUES (v_cat_kinh_te, 'SACH-002', 'Nhà Giả Kim', 'nha-gia-kim', 'Paulo Coelho', 'NXB Hội Nhà Văn', 79000,
                'Hành trình đi tìm kho báu và bài học về ước mơ.')
        RETURNING id INTO v_product_id;

        INSERT INTO product_variants (product_id, variant_name, sku, price_adjustment)
        VALUES (v_product_id, 'Bìa mềm', 'SACH-002-BM', 0)
        RETURNING id INTO v_variant_id;
        INSERT INTO inventories (product_variant_id, quantity_on_hand, reorder_level)
        VALUES (v_variant_id, 150, 15);
    END IF;
END $$;
