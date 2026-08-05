"""
Add claim ownership columns to claim_xml_import_items (MySQL).
Idempotent: treats duplicate column (1060) as success.
"""
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv()

COLS = [
    ("assigned_to_id", "INT NULL"),
    ("assigned_at", "DATETIME NULL"),
    ("assigned_by_id", "INT NULL"),
    ("assignment_note", "VARCHAR(255) NULL"),
]

BATCH_COLS = [
    ("demarcation_rules", "JSON NULL"),
]


def migrate():
    host = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST") or "127.0.0.1"
    port = int(os.getenv("DB_PORT") or os.getenv("MYSQL_PORT") or 3306)
    user = os.getenv("DB_USER") or os.getenv("MYSQL_USER") or "root"
    password = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD") or ""
    database = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB")
    if not database:
        print("DB_NAME / MYSQL_DATABASE not set", file=sys.stderr)
        sys.exit(1)

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            for name, typ in COLS:
                try:
                    cur.execute(
                        f"ALTER TABLE claim_xml_import_items ADD COLUMN {name} {typ}"
                    )
                    print(f"Added claim_xml_import_items.{name}")
                except pymysql.err.OperationalError as e:
                    if e.args and e.args[0] == 1060:
                        print(f"claim_xml_import_items.{name} already exists")
                    else:
                        raise
            for name, typ in BATCH_COLS:
                try:
                    cur.execute(
                        f"ALTER TABLE claim_xml_import_batches ADD COLUMN {name} {typ}"
                    )
                    print(f"Added claim_xml_import_batches.{name}")
                except pymysql.err.OperationalError as e:
                    if e.args and e.args[0] == 1060:
                        print(f"claim_xml_import_batches.{name} already exists")
                    else:
                        raise
        print("Claim ownership MySQL migration complete")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
