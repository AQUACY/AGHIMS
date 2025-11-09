"""
SAFE Migration script to make encounter_id nullable in investigations table
This version is production-safe with extensive validation and rollback capability
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime

def migrate():
    """Make encounter_id nullable in investigations table - PRODUCTION SAFE VERSION"""
    # Get database path
    db_path = Path(__file__).parent / "hms.db"
    
    # Check if database exists
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    # Check if backup/old tables already exist (indicates incomplete migration)
    try:
        temp_conn = sqlite3.connect(str(db_path))
        temp_cursor = temp_conn.cursor()
        temp_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('investigations_old', 'investigations_backup')")
        existing_tables = [row[0] for row in temp_cursor.fetchall()]
        temp_conn.close()
        
        if existing_tables:
            print(f"WARNING: Found existing backup tables: {existing_tables}")
            print("This may indicate a previous incomplete migration.")
            print("Please clean up these tables first or use the recovery script.")
            return False
    except Exception as e:
        print(f"Warning: Could not check for existing tables: {e}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if column already exists and is nullable
        cursor.execute("PRAGMA table_info(investigations)")
        columns = cursor.fetchall()
        encounter_id_col = next((col for col in columns if col[1] == "encounter_id"), None)
        
        if encounter_id_col:
            # Check if it's already nullable
            # In SQLite, column[3] is 0 for nullable, 1 for NOT NULL
            is_nullable = encounter_id_col[3] == 0
            
            if is_nullable:
                print("encounter_id is already nullable. No migration needed.")
                return True
            
            print("Making encounter_id nullable in investigations table...")
            print("This is a SAFE migration with data validation.")
            
            # Get initial row count
            cursor.execute("SELECT COUNT(*) FROM investigations")
            initial_count = cursor.fetchone()[0]
            print(f"Initial row count: {initial_count}")
            
            if initial_count == 0:
                print("No data to migrate. Proceeding with table recreation...")
            else:
                print(f"Migrating {initial_count} rows...")
            
            # Create timestamped backup table
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_table = f"investigations_backup_{timestamp}"
            
            cursor.execute(f"""
                CREATE TABLE {backup_table} AS 
                SELECT * FROM investigations
            """)
            print(f"Created backup table: {backup_table}")
            
            # Verify backup
            cursor.execute(f"SELECT COUNT(*) FROM {backup_table}")
            backup_count = cursor.fetchone()[0]
            if backup_count != initial_count:
                print(f"ERROR: Backup verification failed! Expected {initial_count} rows, got {backup_count}")
                cursor.execute(f"DROP TABLE {backup_table}")
                conn.commit()
                return False
            print(f"Backup verified: {backup_count} rows")
            
            # Rename old table
            cursor.execute("DROP TABLE IF EXISTS investigations_old")
            cursor.execute("ALTER TABLE investigations RENAME TO investigations_old")
            
            # Create new table with nullable encounter_id
            cursor.execute("""
                CREATE TABLE investigations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    encounter_id INTEGER,
                    gdrg_code VARCHAR(50) NOT NULL,
                    procedure_name VARCHAR(500),
                    investigation_type VARCHAR(50) NOT NULL,
                    notes VARCHAR(1000),
                    price VARCHAR(50),
                    status VARCHAR(50) NOT NULL DEFAULT 'requested',
                    service_date DATETIME,
                    requested_by INTEGER NOT NULL,
                    confirmed_by INTEGER,
                    completed_by INTEGER,
                    cancelled_by INTEGER,
                    cancellation_reason VARCHAR(1000),
                    cancelled_at DATETIME,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                    FOREIGN KEY (requested_by) REFERENCES users(id),
                    FOREIGN KEY (confirmed_by) REFERENCES users(id),
                    FOREIGN KEY (completed_by) REFERENCES users(id),
                    FOREIGN KEY (cancelled_by) REFERENCES users(id)
                )
            """)
            print("Created new investigations table with nullable encounter_id")
            
            # Copy data back, ensuring required fields have values
            if initial_count > 0:
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
                """)
                
                rows_inserted = cursor.rowcount
                print(f"Inserted {rows_inserted} rows into new table")
                
                # Verify data was copied correctly
                cursor.execute("SELECT COUNT(*) FROM investigations")
                new_count = cursor.fetchone()[0]
                
                if new_count != initial_count:
                    print(f"ERROR: Data loss detected!")
                    print(f"  Initial count: {initial_count}")
                    print(f"  New count: {new_count}")
                    print("Rolling back migration...")
                    conn.rollback()
                    # Restore old table
                    cursor.execute("DROP TABLE IF EXISTS investigations")
                    cursor.execute("ALTER TABLE investigations_old RENAME TO investigations")
                    conn.commit()
                    print("Migration rolled back. Original table restored.")
                    print(f"Backup table '{backup_table}' is still available for manual recovery.")
                    return False
                
                print(f"Data migration verified: {new_count} rows (matches initial {initial_count} rows)")
            
            # Only drop old table if data migration was successful
            cursor.execute("DROP TABLE investigations_old")
            print("Dropped old investigations_old table")
            
            # Keep backup table for safety (don't drop it automatically)
            print(f"\n✓ Migration completed successfully!")
            print(f"✓ Backup table '{backup_table}' kept for safety")
            print(f"✓ You can drop it manually after verifying: DROP TABLE {backup_table}")
            
            conn.commit()
            return True
        else:
            print("encounter_id column not found in investigations table")
            return False
            
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
            # Try to restore old table if it exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='investigations_old'")
            if cursor.fetchone():
                print("Attempting to restore old table...")
                cursor.execute("DROP TABLE IF EXISTS investigations")
                cursor.execute("ALTER TABLE investigations_old RENAME TO investigations")
                conn.commit()
                print("Old table restored.")
        except Exception as restore_error:
            print(f"Could not restore old table: {restore_error}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("SAFE Migration: Make encounter_id nullable in investigations table")
    print("=" * 60)
    print("This script includes:")
    print("  - Data validation before and after migration")
    print("  - Automatic rollback on data loss")
    print("  - Timestamped backup tables")
    print("  - Production-safe error handling")
    print("=" * 60)
    print()
    
    success = migrate()
    if success:
        print("\n✓ Migration completed successfully")
    else:
        print("\n✗ Migration failed - database should be in original state")
        exit(1)

