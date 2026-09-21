# Migrations

Thay đổi bảng sau khi đã có `schema.sql` được viết thành file đánh số ở đây, ví dụ:

    001_add_products_weight.sql
    002_add_index_orders_status.sql

- Mỗi file chạy đúng một lần, theo thứ tự tên file; đã chạy thì ghi vào bảng `schema_migrations`.
- Không sửa file đã chạy; muốn đổi tiếp thì thêm file mới.
- Hàm nghiệp vụ nằm trong `functions.sql` (CREATE OR REPLACE), sửa trực tiếp file đó, không cần migration.
- Áp dụng: `python -m app.scripts.migrate`
