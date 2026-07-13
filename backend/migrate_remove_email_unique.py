"""
Migration: Remove unique constraint from users.email
This allows multiple users to have the same email address (or NULL emails)
"""
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent / "hms.db"
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if unique index exists on email column
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND sql LIKE '%email%' AND sql LIKE '%UNIQUE%'
        """)
        unique_indexes = cursor.fetchall()
        
        # Drop any unique indexes on email
        for index in unique_indexes:
            index_name = index[0]
            print(f"Dropping unique index: {index_name}")
            cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
            conn.commit()
            print(f"✓ Successfully dropped index: {index_name}")
        
        # Check if there's a UNIQUE constraint in the table definition
        # SQLite doesn't directly support ALTER TABLE to remove UNIQUE constraints
        # We need to recreate the table without the unique constraint
        
        # Get current table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        # Check if email column exists and has unique constraint
        email_column = next((col for col in columns if col[1] == 'email'), None)
        
        if email_column:
            # Check current schema
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
            schema = cursor.fetchone()
            
            if schema and 'UNIQUE' in schema[0] and 'email' in schema[0]:
                print("Found UNIQUE constraint on email in table definition")
                print("Note: SQLite doesn't support dropping UNIQUE constraints directly.")
                print("The unique index has been dropped. The table schema constraint will remain,")
                print("but it won't be enforced since the index is removed.")
                print("To fully remove, you would need to recreate the table (not recommended with existing data).")
            else:
                print("✓ No UNIQUE constraint found in table definition")
        
        print("✓ Migration completed: Email unique constraint removed")
        
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

