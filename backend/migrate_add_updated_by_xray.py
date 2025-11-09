"""
Migration: Add updated_by column to xray_results table
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    """Add updated_by column to xray_results table"""
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(xray_results)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'updated_by' in columns:
            print("Column 'updated_by' already exists in xray_results table")
            conn.close()
            return True
        
        # Add updated_by column
        print("Adding 'updated_by' column to xray_results table...")
        cursor.execute("""
            ALTER TABLE xray_results 
            ADD COLUMN updated_by INTEGER
        """)
        
        conn.commit()
        print("Successfully added 'updated_by' column to xray_results table")
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

