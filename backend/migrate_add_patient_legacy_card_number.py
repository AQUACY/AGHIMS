"""
Migration: Add legacy_card_number to patients table (SQLite).
"""
import sqlite3
from pathlib import Path


def migrate():
    db_path = Path(__file__).parent / "hms.db"
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(patients)")
        columns = {column[1] for column in cursor.fetchall()}
        if "legacy_card_number" not in columns:
            cursor.execute("ALTER TABLE patients ADD COLUMN legacy_card_number VARCHAR(50)")
            conn.commit()
            print("Added legacy_card_number column")
        else:
            print("legacy_card_number already exists")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
