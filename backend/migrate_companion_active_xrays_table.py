"""
Create companion_active_xrays table.
Run from backend folder: python migrate_companion_active_xrays_table.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import engine
from app.models.companion_active_xray import CompanionActiveXray

if __name__ == "__main__":
    print("Creating companion_active_xrays table...")
    CompanionActiveXray.__table__.create(engine, checkfirst=True)
    print("Done.")
