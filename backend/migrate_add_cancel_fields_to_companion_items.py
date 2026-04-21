"""
Migration: Add cancellation (soft-delete) fields to companion_visit_items.

Run from backend folder:
  python migrate_add_cancel_fields_to_companion_items.py

Adds:
- cancelled (bool)
- cancelled_at (datetime)
- cancelled_by_id (int FK users)
- cancel_reason (text)
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text

from app.core.database import engine


def _table_exists_mysql(table: str) -> bool:
    with engine.connect() as conn:
        res = conn.execute(
            text(
                """
                SELECT COUNT(*) AS cnt
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table
                """
            ),
            {"table": table},
        )
        return int(res.scalar() or 0) > 0


def _table_exists_sqlite(table: str) -> bool:
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=:table"),
            {"table": table},
        )
        return int(res.scalar() or 0) > 0


def _col_exists_mysql(table: str, column: str) -> bool:
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


def _col_exists_sqlite(table: str, column: str) -> bool:
    with engine.connect() as conn:
        res = conn.execute(text(f"PRAGMA table_info({table})"))
        cols = [row[1] for row in res.fetchall()]
        return column in cols


def migrate() -> None:
    table = "companion_visit_items"
    dialect = engine.dialect.name.lower()

    def table_exists() -> bool:
        if dialect.startswith("mysql"):
            return _table_exists_mysql(table)
        if dialect.startswith("sqlite"):
            return _table_exists_sqlite(table)
        return False

    def col_exists(c: str) -> bool:
        if dialect.startswith("mysql"):
            return _col_exists_mysql(table, c)
        if dialect.startswith("sqlite"):
            return _col_exists_sqlite(table, c)
        return False

    if not table_exists():
        print(f"SKIP: table '{table}' does not exist yet.")
        return

    stmts = []
    if not col_exists("cancelled"):
        if dialect.startswith("mysql"):
            stmts.append(f"ALTER TABLE {table} ADD COLUMN cancelled TINYINT(1) NOT NULL DEFAULT 0")
        else:
            stmts.append(f"ALTER TABLE {table} ADD COLUMN cancelled BOOLEAN NOT NULL DEFAULT 0")
    if not col_exists("cancelled_at"):
        stmts.append(f"ALTER TABLE {table} ADD COLUMN cancelled_at DATETIME NULL")
    if not col_exists("cancelled_by_id"):
        stmts.append(f"ALTER TABLE {table} ADD COLUMN cancelled_by_id INT NULL")
    if not col_exists("cancel_reason"):
        stmts.append(f"ALTER TABLE {table} ADD COLUMN cancel_reason TEXT NULL")

    if not stmts:
        print("OK: cancellation columns already exist.")
        return

    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))
        # Helpful index for filtering
        try:
            conn.execute(text(f"CREATE INDEX ix_{table}_cancelled ON {table} (cancelled)"))
        except Exception:
            pass

    print("OK: companion_visit_items cancellation fields added.")


if __name__ == "__main__":
    migrate()

