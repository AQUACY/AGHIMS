"""
Migration: columns for live GHIMS co-payment sync.

Run from the backend folder:
  python migrate_companion_ghims_live_sync.py

Adds:
- companion_visits.source, ghims_synced_at, ghims_sync_note, ghims_unmatched_json
- companion_visit_items.ghims_source_type, ghims_source_id
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


def _add(table: str, column: str, ddl: str, col_exists) -> None:
    if col_exists(column):
        print(f"OK: {table}.{column} already exists")
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
    print(f"OK: added {table}.{column}")


def migrate() -> None:
    dialect = engine.dialect.name.lower()
    if dialect.startswith("mysql"):
        visit_exists = lambda c: _col_exists_mysql("companion_visits", c)
        item_exists = lambda c: _col_exists_mysql("companion_visit_items", c)
        note_type = "TEXT NULL"
        json_type = "TEXT NULL"
    elif dialect.startswith("sqlite"):
        visit_exists = lambda c: _col_exists_sqlite("companion_visits", c)
        item_exists = lambda c: _col_exists_sqlite("companion_visit_items", c)
        note_type = "TEXT"
        json_type = "TEXT"
    else:
        raise SystemExit(f"Unsupported database dialect: {dialect}")

    _add("companion_visits", "source", "source VARCHAR(20) NULL", visit_exists)
    _add("companion_visits", "ghims_synced_at", "ghims_synced_at DATETIME NULL", visit_exists)
    _add("companion_visits", "ghims_visit_date", "ghims_visit_date DATETIME NULL", visit_exists)
    _add("companion_visits", "ghims_sync_note", f"ghims_sync_note {note_type}", visit_exists)
    _add("companion_visits", "ghims_unmatched_json", f"ghims_unmatched_json {json_type}", visit_exists)
    _add("companion_visit_items", "ghims_source_type", "ghims_source_type VARCHAR(30) NULL", item_exists)
    _add("companion_visit_items", "ghims_source_id", "ghims_source_id VARCHAR(150) NULL", item_exists)
    price_flag = (
        "needs_copay_price TINYINT(1) NOT NULL DEFAULT 0"
        if dialect.startswith("mysql")
        else "needs_copay_price BOOLEAN NOT NULL DEFAULT 0"
    )
    _add("companion_visit_items", "needs_copay_price", price_flag, item_exists)
    print("OK: live GHIMS co-payment columns are in place.")


def repair() -> None:
    from app.core.database import SessionLocal
    from app.services.ghims_companion_sync import repair_duplicate_live_sync

    db = SessionLocal()
    try:
        result = repair_duplicate_live_sync(db)
        print(
            "OK: removed {visits_removed} older synced visits and {lines_removed} duplicate lines. "
            "{visits_kept} today's synced visits remain.".format(**result)
        )
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
    repair()
