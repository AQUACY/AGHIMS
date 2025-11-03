"""
Migration script to add 'archived' column to encounters table
Run this script if you have an existing database
"""
import sqlite3
import os
from pathlib import Path

def migrate_add_archived():
    """Add archived column to encounters table"""
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print("Database not found. Running init_db.py will create the table with the archived column.")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
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
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Migrating database to add 'archived' column...")
    migrate_add_archived()
    print("Migration complete!")

