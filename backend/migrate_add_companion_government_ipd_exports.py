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


def migrate() -> None:
    CompanionGovernmentIpdExport.__table__.create(engine, checkfirst=True)
    print("OK: companion_government_ipd_exports table created/verified.")


if __name__ == "__main__":
    migrate()
