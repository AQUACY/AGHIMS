"""
Migration: Add completed_at and completed_by_id to claimit_report_errors (MySQL/SQLite).
Idempotent: skips if columns already exist.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import engine
from sqlalchemy import text


def migrate():
    """Add completed_at and completed_by_id to claimit_report_errors."""
    try:
        db_url = str(engine.url)
        is_mysql = "mysql" in db_url.lower() or "pymysql" in db_url.lower()
        is_sqlite = "sqlite" in db_url.lower()

        if not is_mysql and not is_sqlite:
            print(f"Unsupported database type: {db_url}")
            return False

        with engine.connect() as conn:
            table = "claimit_report_errors"

            if is_mysql:
                r = conn.execute(text("""
                    SELECT COUNT(*) FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = 'completed_at'
                """), {"t": table})
                has_column = r.scalar() > 0
            else:
                r = conn.execute(text("PRAGMA table_info(claimit_report_errors)"))
                has_column = any(row[1] == "completed_at" for row in r.fetchall())

            if has_column:
                print("claimit_report_errors: completed_at / completed_by_id already exist, skipping.")
                return True

            print("Adding completed_at and completed_by_id to claimit_report_errors...")
            if is_mysql:
                conn.execute(text("""
                    ALTER TABLE claimit_report_errors
                    ADD COLUMN completed_at DATETIME NULL,
                    ADD COLUMN completed_by_id INT NULL
                """))
                # Add FK separately (may fail if already exists)
                try:
                    conn.execute(text("""
                        ALTER TABLE claimit_report_errors
                        ADD CONSTRAINT fk_claimit_report_errors_completed_by
                        FOREIGN KEY (completed_by_id) REFERENCES users(id) ON DELETE SET NULL
                    """))
                except Exception as e:
                    if "Duplicate foreign key" in str(e) or "already exists" in str(e).lower():
                        pass
                    else:
                        raise
            else:
                conn.execute(text("""
                    ALTER TABLE claimit_report_errors
                    ADD COLUMN completed_at DATETIME NULL
                """))
                conn.execute(text("""
                    ALTER TABLE claimit_report_errors
                    ADD COLUMN completed_by_id INTEGER NULL
                """))
                try:
                    conn.execute(text("""
                        CREATE INDEX ix_claimit_report_errors_completed_by_id
                        ON claimit_report_errors(completed_by_id)
                    """))
                except Exception:
                    pass

            conn.commit()
            print("Done: claimit_report_errors completed_at / completed_by_id added.")
            return True

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
