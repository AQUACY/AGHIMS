"""
Migration: Add created_by_id column to companion_visit_items.

Run from backend folder:
  python migrate_add_created_by_to_companion_items.py

Notes:
- This project doesn't use Alembic; we use lightweight scripts for schema changes.
- We keep the column nullable for backward compatibility.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text

from app.core.database import engine


def _column_exists_mysql(table: str, column: str) -> bool:
    with engine.connect() as conn:
        res = conn.execute(
            text(
                """
                SELECT COUNT(*) AS cnt
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table
                  AND COLUMN_NAME = :column
                """
            ),
            {"table": table, "column": column},
        )
        return int(res.scalar() or 0) > 0


def _column_exists_sqlite(table: str, column: str) -> bool:
    with engine.connect() as conn:
        res = conn.execute(text(f"PRAGMA table_info({table})"))
        cols = [row[1] for row in res.fetchall()]  # (cid, name, type, notnull, dflt_value, pk)
        return column in cols


def migrate() -> None:
    table = "companion_visit_items"
    column = "created_by_id"

    dialect = engine.dialect.name.lower()
    print(f"Dialect: {dialect}")

    if dialect.startswith("mysql"):
        if _column_exists_mysql(table, column):
            print("OK: Column already exists, nothing to do.")
            return
        with engine.begin() as conn:
            print("Adding created_by_id column...")
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} INT NULL"))
            # Index helps audit lookups (optional)
            try:
                conn.execute(text(f"CREATE INDEX ix_{table}_{column} ON {table} ({column})"))
            except Exception:
                # ignore if index exists or not supported
                pass
        print("OK: Migration complete.")
        return

    if dialect.startswith("sqlite"):
        if _column_exists_sqlite(table, column):
            print("OK: Column already exists, nothing to do.")
            return
        with engine.begin() as conn:
            print("Adding created_by_id column...")
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER NULL"))
        print("OK: Migration complete.")
        return

    # Fallback: try generic ALTER
    with engine.begin() as conn:
        print("Attempting generic ALTER TABLE ...")
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER NULL"))
    print("OK: Migration complete.")


if __name__ == "__main__":
    migrate()

