"""
Migration script to add requesting_ward field to inpatient_inventory_debits table
This preserves the original ward that requested inventory even after patient transfer
"""
import pymysql
import os
import sys
from getpass import getpass

def migrate():
    # Get database connection details from environment or prompt
    db_host = os.getenv('DB_HOST', 'localhost')
    db_user = os.getenv('DB_USER', 'root')
    db_name = os.getenv('DB_NAME', 'hms')
    
    # Get password from environment or prompt
    db_password = os.getenv('DB_PASSWORD')
    if not db_password:
        db_password = getpass('Enter database password: ')
    
    # Initialize conn and cursor to None
    conn = None
    cursor = None
    
    try:
        # Connect to MySQL database
        print(f"Connecting to MySQL database '{db_name}' on {db_host}...")
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        if cursor is None:
            raise Exception("Failed to create database cursor")
        
        print("✓ Connected to database")
        
        # Check if table exists first
        try:
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'inpatient_inventory_debits'
            """, (db_name,))
            result = cursor.fetchone()
            table_exists = result is not None
        except Exception as e:
            print(f"Error checking table existence: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        if not table_exists:
            print("⚠ Table 'inpatient_inventory_debits' does not exist. Skipping migration.")
            print("This table may not be needed in your current setup.")
            return
        
        # Check if column already exists
        try:
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'inpatient_inventory_debits' 
                AND COLUMN_NAME = 'requesting_ward'
            """, (db_name,))
            result = cursor.fetchone()
            column_exists = result is not None
        except Exception as e:
            print(f"Error checking existing column: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        if column_exists:
            print("✓ Column 'requesting_ward' already exists")
        else:
            # Add requesting_ward column
            print("Adding 'requesting_ward' column...")
            cursor.execute("""
                ALTER TABLE inpatient_inventory_debits 
                ADD COLUMN requesting_ward VARCHAR(100) NOT NULL DEFAULT ''
            """)
            print("✓ Added 'requesting_ward' column")
            
            # Populate requesting_ward for existing records from ward_admissions
            print("Populating 'requesting_ward' for existing records...")
            cursor.execute("""
                UPDATE inpatient_inventory_debits iid
                INNER JOIN ward_admissions wa ON iid.ward_admission_id = wa.id
                SET iid.requesting_ward = wa.ward
                WHERE iid.requesting_ward = ''
            """)
            affected_rows = cursor.rowcount
            print(f"✓ Updated {affected_rows} existing records with requesting_ward")
        
        # Commit changes
        conn.commit()
        print("\n✓ Migration completed successfully!")
        
    except pymysql.Error as e:
        print(f"\n✗ MySQL Error during migration: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("Database connection closed")

if __name__ == '__main__':
    migrate()

