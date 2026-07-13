"""
Migration script to add procedure_name column to investigations table
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    """Add procedure_name column to investigations table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(investigations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'procedure_name' not in columns:
            print("Adding procedure_name column to investigations table...")
            cursor.execute("ALTER TABLE investigations ADD COLUMN procedure_name TEXT")
            conn.commit()
            print("Successfully added procedure_name column to investigations table")
        else:
            print("procedure_name column already exists in investigations table")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

