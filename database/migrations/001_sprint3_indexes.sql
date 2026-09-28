-- Index bo sung phuc vu Sprint 3 (gio hang/don hang/khuyen mai/tra hang/danh gia).
-- schema.sql la baseline chi chay 1 lan nen bang moi/cot moi phai qua migration,
-- nhung o day cac bang da co san tu dau (carts/orders/promotions/refund_requests/
-- reviews...) -- chi con thieu index cho cac truy van moi trong functions.sql.
CREATE INDEX IF NOT EXISTS idx_cart_items_cart          ON cart_items(cart_id);
CREATE INDEX IF NOT EXISTS idx_order_status_history_ord ON order_status_history(order_id);
CREATE INDEX IF NOT EXISTS idx_refund_requests_order    ON refund_requests(order_id);
CREATE INDEX IF NOT EXISTS idx_refund_requests_status   ON refund_requests(status);
CREATE INDEX IF NOT EXISTS idx_reviews_user             ON reviews(user_id);
CREATE INDEX IF NOT EXISTS idx_promotion_usages_user    ON promotion_usages(user_id);
CREATE INDEX IF NOT EXISTS idx_flash_sale_items_variant ON flash_sale_items(product_variant_id);
CREATE INDEX IF NOT EXISTS idx_payments_status          ON payments(status);
CREATE INDEX IF NOT EXISTS idx_promotions_active_window ON promotions(is_active, starts_at, ends_at);
