"""
Migration: Add legacy_card_number to patients table (SQLite).
On MySQL prod use migrate_add_patient_legacy_card_number_mysql.py (run_migrations skips this twin).
"""
import sqlite3
from pathlib import Path


def migrate():
    try:
        from app.core.config import settings
        if getattr(settings, "DATABASE_MODE", "").lower() == "mysql":
            print("Skipping SQLite legacy_card_number migration (DATABASE_MODE=mysql)")
            return True
    except Exception:
        pass

    db_path = Path(__file__).parent / "hms.db"
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return True

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(patients)")
        columns = {column[1] for column in cursor.fetchall()}
        if not columns:
            print("patients table missing in SQLite DB; nothing to do")
            return True
        if "legacy_card_number" not in columns:
            cursor.execute("ALTER TABLE patients ADD COLUMN legacy_card_number VARCHAR(50)")
            conn.commit()
            print("Added legacy_card_number column")
        else:
            print("legacy_card_number already exists")
        return True
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
