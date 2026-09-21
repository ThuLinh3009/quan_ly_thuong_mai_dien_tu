"""Áp dụng thay đổi database, chạy lại được nhiều lần.

Thứ tự:
  1. schema.sql            - chỉ chạy 1 lần (bản gốc, ghi nhận là "baseline")
  2. migrations/NNN_*.sql  - mỗi file chạy đúng 1 lần theo thứ tự tên file
  3. functions.sql         - chạy lại mỗi lần (CREATE OR REPLACE nên an toàn)
  4. seed.sql              - chỉ khi có --seed, chạy 1 lần

Dùng: python -m app.scripts.migrate [--seed]
"""
import argparse
import sys
from pathlib import Path

import psycopg

from app.core.config import get_settings

DB_DIR = Path(__file__).resolve().parents[3] / "database"
if not DB_DIR.exists():
    DB_DIR = Path("/database")  # đường dẫn khi chạy trong container

BASELINE = "baseline (schema.sql)"
SEED = "seed (seed.sql)"


def applied_names(conn) -> set[str]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
    )
    return {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}


def run_file(conn, path: Path, record_as: str | None) -> None:
    print(f"  chạy {path.name}")
    conn.execute(path.read_text(encoding="utf-8"))
    if record_as:
        conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (record_as,))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", action="store_true", help="nạp thêm seed.sql")
    args = parser.parse_args()

    with psycopg.connect(get_settings().database_url) as conn:
        done = applied_names(conn)
        conn.commit()

        schema = DB_DIR / "schema.sql"
        if BASELINE in done:
            print("schema.sql: đã áp dụng, bỏ qua")
        elif conn.execute("SELECT to_regclass('public.users')").fetchone()[0]:
            print("schema.sql: DB đã có bảng (tạo thủ công trước đó), ghi nhận baseline và bỏ qua")
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (BASELINE,))
            conn.commit()
        else:
            run_file(conn, schema, BASELINE)
            conn.commit()

        for path in sorted((DB_DIR / "migrations").glob("*.sql")):
            if path.name in done:
                continue
            run_file(conn, path, path.name)
            conn.commit()

        run_file(conn, DB_DIR / "functions.sql", None)
        conn.commit()

        if args.seed:
            seed = DB_DIR / "seed.sql"
            if SEED in done:
                print("seed.sql: đã nạp, bỏ qua")
            elif not seed.exists():
                print("seed.sql: chưa có file, bỏ qua")
            else:
                run_file(conn, seed, SEED)
                conn.commit()

    print("Xong.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
