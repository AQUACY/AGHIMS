"""
Migration script to add price column to investigations table
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
        cursor.execute("PRAGMA table_info(investigations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'price' not in columns:
            print("Adding price column to investigations table...")
            cursor.execute("ALTER TABLE investigations ADD COLUMN price VARCHAR(50)")
            conn.commit()
            print("✓ Successfully added price column to investigations table")
        else:
            print("✓ Price column already exists in investigations table")
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

