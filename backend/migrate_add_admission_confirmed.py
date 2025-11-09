"""
Migration: add confirmed_by and confirmed_at columns to admission_recommendations table
"""
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "hms.db"


def upgrade():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admission_recommendations'")
        if not cursor.fetchone():
            print("Table admission_recommendations does not exist. Skipping migration.")
            return
        
        # Check if columns exist
        cursor.execute("PRAGMA table_info(admission_recommendations)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        # Add confirmed_by column if not exists
        if "confirmed_by" not in existing_cols:
            cursor.execute("ALTER TABLE admission_recommendations ADD COLUMN confirmed_by INTEGER")
            conn.commit()
            print("✓ Added confirmed_by column to admission_recommendations")
        else:
            print("✓ confirmed_by column already exists")
        
        # Add confirmed_at column if not exists
        if "confirmed_at" not in existing_cols:
            cursor.execute("ALTER TABLE admission_recommendations ADD COLUMN confirmed_at DATETIME")
            conn.commit()
            print("✓ Added confirmed_at column to admission_recommendations")
        else:
            print("✓ confirmed_at column already exists")
        
        print("Migration completed successfully")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def downgrade():
    # SQLite doesn't support dropping columns easily
    # Would need to recreate table
    print("Downgrade not implemented for SQLite")


if __name__ == "__main__":
    upgrade()

