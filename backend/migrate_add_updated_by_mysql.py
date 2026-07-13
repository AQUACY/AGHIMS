"""
Migration: Add updated_by column to lab_results, scan_results, and xray_results tables (MySQL compatible)
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text

def migrate():
    """Add updated_by column to lab_results, scan_results, and xray_results tables (MySQL/SQLite compatible)"""
    try:
        # Get database URL to determine database type
        db_url = str(engine.url)
        is_mysql = 'mysql' in db_url.lower() or 'pymysql' in db_url.lower()
        is_sqlite = 'sqlite' in db_url.lower()
        
        if not is_mysql and not is_sqlite:
            print(f"Unsupported database type: {db_url}")
            print("This migration supports MySQL and SQLite only.")
            return False
        
        tables = ['lab_results', 'scan_results', 'xray_results']
        
        with engine.connect() as conn:
            for table_name in tables:
                # Check if column already exists
                if is_mysql:
                    # MySQL: Check if column exists
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) 
                        FROM information_schema.COLUMNS 
                        WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = :table_name
                        AND COLUMN_NAME = 'updated_by'
                    """), {"table_name": table_name})
                    column_exists = result.scalar() > 0
                else:
                    # SQLite: Check if column exists
                    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    columns = [row[1] for row in result.fetchall()]
                    column_exists = 'updated_by' in columns
                
                if column_exists:
                    print(f"Column 'updated_by' already exists in {table_name} table")
                    continue
                
                # Add updated_by column
                print(f"Adding 'updated_by' column to {table_name} table...")
                if is_mysql:
                    conn.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN updated_by INTEGER NULL
                    """))
                else:
                    conn.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN updated_by INTEGER
                    """))
                
                print(f"Successfully added 'updated_by' column to {table_name} table")
            
            conn.commit()
            print("\nAll migrations completed successfully!")
            return True
            
    except Exception as e:
        print(f"Error adding columns: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

