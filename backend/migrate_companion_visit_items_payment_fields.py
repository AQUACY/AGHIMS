"""
Add paid_by_id and payment_method to companion_visit_items.
Run from backend folder: python migrate_companion_visit_items_payment_fields.py
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
        # paid_by_id (user who received payment)
        try:
            if settings.DATABASE_MODE.lower() == "sqlite":
                conn.execute(text("ALTER TABLE companion_visit_items ADD COLUMN paid_by_id INTEGER"))
            else:
                conn.execute(text("ALTER TABLE companion_visit_items ADD COLUMN paid_by_id INT"))
            conn.commit()
        except Exception as e:
            if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                raise

        # payment_method (cash, card, mobile_money, etc.)
        try:
            conn.execute(text("ALTER TABLE companion_visit_items ADD COLUMN payment_method VARCHAR(50)"))
            conn.commit()
        except Exception as e:
            if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
                raise
    print("Done.")


if __name__ == "__main__":
    print("Adding paid_by_id and payment_method to companion_visit_items...")
    migrate()

