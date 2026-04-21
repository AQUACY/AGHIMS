"""
Migration: Create companion_government_ipd_exports table.

Run from backend folder:
  python migrate_add_companion_government_ipd_exports.py
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import engine
from app.models.companion_government_ipd_export import CompanionGovernmentIpdExport


def _table_exists_mysql(table: str) -> bool:
    from sqlalchemy import text

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
    from sqlalchemy import text

    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=:table"),
            {"table": table},
        )
        return int(res.scalar() or 0) > 0


def migrate() -> None:
    dialect = engine.dialect.name.lower()
    if dialect.startswith("mysql"):
        visit_table_exists = _table_exists_mysql("companion_visits")
    elif dialect.startswith("sqlite"):
        visit_table_exists = _table_exists_sqlite("companion_visits")
    else:
        visit_table_exists = True

    if not visit_table_exists:
        print("SKIP: companion_visits table does not exist yet.")
        return

    CompanionGovernmentIpdExport.__table__.create(engine, checkfirst=True)
    print("OK: companion_government_ipd_exports table created/verified.")


if __name__ == "__main__":
    migrate()
