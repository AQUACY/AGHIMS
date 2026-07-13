"""
Add admission_deposit_applied / admission_deposit_line_receipt to companion_visit_items (MySQL).
Backfills rows previously paid 100%% from admission deposit so synthetic receipt moves to line_receipt.

Run from backend folder: python migrate_add_companion_item_admission_split_mysql.py
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
    print("Adding admission split columns to companion_visit_items (MySQL)...")
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM information_schema.tables
                WHERE table_schema = %s AND table_name = 'companion_visit_items'
                """,
                (DB_CONFIG["database"],),
            )
            exists_row = cursor.fetchone() or {}
            if int(exists_row.get("cnt") or 0) == 0:
                print("SKIP: companion_visit_items table does not exist yet.")
                return

            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = 'companion_visit_items'
                """,
                (DB_CONFIG["database"],),
            )
            existing = {
                row.get("column_name") or row.get("COLUMN_NAME")
                for row in cursor.fetchall()
            }
            existing.discard(None)

            for col_name, col_spec in [
                ("admission_deposit_applied", "DOUBLE NULL"),
                ("admission_deposit_line_receipt", "VARCHAR(50) NULL"),
            ]:
                if col_name not in existing:
                    cursor.execute(
                        f"ALTER TABLE companion_visit_items ADD COLUMN {col_name} {col_spec}"
                    )
                    print(f"  + {col_name}")
                else:
                    print(f"  (exists) {col_name}")

            # Backfill legacy full-deposit lines
            cursor.execute(
                """
                UPDATE companion_visit_items
                SET admission_deposit_applied = (unit_price * quantity),
                    admission_deposit_line_receipt = receipt_number
                WHERE payment_method = 'admission_deposit'
                  AND COALESCE(cancelled, 0) = 0
                  AND receipt_number IS NOT NULL
                  AND admission_deposit_applied IS NULL
                """
            )
            n = cursor.rowcount
            if n:
                print(f"  backfilled admission_deposit_applied on {n} row(s)")

            cursor.execute(
                """
                UPDATE companion_visit_items
                SET receipt_number = NULL
                WHERE payment_method = 'admission_deposit'
                  AND admission_deposit_line_receipt IS NOT NULL
                  AND admission_deposit_applied IS NOT NULL
                """
            )
            n2 = cursor.rowcount
            if n2:
                print(f"  cleared duplicate receipt_number on {n2} row(s) (synthetic now on line_receipt)")

            connection.commit()
        connection.close()
        print("Done.")
    except pymysql.Error as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    migrate()
