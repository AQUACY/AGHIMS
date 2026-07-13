"""
Migration: add cancellation fields to admission_recommendations table
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
        
        # Add cancelled column if not exists
        if "cancelled" not in existing_cols:
            cursor.execute("ALTER TABLE admission_recommendations ADD COLUMN cancelled INTEGER DEFAULT 0 NOT NULL")
            conn.commit()
            print("✓ Added cancelled column to admission_recommendations")
        else:
            print("✓ cancelled column already exists")
        
        # Add cancelled_by column if not exists
        if "cancelled_by" not in existing_cols:
            cursor.execute("ALTER TABLE admission_recommendations ADD COLUMN cancelled_by INTEGER")
            conn.commit()
            print("✓ Added cancelled_by column to admission_recommendations")
        else:
            print("✓ cancelled_by column already exists")
        
        # Add cancelled_at column if not exists
        if "cancelled_at" not in existing_cols:
            cursor.execute("ALTER TABLE admission_recommendations ADD COLUMN cancelled_at DATETIME")
            conn.commit()
            print("✓ Added cancelled_at column to admission_recommendations")
        else:
            print("✓ cancelled_at column already exists")
        
        # Add cancellation_reason column if not exists
        if "cancellation_reason" not in existing_cols:
            cursor.execute("ALTER TABLE admission_recommendations ADD COLUMN cancellation_reason VARCHAR(500)")
            conn.commit()
            print("✓ Added cancellation_reason column to admission_recommendations")
        else:
            print("✓ cancellation_reason column already exists")
        
        print("Migration completed successfully")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate():
    """Migration entry point called by run_migrations.py"""
    upgrade()


def downgrade():
    # SQLite doesn't support dropping columns easily
    print("Downgrade not implemented for SQLite")


if __name__ == "__main__":
    upgrade()

