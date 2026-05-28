"""
Migration: Add flag_comment column to claim_xml_import_items (MySQL)

Run from backend folder:
  python migrate_add_flag_comment_to_claim_xml_import_items_mysql.py
"""
import os
import sys
from pathlib import Path


def _load_env():
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for base in [Path(__file__).resolve().parent, Path(__file__).resolve().parent.parent]:
        env_path = base / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return
    load_dotenv()


_load_env()


def migrate():
    print("Migration: claim_xml_import_items.flag_comment ...")
    sys.stdout.flush()

    try:
        import pymysql
    except ImportError:
        print("pymysql not installed. Install with: pip install pymysql")
        sys.exit(1)

    db_host = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST", "localhost")
    db_user = os.getenv("DB_USER") or os.getenv("MYSQL_USER", "root")
    db_name = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE", "hms")
    db_password = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD", "")

    print(f"Connecting to MySQL ({db_host}, database={db_name}) ...")
    sys.stdout.flush()

    conn = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_name,
        autocommit=True,
        connect_timeout=15,
        read_timeout=60,
        write_timeout=60,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                "ALTER TABLE claim_xml_import_items "
                "ADD COLUMN flag_comment VARCHAR(800) NULL"
            )
        print("Added claim_xml_import_items.flag_comment")
    except pymysql.err.OperationalError as e:
        # 1060: Duplicate column name
        if len(e.args) >= 1 and int(e.args[0]) == 1060:
            print("Column already exists. Nothing to do.")
            return
        raise
    finally:
        conn.close()

    print("Done.")


if __name__ == "__main__":
    migrate()

