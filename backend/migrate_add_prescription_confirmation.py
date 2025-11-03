"""
Migration script to add prescription confirmation fields
Adds 'confirmed_by' and 'confirmed_at' columns to prescriptions table

Run this script if you have an existing database that doesn't have these columns.
For new databases, these columns will be created automatically via SQLAlchemy.
"""
import sqlite3
import os
from pathlib import Path

def migrate_add_prescription_confirmation():
    """Add confirmed_by and confirmed_at columns to prescriptions table"""
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print("Database not found. Running init_db.py will create the table with these columns.")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
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
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Migrating database to add prescription confirmation fields...")
    migrate_add_prescription_confirmation()
    print("Migration complete!")

