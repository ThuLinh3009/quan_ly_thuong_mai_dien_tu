-- ============================================================
-- TBookStore — PostgreSQL functions
-- Chay sau schema.sql. Goi tu FastAPI (psycopg) qua "SELECT * FROM fn(...)"
-- hoac "SELECT fn(...)" tuy ham tra ve TABLE hay scalar.
-- ============================================================

-- ------------------------------------------------------------
-- 1. get_book_by_id — chi tiet 1 cuon sach + cac bien the + ton kho
-- Vi du: SELECT * FROM get_book_by_id(10);
-- ------------------------------------------------------------
-- Dung chung cho ca trang xem cong khai (chi hien is_active=true qua tang
-- service) lan man hinh quan tri (can them slug/is_active/timestamps de sua).
-- DROP truoc vi doi kieu tra ve (them cot) — Postgres khong cho CREATE OR
-- REPLACE doi return type cua function co san.
DROP FUNCTION IF EXISTS get_book_by_id(BIGINT);
CREATE OR REPLACE FUNCTION get_book_by_id(p_product_id BIGINT)
RETURNS TABLE (
    id              BIGINT,
    sku             VARCHAR,
    name            VARCHAR,
    slug            VARCHAR,
    author          VARCHAR,
    publisher       VARCHAR,
    isbn            VARCHAR,
    description     TEXT,
    cover_image_url VARCHAR,
    base_price      NUMERIC,
    is_active       BOOLEAN,
    created_at      TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ,
    category_id     BIGINT,
    category_name   VARCHAR,
    variants        JSON
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id, p.sku, p.name, p.slug, p.author, p.publisher, p.isbn, p.description,
        p.cover_image_url, p.base_price, p.is_active, p.created_at, p.updated_at,
        c.id, c.name,
        COALESCE(
            (SELECT json_agg(json_build_object(
                'id', pv.id,
                'product_id', pv.product_id,
                'variant_name', pv.variant_name,
                'sku', pv.sku,
                'price_adjustment', pv.price_adjustment,
                'is_active', pv.is_active,
                'quantity_on_hand', inv.quantity_on_hand,
                'quantity_reserved', inv.quantity_reserved,
                'reorder_level', inv.reorder_level
             ) ORDER BY pv.id)
             FROM product_variants pv
             LEFT JOIN inventories inv ON inv.product_variant_id = pv.id
             WHERE pv.product_id = p.id
            ), '[]'::json
        ) AS variants
    FROM products p
    JOIN categories c ON c.id = p.category_id
    WHERE p.id = p_product_id AND p.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- ------------------------------------------------------------
-- 2. search_books — tim kiem/loc/phan trang danh sach sach
-- Vi du: SELECT * FROM search_books('harry potter', NULL, NULL, NULL, 20, 0);
-- ------------------------------------------------------------
-- p_is_active=TRUE (mac dinh) danh cho trang cong khai; man quan tri truyen
-- NULL (xem ca an/hien) hoac FALSE (chi xem sp da an) qua tang service.
-- p_sort_by chi nhan 'name'|'base_price'|'created_at' (whitelist chong SQL
-- injection khi build ORDER BY dong qua EXECUTE).
DROP FUNCTION IF EXISTS search_books(TEXT, BIGINT, NUMERIC, NUMERIC, INT, INT);
CREATE OR REPLACE FUNCTION search_books(
    p_keyword     TEXT DEFAULT NULL,
    p_category_id BIGINT DEFAULT NULL,
    p_min_price   NUMERIC DEFAULT NULL,
    p_max_price   NUMERIC DEFAULT NULL,
    p_is_active   BOOLEAN DEFAULT TRUE,
    p_sort_by     TEXT DEFAULT 'created_at',
    p_sort_dir    TEXT DEFAULT 'desc',
    p_limit       INT DEFAULT 20,
    p_offset      INT DEFAULT 0
)
RETURNS TABLE (
    id              BIGINT,
    sku             VARCHAR,
    name            VARCHAR,
    author          VARCHAR,
    base_price      NUMERIC,
    cover_image_url VARCHAR,
    is_active       BOOLEAN,
    created_at      TIMESTAMPTZ,
    category_id     BIGINT,
    category_name   VARCHAR,
    total_count     BIGINT
) AS $$
DECLARE
    v_order_col TEXT;
    v_order_dir TEXT;
BEGIN
    v_order_col := CASE p_sort_by
        WHEN 'name' THEN 'p.name'
        WHEN 'base_price' THEN 'p.base_price'
        ELSE 'p.created_at'
    END;
    v_order_dir := CASE WHEN lower(p_sort_dir) = 'asc' THEN 'ASC' ELSE 'DESC' END;

    RETURN QUERY EXECUTE format(
        $q$
        SELECT
            p.id, p.sku, p.name, p.author, p.base_price, p.cover_image_url,
            p.is_active, p.created_at, p.category_id, c.name,
            COUNT(*) OVER() AS total_count
        FROM products p
        JOIN categories c ON c.id = p.category_id
        WHERE p.deleted_at IS NULL
          AND ($1 IS NULL OR p.is_active = $1)
          AND ($2 IS NULL OR p.category_id = $2)
          AND ($3 IS NULL OR p.base_price >= $3)
          AND ($4 IS NULL OR p.base_price <= $4)
          AND ($5 IS NULL OR p.search_vector @@ plainto_tsquery('simple', $5))
        ORDER BY %s %s
        LIMIT $6 OFFSET $7
        $q$,
        v_order_col, v_order_dir
    ) USING p_is_active, p_category_id, p_min_price, p_max_price, p_keyword, p_limit, p_offset;
END;
$$ LANGUAGE plpgsql STABLE;

-- ------------------------------------------------------------
-- 3. get_cart_total — tong tien gio hang
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_cart_total(p_cart_id BIGINT)
RETURNS NUMERIC AS $$
    SELECT COALESCE(SUM(quantity * unit_price_snapshot), 0)
    FROM cart_items
    WHERE cart_id = p_cart_id;
$$ LANGUAGE sql STABLE;

-- ------------------------------------------------------------
-- 4. add_to_cart — them/cong don sach vao gio hang cua khach. Ban day du
-- (dung gia flash sale qua get_effective_unit_price()) nam o muc 20 phia
-- duoi, khong dinh nghia lai o day de tranh code trung/gay nham lan.
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- 5. place_order — checkout. Ban day du (kiem tra dia chi thuoc user, cong
-- quantity_sold cho flash sale) nam o muc 23 phia duoi, khong dinh nghia lai
-- o day de tranh code trung/gay nham lan.
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- 6. update_order_status — chuyen trang thai don hang dung quy tac,
--    tu ghi order_status_history, hoan ton kho neu huy don.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION update_order_status(
    p_order_id   BIGINT,
    p_new_status order_status,
    p_changed_by BIGINT,
    p_note       VARCHAR DEFAULT NULL
) RETURNS VOID AS $$
DECLARE
    v_current order_status;
    v_valid   BOOLEAN;
BEGIN
    SELECT status INTO v_current FROM orders WHERE id = p_order_id FOR UPDATE;
    IF v_current IS NULL THEN
        RAISE EXCEPTION 'Order % not found', p_order_id;
    END IF;

    v_valid := CASE v_current
        WHEN 'pending'   THEN p_new_status IN ('confirmed', 'cancelled')
        WHEN 'confirmed' THEN p_new_status IN ('shipping', 'cancelled')
        WHEN 'shipping'  THEN p_new_status = 'delivered'
        ELSE FALSE
    END;

    IF NOT v_valid THEN
        RAISE EXCEPTION 'Invalid transition from % to %', v_current, p_new_status;
    END IF;

    UPDATE orders SET status = p_new_status WHERE id = p_order_id;

    INSERT INTO order_status_history (order_id, from_status, to_status, changed_by, note)
    VALUES (p_order_id, v_current, p_new_status, p_changed_by, p_note);

    IF p_new_status = 'cancelled' THEN
        UPDATE inventories inv
        SET quantity_on_hand = inv.quantity_on_hand + oi.quantity,
            updated_at = now()
        FROM order_items oi
        WHERE oi.order_id = p_order_id AND inv.product_variant_id = oi.product_variant_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 7. get_order_detail — chi tiet don hang de hien thi/tra API. Ban day du
-- (them user_id/address, dung DROP guard) nam o muc 24 phia duoi vi Sprint 3
-- doi return type; khong dinh nghia lai o day de tranh 2 CREATE OR REPLACE
-- xung dot return type voi nhau tren nhung lan chay lai functions.sql sau.
-- ------------------------------------------------------------

-- ------------------------------------------------------------
-- 8. get_top_selling_books — top sach ban chay trong khoang thoi gian
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_top_selling_books(
    p_from  TIMESTAMPTZ,
    p_to    TIMESTAMPTZ,
    p_limit INT DEFAULT 10
) RETURNS TABLE (
    product_id           BIGINT,
    product_name         VARCHAR,
    total_quantity_sold  BIGINT,
    total_revenue        NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pv.product_id,
        p.name,
        SUM(oi.quantity)::BIGINT,
        SUM(oi.line_total - oi.discount_amount)
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p ON p.id = pv.product_id
    WHERE o.status <> 'cancelled'
      AND o.created_at BETWEEN p_from AND p_to
    GROUP BY pv.product_id, p.name
    ORDER BY total_quantity_sold DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ------------------------------------------------------------
-- 9. get_revenue_report — doanh thu theo ngay trong khoang thoi gian
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_revenue_report(
    p_from TIMESTAMPTZ,
    p_to   TIMESTAMPTZ
) RETURNS TABLE (
    report_date  DATE,
    orders_count BIGINT,
    revenue      NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        date_trunc('day', o.created_at)::DATE,
        COUNT(*)::BIGINT,
        SUM(o.total_amount)
    FROM orders o
    WHERE o.status <> 'cancelled'
      AND o.created_at BETWEEN p_from AND p_to
    GROUP BY 1
    ORDER BY 1;
END;
$$ LANGUAGE plpgsql STABLE;

-- ------------------------------------------------------------
-- 10. restock_from_import — cong ton kho khi 1 lo hang duoc nhap
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION restock_from_import(p_import_lot_id BIGINT)
RETURNS VOID AS $$
BEGIN
    INSERT INTO inventories (product_variant_id, quantity_on_hand)
    SELECT iri.product_variant_id, iri.quantity
    FROM import_receipt_items iri
    WHERE iri.import_lot_id = p_import_lot_id
    ON CONFLICT (product_variant_id)
    DO UPDATE SET quantity_on_hand = inventories.quantity_on_hand + EXCLUDED.quantity_on_hand,
                  updated_at = now();
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 11. submit_review — khach hang danh gia sach, chi khi don da Delivered
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION submit_review(
    p_order_item_id BIGINT,
    p_user_id       BIGINT,
    p_rating        SMALLINT,
    p_comment       TEXT DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_product_id BIGINT;
    v_review_id  BIGINT;
BEGIN
    SELECT pv.product_id INTO v_product_id
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    WHERE oi.id = p_order_item_id
      AND o.user_id = p_user_id
      AND o.status = 'delivered';

    IF v_product_id IS NULL THEN
        RAISE EXCEPTION 'Order item % is not eligible for review by user %', p_order_item_id, p_user_id;
    END IF;

    INSERT INTO reviews (product_id, user_id, order_item_id, rating, comment)
    VALUES (v_product_id, p_user_id, p_order_item_id, p_rating, p_comment)
    RETURNING id INTO v_review_id;

    RETURN v_review_id;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 12. get_book_recommendations — "khach mua cung" + cung danh muc
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_book_recommendations(
    p_product_id BIGINT,
    p_limit      INT DEFAULT 8
) RETURNS TABLE (
    product_id   BIGINT,
    product_name VARCHAR,
    base_price   NUMERIC,
    reason       VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    (
        SELECT p2.id, p2.name, p2.base_price, 'bought_together'::VARCHAR
        FROM order_items oi1
        JOIN product_variants pv1 ON pv1.id = oi1.product_variant_id
        JOIN order_items oi2 ON oi2.order_id = oi1.order_id AND oi2.id <> oi1.id
        JOIN product_variants pv2 ON pv2.id = oi2.product_variant_id
        JOIN products p2 ON p2.id = pv2.product_id
        WHERE pv1.product_id = p_product_id
          AND pv2.product_id <> p_product_id
          AND p2.deleted_at IS NULL
        GROUP BY p2.id, p2.name, p2.base_price
        ORDER BY COUNT(*) DESC
        LIMIT p_limit
    )
    UNION ALL
    (
        SELECT p2.id, p2.name, p2.base_price, 'same_category'::VARCHAR
        FROM products p1
        JOIN products p2 ON p2.category_id = p1.category_id AND p2.id <> p1.id
        WHERE p1.id = p_product_id
          AND p2.deleted_at IS NULL
          AND p2.id NOT IN (
              SELECT pv2.product_id
              FROM order_items oi1
              JOIN product_variants pv1 ON pv1.id = oi1.product_variant_id
              JOIN order_items oi2 ON oi2.order_id = oi1.order_id AND oi2.id <> oi1.id
              JOIN product_variants pv2 ON pv2.id = oi2.product_variant_id
              WHERE pv1.product_id = p_product_id
          )
        ORDER BY p2.created_at DESC
        LIMIT p_limit
    )
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================
-- CRUD quan tri (Sprint 1-2) — moi thao tac ghi/doc don gian cung dua vao
-- function de code Python (repositories/*.py) chi goi "SELECT * FROM fn(...)",
-- khong tu viet SQL. Tra ve row/bang de map thang sang response schema.
-- ============================================================

-- ------------------------------------------------------------
-- 13. Category CRUD
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION category_slug_exists(p_slug VARCHAR, p_exclude_id BIGINT DEFAULT NULL)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM categories
        WHERE slug = p_slug AND deleted_at IS NULL
          AND (p_exclude_id IS NULL OR id <> p_exclude_id)
    );
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION create_category(
    p_name      VARCHAR,
    p_slug      VARCHAR,
    p_parent_id BIGINT,
    p_is_active BOOLEAN
) RETURNS TABLE (id BIGINT, parent_id BIGINT, name VARCHAR, slug VARCHAR, is_active BOOLEAN) AS $$
    INSERT INTO categories (parent_id, name, slug, is_active)
    VALUES (p_parent_id, p_name, p_slug, p_is_active)
    RETURNING categories.id, categories.parent_id, categories.name, categories.slug, categories.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION get_category_by_id(p_id BIGINT)
RETURNS TABLE (id BIGINT, parent_id BIGINT, name VARCHAR, slug VARCHAR, is_active BOOLEAN) AS $$
    SELECT c.id, c.parent_id, c.name, c.slug, c.is_active
    FROM categories c WHERE c.id = p_id AND c.deleted_at IS NULL;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION list_categories(
    p_keyword   TEXT DEFAULT NULL,
    p_parent_id BIGINT DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL,
    p_limit     INT DEFAULT 20,
    p_offset    INT DEFAULT 0
) RETURNS TABLE (
    id BIGINT, parent_id BIGINT, name VARCHAR, slug VARCHAR, is_active BOOLEAN, total_count BIGINT
) AS $$
    SELECT c.id, c.parent_id, c.name, c.slug, c.is_active, COUNT(*) OVER() AS total_count
    FROM categories c
    WHERE c.deleted_at IS NULL
      AND (p_keyword IS NULL OR c.name ILIKE '%' || p_keyword || '%')
      AND (p_parent_id IS NULL OR c.parent_id = p_parent_id)
      AND (p_is_active IS NULL OR c.is_active = p_is_active)
    ORDER BY c.name
    LIMIT p_limit OFFSET p_offset;
$$ LANGUAGE sql STABLE;

-- Cac tham so nullable (p_name/p_slug/p_parent_id/p_is_active) da duoc tang
-- service merge san voi gia tri cu truoc khi goi (full-value semantics,
-- khong dung NULL lam "giu nguyen") de tranh nham lan voi parent_id=NULL
-- hop le (category goc). Rieng p_parent_id truyen -1 nghia la "khong doi"
-- (khong dung duoc vi FK), thuc te service luon tinh san gia tri cuoi cung.
CREATE OR REPLACE FUNCTION update_category(
    p_id        BIGINT,
    p_name      VARCHAR,
    p_slug      VARCHAR,
    p_parent_id BIGINT,
    p_is_active BOOLEAN
) RETURNS TABLE (id BIGINT, parent_id BIGINT, name VARCHAR, slug VARCHAR, is_active BOOLEAN) AS $$
    UPDATE categories
    SET name = p_name, slug = p_slug, parent_id = p_parent_id, is_active = p_is_active
    WHERE categories.id = p_id AND deleted_at IS NULL
    RETURNING categories.id, categories.parent_id, categories.name, categories.slug, categories.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION soft_delete_category(p_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE categories SET deleted_at = now(), is_active = FALSE
    WHERE id = p_id AND deleted_at IS NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 14. Supplier CRUD (khong co cot deleted_at — "xoa" = khoa is_active=false)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_supplier(
    p_name          VARCHAR,
    p_contact_phone VARCHAR,
    p_email         VARCHAR,
    p_address       VARCHAR,
    p_is_active     BOOLEAN
) RETURNS TABLE (id BIGINT, name VARCHAR, contact_phone VARCHAR, email VARCHAR, address VARCHAR, is_active BOOLEAN) AS $$
    INSERT INTO suppliers (name, contact_phone, email, address, is_active)
    VALUES (p_name, p_contact_phone, p_email, p_address, p_is_active)
    RETURNING suppliers.id, suppliers.name, suppliers.contact_phone, suppliers.email, suppliers.address, suppliers.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION get_supplier_by_id(p_id BIGINT)
RETURNS TABLE (id BIGINT, name VARCHAR, contact_phone VARCHAR, email VARCHAR, address VARCHAR, is_active BOOLEAN) AS $$
    SELECT s.id, s.name, s.contact_phone, s.email, s.address, s.is_active
    FROM suppliers s WHERE s.id = p_id;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION list_suppliers(
    p_keyword   TEXT DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL,
    p_limit     INT DEFAULT 20,
    p_offset    INT DEFAULT 0
) RETURNS TABLE (
    id BIGINT, name VARCHAR, contact_phone VARCHAR, email VARCHAR, address VARCHAR, is_active BOOLEAN, total_count BIGINT
) AS $$
    SELECT s.id, s.name, s.contact_phone, s.email, s.address, s.is_active, COUNT(*) OVER() AS total_count
    FROM suppliers s
    WHERE (p_keyword IS NULL OR s.name ILIKE '%' || p_keyword || '%')
      AND (p_is_active IS NULL OR s.is_active = p_is_active)
    ORDER BY s.name
    LIMIT p_limit OFFSET p_offset;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION update_supplier(
    p_id            BIGINT,
    p_name          VARCHAR,
    p_contact_phone VARCHAR,
    p_email         VARCHAR,
    p_address       VARCHAR,
    p_is_active     BOOLEAN
) RETURNS TABLE (id BIGINT, name VARCHAR, contact_phone VARCHAR, email VARCHAR, address VARCHAR, is_active BOOLEAN) AS $$
    UPDATE suppliers
    SET name = p_name, contact_phone = p_contact_phone, email = p_email,
        address = p_address, is_active = p_is_active
    WHERE suppliers.id = p_id
    RETURNING suppliers.id, suppliers.name, suppliers.contact_phone, suppliers.email, suppliers.address, suppliers.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION set_supplier_active(p_id BIGINT, p_is_active BOOLEAN)
RETURNS TABLE (id BIGINT, name VARCHAR, contact_phone VARCHAR, email VARCHAR, address VARCHAR, is_active BOOLEAN) AS $$
    UPDATE suppliers SET is_active = p_is_active
    WHERE suppliers.id = p_id
    RETURNING suppliers.id, suppliers.name, suppliers.contact_phone, suppliers.email, suppliers.address, suppliers.is_active;
$$ LANGUAGE sql;

-- ------------------------------------------------------------
-- 15. Product / Variant / Inventory CRUD
-- get_book_by_id() (muc 1) da du field cho ca man chi tiet quan tri lan
-- cong khai nen dung chung, khong tao them ham get rieng.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION product_sku_exists(p_sku VARCHAR)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (SELECT 1 FROM products WHERE sku = p_sku);
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION product_slug_exists(p_slug VARCHAR)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (SELECT 1 FROM products WHERE slug = p_slug);
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION create_product(
    p_category_id     BIGINT,
    p_sku             VARCHAR,
    p_name            VARCHAR,
    p_slug            VARCHAR,
    p_author          VARCHAR,
    p_publisher       VARCHAR,
    p_isbn            VARCHAR,
    p_description     TEXT,
    p_cover_image_url VARCHAR,
    p_base_price      NUMERIC,
    p_is_active       BOOLEAN
) RETURNS BIGINT AS $$
    INSERT INTO products (category_id, sku, name, slug, author, publisher, isbn, description, cover_image_url, base_price, is_active)
    VALUES (p_category_id, p_sku, p_name, p_slug, p_author, p_publisher, p_isbn, p_description, p_cover_image_url, p_base_price, p_is_active)
    RETURNING id;
$$ LANGUAGE sql;

-- Tham so da duoc tang service merge san voi gia tri cu (full-value), giong
-- update_category() — chi sku la khong the doi (khong nam trong tham so).
CREATE OR REPLACE FUNCTION update_product(
    p_id              BIGINT,
    p_category_id     BIGINT,
    p_name            VARCHAR,
    p_slug            VARCHAR,
    p_author          VARCHAR,
    p_publisher       VARCHAR,
    p_isbn            VARCHAR,
    p_description     TEXT,
    p_cover_image_url VARCHAR,
    p_base_price      NUMERIC,
    p_is_active       BOOLEAN
) RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE products
    SET category_id = p_category_id, name = p_name, slug = p_slug, author = p_author,
        publisher = p_publisher, isbn = p_isbn, description = p_description,
        cover_image_url = p_cover_image_url, base_price = p_base_price, is_active = p_is_active
    WHERE id = p_id AND deleted_at IS NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION soft_delete_product(p_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE products SET deleted_at = now(), is_active = FALSE WHERE id = p_id AND deleted_at IS NULL;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION variant_sku_exists(p_sku VARCHAR)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (SELECT 1 FROM product_variants WHERE sku = p_sku);
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION create_variant(
    p_product_id       BIGINT,
    p_variant_name     VARCHAR,
    p_sku              VARCHAR,
    p_price_adjustment NUMERIC,
    p_is_active        BOOLEAN
) RETURNS TABLE (id BIGINT, product_id BIGINT, variant_name VARCHAR, sku VARCHAR, price_adjustment NUMERIC, is_active BOOLEAN) AS $$
    INSERT INTO product_variants (product_id, variant_name, sku, price_adjustment, is_active)
    VALUES (p_product_id, p_variant_name, p_sku, p_price_adjustment, p_is_active)
    RETURNING product_variants.id, product_variants.product_id, product_variants.variant_name,
              product_variants.sku, product_variants.price_adjustment, product_variants.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION get_variant_by_id(p_id BIGINT)
RETURNS TABLE (id BIGINT, product_id BIGINT, variant_name VARCHAR, sku VARCHAR, price_adjustment NUMERIC, is_active BOOLEAN) AS $$
    SELECT v.id, v.product_id, v.variant_name, v.sku, v.price_adjustment, v.is_active
    FROM product_variants v WHERE v.id = p_id;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION update_variant(
    p_id               BIGINT,
    p_variant_name     VARCHAR,
    p_price_adjustment NUMERIC,
    p_is_active        BOOLEAN
) RETURNS TABLE (id BIGINT, product_id BIGINT, variant_name VARCHAR, sku VARCHAR, price_adjustment NUMERIC, is_active BOOLEAN) AS $$
    UPDATE product_variants
    SET variant_name = p_variant_name, price_adjustment = p_price_adjustment, is_active = p_is_active
    WHERE product_variants.id = p_id
    RETURNING product_variants.id, product_variants.product_id, product_variants.variant_name,
              product_variants.sku, product_variants.price_adjustment, product_variants.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION set_variant_active(p_id BIGINT, p_is_active BOOLEAN)
RETURNS TABLE (id BIGINT, product_id BIGINT, variant_name VARCHAR, sku VARCHAR, price_adjustment NUMERIC, is_active BOOLEAN) AS $$
    UPDATE product_variants SET is_active = p_is_active
    WHERE product_variants.id = p_id
    RETURNING product_variants.id, product_variants.product_id, product_variants.variant_name,
              product_variants.sku, product_variants.price_adjustment, product_variants.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION create_inventory_for_variant(
    p_product_variant_id BIGINT,
    p_quantity_on_hand   INT,
    p_reorder_level      INT
) RETURNS VOID AS $$
    INSERT INTO inventories (product_variant_id, quantity_on_hand, reorder_level)
    VALUES (p_product_variant_id, p_quantity_on_hand, p_reorder_level)
    ON CONFLICT (product_variant_id) DO UPDATE
        SET quantity_on_hand = EXCLUDED.quantity_on_hand,
            reorder_level = EXCLUDED.reorder_level,
            updated_at = now();
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION get_inventory_by_variant(p_product_variant_id BIGINT)
RETURNS TABLE (
    id BIGINT, product_variant_id BIGINT, quantity_on_hand INT,
    quantity_reserved INT, reorder_level INT, updated_at TIMESTAMPTZ
) AS $$
    SELECT i.id, i.product_variant_id, i.quantity_on_hand, i.quantity_reserved, i.reorder_level, i.updated_at
    FROM inventories i WHERE i.product_variant_id = p_product_variant_id;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION update_inventory_reorder_level(p_product_variant_id BIGINT, p_reorder_level INT)
RETURNS VOID AS $$
    UPDATE inventories SET reorder_level = p_reorder_level, updated_at = now()
    WHERE product_variant_id = p_product_variant_id;
$$ LANGUAGE sql;

-- ------------------------------------------------------------
-- 16. User / Employee (bang users dung chung cho Admin/Staff/Customer,
-- "employee" chi thao tac tren role='staff')
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_user_by_email(p_email VARCHAR)
RETURNS TABLE (
    id BIGINT, email VARCHAR, password_hash VARCHAR, full_name VARCHAR, phone VARCHAR,
    role user_role, is_active BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
) AS $$
    SELECT u.id, u.email, u.password_hash, u.full_name, u.phone, u.role, u.is_active, u.created_at, u.updated_at
    FROM users u WHERE u.email = p_email AND u.deleted_at IS NULL;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION get_user_by_id(p_id BIGINT)
RETURNS TABLE (
    id BIGINT, email VARCHAR, password_hash VARCHAR, full_name VARCHAR, phone VARCHAR,
    role user_role, is_active BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
) AS $$
    SELECT u.id, u.email, u.password_hash, u.full_name, u.phone, u.role, u.is_active, u.created_at, u.updated_at
    FROM users u WHERE u.id = p_id AND u.deleted_at IS NULL;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION create_user(
    p_email         VARCHAR,
    p_password_hash VARCHAR,
    p_full_name     VARCHAR,
    p_phone         VARCHAR,
    p_role          user_role
) RETURNS TABLE (
    id BIGINT, email VARCHAR, password_hash VARCHAR, full_name VARCHAR, phone VARCHAR,
    role user_role, is_active BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
) AS $$
    INSERT INTO users (email, password_hash, full_name, phone, role)
    VALUES (p_email, p_password_hash, p_full_name, p_phone, p_role)
    RETURNING users.id, users.email, users.password_hash, users.full_name, users.phone,
              users.role, users.is_active, users.created_at, users.updated_at;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION list_staff(
    p_keyword   TEXT DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL,
    p_limit     INT DEFAULT 20,
    p_offset    INT DEFAULT 0
) RETURNS TABLE (
    id BIGINT, email VARCHAR, password_hash VARCHAR, full_name VARCHAR, phone VARCHAR,
    role user_role, is_active BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ, total_count BIGINT
) AS $$
    SELECT u.id, u.email, u.password_hash, u.full_name, u.phone, u.role, u.is_active, u.created_at, u.updated_at,
           COUNT(*) OVER() AS total_count
    FROM users u
    WHERE u.deleted_at IS NULL AND u.role = 'staff'
      AND (p_keyword IS NULL OR u.full_name ILIKE '%' || p_keyword || '%' OR u.email ILIKE '%' || p_keyword || '%')
      AND (p_is_active IS NULL OR u.is_active = p_is_active)
    ORDER BY u.created_at DESC
    LIMIT p_limit OFFSET p_offset;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION update_staff(p_id BIGINT, p_full_name VARCHAR, p_phone VARCHAR)
RETURNS TABLE (
    id BIGINT, email VARCHAR, password_hash VARCHAR, full_name VARCHAR, phone VARCHAR,
    role user_role, is_active BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
) AS $$
    UPDATE users SET full_name = p_full_name, phone = p_phone
    WHERE users.id = p_id AND deleted_at IS NULL AND role = 'staff'
    RETURNING users.id, users.email, users.password_hash, users.full_name, users.phone,
              users.role, users.is_active, users.created_at, users.updated_at;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION set_staff_active(p_id BIGINT, p_is_active BOOLEAN)
RETURNS TABLE (
    id BIGINT, email VARCHAR, password_hash VARCHAR, full_name VARCHAR, phone VARCHAR,
    role user_role, is_active BOOLEAN, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
) AS $$
    UPDATE users SET is_active = p_is_active
    WHERE users.id = p_id AND deleted_at IS NULL AND role = 'staff'
    RETURNING users.id, users.email, users.password_hash, users.full_name, users.phone,
              users.role, users.is_active, users.created_at, users.updated_at;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION soft_delete_staff(p_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    UPDATE users SET deleted_at = now(), is_active = FALSE
    WHERE id = p_id AND deleted_at IS NULL AND role = 'staff';
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 17. Refresh tokens
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_refresh_token(p_user_id BIGINT, p_token_hash VARCHAR, p_expires_at TIMESTAMPTZ)
RETURNS VOID AS $$
    INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (p_user_id, p_token_hash, p_expires_at);
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION get_valid_refresh_token(p_token_hash VARCHAR)
RETURNS TABLE (id BIGINT, user_id BIGINT, token_hash VARCHAR, expires_at TIMESTAMPTZ, revoked_at TIMESTAMPTZ) AS $$
    SELECT rt.id, rt.user_id, rt.token_hash, rt.expires_at, rt.revoked_at
    FROM refresh_tokens rt
    WHERE rt.token_hash = p_token_hash AND rt.revoked_at IS NULL AND rt.expires_at > now();
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION revoke_refresh_token(p_token_hash VARCHAR)
RETURNS VOID AS $$
    UPDATE refresh_tokens SET revoked_at = now() WHERE token_hash = p_token_hash AND revoked_at IS NULL;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION revoke_all_refresh_tokens(p_user_id BIGINT)
RETURNS VOID AS $$
    UPDATE refresh_tokens SET revoked_at = now() WHERE user_id = p_user_id AND revoked_at IS NULL;
$$ LANGUAGE sql;

-- ------------------------------------------------------------
-- 18. Import lots (nhap kho theo lo) — restock_from_import() da co san o
-- muc 10, dung lai nguyen, chi them CRUD tao/xem/liet ke o day.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_import_lot(p_supplier_id BIGINT, p_created_by BIGINT)
RETURNS TABLE (id BIGINT, lot_code VARCHAR) AS $$
    INSERT INTO import_lots (supplier_id, lot_code, created_by)
    VALUES (p_supplier_id, 'LOT-' || to_char(now(), 'YYYYMMDDHH24MISS') || '-' || p_supplier_id, p_created_by)
    RETURNING import_lots.id, import_lots.lot_code;
$$ LANGUAGE sql;

-- Nhan 3 mang song song (khong dung executemany o tang Python nua) de insert
-- nhieu dong import_receipt_items trong 1 lan goi duy nhat.
CREATE OR REPLACE FUNCTION add_import_receipt_items(
    p_import_lot_id BIGINT,
    p_variant_ids   BIGINT[],
    p_quantities    INT[],
    p_unit_costs    NUMERIC[]
) RETURNS VOID AS $$
    INSERT INTO import_receipt_items (import_lot_id, product_variant_id, quantity, unit_cost)
    SELECT p_import_lot_id, v, q, c
    FROM unnest(p_variant_ids, p_quantities, p_unit_costs) AS t(v, q, c);
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION get_import_lot_by_id(p_id BIGINT)
RETURNS TABLE (
    id BIGINT, lot_code VARCHAR, supplier_id BIGINT, supplier_name VARCHAR,
    imported_at TIMESTAMPTZ, created_by BIGINT, items JSON
) AS $$
    SELECT
        l.id, l.lot_code, l.supplier_id, s.name, l.imported_at, l.created_by,
        COALESCE(
            (SELECT json_agg(json_build_object(
                'id', iri.id,
                'product_variant_id', iri.product_variant_id,
                'variant_name', pv.variant_name,
                'sku', pv.sku,
                'quantity', iri.quantity,
                'unit_cost', iri.unit_cost
             ) ORDER BY iri.id)
             FROM import_receipt_items iri
             JOIN product_variants pv ON pv.id = iri.product_variant_id
             WHERE iri.import_lot_id = l.id
            ), '[]'::json
        )
    FROM import_lots l
    JOIN suppliers s ON s.id = l.supplier_id
    WHERE l.id = p_id;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION list_import_lots(
    p_supplier_id BIGINT DEFAULT NULL,
    p_limit       INT DEFAULT 20,
    p_offset      INT DEFAULT 0
) RETURNS TABLE (
    id BIGINT, lot_code VARCHAR, supplier_id BIGINT, supplier_name VARCHAR,
    imported_at TIMESTAMPTZ, created_by BIGINT, total_count BIGINT
) AS $$
    SELECT l.id, l.lot_code, l.supplier_id, s.name, l.imported_at, l.created_by, COUNT(*) OVER() AS total_count
    FROM import_lots l
    JOIN suppliers s ON s.id = l.supplier_id
    WHERE p_supplier_id IS NULL OR l.supplier_id = p_supplier_id
    ORDER BY l.imported_at DESC
    LIMIT p_limit OFFSET p_offset;
$$ LANGUAGE sql STABLE;

-- ------------------------------------------------------------
-- 19. Audit log — ghi 1 dong cho moi thao tac tao/sua/xoa (goi tu service
-- sau khi thao tac chinh thanh cong, cung 1 transaction nen rollback cung).
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION record_audit(
    p_user_id     BIGINT,
    p_action      VARCHAR,
    p_entity_type VARCHAR,
    p_entity_id   BIGINT,
    p_old_value   JSONB DEFAULT NULL,
    p_new_value   JSONB DEFAULT NULL
) RETURNS VOID AS $$
    INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_value, new_value)
    VALUES (p_user_id, p_action, p_entity_type, p_entity_id, p_old_value, p_new_value);
$$ LANGUAGE sql;

-- ============================================================
-- Sprint 3 (Tuan 3) — Ban hang online: gio hang, checkout, don hang,
-- khuyen mai (voucher/flash sale), tra hang/hoan tien, danh gia san pham.
-- ============================================================

-- ------------------------------------------------------------
-- 20. Gia hieu luc cua 1 bien the — uu tien gia flash sale neu dang
-- chay va con suat ban, ngược lai la base_price + price_adjustment.
-- Dung chung cho add_to_cart() va API xem gia hien tai.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_effective_unit_price(p_variant_id BIGINT)
RETURNS NUMERIC AS $$
DECLARE
    v_price       NUMERIC;
    v_flash_price NUMERIC;
BEGIN
    SELECT p.base_price + pv.price_adjustment INTO v_price
    FROM product_variants pv
    JOIN products p ON p.id = pv.product_id
    WHERE pv.id = p_variant_id AND pv.is_active = TRUE AND p.deleted_at IS NULL;

    IF v_price IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT fsi.flash_price INTO v_flash_price
    FROM flash_sale_items fsi
    JOIN promotions promo ON promo.id = fsi.promotion_id
    WHERE fsi.product_variant_id = p_variant_id
      AND promo.is_active = TRUE
      AND promo.type = 'flash_sale'
      AND now() BETWEEN promo.starts_at AND promo.ends_at
      AND fsi.quantity_sold < fsi.quantity_limit
    ORDER BY fsi.flash_price ASC
    LIMIT 1;

    RETURN COALESCE(v_flash_price, v_price);
END;
$$ LANGUAGE plpgsql STABLE;

-- add_to_cart() cap nhat: dung gia hieu luc (co flash sale) thay vi tinh
-- thang base_price + price_adjustment nhu ban dau.
CREATE OR REPLACE FUNCTION add_to_cart(
    p_user_id    BIGINT,
    p_variant_id BIGINT,
    p_quantity   INT
) RETURNS BIGINT AS $$
DECLARE
    v_cart_id BIGINT;
    v_price   NUMERIC;
    v_item_id BIGINT;
BEGIN
    IF p_quantity <= 0 THEN
        RAISE EXCEPTION 'Quantity must be positive';
    END IF;

    v_price := get_effective_unit_price(p_variant_id);
    IF v_price IS NULL THEN
        RAISE EXCEPTION 'Product variant % not found or inactive', p_variant_id;
    END IF;

    INSERT INTO carts (user_id) VALUES (p_user_id)
    ON CONFLICT (user_id) DO UPDATE SET updated_at = now()
    RETURNING id INTO v_cart_id;

    INSERT INTO cart_items (cart_id, product_variant_id, quantity, unit_price_snapshot)
    VALUES (v_cart_id, p_variant_id, p_quantity, v_price)
    ON CONFLICT (cart_id, product_variant_id)
    DO UPDATE SET quantity = cart_items.quantity + EXCLUDED.quantity,
                  unit_price_snapshot = EXCLUDED.unit_price_snapshot
    RETURNING id INTO v_item_id;

    RETURN v_item_id;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 21. Xem/sua/xoa gio hang
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_cart(p_user_id BIGINT)
RETURNS TABLE (cart_id BIGINT, items JSON, subtotal NUMERIC) AS $$
DECLARE
    v_cart_id BIGINT;
BEGIN
    SELECT id INTO v_cart_id FROM carts WHERE user_id = p_user_id;
    IF v_cart_id IS NULL THEN
        RETURN QUERY SELECT NULL::BIGINT, '[]'::json, 0::NUMERIC;
        RETURN;
    END IF;

    RETURN QUERY
    SELECT
        v_cart_id,
        COALESCE(
            (SELECT json_agg(json_build_object(
                'product_variant_id', ci.product_variant_id,
                'product_id', pv.product_id,
                'product_name', p.name,
                'variant_name', pv.variant_name,
                'sku', pv.sku,
                'cover_image_url', p.cover_image_url,
                'quantity', ci.quantity,
                'unit_price', ci.unit_price_snapshot,
                'line_total', ci.quantity * ci.unit_price_snapshot
             ) ORDER BY ci.id)
             FROM cart_items ci
             JOIN product_variants pv ON pv.id = ci.product_variant_id
             JOIN products p ON p.id = pv.product_id
             WHERE ci.cart_id = v_cart_id
            ), '[]'::json
        ),
        get_cart_total(v_cart_id);
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION update_cart_item_quantity(
    p_user_id    BIGINT,
    p_variant_id BIGINT,
    p_quantity   INT
) RETURNS BOOLEAN AS $$
DECLARE
    v_cart_id BIGINT;
    v_count   INT;
BEGIN
    IF p_quantity <= 0 THEN
        RAISE EXCEPTION 'Quantity must be positive';
    END IF;

    SELECT id INTO v_cart_id FROM carts WHERE user_id = p_user_id;
    IF v_cart_id IS NULL THEN
        RAISE EXCEPTION 'Cart not found for user %', p_user_id;
    END IF;

    UPDATE cart_items SET quantity = p_quantity
    WHERE cart_id = v_cart_id AND product_variant_id = p_variant_id;
    GET DIAGNOSTICS v_count = ROW_COUNT;

    UPDATE carts SET updated_at = now() WHERE id = v_cart_id;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION remove_cart_item(p_user_id BIGINT, p_variant_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_cart_id BIGINT;
    v_count   INT;
BEGIN
    SELECT id INTO v_cart_id FROM carts WHERE user_id = p_user_id;
    IF v_cart_id IS NULL THEN
        RETURN FALSE;
    END IF;

    DELETE FROM cart_items WHERE cart_id = v_cart_id AND product_variant_id = p_variant_id;
    GET DIAGNOSTICS v_count = ROW_COUNT;

    UPDATE carts SET updated_at = now() WHERE id = v_cart_id;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION clear_cart(p_user_id BIGINT)
RETURNS VOID AS $$
DECLARE
    v_cart_id BIGINT;
BEGIN
    SELECT id INTO v_cart_id FROM carts WHERE user_id = p_user_id;
    IF v_cart_id IS NOT NULL THEN
        DELETE FROM cart_items WHERE cart_id = v_cart_id;
        UPDATE carts SET updated_at = now() WHERE id = v_cart_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 22. Khuyen mai — logic ap dung voucher tach rieng thanh 2 ham dung
-- chung cho place_order()/preview_checkout(), tranh lap code.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION find_valid_promotion(p_code VARCHAR, p_user_id BIGINT, p_subtotal NUMERIC)
RETURNS promotions AS $$
DECLARE
    v_promotion promotions%ROWTYPE;
BEGIN
    SELECT * INTO v_promotion FROM promotions
    WHERE code = p_code AND is_active = TRUE AND now() BETWEEN starts_at AND ends_at;

    IF v_promotion.id IS NULL THEN
        RAISE EXCEPTION 'Promotion code % invalid or expired', p_code;
    END IF;

    IF p_subtotal < v_promotion.min_order_amount THEN
        RAISE EXCEPTION 'Order does not meet minimum amount for promotion %', p_code;
    END IF;

    IF v_promotion.usage_limit IS NOT NULL AND
       (SELECT COUNT(*) FROM promotion_usages WHERE promotion_id = v_promotion.id) >= v_promotion.usage_limit THEN
        RAISE EXCEPTION 'Promotion % usage limit reached', p_code;
    END IF;

    IF v_promotion.per_user_limit IS NOT NULL AND
       (SELECT COUNT(*) FROM promotion_usages WHERE promotion_id = v_promotion.id AND user_id = p_user_id) >= v_promotion.per_user_limit THEN
        RAISE EXCEPTION 'Promotion % usage limit reached for this user', p_code;
    END IF;

    RETURN v_promotion;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION calculate_discount(p_promotion promotions, p_subtotal NUMERIC)
RETURNS NUMERIC AS $$
DECLARE
    v_discount NUMERIC;
BEGIN
    v_discount := CASE p_promotion.type
        WHEN 'percentage' THEN p_subtotal * p_promotion.value / 100
        ELSE p_promotion.value
    END;

    IF p_promotion.max_discount_amount IS NOT NULL THEN
        v_discount := LEAST(v_discount, p_promotion.max_discount_amount);
    END IF;

    RETURN LEAST(v_discount, p_subtotal);
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION promotion_code_exists(p_code VARCHAR)
RETURNS BOOLEAN AS $$
    SELECT EXISTS (SELECT 1 FROM promotions WHERE code = p_code);
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION create_promotion(
    p_code                VARCHAR,
    p_type                promotion_type,
    p_value               NUMERIC,
    p_min_order_amount    NUMERIC,
    p_max_discount_amount NUMERIC,
    p_starts_at           TIMESTAMPTZ,
    p_ends_at             TIMESTAMPTZ,
    p_usage_limit         INT,
    p_per_user_limit      INT,
    p_is_active           BOOLEAN
) RETURNS TABLE (
    id BIGINT, code VARCHAR, type promotion_type, value NUMERIC, min_order_amount NUMERIC,
    max_discount_amount NUMERIC, starts_at TIMESTAMPTZ, ends_at TIMESTAMPTZ,
    usage_limit INT, per_user_limit INT, is_active BOOLEAN
) AS $$
    INSERT INTO promotions (code, type, value, min_order_amount, max_discount_amount, starts_at, ends_at, usage_limit, per_user_limit, is_active)
    VALUES (p_code, p_type, p_value, p_min_order_amount, p_max_discount_amount, p_starts_at, p_ends_at, p_usage_limit, p_per_user_limit, p_is_active)
    RETURNING promotions.id, promotions.code, promotions.type, promotions.value, promotions.min_order_amount,
              promotions.max_discount_amount, promotions.starts_at, promotions.ends_at,
              promotions.usage_limit, promotions.per_user_limit, promotions.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION get_promotion_by_id(p_id BIGINT)
RETURNS TABLE (
    id BIGINT, code VARCHAR, type promotion_type, value NUMERIC, min_order_amount NUMERIC,
    max_discount_amount NUMERIC, starts_at TIMESTAMPTZ, ends_at TIMESTAMPTZ,
    usage_limit INT, per_user_limit INT, is_active BOOLEAN
) AS $$
    SELECT p.id, p.code, p.type, p.value, p.min_order_amount, p.max_discount_amount,
           p.starts_at, p.ends_at, p.usage_limit, p.per_user_limit, p.is_active
    FROM promotions p WHERE p.id = p_id;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION list_promotions(
    p_type      promotion_type DEFAULT NULL,
    p_is_active BOOLEAN DEFAULT NULL,
    p_limit     INT DEFAULT 20,
    p_offset    INT DEFAULT 0
) RETURNS TABLE (
    id BIGINT, code VARCHAR, type promotion_type, value NUMERIC, min_order_amount NUMERIC,
    max_discount_amount NUMERIC, starts_at TIMESTAMPTZ, ends_at TIMESTAMPTZ,
    usage_limit INT, per_user_limit INT, is_active BOOLEAN, total_count BIGINT
) AS $$
    SELECT p.id, p.code, p.type, p.value, p.min_order_amount, p.max_discount_amount,
           p.starts_at, p.ends_at, p.usage_limit, p.per_user_limit, p.is_active,
           COUNT(*) OVER() AS total_count
    FROM promotions p
    WHERE (p_type IS NULL OR p.type = p_type)
      AND (p_is_active IS NULL OR p.is_active = p_is_active)
    ORDER BY p.starts_at DESC
    LIMIT p_limit OFFSET p_offset;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION update_promotion(
    p_id                  BIGINT,
    p_value               NUMERIC,
    p_min_order_amount    NUMERIC,
    p_max_discount_amount NUMERIC,
    p_starts_at           TIMESTAMPTZ,
    p_ends_at             TIMESTAMPTZ,
    p_usage_limit         INT,
    p_per_user_limit      INT,
    p_is_active           BOOLEAN
) RETURNS TABLE (
    id BIGINT, code VARCHAR, type promotion_type, value NUMERIC, min_order_amount NUMERIC,
    max_discount_amount NUMERIC, starts_at TIMESTAMPTZ, ends_at TIMESTAMPTZ,
    usage_limit INT, per_user_limit INT, is_active BOOLEAN
) AS $$
    UPDATE promotions
    SET value = p_value, min_order_amount = p_min_order_amount, max_discount_amount = p_max_discount_amount,
        starts_at = p_starts_at, ends_at = p_ends_at, usage_limit = p_usage_limit,
        per_user_limit = p_per_user_limit, is_active = p_is_active
    WHERE promotions.id = p_id
    RETURNING promotions.id, promotions.code, promotions.type, promotions.value, promotions.min_order_amount,
              promotions.max_discount_amount, promotions.starts_at, promotions.ends_at,
              promotions.usage_limit, promotions.per_user_limit, promotions.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION set_promotion_active(p_id BIGINT, p_is_active BOOLEAN)
RETURNS TABLE (
    id BIGINT, code VARCHAR, type promotion_type, value NUMERIC, min_order_amount NUMERIC,
    max_discount_amount NUMERIC, starts_at TIMESTAMPTZ, ends_at TIMESTAMPTZ,
    usage_limit INT, per_user_limit INT, is_active BOOLEAN
) AS $$
    UPDATE promotions SET is_active = p_is_active WHERE promotions.id = p_id
    RETURNING promotions.id, promotions.code, promotions.type, promotions.value, promotions.min_order_amount,
              promotions.max_discount_amount, promotions.starts_at, promotions.ends_at,
              promotions.usage_limit, promotions.per_user_limit, promotions.is_active;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION add_flash_sale_item(
    p_promotion_id   BIGINT,
    p_variant_id     BIGINT,
    p_flash_price    NUMERIC,
    p_quantity_limit INT
) RETURNS TABLE (
    id BIGINT, promotion_id BIGINT, product_variant_id BIGINT, flash_price NUMERIC,
    quantity_limit INT, quantity_sold INT
) AS $$
    INSERT INTO flash_sale_items (promotion_id, product_variant_id, flash_price, quantity_limit)
    VALUES (p_promotion_id, p_variant_id, p_flash_price, p_quantity_limit)
    ON CONFLICT (promotion_id, product_variant_id)
    DO UPDATE SET flash_price = EXCLUDED.flash_price, quantity_limit = EXCLUDED.quantity_limit
    RETURNING flash_sale_items.id, flash_sale_items.promotion_id, flash_sale_items.product_variant_id,
              flash_sale_items.flash_price, flash_sale_items.quantity_limit, flash_sale_items.quantity_sold;
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION list_flash_sale_items(p_promotion_id BIGINT)
RETURNS TABLE (
    id BIGINT, promotion_id BIGINT, product_variant_id BIGINT, variant_name VARCHAR,
    product_name VARCHAR, flash_price NUMERIC, quantity_limit INT, quantity_sold INT
) AS $$
    SELECT fsi.id, fsi.promotion_id, fsi.product_variant_id, pv.variant_name, p.name,
           fsi.flash_price, fsi.quantity_limit, fsi.quantity_sold
    FROM flash_sale_items fsi
    JOIN product_variants pv ON pv.id = fsi.product_variant_id
    JOIN products p ON p.id = pv.product_id
    WHERE fsi.promotion_id = p_promotion_id
    ORDER BY fsi.id;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION get_active_flash_sales(p_limit INT DEFAULT 20)
RETURNS TABLE (
    promotion_id BIGINT, product_variant_id BIGINT, product_id BIGINT, product_name VARCHAR,
    variant_name VARCHAR, base_price NUMERIC, flash_price NUMERIC,
    quantity_limit INT, quantity_sold INT, ends_at TIMESTAMPTZ
) AS $$
    SELECT promo.id, fsi.product_variant_id, p.id, p.name, pv.variant_name,
           p.base_price + pv.price_adjustment, fsi.flash_price, fsi.quantity_limit, fsi.quantity_sold, promo.ends_at
    FROM flash_sale_items fsi
    JOIN promotions promo ON promo.id = fsi.promotion_id
    JOIN product_variants pv ON pv.id = fsi.product_variant_id
    JOIN products p ON p.id = pv.product_id
    WHERE promo.is_active = TRUE AND promo.type = 'flash_sale'
      AND now() BETWEEN promo.starts_at AND promo.ends_at
      AND fsi.quantity_sold < fsi.quantity_limit
      AND p.deleted_at IS NULL
    ORDER BY promo.ends_at ASC
    LIMIT p_limit;
$$ LANGUAGE sql STABLE;

-- ------------------------------------------------------------
-- 23. Checkout — place_order() viet lai de dung chung
-- find_valid_promotion()/calculate_discount() thay vi lap logic; them
-- kiem tra dia chi thuoc ve user va cong don quantity_sold cho flash sale
-- (2 cho nay bi thieu o ban dau).
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION place_order(
    p_user_id          BIGINT,
    p_address_id       BIGINT,
    p_payment_method   payment_method,
    p_promotion_code   VARCHAR DEFAULT NULL
) RETURNS BIGINT AS $$
DECLARE
    v_cart_id      BIGINT;
    v_subtotal     NUMERIC := 0;
    v_discount     NUMERIC := 0;
    v_shipping_fee NUMERIC := 30000;
    v_total        NUMERIC;
    v_order_id     BIGINT;
    v_promotion    promotions%ROWTYPE;
    v_item         RECORD;
    v_available    INT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM addresses WHERE id = p_address_id AND user_id = p_user_id) THEN
        RAISE EXCEPTION 'Address % does not belong to user %', p_address_id, p_user_id;
    END IF;

    SELECT id INTO v_cart_id FROM carts WHERE user_id = p_user_id;
    IF v_cart_id IS NULL THEN
        RAISE EXCEPTION 'Cart not found for user %', p_user_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM cart_items WHERE cart_id = v_cart_id) THEN
        RAISE EXCEPTION 'Cart is empty';
    END IF;

    -- Khoa va kiem tra ton kho truoc khi tru tien
    FOR v_item IN
        SELECT ci.product_variant_id, ci.quantity
        FROM cart_items ci
        WHERE ci.cart_id = v_cart_id
    LOOP
        SELECT (quantity_on_hand - quantity_reserved) INTO v_available
        FROM inventories
        WHERE product_variant_id = v_item.product_variant_id
        FOR UPDATE;

        IF v_available IS NULL OR v_available < v_item.quantity THEN
            RAISE EXCEPTION 'Insufficient stock for variant %', v_item.product_variant_id;
        END IF;
    END LOOP;

    SELECT get_cart_total(v_cart_id) INTO v_subtotal;

    IF p_promotion_code IS NOT NULL THEN
        v_promotion := find_valid_promotion(p_promotion_code, p_user_id, v_subtotal);
        v_discount := calculate_discount(v_promotion, v_subtotal);
    END IF;

    v_total := v_subtotal - v_discount + v_shipping_fee;

    -- order_code sinh theo id (IDENTITY, luon duy nhat) thay vi timestamp giay
    -- (bi trung khi 1 user dat >=2 don trong cung 1 giay, gap UniqueViolation
    -- tren orders_order_code_key — phat hien khi test checkout lien tuc nhanh).
    -- order_code cot VARCHAR(30) nen dung placeholder ngan (khong the nhet
    -- nguyen UUID 36 ky tu), du duy nhat tam thoi la du vi UPDATE ngay ben duoi.
    INSERT INTO orders (order_code, user_id, address_id, status, subtotal, discount_amount, shipping_fee, total_amount)
    VALUES (
        'TMP-' || left(gen_random_uuid()::text, 20),
        p_user_id, p_address_id, 'pending', v_subtotal, v_discount, v_shipping_fee, v_total
    )
    RETURNING id INTO v_order_id;

    UPDATE orders SET order_code = 'ORD-' || to_char(now(), 'YYYYMMDD') || '-' || v_order_id
    WHERE id = v_order_id;

    INSERT INTO order_items (order_id, product_variant_id, product_name_snapshot, sku_snapshot, quantity, unit_price, discount_amount, line_total)
    SELECT
        v_order_id,
        ci.product_variant_id,
        p.name || ' (' || pv.variant_name || ')',
        pv.sku,
        ci.quantity,
        ci.unit_price_snapshot,
        0,
        ci.quantity * ci.unit_price_snapshot
    FROM cart_items ci
    JOIN product_variants pv ON pv.id = ci.product_variant_id
    JOIN products p ON p.id = pv.product_id
    WHERE ci.cart_id = v_cart_id;

    UPDATE inventories inv
    SET quantity_on_hand = inv.quantity_on_hand - ci.quantity,
        updated_at = now()
    FROM cart_items ci
    WHERE ci.cart_id = v_cart_id AND inv.product_variant_id = ci.product_variant_id;

    -- Cong don so luong da ban cho cac flash sale item lien quan (bi thieu o
    -- ban goc). Luu y: khong the JOIN dong bang chinh bang dich (fsi) o menh
    -- de FROM/JOIN cua UPDATE — Postgres khong cho tham chieu bang dich trong
    -- ON clause, phai dua dieu kien tuong quan xuong WHERE.
    UPDATE flash_sale_items fsi
    SET quantity_sold = fsi.quantity_sold + ci.quantity
    FROM cart_items ci, promotions promo
    WHERE ci.cart_id = v_cart_id
      AND fsi.product_variant_id = ci.product_variant_id
      AND fsi.promotion_id = promo.id
      AND promo.is_active = TRUE AND promo.type = 'flash_sale'
      AND now() BETWEEN promo.starts_at AND promo.ends_at;

    INSERT INTO order_status_history (order_id, from_status, to_status, changed_by, note)
    VALUES (v_order_id, NULL, 'pending', p_user_id, 'Don hang duoc tao');

    INSERT INTO payments (order_id, method, status, amount)
    VALUES (v_order_id, p_payment_method, 'pending', v_total);

    IF p_promotion_code IS NOT NULL THEN
        INSERT INTO promotion_usages (promotion_id, user_id, order_id)
        VALUES (v_promotion.id, p_user_id, v_order_id);
    END IF;

    DELETE FROM cart_items WHERE cart_id = v_cart_id;

    RETURN v_order_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION preview_checkout(p_user_id BIGINT, p_promotion_code VARCHAR DEFAULT NULL)
RETURNS TABLE (
    subtotal        NUMERIC,
    discount_amount NUMERIC,
    shipping_fee    NUMERIC,
    total_amount    NUMERIC
) AS $$
DECLARE
    v_cart_id      BIGINT;
    v_subtotal     NUMERIC := 0;
    v_discount     NUMERIC := 0;
    v_shipping_fee NUMERIC := 30000;
    v_promotion    promotions%ROWTYPE;
BEGIN
    SELECT id INTO v_cart_id FROM carts WHERE user_id = p_user_id;
    IF v_cart_id IS NULL OR NOT EXISTS (SELECT 1 FROM cart_items WHERE cart_id = v_cart_id) THEN
        RAISE EXCEPTION 'Cart is empty';
    END IF;

    SELECT get_cart_total(v_cart_id) INTO v_subtotal;

    IF p_promotion_code IS NOT NULL THEN
        v_promotion := find_valid_promotion(p_promotion_code, p_user_id, v_subtotal);
        v_discount := calculate_discount(v_promotion, v_subtotal);
    END IF;

    RETURN QUERY SELECT v_subtotal, v_discount, v_shipping_fee, v_subtotal - v_discount + v_shipping_fee;
END;
$$ LANGUAGE plpgsql STABLE;

-- ------------------------------------------------------------
-- 24. Don hang — liet ke theo khach hang / theo quan tri, gia lap
-- payment gateway callback, xem chu so huu.
-- get_order_detail() doi return type (them user_id/address) nen phai DROP
-- truoc khi CREATE OR REPLACE (Postgres khong cho doi return type function
-- co san).
-- ------------------------------------------------------------
DROP FUNCTION IF EXISTS get_order_detail(BIGINT);
CREATE OR REPLACE FUNCTION get_order_detail(p_order_id BIGINT)
RETURNS TABLE (
    id              BIGINT,
    order_code      VARCHAR,
    user_id         BIGINT,
    status          order_status,
    subtotal        NUMERIC,
    discount_amount NUMERIC,
    shipping_fee    NUMERIC,
    total_amount    NUMERIC,
    created_at      TIMESTAMPTZ,
    address         JSON,
    items           JSON,
    payment         JSON,
    status_history  JSON
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        o.id, o.order_code, o.user_id, o.status, o.subtotal, o.discount_amount, o.shipping_fee, o.total_amount, o.created_at,
        (SELECT json_build_object(
            'recipient_name', a.recipient_name, 'phone', a.phone, 'line1', a.line1,
            'ward', a.ward, 'district', a.district, 'province', a.province
         ) FROM addresses a WHERE a.id = o.address_id),
        (SELECT json_agg(json_build_object(
            'id', oi.id,
            'product_variant_id', oi.product_variant_id,
            'product_name', oi.product_name_snapshot,
            'sku', oi.sku_snapshot,
            'quantity', oi.quantity,
            'unit_price', oi.unit_price,
            'line_total', oi.line_total
         ) ORDER BY oi.id) FROM order_items oi WHERE oi.order_id = o.id),
        (SELECT json_build_object('method', pm.method, 'status', pm.status, 'amount', pm.amount, 'paid_at', pm.paid_at)
         FROM payments pm WHERE pm.order_id = o.id),
        (SELECT json_agg(json_build_object(
            'from_status', h.from_status, 'to_status', h.to_status, 'note', h.note, 'created_at', h.created_at
         ) ORDER BY h.created_at)
         FROM order_status_history h WHERE h.order_id = o.id)
    FROM orders o
    WHERE o.id = p_order_id AND o.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION list_orders_for_user(
    p_user_id BIGINT,
    p_status  order_status DEFAULT NULL,
    p_limit   INT DEFAULT 20,
    p_offset  INT DEFAULT 0
) RETURNS TABLE (
    id BIGINT, order_code VARCHAR, status order_status, subtotal NUMERIC, discount_amount NUMERIC,
    shipping_fee NUMERIC, total_amount NUMERIC, created_at TIMESTAMPTZ, total_count BIGINT
) AS $$
    SELECT o.id, o.order_code, o.status, o.subtotal, o.discount_amount, o.shipping_fee, o.total_amount,
           o.created_at, COUNT(*) OVER() AS total_count
    FROM orders o
    WHERE o.user_id = p_user_id AND o.deleted_at IS NULL
      AND (p_status IS NULL OR o.status = p_status)
    ORDER BY o.created_at DESC
    LIMIT p_limit OFFSET p_offset;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION list_orders_admin(
    p_status  order_status DEFAULT NULL,
    p_user_id BIGINT DEFAULT NULL,
    p_from    TIMESTAMPTZ DEFAULT NULL,
    p_to      TIMESTAMPTZ DEFAULT NULL,
    p_limit   INT DEFAULT 20,
    p_offset  INT DEFAULT 0
) RETURNS TABLE (
    id BIGINT, order_code VARCHAR, status order_status, user_id BIGINT, customer_name VARCHAR,
    total_amount NUMERIC, created_at TIMESTAMPTZ, total_count BIGINT
) AS $$
    SELECT o.id, o.order_code, o.status, o.user_id, u.full_name, o.total_amount, o.created_at,
           COUNT(*) OVER() AS total_count
    FROM orders o
    JOIN users u ON u.id = o.user_id
    WHERE o.deleted_at IS NULL
      AND (p_status IS NULL OR o.status = p_status)
      AND (p_user_id IS NULL OR o.user_id = p_user_id)
      AND (p_from IS NULL OR o.created_at >= p_from)
      AND (p_to IS NULL OR o.created_at <= p_to)
    ORDER BY o.created_at DESC
    LIMIT p_limit OFFSET p_offset;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION simulate_payment_gateway(
    p_order_id   BIGINT,
    p_success    BOOLEAN,
    p_changed_by BIGINT DEFAULT NULL
) RETURNS TABLE (
    order_id BIGINT, order_status order_status, payment_status payment_status, transaction_ref VARCHAR
) AS $$
DECLARE
    v_current_status order_status;
    v_txn_ref        VARCHAR;
BEGIN
    SELECT status INTO v_current_status FROM orders WHERE id = p_order_id AND deleted_at IS NULL;
    IF v_current_status IS NULL THEN
        RAISE EXCEPTION 'Order % not found', p_order_id;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM payments WHERE payments.order_id = p_order_id AND status = 'pending') THEN
        RAISE EXCEPTION 'Order % has no pending payment to process', p_order_id;
    END IF;

    v_txn_ref := 'SIM-' || to_char(now(), 'YYYYMMDDHH24MISS') || '-' || p_order_id;

    IF p_success THEN
        UPDATE payments SET status = 'success', paid_at = now(), transaction_ref = v_txn_ref
        WHERE payments.order_id = p_order_id;

        IF v_current_status = 'pending' THEN
            PERFORM update_order_status(p_order_id, 'confirmed', p_changed_by, 'Thanh toan thanh cong (gia lap gateway)');
        END IF;
    ELSE
        UPDATE payments SET status = 'failed', transaction_ref = v_txn_ref
        WHERE payments.order_id = p_order_id;
    END IF;

    RETURN QUERY
    SELECT o.id, o.status, pm.status, pm.transaction_ref
    FROM orders o JOIN payments pm ON pm.order_id = o.id
    WHERE o.id = p_order_id;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 25. Tra hang / hoan tien
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_refund_request(
    p_order_id      BIGINT,
    p_user_id       BIGINT,
    p_reason        VARCHAR,
    p_refund_amount NUMERIC DEFAULT NULL
) RETURNS TABLE (
    id BIGINT, order_id BIGINT, reason VARCHAR, status refund_status, refund_amount NUMERIC, requested_at TIMESTAMPTZ
) AS $$
DECLARE
    v_order  orders%ROWTYPE;
    v_amount NUMERIC;
BEGIN
    -- Phai qualify orders.id: cot "id" trong RETURNS TABLE tro thanh 1 bien
    -- OUT-parameter cung ten, "id" khong qualify se bi coi la tham chieu mo ho.
    SELECT * INTO v_order FROM orders WHERE orders.id = p_order_id AND orders.user_id = p_user_id AND orders.deleted_at IS NULL;
    IF v_order.id IS NULL THEN
        RAISE EXCEPTION 'Order % not found for user %', p_order_id, p_user_id;
    END IF;

    IF v_order.status <> 'delivered' THEN
        RAISE EXCEPTION 'Only delivered orders can be returned/refunded (current status: %)', v_order.status;
    END IF;

    IF EXISTS (
        SELECT 1 FROM refund_requests r
        WHERE r.order_id = p_order_id AND r.status IN ('requested', 'approved', 'refunded')
    ) THEN
        RAISE EXCEPTION 'Order % already has an active refund request', p_order_id;
    END IF;

    v_amount := COALESCE(p_refund_amount, v_order.total_amount);

    RETURN QUERY
    INSERT INTO refund_requests (order_id, reason, refund_amount)
    VALUES (p_order_id, p_reason, v_amount)
    RETURNING refund_requests.id, refund_requests.order_id, refund_requests.reason, refund_requests.status,
              refund_requests.refund_amount, refund_requests.requested_at;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION get_refund_request_by_id(p_id BIGINT)
RETURNS TABLE (
    id BIGINT, order_id BIGINT, order_code VARCHAR, user_id BIGINT, reason VARCHAR, status refund_status,
    refund_amount NUMERIC, requested_at TIMESTAMPTZ, processed_by BIGINT, processed_at TIMESTAMPTZ
) AS $$
    SELECT r.id, r.order_id, o.order_code, o.user_id, r.reason, r.status, r.refund_amount,
           r.requested_at, r.processed_by, r.processed_at
    FROM refund_requests r JOIN orders o ON o.id = r.order_id
    WHERE r.id = p_id;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION list_refund_requests(
    p_status  refund_status DEFAULT NULL,
    p_user_id BIGINT DEFAULT NULL,
    p_limit   INT DEFAULT 20,
    p_offset  INT DEFAULT 0
) RETURNS TABLE (
    id BIGINT, order_id BIGINT, order_code VARCHAR, user_id BIGINT, reason VARCHAR, status refund_status,
    refund_amount NUMERIC, requested_at TIMESTAMPTZ, total_count BIGINT
) AS $$
    SELECT r.id, r.order_id, o.order_code, o.user_id, r.reason, r.status, r.refund_amount, r.requested_at,
           COUNT(*) OVER() AS total_count
    FROM refund_requests r JOIN orders o ON o.id = r.order_id
    WHERE (p_status IS NULL OR r.status = p_status)
      AND (p_user_id IS NULL OR o.user_id = p_user_id)
    ORDER BY r.requested_at DESC
    LIMIT p_limit OFFSET p_offset;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION process_refund_request(
    p_id           BIGINT,
    p_approve      BOOLEAN,
    p_processed_by BIGINT
) RETURNS TABLE (
    id BIGINT, order_id BIGINT, status refund_status, refund_amount NUMERIC, processed_at TIMESTAMPTZ
) AS $$
DECLARE
    v_current    refund_status;
    v_order_id   BIGINT;
    v_new_status refund_status;
BEGIN
    -- Phai qualify refund_requests.status: cot "status" trong RETURNS TABLE
    -- tro thanh 1 bien OUT-parameter cung ten, khong qualify se bi mo ho.
    SELECT refund_requests.status, refund_requests.order_id INTO v_current, v_order_id
    FROM refund_requests WHERE refund_requests.id = p_id FOR UPDATE;

    IF v_current IS NULL THEN
        RAISE EXCEPTION 'Refund request % not found', p_id;
    END IF;
    IF v_current <> 'requested' THEN
        RAISE EXCEPTION 'Refund request % already processed (status: %)', p_id, v_current;
    END IF;

    v_new_status := CASE WHEN p_approve THEN 'refunded' ELSE 'rejected' END;

    UPDATE refund_requests
    SET status = v_new_status, processed_by = p_processed_by, processed_at = now()
    WHERE refund_requests.id = p_id;

    IF p_approve THEN
        UPDATE payments SET status = 'refunded' WHERE payments.order_id = v_order_id;
    END IF;

    RETURN QUERY
    SELECT r.id, r.order_id, r.status, r.refund_amount, r.processed_at
    FROM refund_requests r WHERE r.id = p_id;
END;
$$ LANGUAGE plpgsql;

-- ------------------------------------------------------------
-- 26. Danh gia san pham — bo sung ben canh submit_review() (muc 11)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION list_reviews_for_product(
    p_product_id BIGINT,
    p_limit      INT DEFAULT 20,
    p_offset     INT DEFAULT 0
) RETURNS TABLE (
    id BIGINT, user_id BIGINT, full_name VARCHAR, rating SMALLINT, comment TEXT,
    created_at TIMESTAMPTZ, total_count BIGINT
) AS $$
    SELECT r.id, r.user_id, u.full_name, r.rating, r.comment, r.created_at, COUNT(*) OVER() AS total_count
    FROM reviews r
    JOIN users u ON u.id = r.user_id
    WHERE r.product_id = p_product_id AND r.is_approved = TRUE
    ORDER BY r.created_at DESC
    LIMIT p_limit OFFSET p_offset;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION get_product_rating_summary(p_product_id BIGINT)
RETURNS TABLE (average_rating NUMERIC, review_count BIGINT) AS $$
    SELECT COALESCE(ROUND(AVG(rating), 2), 0), COUNT(*)
    FROM reviews WHERE product_id = p_product_id AND is_approved = TRUE;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION list_reviewable_order_items(p_user_id BIGINT)
RETURNS TABLE (
    order_item_id BIGINT, order_id BIGINT, order_code VARCHAR, product_id BIGINT,
    product_name VARCHAR, sku VARCHAR, delivered_at TIMESTAMPTZ
) AS $$
    SELECT oi.id, o.id, o.order_code, pv.product_id, p.name, oi.sku_snapshot, o.updated_at
    FROM order_items oi
    JOIN orders o ON o.id = oi.order_id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p ON p.id = pv.product_id
    WHERE o.user_id = p_user_id AND o.status = 'delivered'
      AND NOT EXISTS (SELECT 1 FROM reviews rv WHERE rv.order_item_id = oi.id)
    ORDER BY o.updated_at DESC;
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Sprint 4 (Tuan 4) — Bao cao thong ke
-- ============================================================

-- ------------------------------------------------------------
-- 27. Tong quan dashboard (dung chung voi get_top_selling_books/
-- get_revenue_report da co san o muc 8-9)
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_dashboard_summary(p_from TIMESTAMPTZ, p_to TIMESTAMPTZ)
RETURNS TABLE (
    total_orders   BIGINT,
    total_revenue  NUMERIC,
    pending_orders BIGINT,
    new_customers  BIGINT
) AS $$
    SELECT
        (SELECT COUNT(*) FROM orders WHERE created_at BETWEEN p_from AND p_to AND status <> 'cancelled'),
        (SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE created_at BETWEEN p_from AND p_to AND status <> 'cancelled'),
        (SELECT COUNT(*) FROM orders WHERE status = 'pending'),
        (SELECT COUNT(*) FROM users WHERE role = 'customer' AND created_at BETWEEN p_from AND p_to);
$$ LANGUAGE sql STABLE;

-- ------------------------------------------------------------
-- 28. Dia chi giao hang (Addresses) — customer tu quan ly de dung khi checkout.
-- Khong co trong bang liet ke Sprint 3 nhung place_order() can address_id nen
-- phai co API tao/xem truoc.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION create_address(
    p_user_id        BIGINT,
    p_recipient_name VARCHAR,
    p_phone          VARCHAR,
    p_line1          VARCHAR,
    p_ward           VARCHAR,
    p_district       VARCHAR,
    p_province       VARCHAR,
    p_is_default     BOOLEAN
) RETURNS TABLE (
    id BIGINT, user_id BIGINT, recipient_name VARCHAR, phone VARCHAR, line1 VARCHAR,
    ward VARCHAR, district VARCHAR, province VARCHAR, is_default BOOLEAN, created_at TIMESTAMPTZ
) AS $$
DECLARE
    v_id BIGINT;
BEGIN
    IF p_is_default THEN
        UPDATE addresses SET is_default = FALSE WHERE addresses.user_id = p_user_id;
    END IF;

    INSERT INTO addresses (user_id, recipient_name, phone, line1, ward, district, province, is_default)
    VALUES (p_user_id, p_recipient_name, p_phone, p_line1, p_ward, p_district, p_province, p_is_default)
    RETURNING addresses.id INTO v_id;

    RETURN QUERY
    SELECT a.id, a.user_id, a.recipient_name, a.phone, a.line1, a.ward, a.district, a.province, a.is_default, a.created_at
    FROM addresses a WHERE a.id = v_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION list_addresses_for_user(p_user_id BIGINT)
RETURNS TABLE (
    id BIGINT, user_id BIGINT, recipient_name VARCHAR, phone VARCHAR, line1 VARCHAR,
    ward VARCHAR, district VARCHAR, province VARCHAR, is_default BOOLEAN, created_at TIMESTAMPTZ
) AS $$
    SELECT a.id, a.user_id, a.recipient_name, a.phone, a.line1, a.ward, a.district, a.province, a.is_default, a.created_at
    FROM addresses a WHERE a.user_id = p_user_id
    ORDER BY a.is_default DESC, a.created_at DESC;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION get_address_by_id(p_id BIGINT)
RETURNS TABLE (
    id BIGINT, user_id BIGINT, recipient_name VARCHAR, phone VARCHAR, line1 VARCHAR,
    ward VARCHAR, district VARCHAR, province VARCHAR, is_default BOOLEAN, created_at TIMESTAMPTZ
) AS $$
    SELECT a.id, a.user_id, a.recipient_name, a.phone, a.line1, a.ward, a.district, a.province, a.is_default, a.created_at
    FROM addresses a WHERE a.id = p_id;
$$ LANGUAGE sql STABLE;

CREATE OR REPLACE FUNCTION set_default_address(p_id BIGINT, p_user_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM addresses WHERE id = p_id AND user_id = p_user_id) THEN
        RETURN FALSE;
    END IF;
    UPDATE addresses SET is_default = FALSE WHERE user_id = p_user_id;
    UPDATE addresses SET is_default = TRUE WHERE id = p_id;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;
