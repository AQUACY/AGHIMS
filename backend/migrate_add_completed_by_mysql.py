"""
Migration: Add completed_by column to investigations table (MySQL compatible)
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text

def migrate():
    """Add completed_by column to investigations table (MySQL/SQLite compatible)"""
    try:
        # Get database URL to determine database type
        db_url = str(engine.url)
        is_mysql = 'mysql' in db_url.lower() or 'pymysql' in db_url.lower()
        is_sqlite = 'sqlite' in db_url.lower()
        
        if not is_mysql and not is_sqlite:
            print(f"Unsupported database type: {db_url}")
            print("This migration supports MySQL and SQLite only.")
            return False
        
        with engine.connect() as conn:
            # Check if column already exists
            if is_mysql:
                # MySQL: Check if column exists
                result = conn.execute(text("""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'investigations' 
                    AND COLUMN_NAME = 'completed_by'
                """))
                column_exists = result.scalar() > 0
            else:
                # SQLite: Check if column exists
                result = conn.execute(text("PRAGMA table_info(investigations)"))
                columns = [row[1] for row in result.fetchall()]
                column_exists = 'completed_by' in columns
            
            if column_exists:
                print("Column 'completed_by' already exists in investigations table")
                return True
            
            # Add completed_by column
            print("Adding 'completed_by' column to investigations table...")
            if is_mysql:
                conn.execute(text("""
                    ALTER TABLE investigations 
                    ADD COLUMN completed_by INTEGER NULL
                """))
            else:
                conn.execute(text("""
                    ALTER TABLE investigations 
                    ADD COLUMN completed_by INTEGER
                """))
            
            conn.commit()
            print("Successfully added 'completed_by' column to investigations table")
            return True
            
    except Exception as e:
        print(f"Error adding column: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

