"""
Migration script to add blood_processing_fee_gdrg_code column to blood_transfusion_types table (MySQL version)
"""
import pymysql
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from current directory
    load_dotenv()

def migrate():
    # Get database connection details from environment (support both DB_* and MYSQL_*)
    db_host = os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', 'localhost')
    db_user = os.getenv('DB_USER') or os.getenv('MYSQL_USER', 'root')
    db_name = os.getenv('DB_NAME') or os.getenv('MYSQL_DATABASE', 'hms')
    
    # Get password from environment (no prompting)
    db_password = os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', '')
    
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
        
        # Check if table exists
        try:
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'blood_transfusion_types'
            """, (db_name,))
            result = cursor.fetchone()
            table_exists = result is not None
        except Exception as e:
            print(f"Error checking table existence: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        if not table_exists:
            print("✗ Error: Table 'blood_transfusion_types' does not exist.")
            print("Please run 'migrate_create_blood_transfusion_tables.py' first.")
            sys.exit(1)
        
        # Check if column already exists
        try:
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'blood_transfusion_types'
                AND COLUMN_NAME = 'blood_processing_fee_gdrg_code'
            """, (db_name,))
            result = cursor.fetchone()
            column_exists = result is not None
        except Exception as e:
            print(f"Error checking column existence: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        if column_exists:
            print("✓ Column 'blood_processing_fee_gdrg_code' already exists in 'blood_transfusion_types' table")
        else:
            # Add blood_processing_fee_gdrg_code column
            print("Adding 'blood_processing_fee_gdrg_code' column to 'blood_transfusion_types' table...")
            cursor.execute("""
                ALTER TABLE blood_transfusion_types 
                ADD COLUMN blood_processing_fee_gdrg_code VARCHAR(50) NULL
                AFTER unit_type
            """)
            print("✓ Added 'blood_processing_fee_gdrg_code' column to 'blood_transfusion_types' table")
        
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

