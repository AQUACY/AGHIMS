"""
Migration script to create consultation_notes table
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    """Create consultation_notes table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='consultation_notes'")
        if cursor.fetchone():
            print("consultation_notes table already exists")
            conn.close()
            return
        
        print("Creating consultation_notes table...")
        cursor.execute("""
            CREATE TABLE consultation_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                encounter_id INTEGER NOT NULL UNIQUE,
                presenting_complaints TEXT,
                doctor_notes TEXT,
                follow_up_date DATE,
                created_by INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        # Create index on encounter_id
        cursor.execute("CREATE INDEX ix_consultation_notes_encounter_id ON consultation_notes(encounter_id)")
        
        conn.commit()
        print("Successfully created consultation_notes table")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

