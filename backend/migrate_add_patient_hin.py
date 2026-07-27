"""
Migration: Add hin column to patients table (SQLite).
On MySQL prod use migrate_add_patient_hin_mysql.py (run_migrations skips this twin).
"""
import sqlite3
from pathlib import Path

from app.core.config import settings


def migrate():
    if getattr(settings, "DATABASE_MODE", "").lower() == "mysql":
        print("Skipping SQLite patient hin migration (DATABASE_MODE=mysql)")
        return True

    db_path = Path(settings.SQLITE_DB_PATH)
    if not db_path.is_absolute():
        db_path = Path(__file__).parent / db_path
    if not db_path.exists():
        print(f"SQLite database not found at {db_path}")
        return True

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(patients)")
        columns = {row[1] for row in cursor.fetchall()}
        if not columns:
            print("patients table missing in SQLite DB; nothing to do")
            return True
        if "hin" not in columns:
            cursor.execute("ALTER TABLE patients ADD COLUMN hin VARCHAR(100)")
            conn.commit()
            print("Added hin column")
        else:
            print("hin already exists")
        return True
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
