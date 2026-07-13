"""
Migration: Add other_names column to patients table (MySQL)
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


def migrate():
    """Migration entry point called by run_migrations.py"""
    # Get database connection details from environment (support both DB_* and MYSQL_*)
    db_host = os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT') or os.getenv('MYSQL_PORT', '3306'))
    db_name = os.getenv('DB_NAME') or os.getenv('MYSQL_DATABASE', 'hms')
    db_user = os.getenv('DB_USER') or os.getenv('MYSQL_USER', 'root')
    
    # Get password from environment (no prompting)
    db_password = os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', '')
    
    try:
        print(f"Connecting to MySQL database: {db_name}@{db_host}:{db_port}")
        conn = pymysql.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password,
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        # Check if patients table exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = 'patients'
        """, (db_name,))
        
        if cursor.fetchone()[0] == 0:
            print("Table patients does not exist. Skipping migration.")
            conn.close()
            return
        
        # Get existing columns
        print("Checking for 'other_names' column in patients table...")
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'patients'
        """, (db_name,))
        columns = {row[0] for row in cursor.fetchall()}
        
        # Add other_names column if not exists
        if "other_names" not in columns:
            print("Adding 'other_names' column to patients table...")
            cursor.execute("""
                ALTER TABLE patients
                ADD COLUMN other_names VARCHAR(255) NULL
            """)
            print("✓ Successfully added 'other_names' column")
        else:
            print("✓ Column 'other_names' already exists")
        
        conn.commit()
        conn.close()
        print("\n✓ Migration completed successfully!")
        
    except pymysql.Error as e:
        print(f"✗ MySQL Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"✗ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate()

