"""
Create app_license_activation_log table (SQLite / MySQL).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text


def migrate():
    try:
        db_url = str(engine.url)
        is_mysql = "mysql" in db_url.lower() or "pymysql" in db_url.lower()
        is_sqlite = "sqlite" in db_url.lower()
        if not is_mysql and not is_sqlite:
            print(f"Unsupported database type: {db_url}")
            return False

        table = "app_license_activation_log"

        with engine.connect() as conn:
            if is_mysql:
                r = conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM information_schema.TABLES
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t
                        """
                    ),
                    {"t": table},
                )
                exists = r.scalar() > 0
            else:
                r = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
                    {"t": table},
                )
                exists = r.fetchone() is not None

            if exists:
                print(f"Table '{table}' already exists")
                conn.commit()
                return True

            if is_mysql:
                conn.execute(
                    text(
                        f"""
                        CREATE TABLE {table} (
                            id INTEGER AUTO_INCREMENT PRIMARY KEY,
                            activated_at DATETIME NOT NULL,
                            license_public_id VARCHAR(64) NOT NULL,
                            customer_label VARCHAR(255) NOT NULL DEFAULT '',
                            valid_until DATETIME NULL,
                            facility_code_in_license VARCHAR(64) NULL,
                            INDEX ix_license_log_license_id (license_public_id)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                        """
                    )
                )
            else:
                conn.execute(
                    text(
                        f"""
                        CREATE TABLE {table} (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            activated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                            license_public_id VARCHAR(64) NOT NULL,
                            customer_label VARCHAR(255) NOT NULL DEFAULT '',
                            valid_until TIMESTAMP NULL,
                            facility_code_in_license VARCHAR(64) NULL
                        )
                        """
                    )
                )
                conn.execute(
                    text(f"CREATE INDEX IF NOT EXISTS ix_license_log_license_id ON {table}(license_public_id)")
                )
            conn.commit()
        print(f"Created table '{table}'")
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate()
