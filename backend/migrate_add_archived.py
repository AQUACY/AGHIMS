"""
Migration: Add archived column to encounters table (SQLite version)
"""
import sqlite3
from pathlib import Path

def migrate():
    """Add archived column to encounters table"""
    print("=" * 60)
    print("Migration: Add archived column to encounters table")
    print("=" * 60)
    print()
    
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print("⚠ SQLite database not found. This migration is SQLite-specific.")
        print("  For MySQL, use migrate_add_archived_mysql.py instead.")
        print("  Skipping this migration.")
        return
    
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        # Check if column already exists
        cursor.execute("PRAGMA table_info(encounters)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'archived' in columns:
            print("✓ Column 'archived' already exists in encounters table")
        else:
            # Add archived column with default value False
            cursor.execute("ALTER TABLE encounters ADD COLUMN archived BOOLEAN DEFAULT 0 NOT NULL")
            conn.commit()
            print("✓ Added 'archived' column to encounters table")
        
    except sqlite3.OperationalError as e:
        print(f"✗ Error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
    
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    migrate()

