"""
Migration script to add anaesthetist fields to inpatient_surgeries table (MySQL version)
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
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = 'inpatient_surgeries'
            """, (db_name,))
            table_exists = cursor.fetchone()[0] > 0
            
            if not table_exists:
                print("✗ Table 'inpatient_surgeries' does not exist. Please create it first.")
                return False
        except Exception as e:
            print(f"✗ Error checking table existence: {e}")
            return False
        
        print("✓ Table 'inpatient_surgeries' exists")
        
        # List of columns to add
        columns_to_add = [
            {
                'name': 'anaesthetist_consultation',
                'type': 'TEXT',
                'after': 'completed_by'
            },
            {
                'name': 'intra_operation_care',
                'type': 'TEXT',
                'after': 'anaesthetist_consultation'
            },
            {
                'name': 'post_operation_care',
                'type': 'TEXT',
                'after': 'intra_operation_care'
            },
            {
                'name': 'drugs_given',
                'type': 'TEXT',
                'after': 'post_operation_care'
            },
            {
                'name': 'anaesthesia_used',
                'type': 'TEXT',
                'after': 'drugs_given'
            }
        ]
        
        # Check and add each column
        for col in columns_to_add:
            try:
                # Check if column exists
                cursor.execute("""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_schema = %s 
                    AND table_name = 'inpatient_surgeries' 
                    AND column_name = %s
                """, (db_name, col['name']))
                column_exists = cursor.fetchone()[0] > 0
                
                if column_exists:
                    print(f"✓ Column '{col['name']}' already exists in 'inpatient_surgeries' table")
                else:
                    print(f"Adding column '{col['name']}' to 'inpatient_surgeries' table...")
                    cursor.execute(f"""
                        ALTER TABLE inpatient_surgeries
                        ADD COLUMN {col['name']} {col['type']} NULL AFTER {col['after']}
                    """)
                    print(f"✓ Added column '{col['name']}' to 'inpatient_surgeries' table")
            except Exception as e:
                print(f"✗ Error adding column '{col['name']}': {e}")
                # Continue with other columns even if one fails
        
        # Commit changes
        conn.commit()
        print("\n✓ Migration completed successfully!")
        return True
        
    except pymysql.Error as e:
        print(f"\n✗ MySQL Error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("✓ Database connection closed")

if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add Anaesthetist Fields to Inpatient Surgeries")
    print("=" * 60)
    print()
    
    success = migrate()
    
    if success:
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("Migration failed. Please check the errors above.")
        print("=" * 60)
        sys.exit(1)

