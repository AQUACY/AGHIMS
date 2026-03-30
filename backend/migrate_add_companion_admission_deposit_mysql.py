"""
Add admission_deposit_* columns to companion_visits (MySQL).
Run from backend folder: python migrate_add_companion_admission_deposit_mysql.py
"""
import pymysql
import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST") or os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("DB_USER") or os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE", "hms"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}


def migrate():
    print("Adding admission_deposit columns to companion_visits (MySQL)...")
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = 'companion_visits'
                """,
                (DB_CONFIG["database"],),
            )
            existing = {row["column_name"] for row in cursor.fetchall()}

            columns_to_add = [
                ("admission_deposit_amount", "DOUBLE NULL"),
                ("admission_deposit_receipt_number", "VARCHAR(50) NULL"),
            ]

            for col_name, col_spec in columns_to_add:
                if col_name not in existing:
                    cursor.execute(
                        f"ALTER TABLE companion_visits ADD COLUMN {col_name} {col_spec}"
                    )
                    print(f"  + {col_name}")
                else:
                    print(f"  (exists) {col_name}")

            connection.commit()
        connection.close()
        print("Done.")
    except pymysql.Error as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    migrate()
