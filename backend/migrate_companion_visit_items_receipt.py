"""
Add receipt_number and paid_at to companion_visit_items.
Run from backend folder: python migrate_companion_visit_items_receipt.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import engine
from app.core.config import settings
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        # receipt_number
        try:
            if settings.DATABASE_MODE.lower() == "sqlite":
                conn.execute(text("ALTER TABLE companion_visit_items ADD COLUMN receipt_number VARCHAR(50)"))
            else:
                conn.execute(text("ALTER TABLE companion_visit_items ADD COLUMN receipt_number VARCHAR(50)"))
            conn.commit()
        except Exception as e:
            if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                raise
        # paid_at
        try:
            if settings.DATABASE_MODE.lower() == "sqlite":
                conn.execute(text("ALTER TABLE companion_visit_items ADD COLUMN paid_at DATETIME"))
            else:
                conn.execute(text("ALTER TABLE companion_visit_items ADD COLUMN paid_at DATETIME"))
            conn.commit()
        except Exception as e:
            if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                raise
    print("Done.")

if __name__ == "__main__":
    print("Adding receipt_number and paid_at to companion_visit_items...")
    migrate()
