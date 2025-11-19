"""
Migration script to add release fields to inpatient_inventory_debits table (SQLite)
Adds: is_released, released_by, released_at columns
"""
import sqlite3
import os
import sys

def migrate():
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
        print(f"✗ Database file not found at: {db_path}")
        print("Please ensure the database file exists or set SQLITE_DB_PATH environment variable.")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
        sys.exit(1)
    
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
            conn.close()
            return
        
        # Check if columns already exist
        cursor.execute("""
            SELECT name 
            FROM pragma_table_info('inpatient_inventory_debits')
            WHERE name IN ('is_released', 'released_by', 'released_at')
        """)
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add is_released column if it doesn't exist
        if 'is_released' not in existing_columns:
            print("Adding 'is_released' column...")
            cursor.execute("""
                ALTER TABLE inpatient_inventory_debits 
                ADD COLUMN is_released INTEGER DEFAULT 0 NOT NULL
            """)
            print("✓ Added 'is_released' column")
        else:
            print("✓ Column 'is_released' already exists")
        
        # Add released_by column if it doesn't exist
        if 'released_by' not in existing_columns:
            print("Adding 'released_by' column...")
            cursor.execute("""
                ALTER TABLE inpatient_inventory_debits 
                ADD COLUMN released_by INTEGER NULL
            """)
            print("✓ Added 'released_by' column")
        else:
            print("✓ Column 'released_by' already exists")
        
        # Add released_at column if it doesn't exist
        if 'released_at' not in existing_columns:
            print("Adding 'released_at' column...")
            cursor.execute("""
                ALTER TABLE inpatient_inventory_debits 
                ADD COLUMN released_at TEXT NULL
            """)
            print("✓ Added 'released_at' column")
        else:
            print("✓ Column 'released_at' already exists")
        
        # SQLite doesn't support adding foreign key constraints via ALTER TABLE
        # Foreign keys are enforced at the application level or via table recreation
        # The foreign key relationship is already defined in the model
        
        # Commit changes
        conn.commit()
        print("\n✓ Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"\n✗ SQLite Error during migration: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("Database connection closed")

if __name__ == '__main__':
    migrate()

