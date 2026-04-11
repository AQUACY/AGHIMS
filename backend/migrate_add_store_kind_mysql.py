"""
Add store_kind to stores: pharmacy vs general (main store) for reporting and UI defaults.
Backfill: name contains 'pharmacy' (case-insensitive) -> pharmacy, else general.
"""
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
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


def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) AS c FROM information_schema.columns
                WHERE table_schema = %s AND table_name = 'stores' AND column_name = 'store_kind'
                """,
                (DB_CONFIG["database"],),
            )
            if cursor.fetchone()["c"] > 0:
                print("stores.store_kind already exists; skipping.")
                return

            print("Adding stores.store_kind ...")
            cursor.execute(
                """
                ALTER TABLE stores
                ADD COLUMN store_kind VARCHAR(32) NOT NULL DEFAULT 'general'
                AFTER description
                """
            )
            conn.commit()

            cursor.execute(
                """
                UPDATE stores
                SET store_kind = 'pharmacy'
                WHERE LOWER(name) LIKE %s
                """,
                ("%pharmacy%",),
            )
            updated = cursor.rowcount
            conn.commit()
            print(f"Backfill: marked {updated} row(s) as pharmacy by name pattern.")

        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
