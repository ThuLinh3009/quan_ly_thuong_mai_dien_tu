-- ============================================================
-- TBookStore — PostgreSQL functions
-- Chay sau schema.sql. Goi tu FastAPI (psycopg) qua "SELECT * FROM fn(...)"
-- hoac "SELECT fn(...)" tuy ham tra ve TABLE hay scalar.
-- ============================================================

-- ------------------------------------------------------------
-- 1. get_book_by_id — chi tiet 1 cuon sach + cac bien the + ton kho
-- Vi du: SELECT * FROM get_book_by_id(10);
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_book_by_id(p_product_id BIGINT)
RETURNS TABLE (
    id              BIGINT,
    sku             VARCHAR,
    name            VARCHAR,
    author          VARCHAR,
    publisher       VARCHAR,
    isbn            VARCHAR,
    description     TEXT,
    cover_image_url VARCHAR,
    base_price      NUMERIC,
    category_id     BIGINT,
    category_name   VARCHAR,
    variants        JSON
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id, p.sku, p.name, p.author, p.publisher, p.isbn, p.description,
        p.cover_image_url, p.base_price, c.id, c.name,
        COALESCE(
            (SELECT json_agg(json_build_object(
                'variant_id', pv.id,
                'variant_name', pv.variant_name,
                'sku', pv.sku,
                'price', p.base_price + pv.price_adjustment,
                'quantity_available', COALESCE(inv.quantity_on_hand - inv.quantity_reserved, 0)
             ))
             FROM product_variants pv
             LEFT JOIN inventories inv ON inv.product_variant_id = pv.id
             WHERE pv.product_id = p.id AND pv.is_active = TRUE
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
CREATE OR REPLACE FUNCTION search_books(
    p_keyword     TEXT DEFAULT NULL,
    p_category_id BIGINT DEFAULT NULL,
    p_min_price   NUMERIC DEFAULT NULL,
    p_max_price   NUMERIC DEFAULT NULL,
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
    category_name   VARCHAR,
    total_count     BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id, p.sku, p.name, p.author, p.base_price, p.cover_image_url, c.name,
        COUNT(*) OVER() AS total_count
    FROM products p
    JOIN categories c ON c.id = p.category_id
    WHERE p.deleted_at IS NULL
      AND p.is_active = TRUE
      AND (p_category_id IS NULL OR p.category_id = p_category_id)
      AND (p_min_price IS NULL OR p.base_price >= p_min_price)
      AND (p_max_price IS NULL OR p.base_price <= p_max_price)
      AND (p_keyword IS NULL OR p.search_vector @@ plainto_tsquery('simple', p_keyword))
    ORDER BY
        CASE WHEN p_keyword IS NOT NULL
             THEN ts_rank(p.search_vector, plainto_tsquery('simple', p_keyword)) END DESC NULLS LAST,
        p.created_at DESC
    LIMIT p_limit OFFSET p_offset;
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
