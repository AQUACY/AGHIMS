"""
Migration: Add endpoint_path and http_method columns to audit_logs table (MySQL/SQLite compatible)
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text

def migrate():
    """Add endpoint_path and http_method columns to audit_logs table (MySQL/SQLite compatible)"""
    try:
        # Get database URL to determine database type
        db_url = str(engine.url)
        is_mysql = 'mysql' in db_url.lower() or 'pymysql' in db_url.lower()
        is_sqlite = 'sqlite' in db_url.lower()
        
        if not is_mysql and not is_sqlite:
            print(f"Unsupported database type: {db_url}")
            print("This migration supports MySQL and SQLite only.")
            return False
        
        table_name = 'audit_logs'
        
        with engine.connect() as conn:
            # Check if columns already exist
            if is_mysql:
                # MySQL: Check if columns exist
                result = conn.execute(text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = :table_name
                    AND COLUMN_NAME IN ('endpoint_path', 'http_method')
                """), {"table_name": table_name})
                columns_exist = result.scalar() >= 2
            else:
                # SQLite: Check if columns exist
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                columns = [row[1] for row in result.fetchall()]
                columns_exist = 'endpoint_path' in columns and 'http_method' in columns
            
            if columns_exist:
                print(f"Columns 'endpoint_path' and 'http_method' already exist in {table_name} table")
                conn.commit()
                return True
            
            # Add endpoint_path column
            if is_mysql:
                # Check if endpoint_path exists
                result = conn.execute(text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = :table_name
                    AND COLUMN_NAME = 'endpoint_path'
                """), {"table_name": table_name})
                endpoint_path_exists = result.scalar() > 0
            else:
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                columns = [row[1] for row in result.fetchall()]
                endpoint_path_exists = 'endpoint_path' in columns
            
            if not endpoint_path_exists:
                print(f"Adding 'endpoint_path' column to {table_name} table...")
                if is_mysql:
                    conn.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN endpoint_path VARCHAR(500) NULL,
                        ADD INDEX idx_audit_logs_endpoint_path (endpoint_path)
                    """))
                else:
                    conn.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN endpoint_path VARCHAR(500)
                    """))
                print(f"Successfully added 'endpoint_path' column to {table_name} table")
            
            # Add http_method column
            if is_mysql:
                # Check if http_method exists
                result = conn.execute(text(f"""
                    SELECT COUNT(*) 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = :table_name
                    AND COLUMN_NAME = 'http_method'
                """), {"table_name": table_name})
                http_method_exists = result.scalar() > 0
            else:
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                columns = [row[1] for row in result.fetchall()]
                http_method_exists = 'http_method' in columns
            
            if not http_method_exists:
                print(f"Adding 'http_method' column to {table_name} table...")
                if is_mysql:
                    conn.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN http_method VARCHAR(10) NULL,
                        ADD INDEX idx_audit_logs_http_method (http_method)
                    """))
                else:
                    conn.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN http_method VARCHAR(10)
                    """))
                print(f"Successfully added 'http_method' column to {table_name} table")
            
            conn.commit()
            print("\nMigration completed successfully!")
            return True
            
    except Exception as e:
        print(f"Error adding columns: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

