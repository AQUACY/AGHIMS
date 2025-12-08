"""
Migration: Add approved_quantity field to requisition_items table
This allows Pharmacy Head to approve partial quantities per item
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
    """Add approved_quantity column to requisition_items table"""
    print("=" * 60)
    print("Migration: Add approved_quantity to requisition_items")
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
                AND table_name = 'requisition_items'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                print("✗ Error: requisition_items table does not exist")
                print("  Please run the pharmacy requisition system migration first.")
                connection.close()
                return
            
            # Check if column already exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.columns 
                WHERE table_schema = %s 
                AND table_name = 'requisition_items'
                AND column_name = 'approved_quantity'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] > 0:
                print("✓ approved_quantity column already exists")
                connection.close()
                return
            
            print("Adding approved_quantity column to requisition_items table...")
            
            start_time = datetime.now()
            
            try:
                # Set a longer timeout for this operation
                cursor.execute("SET SESSION innodb_lock_wait_timeout = 300")
                cursor.execute("SET SESSION lock_wait_timeout = 300")
                
                # Add the approved_quantity column
                # Default to NULL, will be set when approved
                cursor.execute("""
                    ALTER TABLE requisition_items 
                    ADD COLUMN approved_quantity FLOAT NULL 
                    AFTER requested_quantity
                """)
                
                # For existing records, set approved_quantity to requested_quantity if requisition is approved
                cursor.execute("""
                    UPDATE requisition_items ri
                    INNER JOIN pharmacy_requisitions pr ON ri.requisition_id = pr.id
                    SET ri.approved_quantity = ri.requested_quantity
                    WHERE pr.status = 'approved'
                """)
                
                connection.commit()
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                print(f"✓ Successfully added approved_quantity column")
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

