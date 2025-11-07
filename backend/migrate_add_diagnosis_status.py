"""
Migration script to add diagnosis_status column to diagnoses table
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    """Add diagnosis_status column to diagnoses table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(diagnoses)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'diagnosis_status' in columns:
            print("diagnosis_status column already exists in diagnoses table")
            conn.close()
            return
        
        print("Adding diagnosis_status column to diagnoses table...")
        cursor.execute("""
            ALTER TABLE diagnoses 
            ADD COLUMN diagnosis_status VARCHAR(20)
        """)
        
        conn.commit()
        print("Successfully added diagnosis_status column to diagnoses table")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

