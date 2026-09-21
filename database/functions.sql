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
-- 4. add_to_cart — them/cong don sach vao gio hang cua khach
-- ------------------------------------------------------------
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

    INSERT INTO carts (user_id) VALUES (p_user_id)
    ON CONFLICT (user_id) DO UPDATE SET updated_at = now()
    RETURNING id INTO v_cart_id;

    SELECT p.base_price + pv.price_adjustment INTO v_price
    FROM product_variants pv
    JOIN products p ON p.id = pv.product_id
    WHERE pv.id = p_variant_id AND pv.is_active = TRUE;

    IF v_price IS NULL THEN
        RAISE EXCEPTION 'Product variant % not found or inactive', p_variant_id;
    END IF;

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
-- 5. place_order — checkout: kiem tra ton kho, ap voucher, tao don,
--    tru ton kho, xoa gio hang. Chay trong 1 transaction (psycopg goi ham trong 1 transaction).
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
        SELECT * INTO v_promotion FROM promotions
        WHERE code = p_promotion_code
          AND is_active = TRUE
          AND now() BETWEEN starts_at AND ends_at;

        IF v_promotion.id IS NULL THEN
            RAISE EXCEPTION 'Promotion code % invalid or expired', p_promotion_code;
        END IF;

        IF v_subtotal < v_promotion.min_order_amount THEN
            RAISE EXCEPTION 'Order does not meet minimum amount for promotion %', p_promotion_code;
        END IF;

        IF v_promotion.per_user_limit IS NOT NULL AND
           (SELECT COUNT(*) FROM promotion_usages WHERE promotion_id = v_promotion.id AND user_id = p_user_id) >= v_promotion.per_user_limit THEN
            RAISE EXCEPTION 'Promotion % usage limit reached for this user', p_promotion_code;
        END IF;

        v_discount := CASE v_promotion.type
            WHEN 'percentage' THEN v_subtotal * v_promotion.value / 100
            ELSE v_promotion.value
        END;

        IF v_promotion.max_discount_amount IS NOT NULL THEN
            v_discount := LEAST(v_discount, v_promotion.max_discount_amount);
        END IF;
    END IF;

    v_total := v_subtotal - v_discount + v_shipping_fee;

    INSERT INTO orders (order_code, user_id, address_id, status, subtotal, discount_amount, shipping_fee, total_amount)
    VALUES (
        'ORD-' || to_char(now(), 'YYYYMMDDHH24MISS') || '-' || p_user_id,
        p_user_id, p_address_id, 'pending', v_subtotal, v_discount, v_shipping_fee, v_total
    )
    RETURNING id INTO v_order_id;

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
-- 7. get_order_detail — chi tiet don hang de hien thi/tra API
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_order_detail(p_order_id BIGINT)
RETURNS TABLE (
    id              BIGINT,
    order_code      VARCHAR,
    status          order_status,
    subtotal        NUMERIC,
    discount_amount NUMERIC,
    shipping_fee    NUMERIC,
    total_amount    NUMERIC,
    created_at      TIMESTAMPTZ,
    items           JSON,
    payment         JSON,
    status_history  JSON
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        o.id, o.order_code, o.status, o.subtotal, o.discount_amount, o.shipping_fee, o.total_amount, o.created_at,
        (SELECT json_agg(json_build_object(
            'product_name', oi.product_name_snapshot,
            'sku', oi.sku_snapshot,
            'quantity', oi.quantity,
            'unit_price', oi.unit_price,
            'line_total', oi.line_total
         )) FROM order_items oi WHERE oi.order_id = o.id),
        (SELECT json_build_object('method', pm.method, 'status', pm.status, 'amount', pm.amount, 'paid_at', pm.paid_at)
         FROM payments pm WHERE pm.order_id = o.id),
        (SELECT json_agg(json_build_object(
            'from_status', h.from_status, 'to_status', h.to_status, 'note', h.note, 'created_at', h.created_at
         ) ORDER BY h.created_at)
         FROM order_status_history h WHERE h.order_id = o.id)
    FROM orders o
    WHERE o.id = p_order_id;
END;
$$ LANGUAGE plpgsql STABLE;

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
