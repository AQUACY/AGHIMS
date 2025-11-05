"""
Migration script to add cancellation fields to investigations table
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
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(investigations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'cancelled_by' not in columns:
            print("Adding cancelled_by column to investigations table...")
            cursor.execute("ALTER TABLE investigations ADD COLUMN cancelled_by INTEGER")
            conn.commit()
            print("✓ Successfully added cancelled_by column")
        else:
            print("✓ cancelled_by column already exists")
        
        if 'cancellation_reason' not in columns:
            print("Adding cancellation_reason column to investigations table...")
            cursor.execute("ALTER TABLE investigations ADD COLUMN cancellation_reason VARCHAR(1000)")
            conn.commit()
            print("✓ Successfully added cancellation_reason column")
        else:
            print("✓ cancellation_reason column already exists")
        
        if 'cancelled_at' not in columns:
            print("Adding cancelled_at column to investigations table...")
            cursor.execute("ALTER TABLE investigations ADD COLUMN cancelled_at DATETIME")
            conn.commit()
            print("✓ Successfully added cancelled_at column")
        else:
            print("✓ cancelled_at column already exists")
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

