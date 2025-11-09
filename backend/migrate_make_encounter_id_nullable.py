"""
Migration script to make encounter_id nullable in investigations table
This allows direct walk-in services without a consultation/encounter

IMPORTANT: This migration is IDEMPOTENT and SAFE to run multiple times.
It checks if encounter_id is already nullable BEFORE doing any table operations.
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime

def migrate():
    """Make encounter_id nullable in investigations table - IDEMPOTENT VERSION"""
    # Get database path
    db_path = Path(__file__).parent / "hms.db"
    
    # Check if database exists
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # FIRST: Check if column already exists and is nullable (IDEMPOTENT CHECK)
        # This check happens BEFORE any table operations to prevent data loss
        cursor.execute("PRAGMA table_info(investigations)")
        columns = cursor.fetchall()
        encounter_id_col = next((col for col in columns if col[1] == "encounter_id"), None)
        
        if encounter_id_col:
            # Check if it's already nullable
            # In SQLite, column[3] is 0 for nullable, 1 for NOT NULL
            is_nullable = encounter_id_col[3] == 0
            
            if is_nullable:
                print("encounter_id is already nullable. Migration already applied - skipping.")
                # Clean up any leftover backup tables from previous failed attempts
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('investigations_old', 'investigations_backup')")
                leftover_tables = [row[0] for row in cursor.fetchall()]
                if leftover_tables:
                    print(f"Cleaning up leftover backup tables: {leftover_tables}")
                    for table in leftover_tables:
                        cursor.execute(f"DROP TABLE IF EXISTS {table}")
                    conn.commit()
                conn.close()
                return True
            
            print("Making encounter_id nullable in investigations table...")
            
            # Check if backup/old tables already exist (indicates incomplete migration)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('investigations_old', 'investigations_backup')")
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            if existing_tables:
                print(f"WARNING: Found existing backup tables: {existing_tables}")
                print("This may indicate a previous incomplete migration.")
                print("Attempting to recover from backup tables...")
                
                # Try to restore from old table if it exists
                if 'investigations_old' in existing_tables:
                    cursor.execute("SELECT COUNT(*) FROM investigations_old")
                    old_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM investigations")
                    new_count = cursor.fetchone()[0]
                    
                    if old_count > new_count:
                        print(f"Found {old_count} rows in old table vs {new_count} in new table. Restoring...")
                        # Restore from old table
                        cursor.execute("DROP TABLE IF EXISTS investigations")
                        cursor.execute("ALTER TABLE investigations_old RENAME TO investigations")
                        conn.commit()
                        print("Restored investigations table from old table. Re-running migration check...")
                        # Re-check nullability
                        cursor.execute("PRAGMA table_info(investigations)")
                        columns = cursor.fetchall()
                        encounter_id_col = next((col for col in columns if col[1] == "encounter_id"), None)
                        if encounter_id_col and encounter_id_col[3] == 0:
                            print("encounter_id is now nullable after restore. Migration complete.")
                            conn.close()
                            return True
                        # Continue with migration if still not nullable
                    else:
                        # Old table has same or fewer rows, drop it
                        cursor.execute("DROP TABLE IF EXISTS investigations_old")
                
                # Clean up backup tables
                for table in existing_tables:
                    if table != 'investigations_old':  # Already handled above
                        cursor.execute(f"DROP TABLE IF EXISTS {table}")
            
            # SQLite doesn't support MODIFY COLUMN directly
            # We need to recreate the table with the nullable column
            # First, create a timestamped backup of the data
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_table = f"investigations_backup_{timestamp}"
            
            cursor.execute(f"""
                CREATE TABLE {backup_table} AS 
                SELECT * FROM investigations
            """)
            print(f"Created backup table: {backup_table}")
            
            # Drop the old table if it exists
            cursor.execute("DROP TABLE IF EXISTS investigations_old")
            cursor.execute("""
                ALTER TABLE investigations RENAME TO investigations_old
            """)
            
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
            
            # Get count of rows in old table
            cursor.execute("SELECT COUNT(*) FROM investigations_old")
            old_count = cursor.fetchone()[0]
            print(f"Found {old_count} rows in old table to migrate")
            
            # Copy data back, ensuring required fields have values
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
            
            # Verify data was copied correctly
            cursor.execute("SELECT COUNT(*) FROM investigations")
            new_count = cursor.fetchone()[0]
            
            if new_count < old_count:
                print(f"ERROR: Data loss detected! Old table had {old_count} rows, new table has {new_count} rows")
                print("Rolling back migration...")
                conn.rollback()
                # Restore old table
                cursor.execute("DROP TABLE IF EXISTS investigations")
                cursor.execute("ALTER TABLE investigations_old RENAME TO investigations")
                conn.commit()
                print("Migration rolled back. Original table restored.")
                return False
            
            print(f"Data migration verified: {new_count} rows copied successfully")
            
            # Only drop old table if data migration was successful
            cursor.execute("DROP TABLE investigations_old")
            print("Dropped old investigations_old table")
            
            # Keep timestamped backup table for safety (don't drop it automatically)
            print(f"Backup table '{backup_table}' kept for safety.")
            print(f"You can drop it manually after verifying: DROP TABLE {backup_table}")
            
            conn.commit()
            print("Successfully made encounter_id nullable in investigations table")
            return True
        else:
            print("encounter_id column not found in investigations table")
            return False
            
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting migration: Make encounter_id nullable in investigations table")
    success = migrate()
    if success:
        print("Migration completed successfully")
    else:
        print("Migration failed")
        exit(1)

