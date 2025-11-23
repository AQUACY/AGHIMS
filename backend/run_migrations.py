"""
Centralized Migration Runner
Automatically detects and runs all new migrations in the correct order.

Usage:
    python run_migrations.py

This script will:
1. Load database credentials from .env file
2. Check if migration_tracker table exists (create if not)
3. Scan for all migration files (migrate_*.py)
4. Filter out already executed migrations
5. Run new migrations in order
6. Record successful executions
"""

import importlib.util
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Union
import os

# Add app directory to path to import config
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.core.config import settings
except ImportError:
    print("Warning: Could not import settings. Using defaults.")
    # Fallback to environment variables or defaults
    class Settings:
        DATABASE_MODE = os.getenv("DATABASE_MODE", "sqlite")
        SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "./hms.db")
        MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
        MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
        MYSQL_USER = os.getenv("MYSQL_USER", "root")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
        MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "hms")
        MYSQL_CHARSET = os.getenv("MYSQL_CHARSET", "utf8mb4")
    
    settings = Settings()

def get_db_connection():
    """Get database connection based on DATABASE_MODE from .env"""
    if settings.DATABASE_MODE.lower() == "mysql":
        try:
            import pymysql
            conn = pymysql.connect(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                charset=settings.MYSQL_CHARSET,
                cursorclass=pymysql.cursors.DictCursor
            )
            print(f"Connected to MySQL: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
            return conn, "mysql"
        except ImportError:
            print("✗ Error: pymysql is required for MySQL connections")
            print("Install it with: pip install pymysql")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error connecting to MySQL: {e}")
            print(f"  Host: {settings.MYSQL_HOST}")
            print(f"  Port: {settings.MYSQL_PORT}")
            print(f"  User: {settings.MYSQL_USER}")
            print(f"  Database: {settings.MYSQL_DATABASE}")
            sys.exit(1)
    else:  # SQLite
        import sqlite3
        script_dir = Path(__file__).parent
        db_path = script_dir / settings.SQLITE_DB_PATH.lstrip("./")
        if not db_path.exists():
            print(f"✗ Database not found at {db_path}")
            print("Please ensure the database file exists before running migrations.")
            sys.exit(1)
        conn = sqlite3.connect(str(db_path))
        print(f"Connected to SQLite: {db_path}")
        return conn, "sqlite"

def ensure_migration_tracker(conn, db_type: str):
    """Ensure migration_tracker table exists"""
    cursor = conn.cursor()
    
    if db_type == "mysql":
        # Check if table exists in MySQL
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE() 
            AND table_name = 'migration_tracker'
        """)
        result = cursor.fetchone()
        table_exists = result['count'] > 0 if isinstance(result, dict) else result[0] > 0
    else:  # SQLite
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='migration_tracker'
        """)
        table_exists = cursor.fetchone() is not None
    
    if not table_exists:
        print("Creating migration_tracker table...")
        if db_type == "mysql":
            cursor.execute("""
                CREATE TABLE migration_tracker (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INT,
                    status VARCHAR(20) NOT NULL DEFAULT 'success',
                    error_message TEXT
                )
            """)
        else:  # SQLite
            cursor.execute("""
                CREATE TABLE migration_tracker (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    migration_name TEXT NOT NULL UNIQUE,
                    executed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    status TEXT NOT NULL DEFAULT 'success',
                    error_message TEXT
                )
            """)
        conn.commit()
        print("✓ Migration tracker table created")

def get_executed_migrations(conn, db_type: str) -> set:
    """Get set of already executed migration names"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT migration_name FROM migration_tracker 
        WHERE status = 'success'
    """)
    if db_type == "mysql":
        # MySQL returns dict-like rows
        return {row['migration_name'] for row in cursor.fetchall()}
    else:
        # SQLite returns tuples
        return {row[0] for row in cursor.fetchall()}

def find_migration_files() -> List[Path]:
    """Find all migration files in the backend directory"""
    script_dir = Path(__file__).parent
    migration_files = sorted(script_dir.glob("migrate_*.py"))
    # Exclude the tracker migration itself from auto-execution (it's special)
    return [f for f in migration_files if f.name != "migrate_create_migration_tracker.py"]

def load_migration_module(file_path: Path):
    """Load a migration module dynamically"""
    module_name = file_path.stem
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module {module_name}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def run_migration(conn, migration_file: Path) -> Tuple[bool, str, int]:
    """
    Run a single migration file
    
    Returns:
        (success: bool, error_message: str, execution_time_ms: int)
    """
    migration_name = migration_file.name
    start_time = datetime.now()
    
    try:
        print(f"\n{'='*60}")
        print(f"Running: {migration_name}")
        print(f"{'='*60}")
        
        # Load the migration module
        module = load_migration_module(migration_file)
        
        # Check if migrate function exists
        if not hasattr(module, 'migrate'):
            error_msg = f"Migration {migration_name} does not have a 'migrate()' function"
            print(f"✗ {error_msg}")
            return False, error_msg, 0
        
        # Run the migration
        module.migrate()
        
        end_time = datetime.now()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        print(f"✓ Successfully executed {migration_name} ({execution_time_ms}ms)")
        return True, "", execution_time_ms
        
    except Exception as e:
        end_time = datetime.now()
        execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
        error_msg = str(e)
        print(f"✗ Error executing {migration_name}: {error_msg}")
        return False, error_msg, execution_time_ms

def record_migration(conn, db_type: str, migration_name: str, success: bool, error_message: str, execution_time_ms: int):
    """Record migration execution in tracker table"""
    cursor = conn.cursor()
    
    # Check if migration already exists in tracker
    cursor.execute("SELECT id FROM migration_tracker WHERE migration_name = %s" if db_type == "mysql" else "SELECT id FROM migration_tracker WHERE migration_name = ?", (migration_name,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing record
        if db_type == "mysql":
            cursor.execute("""
                UPDATE migration_tracker 
                SET executed_at = CURRENT_TIMESTAMP,
                    execution_time_ms = %s,
                    status = %s,
                    error_message = %s
                WHERE migration_name = %s
            """, (execution_time_ms, 'success' if success else 'failed', error_message, migration_name))
        else:
            cursor.execute("""
                UPDATE migration_tracker 
                SET executed_at = CURRENT_TIMESTAMP,
                    execution_time_ms = ?,
                    status = ?,
                    error_message = ?
                WHERE migration_name = ?
            """, (execution_time_ms, 'success' if success else 'failed', error_message, migration_name))
    else:
        # Insert new record
        if db_type == "mysql":
            cursor.execute("""
                INSERT INTO migration_tracker 
                (migration_name, execution_time_ms, status, error_message)
                VALUES (%s, %s, %s, %s)
            """, (migration_name, execution_time_ms, 'success' if success else 'failed', error_message))
        else:
            cursor.execute("""
                INSERT INTO migration_tracker 
                (migration_name, execution_time_ms, status, error_message)
                VALUES (?, ?, ?, ?)
            """, (migration_name, execution_time_ms, 'success' if success else 'failed', error_message))
    
    conn.commit()

def run_all_migrations():
    """Main function to run all pending migrations"""
    print("="*60)
    print("MIGRATION RUNNER")
    print("="*60)
    print(f"Database Mode: {settings.DATABASE_MODE.upper()}")
    if settings.DATABASE_MODE.lower() == "mysql":
        print(f"  Host: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")
        print(f"  Database: {settings.MYSQL_DATABASE}")
        print(f"  User: {settings.MYSQL_USER}")
    else:
        print(f"  Path: {settings.SQLITE_DB_PATH}")
    print("="*60)
    print()
    
    try:
        conn, db_type = get_db_connection()
    except SystemExit:
        return False
    
    try:
        # Ensure migration tracker exists
        ensure_migration_tracker(conn, db_type)
        
        # Get already executed migrations
        executed = get_executed_migrations(conn, db_type)
        print(f"\nFound {len(executed)} already executed migrations")
        
        # Find all migration files
        migration_files = find_migration_files()
        print(f"Found {len(migration_files)} migration files")
        
        # Filter out already executed migrations
        pending_migrations = [
            f for f in migration_files 
            if f.name not in executed
        ]
        
        if not pending_migrations:
            print("\n✓ All migrations are up to date!")
            return True
        
        print(f"\nFound {len(pending_migrations)} pending migrations:")
        for migration in pending_migrations:
            print(f"  - {migration.name}")
        
        # Run pending migrations in order
        success_count = 0
        failed_count = 0
        
        for migration_file in pending_migrations:
            success, error_msg, exec_time = run_migration(conn, migration_file)
            record_migration(conn, db_type, migration_file.name, success, error_msg, exec_time)
            
            if success:
                success_count += 1
            else:
                failed_count += 1
                print(f"\n⚠ Migration {migration_file.name} failed. Continuing with remaining migrations...")
        
        # Summary
        print(f"\n{'='*60}")
        print("MIGRATION SUMMARY")
        print(f"{'='*60}")
        print(f"Total migrations: {len(pending_migrations)}")
        print(f"✓ Successful: {success_count}")
        if failed_count > 0:
            print(f"✗ Failed: {failed_count}")
        print(f"{'='*60}\n")
        
        return failed_count == 0
        
    except Exception as e:
        print(f"\n✗ Fatal error during migration process: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        conn.close()

def show_migration_status():
    """Show status of all migrations"""
    try:
        conn, db_type = get_db_connection()
    except SystemExit:
        return
    
    try:
        ensure_migration_tracker(conn, db_type)
        
        migration_files = find_migration_files()
        executed = get_executed_migrations(conn, db_type)
        
        print(f"\n{'='*60}")
        print("MIGRATION STATUS")
        print(f"{'='*60}")
        print(f"Total migration files: {len(migration_files)}")
        print(f"Executed: {len(executed)}")
        print(f"Pending: {len(migration_files) - len(executed)}")
        print(f"\n{'='*60}\n")
        
        # Show detailed status
        cursor = conn.cursor()
        cursor.execute("""
            SELECT migration_name, executed_at, status, execution_time_ms
            FROM migration_tracker
            ORDER BY executed_at
        """)
        rows = cursor.fetchall()
        if db_type == "mysql":
            executed_details = {row['migration_name']: (row['executed_at'], row['status'], row['execution_time_ms']) for row in rows}
        else:
            executed_details = {row[0]: (row[1], row[2], row[3]) for row in rows}
        
        for migration_file in migration_files:
            name = migration_file.name
            if name in executed:
                exec_time, status, time_ms = executed_details.get(name, ('', 'success', 0))
                status_icon = "✓" if status == 'success' else "✗"
                print(f"{status_icon} {name} - {exec_time} ({time_ms}ms)")
            else:
                print(f"○ {name} - PENDING")
        
        print(f"\n{'='*60}\n")
        
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run database migrations')
    parser.add_argument('--status', action='store_true', help='Show migration status only')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be run without executing')
    
    args = parser.parse_args()
    
    if args.status:
        show_migration_status()
    elif args.dry_run:
        try:
            conn, db_type = get_db_connection()
            try:
                ensure_migration_tracker(conn, db_type)
                executed = get_executed_migrations(conn, db_type)
                migration_files = find_migration_files()
                pending = [f for f in migration_files if f.name not in executed]
                
                print(f"\n{'='*60}")
                print("DRY RUN - Migrations that would be executed:")
                print(f"{'='*60}")
                for migration in pending:
                    print(f"  - {migration.name}")
                print(f"\nTotal: {len(pending)} migrations")
                print(f"{'='*60}\n")
            finally:
                conn.close()
        except SystemExit:
            pass
    else:
        success = run_all_migrations()
        sys.exit(0 if success else 1)

