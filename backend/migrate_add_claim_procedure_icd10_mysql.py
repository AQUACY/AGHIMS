"""
Migration: Add icd10 column to claim_procedures table (MySQL)
"""
import os
import sys
from pathlib import Path

# Load .env from script dir (backend) or parent (project root)
def _load_env():
    from dotenv import load_dotenv
    for base in [Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent]:
        env_path = base / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            return
    load_dotenv()

_load_env()

def migrate():
    print("Migration: claim_procedures.icd10 ...")
    sys.stdout.flush()
    try:
        import pymysql
    except ImportError:
        print("pymysql not installed. Install with: pip install pymysql")
        sys.exit(1)

    db_host = os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', 'localhost')
    db_user = os.getenv('DB_USER') or os.getenv('MYSQL_USER', 'root')
    db_name = os.getenv('DB_NAME') or os.getenv('MYSQL_DATABASE', 'hms')
    db_password = os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', '')

    print(f"Connecting to MySQL ({db_host}, database={db_name}) ...")
    sys.stdout.flush()

    # Use long timeouts for ALTER TABLE (can take minutes on busy/large DB)
    MIGRATION_QUERY_TIMEOUT = 600  # 10 minutes

    conn = None
    try:
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            charset='utf8mb4',
            connect_timeout=15,
            read_timeout=MIGRATION_QUERY_TIMEOUT,
            write_timeout=MIGRATION_QUERY_TIMEOUT
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_schema = %s AND table_name = 'claim_procedures' AND column_name = 'icd10'
        """, (db_name,))
        if cursor.fetchone()[0] > 0:
            print("Column claim_procedures.icd10 already exists. Skipping.")
        else:
            print("Adding icd10 column (ALTER TABLE may take 1–2 minutes on a busy server) ...")
            sys.stdout.flush()
            cursor.execute("ALTER TABLE claim_procedures ADD COLUMN icd10 VARCHAR(50) NULL AFTER gdrg_code")
            conn.commit()
            print("Added icd10 column to claim_procedures.")
        print("Done.")
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass  # Connection may already be dead after timeout
        print(f"Migration error: {e}")
        sys.exit(1)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

if __name__ == '__main__':
    migrate()
