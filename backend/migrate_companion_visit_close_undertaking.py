"""
Add close/reopen/undertaking fields to companion_visits.
Run from backend folder: python migrate_companion_visit_close_undertaking.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import engine
from app.core.config import settings
from sqlalchemy import text


def add_col(conn, name, spec):
    try:
        conn.execute(text(f"ALTER TABLE companion_visits ADD COLUMN {name} {spec}"))
        conn.commit()
        print(f"  + {name}")
    except Exception as e:
        if "duplicate" not in str(e).lower() and "already exists" not in str(e).lower():
            raise
        print(f"  (exists) {name}")


def migrate():
    with engine.connect() as conn:
        if settings.DATABASE_MODE.lower() == "sqlite":
            add_col(conn, "closed_at", "DATETIME")
            add_col(conn, "closed_by_id", "INTEGER REFERENCES users(id)")
            add_col(conn, "reopened_at", "DATETIME")
            add_col(conn, "reopened_by_id", "INTEGER REFERENCES users(id)")
            add_col(conn, "reopen_reason", "TEXT")
            add_col(conn, "undertaking_status", "VARCHAR(20)")
            add_col(conn, "undertaking_deposit_amount", "FLOAT")
            add_col(conn, "undertaking_deposit_receipt_number", "VARCHAR(50)")
            add_col(conn, "undertaking_requested_at", "DATETIME")
            add_col(conn, "undertaking_requested_by_id", "INTEGER REFERENCES users(id)")
            add_col(conn, "undertaking_approved_at", "DATETIME")
            add_col(conn, "undertaking_approved_by_id", "INTEGER REFERENCES users(id)")
            add_col(conn, "undertaking_unapproved_at", "DATETIME")
            add_col(conn, "undertaking_unapproved_by_id", "INTEGER REFERENCES users(id)")
            add_col(conn, "undertaking_unapprove_reason", "TEXT")
        else:
            add_col(conn, "closed_at", "DATETIME")
            add_col(conn, "closed_by_id", "INT")
            add_col(conn, "reopened_at", "DATETIME")
            add_col(conn, "reopened_by_id", "INT")
            add_col(conn, "reopen_reason", "TEXT")
            add_col(conn, "undertaking_status", "VARCHAR(20)")
            add_col(conn, "undertaking_deposit_amount", "FLOAT")
            add_col(conn, "undertaking_deposit_receipt_number", "VARCHAR(50)")
            add_col(conn, "undertaking_requested_at", "DATETIME")
            add_col(conn, "undertaking_requested_by_id", "INT")
            add_col(conn, "undertaking_approved_at", "DATETIME")
            add_col(conn, "undertaking_approved_by_id", "INT")
            add_col(conn, "undertaking_unapproved_at", "DATETIME")
            add_col(conn, "undertaking_unapproved_by_id", "INT")
            add_col(conn, "undertaking_unapprove_reason", "TEXT")
    print("Done.")


if __name__ == "__main__":
    print("Adding close/undertaking/reopen columns to companion_visits...")
    migrate()
