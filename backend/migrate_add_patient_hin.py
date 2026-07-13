"""
Migration: Add hin column to patients table (SQLite).
"""
import sqlite3
from pathlib import Path

from app.core.config import settings


def migrate():
    db_path = Path(settings.SQLITE_DB_PATH)
    if not db_path.is_absolute():
        db_path = Path(__file__).parent / db_path
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(patients)")
        columns = {row[1] for row in cursor.fetchall()}
        if "hin" not in columns:
            cursor.execute("ALTER TABLE patients ADD COLUMN hin VARCHAR(100)")
            conn.commit()
            print("Added hin column")
        else:
            print("hin already exists")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
