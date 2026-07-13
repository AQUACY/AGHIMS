"""
Create companion_active_investigations table.
Run from backend folder: python migrate_companion_active_investigations_table.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import Base, engine
from app.models.companion_active_investigation import CompanionActiveInvestigation

if __name__ == "__main__":
    print("Creating companion_active_investigations table...")
    CompanionActiveInvestigation.__table__.create(engine, checkfirst=True)
    print("Done.")
