"""
Migration script to add other_names column to patients table (SQLite)
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
        # Check if column already exists
        cursor.execute("PRAGMA table_info(patients)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "other_names" not in columns:
            print("Adding 'other_names' column to patients table...")
            cursor.execute("ALTER TABLE patients ADD COLUMN other_names VARCHAR(255)")
            conn.commit()
            print("✓ Successfully added 'other_names' column")
        else:
            print("✓ Column 'other_names' already exists")
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

