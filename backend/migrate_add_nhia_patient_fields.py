"""
Migration: Add NHIA-related columns to patients table (SQLite).
On MySQL prod use migrate_add_nhia_patient_fields_mysql.py (run_migrations skips this twin).
"""
import sqlite3
from pathlib import Path


def migrate():
    try:
        from app.core.config import settings
        if getattr(settings, "DATABASE_MODE", "").lower() == "mysql":
            print("Skipping SQLite NHIA patient fields migration (DATABASE_MODE=mysql)")
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

        new_columns = [
            ("nhis_active", "BOOLEAN DEFAULT 0"),
            ("ccc_status", "VARCHAR(50)"),
        ]

        for column_name, column_type in new_columns:
            if column_name not in columns:
                print(f"Adding {column_name} column to patients table...")
                cursor.execute(f"ALTER TABLE patients ADD COLUMN {column_name} {column_type}")
                conn.commit()
                print(f"Successfully added {column_name}")
            else:
                print(f"{column_name} column already exists")
        return True
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
