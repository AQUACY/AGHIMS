"""
Migration script to add blood_type column to blood_transfusion_requests table (MySQL version)
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
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = %s
                AND table_name = 'blood_transfusion_requests'
            """, (db_name,))
            
            table_exists = cursor.fetchone()[0] > 0
            
            if not table_exists:
                print("Error: Table 'blood_transfusion_requests' does not exist")
                conn.close()
                sys.exit(1)
        except Exception as e:
            print(f"Error checking if table exists: {e}")
            conn.close()
            sys.exit(1)
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'blood_transfusion_requests'
            AND column_name = 'blood_type'
        """, (db_name,))
        
        column_exists = cursor.fetchone()[0] > 0
        
        if column_exists:
            print("✓ Column 'blood_type' already exists in 'blood_transfusion_requests' table")
        else:
            print("Adding 'blood_type' column to 'blood_transfusion_requests' table...")
            cursor.execute("""
                ALTER TABLE blood_transfusion_requests
                ADD COLUMN blood_type VARCHAR(5) NULL
                AFTER transfusion_type_id
            """)
            conn.commit()
            print("✓ Added 'blood_type' column to 'blood_transfusion_requests' table")
        
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        
        conn.close()
        
    except pymysql.Error as e:
        print(f"\nMySQL Error: {e}")
        if conn:
            conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        if conn:
            conn.close()
        sys.exit(1)

if __name__ == "__main__":
    migrate()

