"""
Migration script to add finalized_by column to encounters table
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    """Add finalized_by column to encounters table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(encounters)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'finalized_by' in columns:
            print("finalized_by column already exists in encounters table")
            conn.close()
            return
        
        print("Adding finalized_by column to encounters table...")
        cursor.execute("""
            ALTER TABLE encounters 
            ADD COLUMN finalized_by INTEGER
        """)
        
        # Add foreign key constraint if possible (SQLite doesn't support adding FK constraints via ALTER TABLE)
        # The foreign key relationship is handled by SQLAlchemy
        
        conn.commit()
        print("Successfully added finalized_by column to encounters table")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

