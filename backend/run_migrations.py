"""
Centralized Migration Runner
Automatically detects and runs all new migrations in the correct order.

Usage:
    python run_migrations.py

This script will:
1. Check if migration_tracker table exists (create if not)
2. Scan for all migration files (migrate_*.py)
3. Filter out already executed migrations
4. Run new migrations in order
5. Record successful executions
"""

import sqlite3
import importlib.util
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

def get_db_path():
    """Get the database path"""
    script_dir = Path(__file__).parent
    db_path = script_dir / "hms.db"
    return db_path

def ensure_migration_tracker(conn):
    """Ensure migration_tracker table exists"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='migration_tracker'
    """)
    
    if cursor.fetchone() is None:
        print("Creating migration_tracker table...")
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

def get_executed_migrations(conn) -> set:
    """Get set of already executed migration names"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT migration_name FROM migration_tracker 
        WHERE status = 'success'
    """)
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

def record_migration(conn, migration_name: str, success: bool, error_message: str, execution_time_ms: int):
    """Record migration execution in tracker table"""
    cursor = conn.cursor()
    
    # Check if migration already exists in tracker
    cursor.execute("SELECT id FROM migration_tracker WHERE migration_name = ?", (migration_name,))
    existing = cursor.fetchone()
    
    if existing:
        # Update existing record
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
        cursor.execute("""
            INSERT INTO migration_tracker 
            (migration_name, execution_time_ms, status, error_message)
            VALUES (?, ?, ?, ?)
        """, (migration_name, execution_time_ms, 'success' if success else 'failed', error_message))
    
    conn.commit()

def run_all_migrations():
    """Main function to run all pending migrations"""
    db_path = get_db_path()
    
    if not db_path.exists():
        print(f"✗ Database not found at {db_path}")
        print("Please ensure the database file exists before running migrations.")
        return False
    
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    
    try:
        # Ensure migration tracker exists
        ensure_migration_tracker(conn)
        
        # Get already executed migrations
        executed = get_executed_migrations(conn)
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
            record_migration(conn, migration_file.name, success, error_msg, exec_time)
            
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
    db_path = get_db_path()
    
    if not db_path.exists():
        print(f"✗ Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    
    try:
        ensure_migration_tracker(conn)
        
        migration_files = find_migration_files()
        executed = get_executed_migrations(conn)
        
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
        executed_details = {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}
        
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
        db_path = get_db_path()
        if db_path.exists():
            conn = sqlite3.connect(str(db_path))
            try:
                ensure_migration_tracker(conn)
                executed = get_executed_migrations(conn)
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
    else:
        success = run_all_migrations()
        sys.exit(0 if success else 1)

