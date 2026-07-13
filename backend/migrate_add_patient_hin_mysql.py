"""
Migration: Add hin column to patients table (MySQL).
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
        if "hin" not in columns:
            cursor.execute("ALTER TABLE patients ADD COLUMN hin VARCHAR(100) NULL")
            conn.commit()
            print("Added hin column")
        else:
            print("hin already exists")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
