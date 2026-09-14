-- ============================================================
-- TBookStore — PostgreSQL schema
-- 23 bang, chia 7 nhom nghiep vu. Quy uoc: id BIGINT IDENTITY,
-- timestamp dung TIMESTAMPTZ, soft-delete qua cot deleted_at.
-- ============================================================

-- ------------------------------------------------------------
-- 0. ENUM types
-- ------------------------------------------------------------
CREATE TYPE user_role        AS ENUM ('admin', 'staff', 'customer');
CREATE TYPE order_status     AS ENUM ('pending', 'confirmed', 'shipping', 'delivered', 'cancelled');
CREATE TYPE payment_method   AS ENUM ('cod', 'simulated_gateway');
CREATE TYPE payment_status   AS ENUM ('pending', 'success', 'failed', 'refunded');
CREATE TYPE promotion_type   AS ENUM ('percentage', 'fixed_amount', 'flash_sale');
CREATE TYPE shipment_status  AS ENUM ('preparing', 'in_transit', 'delivered', 'returned');
CREATE TYPE refund_status    AS ENUM ('requested', 'approved', 'rejected', 'refunded');

-- ------------------------------------------------------------
-- 1. Nguoi dung & phan quyen
-- ------------------------------------------------------------
CREATE TABLE users (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(150) NOT NULL,
    phone         VARCHAR(20),
    role          user_role NOT NULL DEFAULT 'customer',
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ
);

CREATE TABLE addresses (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id        BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_name VARCHAR(150) NOT NULL,
    phone          VARCHAR(20) NOT NULL,
    line1          VARCHAR(255) NOT NULL,
    ward           VARCHAR(100),
    district       VARCHAR(100),
    province       VARCHAR(100) NOT NULL,
    is_default     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE refresh_tokens (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 2. Danh muc / san pham / ton kho
-- ------------------------------------------------------------
CREATE TABLE categories (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    parent_id  BIGINT REFERENCES categories(id) ON DELETE SET NULL,
    name       VARCHAR(150) NOT NULL,
    slug       VARCHAR(160) NOT NULL UNIQUE,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at TIMESTAMPTZ
);

CREATE TABLE suppliers (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name          VARCHAR(200) NOT NULL,
    contact_phone VARCHAR(20),
    email         VARCHAR(255),
    address       VARCHAR(255),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE products (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id     BIGINT NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    sku             VARCHAR(50) NOT NULL UNIQUE,
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(270) NOT NULL UNIQUE,
    author          VARCHAR(150),
    publisher       VARCHAR(150),
    isbn            VARCHAR(20),
    description     TEXT,
    cover_image_url VARCHAR(500),
    base_price      NUMERIC(12, 2) NOT NULL CHECK (base_price >= 0),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    -- Vietnamese khong co text-search config san co trong Postgres nen dung 'simple'
    search_vector   tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('simple', coalesce(name, '')), 'A') ||
        setweight(to_tsvector('simple', coalesce(author, '')), 'B') ||
        setweight(to_tsvector('simple', coalesce(description, '')), 'C')
    ) STORED
);

CREATE TABLE product_variants (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    variant_name    VARCHAR(100) NOT NULL,
    sku             VARCHAR(60) NOT NULL UNIQUE,
    price_adjustment NUMERIC(12, 2) NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE inventories (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_variant_id BIGINT NOT NULL UNIQUE REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity_on_hand   INT NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    quantity_reserved  INT NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
    reorder_level      INT NOT NULL DEFAULT 0,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE import_lots (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    supplier_id BIGINT NOT NULL REFERENCES suppliers(id) ON DELETE RESTRICT,
    lot_code    VARCHAR(50) NOT NULL UNIQUE,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT
);

CREATE TABLE import_receipt_items (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_lot_id      BIGINT NOT NULL REFERENCES import_lots(id) ON DELETE CASCADE,
    product_variant_id BIGINT NOT NULL REFERENCES product_variants(id) ON DELETE RESTRICT,
    quantity           INT NOT NULL CHECK (quantity > 0),
    unit_cost          NUMERIC(12, 2) NOT NULL CHECK (unit_cost >= 0)
);

-- ------------------------------------------------------------
-- 3. Gio hang & don hang
-- ------------------------------------------------------------
CREATE TABLE carts (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cart_items (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cart_id            BIGINT NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    product_variant_id BIGINT NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity           INT NOT NULL CHECK (quantity > 0),
    unit_price_snapshot NUMERIC(12, 2) NOT NULL,
    UNIQUE (cart_id, product_variant_id)
);

CREATE TABLE orders (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_code      VARCHAR(30) NOT NULL UNIQUE,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    address_id      BIGINT NOT NULL REFERENCES addresses(id) ON DELETE RESTRICT,
    status          order_status NOT NULL DEFAULT 'pending',
    subtotal        NUMERIC(12, 2) NOT NULL CHECK (subtotal >= 0),
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    shipping_fee    NUMERIC(12, 2) NOT NULL DEFAULT 0 CHECK (shipping_fee >= 0),
    total_amount    NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    handled_by      BIGINT REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ
);

CREATE TABLE order_items (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id              BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_variant_id    BIGINT NOT NULL REFERENCES product_variants(id) ON DELETE RESTRICT,
    product_name_snapshot VARCHAR(255) NOT NULL,
    sku_snapshot          VARCHAR(60) NOT NULL,
    quantity              INT NOT NULL CHECK (quantity > 0),
    unit_price            NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    discount_amount       NUMERIC(12, 2) NOT NULL DEFAULT 0,
    line_total            NUMERIC(12, 2) NOT NULL CHECK (line_total >= 0)
);

CREATE TABLE order_status_history (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id    BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    from_status order_status,
    to_status   order_status NOT NULL,
    changed_by  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    note        VARCHAR(500),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE payments (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        BIGINT NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    method          payment_method NOT NULL,
    status          payment_status NOT NULL DEFAULT 'pending',
    amount          NUMERIC(12, 2) NOT NULL CHECK (amount >= 0),
    transaction_ref VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_at         TIMESTAMPTZ
);

-- ------------------------------------------------------------
-- 4. Khuyen mai
-- ------------------------------------------------------------
CREATE TABLE promotions (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code               VARCHAR(50) UNIQUE,
    type               promotion_type NOT NULL,
    value              NUMERIC(12, 2) NOT NULL CHECK (value > 0),
    min_order_amount   NUMERIC(12, 2) NOT NULL DEFAULT 0,
    max_discount_amount NUMERIC(12, 2),
    starts_at          TIMESTAMPTZ NOT NULL,
    ends_at            TIMESTAMPTZ NOT NULL,
    usage_limit        INT,
    per_user_limit     INT,
    is_active          BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (ends_at > starts_at)
);

CREATE TABLE flash_sale_items (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    promotion_id       BIGINT NOT NULL REFERENCES promotions(id) ON DELETE CASCADE,
    product_variant_id BIGINT NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    flash_price        NUMERIC(12, 2) NOT NULL CHECK (flash_price >= 0),
    quantity_limit     INT NOT NULL CHECK (quantity_limit > 0),
    quantity_sold      INT NOT NULL DEFAULT 0 CHECK (quantity_sold >= 0),
    UNIQUE (promotion_id, product_variant_id)
);

CREATE TABLE promotion_usages (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    promotion_id BIGINT NOT NULL REFERENCES promotions(id) ON DELETE CASCADE,
    user_id      BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_id     BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    used_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (order_id, promotion_id)
);

-- ------------------------------------------------------------
-- 5. Van chuyen & sau ban hang
-- ------------------------------------------------------------
CREATE TABLE shipments (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id      BIGINT NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE,
    carrier       VARCHAR(100),
    tracking_code VARCHAR(100),
    status        shipment_status NOT NULL DEFAULT 'preparing',
    shipped_at    TIMESTAMPTZ,
    delivered_at  TIMESTAMPTZ
);

CREATE TABLE refund_requests (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id      BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    reason        VARCHAR(500) NOT NULL,
    status        refund_status NOT NULL DEFAULT 'requested',
    refund_amount NUMERIC(12, 2) NOT NULL CHECK (refund_amount >= 0),
    requested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_by  BIGINT REFERENCES users(id) ON DELETE SET NULL,
    processed_at  TIMESTAMPTZ
);

-- ------------------------------------------------------------
-- 6. Danh gia
-- ------------------------------------------------------------
CREATE TABLE reviews (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id    BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id       BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    order_item_id BIGINT NOT NULL UNIQUE REFERENCES order_items(id) ON DELETE CASCADE,
    rating        SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment       TEXT,
    is_approved   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 7. Van hanh
-- ------------------------------------------------------------
CREATE TABLE audit_logs (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action      VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id   BIGINT NOT NULL,
    old_value   JSONB,
    new_value   JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 8. Index bo sung (ngoai UNIQUE/PK da tao cung bang)
-- ------------------------------------------------------------
CREATE INDEX idx_products_category        ON products(category_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_search_vector   ON products USING GIN (search_vector);
CREATE INDEX idx_product_variants_product ON product_variants(product_id);
CREATE INDEX idx_orders_user_status       ON orders(user_id, status);
CREATE INDEX idx_orders_created_at        ON orders(created_at);
CREATE INDEX idx_order_items_order        ON order_items(order_id);
CREATE INDEX idx_order_items_variant      ON order_items(product_variant_id);
CREATE INDEX idx_reviews_product          ON reviews(product_id);
CREATE INDEX idx_audit_logs_entity        ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_flash_sale_promotion     ON flash_sale_items(promotion_id);
CREATE INDEX idx_import_receipt_lot       ON import_receipt_items(import_lot_id);

-- ------------------------------------------------------------
-- 9. Trigger tu dong cap nhat updated_at
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at    BEFORE UPDATE ON users    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_products_updated_at BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_carts_updated_at    BEFORE UPDATE ON carts    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_orders_updated_at   BEFORE UPDATE ON orders   FOR EACH ROW EXECUTE FUNCTION set_updated_at();
