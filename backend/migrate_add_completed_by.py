"""
Migration: Add completed_by column to investigations table
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    """Add completed_by column to investigations table"""
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(investigations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'completed_by' in columns:
            print("Column 'completed_by' already exists in investigations table")
            conn.close()
            return True
        
        # Add completed_by column
        print("Adding 'completed_by' column to investigations table...")
        cursor.execute("""
            ALTER TABLE investigations 
            ADD COLUMN completed_by INTEGER
        """)
        
        conn.commit()
        print("Successfully added 'completed_by' column to investigations table")
        conn.close()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Error adding column: {e}")
        conn.close()
        return False

if __name__ == "__main__":
    success = migrate()
    exit(0 if success else 1)

