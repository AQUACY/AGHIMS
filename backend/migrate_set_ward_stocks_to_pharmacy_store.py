"""
Migration: Set all ward_stocks records to Pharmacy store (store_id = 2)
This updates all existing ward_stocks records to use store_id = 2 (Pharmacy store)
since the main store is not being used yet.
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
    """Set all ward_stocks records to Pharmacy store (store_id = 2)"""
    print("=" * 60)
    print("Migration: Set all ward_stocks to Pharmacy store (store_id = 2)")
    print("=" * 60)
    print()
    
    PHARMACY_STORE_ID = 2
    
    try:
        connection = pymysql.connect(**DB_CONFIG)
        print("✓ Connected to database")
        print()
        
        with connection.cursor() as cursor:
            # Check if ward_stocks table exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = 'ward_stocks'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                print("⚠ ward_stocks table does not exist, skipping")
                connection.close()
                return
            
            # Check if store_id column exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.columns 
                WHERE table_schema = %s 
                AND table_name = 'ward_stocks'
                AND column_name = 'store_id'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                print("⚠ store_id column does not exist in ward_stocks table")
                print("  Run migrate_departments_and_stores_mysql.py first")
                connection.close()
                return
            
            # Check if Pharmacy store (id = 2) exists
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM stores
                WHERE id = %s
            """, (PHARMACY_STORE_ID,))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                print(f"⚠ Store with id {PHARMACY_STORE_ID} does not exist")
                print("  Please ensure the Pharmacy store is created first")
                connection.close()
                return
            
            # Count records that need updating
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM ward_stocks
                WHERE store_id IS NULL OR store_id != %s
            """, (PHARMACY_STORE_ID,))
            
            result = cursor.fetchone()
            records_to_update = result['count']
            
            if records_to_update == 0:
                print("✓ All ward_stocks records already have store_id = 2")
                connection.close()
                return
            
            print(f"Found {records_to_update} ward_stocks records to update")
            print(f"Setting all records to store_id = {PHARMACY_STORE_ID} (Pharmacy store)")
            print()
            
            # Update all records to store_id = 2
            cursor.execute("""
                UPDATE ward_stocks
                SET store_id = %s
                WHERE store_id IS NULL OR store_id != %s
            """, (PHARMACY_STORE_ID, PHARMACY_STORE_ID))
            
            updated_count = cursor.rowcount
            connection.commit()
            
            print(f"✓ Successfully updated {updated_count} ward_stocks records")
            print(f"  All records now have store_id = {PHARMACY_STORE_ID} (Pharmacy store)")
            print()
            
            # Verify the update
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM ward_stocks
                WHERE store_id = %s
            """, (PHARMACY_STORE_ID,))
            
            result = cursor.fetchone()
            total_with_pharmacy_store = result['count']
            
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM ward_stocks
            """)
            
            result = cursor.fetchone()
            total_records = result['count']
            
            print(f"Verification:")
            print(f"  Total ward_stocks records: {total_records}")
            print(f"  Records with store_id = {PHARMACY_STORE_ID}: {total_with_pharmacy_store}")
            
            if total_records == total_with_pharmacy_store:
                print("✓ All records successfully updated!")
            else:
                print(f"⚠ Warning: {total_records - total_with_pharmacy_store} records still have different store_id")
        
        connection.close()
        print()
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

