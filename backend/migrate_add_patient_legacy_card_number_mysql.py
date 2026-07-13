"""
Migration: Add legacy_card_number to patients table (MySQL).
"""
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


def migrate():
    db_host = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT") or os.getenv("MYSQL_PORT", "3306"))
    db_name = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE", "hms")
    db_user = os.getenv("DB_USER") or os.getenv("MYSQL_USER", "root")
    db_password = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD", "")

    conn = pymysql.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
        charset="utf8mb4",
    )
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'patients'
            """,
            (db_name,),
        )
        columns = {row[0] for row in cursor.fetchall()}
        if "legacy_card_number" not in columns:
            cursor.execute(
                "ALTER TABLE patients ADD COLUMN legacy_card_number VARCHAR(50) NULL"
            )
            cursor.execute(
                "CREATE INDEX idx_patients_legacy_card_number ON patients (legacy_card_number)"
            )
            conn.commit()
            print("Added legacy_card_number column")
        else:
            print("legacy_card_number already exists")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
