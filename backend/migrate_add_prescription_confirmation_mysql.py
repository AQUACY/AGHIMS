"""
Migration: Add prescription confirmation fields (MySQL version)
Adds 'confirmed_by' and 'confirmed_at' columns to prescriptions table
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
    """Add confirmed_by and confirmed_at columns to prescriptions table"""
    print("=" * 60)
    print("Migration: Add prescription confirmation fields")
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
                AND table_name = 'prescriptions'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                print("⚠ prescriptions table does not exist, skipping")
                connection.close()
                return
            
            # Check if columns already exist
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_schema = %s 
                AND table_name = 'prescriptions'
                AND column_name IN ('confirmed_by', 'confirmed_at')
            """, (DB_CONFIG['database'],))
            
            existing_columns = {row['column_name'] for row in cursor.fetchall()}
            
            # Add confirmed_by column if it doesn't exist
            if 'confirmed_by' not in existing_columns:
                print("Adding confirmed_by column to prescriptions table...")
                cursor.execute("""
                    ALTER TABLE prescriptions 
                    ADD COLUMN confirmed_by INT NULL,
                    ADD FOREIGN KEY (confirmed_by) REFERENCES users(id)
                """)
                print("✓ Added 'confirmed_by' column to prescriptions table")
            else:
                print("✓ Column 'confirmed_by' already exists in prescriptions table")
            
            # Add confirmed_at column if it doesn't exist
            if 'confirmed_at' not in existing_columns:
                print("Adding confirmed_at column to prescriptions table...")
                cursor.execute("""
                    ALTER TABLE prescriptions 
                    ADD COLUMN confirmed_at DATETIME NULL
                """)
                print("✓ Added 'confirmed_at' column to prescriptions table")
            else:
                print("✓ Column 'confirmed_at' already exists in prescriptions table")
            
            connection.commit()
        
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

