"""
Migration/Cleanup Script: Remove GET request audit logs to reduce database size
This script deletes all audit logs where http_method = 'GET' to free up space.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text

def column_exists(conn, table_name: str, column_name: str, is_mysql: bool) -> bool:
    """Check if a column exists in a table"""
    try:
        if is_mysql:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = :table_name
                AND COLUMN_NAME = :column_name
            """), {"table_name": table_name, "column_name": column_name})
            return result.scalar() > 0
        else:
            # SQLite
            result = conn.execute(text(f"PRAGMA table_info({table_name})"))
            columns = [row[1] for row in result.fetchall()]
            return column_name in columns
    except Exception:
        return False

def get_audit_log_count(conn, http_method: Optional[str] = None, action: Optional[str] = None) -> int:
    """Get count of audit logs, optionally filtered by http_method or action"""
    if http_method:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM audit_logs WHERE http_method = :method
        """), {"method": http_method})
    elif action:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM audit_logs WHERE action = :action
        """), {"action": action})
    else:
        result = conn.execute(text("SELECT COUNT(*) FROM audit_logs"))
    return result.scalar() or 0

def cleanup_get_audit_logs(
    older_than_days: Optional[int] = None,
    dry_run: bool = False
) -> dict:
    """
    Clean up GET request audit logs from the database
    
    Args:
        older_than_days: If provided, only delete logs older than this many days. 
                        If None, delete all GET request logs.
        dry_run: If True, only count and report, don't actually delete
    
    Returns:
        dict with statistics about the cleanup
    """
    try:
        # Get database URL to determine database type
        db_url = str(engine.url)
        is_mysql = 'mysql' in db_url.lower() or 'pymysql' in db_url.lower()
        is_sqlite = 'sqlite' in db_url.lower()
        
        if not is_mysql and not is_sqlite:
            print(f"Unsupported database type: {db_url}")
            print("This cleanup script supports MySQL and SQLite only.")
            return {"success": False, "error": "Unsupported database type"}
        
        stats = {
            "success": False,
            "total_logs_before": 0,
            "get_logs_count": 0,
            "deleted_count": 0,
            "total_logs_after": 0,
            "dry_run": dry_run
        }
        
        with engine.connect() as conn:
            # Check if http_method column exists
            has_http_method_column = column_exists(conn, "audit_logs", "http_method", is_mysql)
            
            if not has_http_method_column:
                # Column doesn't exist - check if we can use action='VIEW' instead
                # (GET requests were logged as 'VIEW' before http_method column was added)
                has_action_column = column_exists(conn, "audit_logs", "action", is_mysql)
                
                if not has_action_column:
                    return {
                        "success": False,
                        "error": "Neither 'http_method' nor 'action' column exists in audit_logs table. Please run migrate_add_audit_log_endpoint_fields_mysql.py first."
                    }
                
                # Use action='VIEW' to identify GET requests (legacy approach)
                print("\n⚠ WARNING: 'http_method' column does not exist.")
                print("Using 'action=VIEW' to identify GET request logs (legacy method).")
                print("Consider running migrate_add_audit_log_endpoint_fields_mysql.py to add the http_method column.\n")
                
                use_action_filter = True
                filter_value = "VIEW"
            else:
                use_action_filter = False
                filter_value = "GET"
            
            # Get statistics before cleanup
            stats["total_logs_before"] = get_audit_log_count(conn)
            
            if use_action_filter:
                stats["get_logs_count"] = get_audit_log_count(conn, action=filter_value)
            else:
                stats["get_logs_count"] = get_audit_log_count(conn, http_method=filter_value)
            
            print(f"\n{'='*60}")
            print("AUDIT LOG CLEANUP - GET REQUEST LOGS")
            print(f"{'='*60}")
            print(f"Total audit logs in database: {stats['total_logs_before']:,}")
            print(f"GET request logs to delete: {stats['get_logs_count']:,}")
            
            if older_than_days:
                print(f"Filter: Only deleting logs older than {older_than_days} days")
            
            if dry_run:
                print("\n[DRY RUN MODE] - No logs will be deleted")
                stats["deleted_count"] = stats["get_logs_count"]
                stats["total_logs_after"] = stats["total_logs_before"] - stats["deleted_count"]
            else:
                # Build DELETE query
                if use_action_filter:
                    # Use action='VIEW' filter
                    if older_than_days:
                        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
                        delete_query = text("""
                            DELETE FROM audit_logs 
                            WHERE action = :filter_value 
                            AND timestamp < :cutoff_date
                        """)
                        result = conn.execute(delete_query, {"filter_value": filter_value, "cutoff_date": cutoff_date})
                    else:
                        delete_query = text("DELETE FROM audit_logs WHERE action = :filter_value")
                        result = conn.execute(delete_query, {"filter_value": filter_value})
                else:
                    # Use http_method='GET' filter
                    if older_than_days:
                        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
                        delete_query = text("""
                            DELETE FROM audit_logs 
                            WHERE http_method = :filter_value 
                            AND timestamp < :cutoff_date
                        """)
                        result = conn.execute(delete_query, {"filter_value": filter_value, "cutoff_date": cutoff_date})
                    else:
                        delete_query = text("DELETE FROM audit_logs WHERE http_method = :filter_value")
                        result = conn.execute(delete_query, {"filter_value": filter_value})
                
                stats["deleted_count"] = result.rowcount
                conn.commit()
                
                # Get statistics after cleanup
                stats["total_logs_after"] = get_audit_log_count(conn)
            
            print(f"\nDeleted logs: {stats['deleted_count']:,}")
            print(f"Remaining audit logs: {stats['total_logs_after']:,}")
            print(f"{'='*60}\n")
            
            stats["success"] = True
            return stats
            
    except Exception as e:
        print(f"Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def migrate(older_than_days: Optional[int] = None, dry_run: bool = False):
    """
    Main migration function - can be called from migration runner
    
    Args:
        older_than_days: If provided, only delete logs older than this many days
        dry_run: If True, only count and report, don't actually delete
    """
    return cleanup_get_audit_logs(older_than_days=older_than_days, dry_run=dry_run)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up GET request audit logs")
    parser.add_argument(
        "--older-than-days",
        type=int,
        default=None,
        help="Only delete logs older than this many days (optional)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only count and report, don't actually delete"
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Show what will be deleted
    print("\n" + "="*60)
    print("AUDIT LOG CLEANUP SCRIPT")
    print("="*60)
    print("This script will delete all GET request audit logs.")
    if args.older_than_days:
        print(f"Only logs older than {args.older_than_days} days will be deleted.")
    if args.dry_run:
        print("DRY RUN MODE: No logs will actually be deleted.")
    print("="*60)
    
    # Confirm before proceeding (unless --yes flag)
    if not args.yes and not args.dry_run:
        response = input("\nProceed with cleanup? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            print("Cleanup cancelled.")
            sys.exit(0)
    
    # Run cleanup
    result = cleanup_get_audit_logs(
        older_than_days=args.older_than_days,
        dry_run=args.dry_run
    )
    
    if result.get("success"):
        print("✓ Cleanup completed successfully!")
        sys.exit(0)
    else:
        print(f"✗ Cleanup failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

