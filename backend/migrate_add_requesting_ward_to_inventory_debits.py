"""
Migration script to add requesting_ward field to inpatient_inventory_debits table (SQLite)
This preserves the original ward that requested inventory even after patient transfer
"""
import sqlite3
import os
import sys

def migrate():
    """Add requesting_ward field to inpatient_inventory_debits table (SQLite version)"""
    print("=" * 60)
    print("Migration: Add requesting_ward to inpatient_inventory_debits")
    print("=" * 60)
    print()
    
    # Get database path from environment or use default
    # Default SQLite path from config is "./hms.db" relative to backend directory
    db_path = os.getenv('SQLITE_DB_PATH', './hms.db')
    
    # If not an absolute path, make it relative to the backend directory (where this script is)
    if not os.path.isabs(db_path):
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, db_path)
    
    # Normalize the path (handle ./ and ../)
    db_path = os.path.normpath(db_path)
    
    if not os.path.exists(db_path):
        print("⚠ SQLite database not found. This migration is SQLite-specific.")
        print("  For MySQL, use migrate_add_requesting_ward_to_inventory_debits_mysql.py instead.")
        print("  Skipping this migration.")
        return
    
    # Initialize conn and cursor to None
    conn = None
    cursor = None
    
    try:
        # Connect to SQLite database
        print(f"Connecting to SQLite database at '{db_path}'...")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("✓ Connected to database")
        
        # Check if table exists first
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='inpatient_inventory_debits'
        """)
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("⚠ Table 'inpatient_inventory_debits' does not exist. Skipping migration.")
            print("This is normal if you're using MySQL in production.")
            return
        
        # Check if column already exists
        cursor.execute("""
            SELECT name 
            FROM pragma_table_info('inpatient_inventory_debits')
            WHERE name = 'requesting_ward'
        """)
        column_exists = cursor.fetchone() is not None
        
        if column_exists:
            print("✓ Column 'requesting_ward' already exists")
        else:
            # Add requesting_ward column
            print("Adding 'requesting_ward' column...")
            cursor.execute("""
                ALTER TABLE inpatient_inventory_debits 
                ADD COLUMN requesting_ward TEXT NOT NULL DEFAULT ''
            """)
            print("✓ Added 'requesting_ward' column")
            
            # Populate requesting_ward for existing records from ward_admissions
            print("Populating 'requesting_ward' for existing records...")
            cursor.execute("""
                UPDATE inpatient_inventory_debits 
                SET requesting_ward = (
                    SELECT ward 
                    FROM ward_admissions 
                    WHERE ward_admissions.id = inpatient_inventory_debits.ward_admission_id
                )
                WHERE requesting_ward = ''
            """)
            affected_rows = cursor.rowcount
            print(f"✓ Updated {affected_rows} existing records with requesting_ward")
        
        # Commit changes
        conn.commit()
        print("\n✓ Migration completed successfully!")
        print("=" * 60)
        
    except sqlite3.Error as e:
        print(f"\n✗ SQLite Error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    migrate()

