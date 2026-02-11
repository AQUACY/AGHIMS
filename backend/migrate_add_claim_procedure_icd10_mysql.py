"""
Migration: Add icd10 column to claim_procedures table (MySQL)
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

def migrate():
    try:
        import pymysql
    except ImportError:
        print("pymysql not installed. Install with: pip install pymysql")
        sys.exit(1)

    db_host = os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', 'localhost')
    db_user = os.getenv('DB_USER') or os.getenv('MYSQL_USER', 'root')
    db_name = os.getenv('DB_NAME') or os.getenv('MYSQL_DATABASE', 'hms')
    db_password = os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', '')

    conn = None
    try:
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            charset='utf8mb4'
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = %s AND table_name = 'claim_procedures' AND column_name = 'icd10'
        """, (db_name,))
        if cursor.fetchone()[0] > 0:
            print("Column claim_procedures.icd10 already exists. Skipping.")
        else:
            cursor.execute("ALTER TABLE claim_procedures ADD COLUMN icd10 VARCHAR(50) NULL AFTER gdrg_code")
            conn.commit()
            print("Added icd10 column to claim_procedures.")
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Migration error: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate()
