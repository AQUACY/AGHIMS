"""
Migration: Change bill_items.quantity from Integer to Float
This allows fractional quantities for services like additional services (e.g., 6.15 hours)
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

def migrate():
    """Change bill_items.quantity column from Integer to Float"""
    print("=" * 60)
    print("Migration: Change bill_items.quantity to Float")
    print("=" * 60)
    print()
    
    try:
        # Connect to database
        print("Connecting to database...")
        connection = pymysql.connect(**DB_CONFIG)
        print("✓ Connected to database")
        print()
        
        with connection.cursor() as cursor:
            # Check if table exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = 'bill_items'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            table_exists = result['count'] > 0
            
            if not table_exists:
                print("✗ bill_items table does not exist")
                connection.close()
                return
            
            # Check current column type
            cursor.execute("""
                SELECT DATA_TYPE, COLUMN_TYPE
                FROM information_schema.columns 
                WHERE table_schema = %s 
                AND table_name = 'bill_items'
                AND column_name = 'quantity'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if not result:
                print("✗ quantity column not found in bill_items table")
                connection.close()
                return
            
            current_type = result['DATA_TYPE'].upper()
            column_type = result['COLUMN_TYPE']
            
            # Check if already Float/Double/Decimal
            if current_type in ['FLOAT', 'DOUBLE', 'DECIMAL', 'DOUBLE PRECISION']:
                print(f"✓ quantity column is already {current_type} ({column_type})")
                print("  No migration needed")
                connection.close()
                return
            
            print(f"Current column type: {column_type}")
            print("Changing bill_items.quantity from Integer to Decimal(10,2)...")
            print()
            print("⚠ WARNING: This operation may take some time on large tables.")
            print("  The table will be locked during the operation.")
            print()
            
            # Get row count for progress indication
            cursor.execute("SELECT COUNT(*) as count FROM bill_items")
            row_count = cursor.fetchone()['count']
            print(f"  Table has {row_count:,} rows")
            print()
            
            # For MySQL, use MODIFY COLUMN with proper type
            # Using DECIMAL instead of FLOAT for better precision
            start_time = datetime.now()
            
            try:
                # Set a longer timeout for this operation
                cursor.execute("SET SESSION innodb_lock_wait_timeout = 300")
                cursor.execute("SET SESSION lock_wait_timeout = 300")
                
                # Perform the ALTER TABLE operation
                # Using DECIMAL(10,2) for better precision than FLOAT
                cursor.execute("""
                    ALTER TABLE bill_items 
                    MODIFY COLUMN quantity DECIMAL(10,2) NOT NULL DEFAULT 1.0
                """)
                
                connection.commit()
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                print(f"✓ Successfully changed bill_items.quantity to DECIMAL(10,2)")
                print(f"  Operation completed in {duration:.2f} seconds")
                print()
                
            except pymysql.Error as e:
                connection.rollback()
                if e.args[0] == 1205:  # Lock wait timeout
                    print("✗ Error: Lock wait timeout exceeded")
                    print("  The table may be locked by another process.")
                    print("  Please try again when the table is not in use.")
                elif e.args[0] == 1213:  # Deadlock
                    print("✗ Error: Deadlock detected")
                    print("  Please retry the migration.")
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

