"""
Link ClaimIT report batches to GHIMS XML import batches; link each error row to a GHIMS import item.
Adds: claimit_report_batches.ghims_import_batch_id, claimit_report_errors.ghims_import_item_id
Idempotent.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import engine
from sqlalchemy import text


def _has_column(conn, is_mysql: bool, table: str, column: str) -> bool:
    if is_mysql:
        r = conn.execute(
            text("""
                SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c
            """),
            {"t": table, "c": column},
        )
        return (r.scalar() or 0) > 0
    r = conn.execute(text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in r.fetchall())


def migrate():
    try:
        db_url = str(engine.url)
        is_mysql = "mysql" in db_url.lower() or "pymysql" in db_url.lower()
        is_sqlite = "sqlite" in db_url.lower()
        if not is_mysql and not is_sqlite:
            print(f"Unsupported database type: {db_url}")
            return False

        with engine.connect() as conn:
            # --- claimit_report_batches.ghims_import_batch_id ---
            if _has_column(conn, is_mysql, "claimit_report_batches", "ghims_import_batch_id"):
                print("claimit_report_batches.ghims_import_batch_id already exists.")
            else:
                print("Adding claimit_report_batches.ghims_import_batch_id...")
                if is_mysql:
                    conn.execute(text("""
                        ALTER TABLE claimit_report_batches
                        ADD COLUMN ghims_import_batch_id INT NULL
                    """))
                else:
                    conn.execute(text("""
                        ALTER TABLE claimit_report_batches
                        ADD COLUMN ghims_import_batch_id INTEGER NULL
                    """))
                try:
                    conn.execute(text("""
                        CREATE INDEX ix_claimit_report_batches_ghims_import_batch_id
                        ON claimit_report_batches(ghims_import_batch_id)
                    """))
                except Exception:
                    pass

            # --- claimit_report_errors.ghims_import_item_id ---
            if _has_column(conn, is_mysql, "claimit_report_errors", "ghims_import_item_id"):
                print("claimit_report_errors.ghims_import_item_id already exists.")
            else:
                print("Adding claimit_report_errors.ghims_import_item_id...")
                if is_mysql:
                    conn.execute(text("""
                        ALTER TABLE claimit_report_errors
                        ADD COLUMN ghims_import_item_id INT NULL
                    """))
                else:
                    conn.execute(text("""
                        ALTER TABLE claimit_report_errors
                        ADD COLUMN ghims_import_item_id INTEGER NULL
                    """))
                try:
                    conn.execute(text("""
                        CREATE INDEX ix_claimit_report_errors_ghims_import_item_id
                        ON claimit_report_errors(ghims_import_item_id)
                    """))
                except Exception:
                    pass

            conn.commit()
            print("Done: ClaimIT report <-> GHIMS link columns.")
            return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sys.exit(0 if migrate() else 1)
