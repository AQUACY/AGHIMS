"""
Create claimit_report_batches and claimit_report_errors tables.
Run from backend folder: python migrate_claimit_report_tables.py
Uses the app's database connection (no ORM models needed for create_all).
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import Base, engine
from app.models.claimit_report import ClaimItReportBatch, ClaimItReportError

if __name__ == "__main__":
    print("Creating claimit_report_batches and claimit_report_errors tables...")
    # Only create these two tables (and their dependencies like users if needed for FK)
    ClaimItReportBatch.__table__.create(engine, checkfirst=True)
    ClaimItReportError.__table__.create(engine, checkfirst=True)
    print("Done.")
