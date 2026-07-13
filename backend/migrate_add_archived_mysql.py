"""
Migration: Add archived column to encounters table (MySQL version)
"""
import pymysql
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('DB_USER') or os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('DB_NAME') or os.getenv('MYSQL_DATABASE', 'hms'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def migrate():
    """Add archived column to encounters table"""
    print("=" * 60)
    print("Migration: Add archived column to encounters table")
    print("=" * 60)
    print()
    
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print("✓ Connected to database")
        print()
        
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = 'encounters'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                print("✗ Error: encounters table does not exist")
                connection.close()
                return
            
            # Check if column already exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.columns 
                WHERE table_schema = %s 
                AND table_name = 'encounters'
                AND column_name = 'archived'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] > 0:
                print("✓ archived column already exists")
                connection.close()
                return
            
            print("Adding archived column to encounters table...")
            
            start_time = datetime.now()
            
            try:
                cursor.execute("SET SESSION innodb_lock_wait_timeout = 300")
                cursor.execute("SET SESSION lock_wait_timeout = 300")
                
                cursor.execute("""
                    ALTER TABLE encounters 
                    ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0
                """)
                
                connection.commit()
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                print(f"✓ Successfully added archived column")
                print(f"  Operation completed in {duration:.2f} seconds")
                print()
                
            except pymysql.Error as e:
                connection.rollback()
                if e.args[0] == 1205:
                    print("✗ Error: Lock wait timeout exceeded")
                elif e.args[0] == 1213:
                    print("✗ Error: Deadlock detected")
                else:
                    print(f"✗ Database error: {e}")
                raise
        
        connection.close()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        
    except pymysql.Error as e:
        print(f"✗ Database error: {e}")
        raise
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate()

