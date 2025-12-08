"""
Migration: add extended vitals fields (MySQL version)
Fields: respiration, bmi, spo2, rbs, fbs, upt, rdt_malaria, retro_rdt
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
    """Add extended vitals fields"""
    print("=" * 60)
    print("Migration: Add extended vitals fields")
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
                AND table_name = 'vitals'
            """, (DB_CONFIG['database'],))
            
            result = cursor.fetchone()
            if result['count'] == 0:
                print("⚠ vitals table does not exist, skipping")
                connection.close()
                return
            
            # Get existing columns
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_schema = %s 
                AND table_name = 'vitals'
            """, (DB_CONFIG['database'],))
            
            existing_columns = {row['column_name'] for row in cursor.fetchall()}
            
            # Columns to add
            columns_to_add = [
                ('respiration', 'INTEGER'),
                ('bmi', 'FLOAT'),
                ('spo2', 'INTEGER'),
                ('rbs', 'FLOAT'),
                ('fbs', 'FLOAT'),
                ('upt', 'TEXT'),
                ('rdt_malaria', 'TEXT'),
                ('retro_rdt', 'TEXT'),
            ]
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_columns:
                    print(f"Adding {col_name} column to vitals table...")
                    cursor.execute(f"""
                        ALTER TABLE vitals 
                        ADD COLUMN {col_name} {col_type} NULL
                    """)
                    print(f"✓ Added {col_name} column")
                else:
                    print(f"✓ Column {col_name} already exists")
            
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

