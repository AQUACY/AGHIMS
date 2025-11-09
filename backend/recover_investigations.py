"""
Recovery script to restore investigations data from backup tables
"""
import sqlite3
from pathlib import Path

def recover():
    """Recover investigations data from backup/old tables"""
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'investigations%'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Found tables: {tables}")
        
        # Get column info from old table
        cursor.execute("PRAGMA table_info(investigations_old)")
        old_columns = cursor.fetchall()
        old_col_names = [col[1] for col in old_columns]
        print(f"Old table columns: {old_col_names}")
        
        # Get column info from new table
        cursor.execute("PRAGMA table_info(investigations)")
        new_columns = cursor.fetchall()
        new_col_names = [col[1] for col in new_columns]
        print(f"New table columns: {new_col_names}")
        
        # Count rows
        cursor.execute("SELECT COUNT(*) FROM investigations_old")
        old_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM investigations")
        new_count = cursor.fetchone()[0]
        print(f"Old table: {old_count} rows, New table: {new_count} rows")
        
        # Find common columns
        common_cols = [col for col in old_col_names if col in new_col_names]
        print(f"Common columns: {common_cols}")
        
        # Delete existing data in new table (keep only the 1 new one if needed)
        # Actually, let's just insert missing ones
        cursor.execute("""
            INSERT INTO investigations (
                id, encounter_id, gdrg_code, procedure_name, investigation_type,
                notes, price, status, service_date, requested_by,
                confirmed_by, completed_by, cancelled_by, cancellation_reason,
                cancelled_at, created_at
            )
            SELECT 
                id, 
                encounter_id, 
                COALESCE(gdrg_code, '') as gdrg_code,
                procedure_name,
                COALESCE(investigation_type, 'lab') as investigation_type,
                notes,
                price,
                COALESCE(status, 'requested') as status,
                service_date,
                requested_by,
                confirmed_by,
                completed_by,
                cancelled_by,
                cancellation_reason,
                cancelled_at,
                COALESCE(created_at, CURRENT_TIMESTAMP) as created_at
            FROM investigations_old
            WHERE id NOT IN (SELECT id FROM investigations)
        """)
        
        rows_inserted = cursor.rowcount
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM investigations")
        final_count = cursor.fetchone()[0]
        print(f"Recovery complete: Inserted {rows_inserted} rows. Total rows now: {final_count}")
        
        return True
        
    except Exception as e:
        print(f"Error during recovery: {str(e)}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting recovery of investigations data...")
    success = recover()
    if success:
        print("Recovery completed successfully")
    else:
        print("Recovery failed")
        exit(1)

