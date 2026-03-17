"""
Migration: Add is_super_admin column to users table (MySQL/SQLite compatible)
Super admin (ghost) accounts are not shown in staff list, leave no audit trail, and their actions are stored as system user.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text


def migrate():
    """Add is_super_admin column to users table (MySQL/SQLite compatible)"""
    try:
        db_url = str(engine.url)
        is_mysql = "mysql" in db_url.lower() or "pymysql" in db_url.lower()
        is_sqlite = "sqlite" in db_url.lower()

        if not is_mysql and not is_sqlite:
            print(f"Unsupported database type: {db_url}")
            return False

        table_name = "users"
        column_name = "is_super_admin"

        with engine.connect() as conn:
            if is_mysql:
                result = conn.execute(
                    text("""
                        SELECT COUNT(*) FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c
                    """),
                    {"t": table_name, "c": column_name},
                )
                exists = result.scalar() > 0
            else:
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                exists = any(row[1] == column_name for row in result.fetchall())

            if exists:
                print(f"Column '{column_name}' already exists in {table_name}")
                conn.commit()
                return True

            if is_mysql:
                conn.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} TINYINT(1) NOT NULL DEFAULT 0")
                )
            else:
                conn.execute(
                    text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} BOOLEAN NOT NULL DEFAULT 0")
                )
            conn.commit()
        print(f"Added column '{column_name}' to {table_name}")
        return True
    except Exception as e:
        print(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    migrate()
