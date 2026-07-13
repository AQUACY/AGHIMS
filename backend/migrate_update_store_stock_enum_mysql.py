"""
Migration script to update store_stocks table enum values from lowercase to uppercase
"""
import pymysql
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from current directory
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


def update_store_stocks_enum(connection):
    """Update store_stocks table enum from lowercase to uppercase"""
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'store_stocks'
        """, (DB_CONFIG['database'],))
        result = cursor.fetchone()
        table_exists = result['count'] > 0
        
        if not table_exists:
            print("✓ store_stocks table does not exist - no update needed")
            return
        
        # Check current enum values
        cursor.execute("""
            SELECT COLUMN_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'store_stocks'
            AND COLUMN_NAME = 'status'
        """, (DB_CONFIG['database'],))
        result = cursor.fetchone()
        
        if result:
            current_enum = result['COLUMN_TYPE']
            print(f"Current enum definition: {current_enum}")
            
            # Check if already uppercase
            if "PENDING" in current_enum and "APPROVED" in current_enum:
                print("✓ Enum already uses uppercase values - no update needed")
                return
            
            # Update any existing data first (convert lowercase to uppercase)
            print("Updating existing data from lowercase to uppercase...")
            cursor.execute("""
                UPDATE store_stocks 
                SET status = UPPER(status)
                WHERE status IN ('pending', 'approved', 'rejected', 'expired')
            """)
            updated_rows = cursor.rowcount
            print(f"✓ Updated {updated_rows} rows")
            
            # Alter the enum column to use uppercase values
            print("Altering enum column to use uppercase values...")
            cursor.execute("""
                ALTER TABLE store_stocks 
                MODIFY COLUMN status ENUM('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED') 
                NOT NULL DEFAULT 'PENDING'
            """)
            print("✓ Updated enum column to use uppercase values")
        else:
            print("✓ status column not found - table may not have been created yet")


def migrate():
    """Migration function"""
    print("=" * 60)
    print("Update Store Stock Enum Migration Script")
    print("=" * 60)
    print()
    
    conn = None
    try:
        # Connect to database
        print("Connecting to database...")
        conn = pymysql.connect(**DB_CONFIG)
        print("✓ Connected to database")
        print()
        
        # Update enum
        print("Updating store_stocks enum...")
        update_store_stocks_enum(conn)
        print()
        
        # Commit changes
        conn.commit()
        print("✓ Migration completed successfully!")
        
    except pymysql.Error as e:
        print(f"\n✗ MySQL Error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
            print("Database connection closed")


if __name__ == '__main__':
    migrate()

