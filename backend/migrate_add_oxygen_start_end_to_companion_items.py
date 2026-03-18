"""
Migration: Add start_time and end_time to companion_visit_items for oxygen (hourly billing).

Run from backend folder:
  python migrate_add_oxygen_start_end_to_companion_items.py

Adds:
- start_time (datetime, nullable)
- end_time (datetime, nullable)
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text

from app.core.database import engine


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

    def col_exists(c: str) -> bool:
        if dialect.startswith("mysql"):
            return _col_exists_mysql(table, c)
        if dialect.startswith("sqlite"):
            return _col_exists_sqlite(table, c)
        return False

    stmts = []
    if not col_exists("start_time"):
        stmts.append(f"ALTER TABLE {table} ADD COLUMN start_time DATETIME NULL")
    if not col_exists("end_time"):
        stmts.append(f"ALTER TABLE {table} ADD COLUMN end_time DATETIME NULL")

    if not stmts:
        print("OK: start_time/end_time columns already exist.")
        return

    with engine.begin() as conn:
        for s in stmts:
            conn.execute(text(s))

    print("OK: companion_visit_items start_time and end_time added.")


if __name__ == "__main__":
    migrate()
