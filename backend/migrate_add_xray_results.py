"""
Migration script to create xray_results table
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    """Create xray_results table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='xray_results'")
        if cursor.fetchone():
            print("xray_results table already exists")
            conn.close()
            return
        
        print("Creating xray_results table...")
        cursor.execute("""
            CREATE TABLE xray_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id INTEGER NOT NULL UNIQUE,
                results_text TEXT,
                attachment_path TEXT,
                entered_by INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (investigation_id) REFERENCES investigations(id),
                FOREIGN KEY (entered_by) REFERENCES users(id)
            )
        """)
        
        # Create index on investigation_id
        cursor.execute("CREATE INDEX ix_xray_results_investigation_id ON xray_results(investigation_id)")
        
        conn.commit()
        print("Successfully created xray_results table")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

