"""Add analysis_mode to ai_claim_vetting_jobs (MySQL). Idempotent."""
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv()


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
        host=host, port=port, user=user, password=password, database=database,
        charset="utf8mb4", autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "ALTER TABLE ai_claim_vetting_jobs "
                    "ADD COLUMN analysis_mode VARCHAR(20) NOT NULL DEFAULT 'standard'"
                )
                print("Added ai_claim_vetting_jobs.analysis_mode")
            except pymysql.err.OperationalError as e:
                if e.args and e.args[0] == 1060:
                    print("analysis_mode already exists")
                else:
                    raise
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
