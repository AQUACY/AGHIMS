"""
Migration: Add prescription confirmation fields (SQLite version)
Adds 'confirmed_by' and 'confirmed_at' columns to prescriptions table
"""
import sqlite3
from pathlib import Path

def migrate():
    """Add confirmed_by and confirmed_at columns to prescriptions table"""
    print("=" * 60)
    print("Migration: Add prescription confirmation fields")
    print("=" * 60)
    print()
    
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print("⚠ SQLite database not found. This migration is SQLite-specific.")
        print("  For MySQL, use migrate_add_prescription_confirmation_mysql.py instead.")
        print("  Skipping this migration.")
        return
    
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(prescriptions)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add confirmed_by column if it doesn't exist
        if 'confirmed_by' in columns:
            print("✓ Column 'confirmed_by' already exists in prescriptions table")
        else:
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN confirmed_by INTEGER")
            conn.commit()
            print("✓ Added 'confirmed_by' column to prescriptions table")
        
        # Add confirmed_at column if it doesn't exist
        if 'confirmed_at' in columns:
            print("✓ Column 'confirmed_at' already exists in prescriptions table")
        else:
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN confirmed_at DATETIME")
            conn.commit()
            print("✓ Added 'confirmed_at' column to prescriptions table")
        
    except sqlite3.OperationalError as e:
        print(f"✗ Error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
    
    print()
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    migrate()

