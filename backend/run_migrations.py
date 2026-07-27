"""
Run database migrations. Usage (from backend folder): python run_migrations.py

- Discovers all migrate_*.py scripts in the backend folder and runs them in sorted order.
- Tracks successful runs in migration_tracker so already-run migrations are skipped.
- Only runs migrations that define migrate() or upgrade(); others are skipped.
- Use the same app database (MySQL or SQLite) via app.core.database.engine.
"""
import importlib.util
import sys
import time
from pathlib import Path

# Add backend to path before importing app
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text

# Import engine after path is set
from app.core.database import engine


TRACKER_TABLE = "migration_tracker"
# Skip: we create the tracker table in this runner
SKIP_MIGRATIONS = {"migrate_create_migration_tracker"}


def should_skip_for_db(name: str, is_mysql: bool):
    """
    Return a skip reason when this script is for the other database dialect.
    - On MySQL: skip SQLite twins when a matching *_mysql.py exists.
    - On SQLite: skip *_mysql.py scripts.
    """
    if is_mysql:
        if not name.endswith("_mysql") and (backend_dir / f"{name}_mysql.py").exists():
            return f"sqlite-only twin; use {name}_mysql.py on MySQL"
    elif name.endswith("_mysql"):
        return "MySQL-only migration; skipped on SQLite"
    return None


def ensure_tracker_table(conn, is_mysql: bool):
    """Create migration_tracker table if it does not exist."""
    if is_mysql:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS migration_tracker (
                id INT AUTO_INCREMENT PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                executed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'success',
                error_message TEXT NULL
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS migration_tracker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT NOT NULL UNIQUE,
                executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER NULL,
                status TEXT NOT NULL DEFAULT 'success',
                error_message TEXT NULL
            )
        """))


def is_migration_success(conn, migration_name: str) -> bool:
    """Return True if this migration was already run successfully."""
    r = conn.execute(
        text("SELECT 1 FROM migration_tracker WHERE migration_name = :name AND status = 'success'"),
        {"name": migration_name},
    )
    return r.scalar() is not None


def record_migration(conn, migration_name: str, status: str, execution_time_ms: int, error_message: str = None):
    """Record migration result (delete existing row then insert so re-runs update status)."""
    conn.execute(text("DELETE FROM migration_tracker WHERE migration_name = :name"), {"name": migration_name})
    conn.execute(
        text("""
            INSERT INTO migration_tracker (migration_name, executed_at, execution_time_ms, status, error_message)
            VALUES (:name, CURRENT_TIMESTAMP, :ms, :status, :err)
        """),
        {"name": migration_name, "ms": execution_time_ms, "status": status, "err": error_message},
    )


def get_run_fn(mod):
    """Return migrate() or upgrade() if present (for backward compatibility)."""
    if callable(getattr(mod, "migrate", None)):
        return getattr(mod, "migrate")
    if callable(getattr(mod, "upgrade", None)):
        return getattr(mod, "upgrade")
    return None


def main():
    # On Windows, migration scripts often print ✓/✗; force UTF-8 stdout to avoid UnicodeEncodeError
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    db_url = str(engine.url)
    is_mysql = "mysql" in db_url.lower() or "pymysql" in db_url.lower()

    migration_files = sorted(backend_dir.glob("migrate_*.py"))
    if not migration_files:
        print("No migrate_*.py scripts found.")
        return 0

    print(f"Found {len(migration_files)} migration script(s). Checking tracker and running any not yet successful...\n")

    ran = 0
    skipped = 0
    failed = []
    no_fn = []

    with engine.connect() as conn:
        ensure_tracker_table(conn, is_mysql)
        conn.commit()

        for path in migration_files:
            name = path.stem
            if name in SKIP_MIGRATIONS:
                print(f"Skip (runner-managed): {name}")
                skipped += 1
                continue

            dialect_skip = should_skip_for_db(name, is_mysql)
            if dialect_skip:
                # Mark as success so old failed SQLite twins stop counting as Failed on MySQL prod
                if not is_migration_success(conn, name):
                    record_migration(conn, name, "success", 0, f"skipped: {dialect_skip}")
                    conn.commit()
                print(f"Skip (wrong DB dialect): {name} — {dialect_skip}")
                skipped += 1
                continue

            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                no_fn.append(name)
                continue
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            run_fn = get_run_fn(mod)
            if run_fn is None:
                no_fn.append(name)
                continue

            if is_migration_success(conn, name):
                print(f"Skip (already success): {name}")
                skipped += 1
                continue

            print(f"\n--- {name} ---")
            t0 = time.perf_counter()
            try:
                ok = run_fn()
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                if ok is False:
                    record_migration(conn, name, "failed", elapsed_ms, "migrate() returned False")
                    conn.commit()
                    failed.append(name)
                    print(f"FAIL: {name} (migrate returned False)")
                else:
                    record_migration(conn, name, "success", elapsed_ms, None)
                    conn.commit()
                    ran += 1
                    print(f"OK: {name} ({elapsed_ms} ms)")
            except Exception as e:
                elapsed_ms = int((time.perf_counter() - t0) * 1000)
                err_msg = str(e)
                record_migration(conn, name, "failed", elapsed_ms, err_msg)
                conn.commit()
                failed.append(name)
                print(f"FAIL: {name} - {e}")
                import traceback
                traceback.print_exc()

    print(f"\nRan: {ran}  Skipped (already success): {skipped}  Failed: {len(failed)}")
    if no_fn:
        print(f"Skipped (no migrate/upgrade): {len(no_fn)}")
    if failed:
        print("Failed:", ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
