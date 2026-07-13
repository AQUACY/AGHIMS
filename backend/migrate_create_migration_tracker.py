"""
Initial migration to create the migration_tracker table
This must be run first before using the migration runner
"""
import sqlite3
from pathlib import Path
from datetime import datetime

def migrate():
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if migration_tracker table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='migration_tracker'
        """)
        
        if cursor.fetchone() is None:
            print("Creating migration_tracker table...")
            cursor.execute("""
                CREATE TABLE migration_tracker (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT NOT NULL UNIQUE,
                    executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    status TEXT NOT NULL DEFAULT 'success',
                    error_message TEXT
                )
            """)
            conn.commit()
            print("✓ Successfully created migration_tracker table")
        else:
            print("✓ migration_tracker table already exists")
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

