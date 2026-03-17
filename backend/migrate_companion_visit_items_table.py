"""
Create companion_visit_items table.
Run from backend folder: python migrate_companion_visit_items_table.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import Base, engine
from app.models.companion_visit_item import CompanionVisitItem

if __name__ == "__main__":
    print("Creating companion_visit_items table...")
    CompanionVisitItem.__table__.create(engine, checkfirst=True)
    print("Done.")
