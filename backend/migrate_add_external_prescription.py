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
        cursor.execute("PRAGMA table_info(prescriptions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_external' not in columns:
            print("Adding is_external column to prescriptions table...")
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN is_external INTEGER DEFAULT 0")
            conn.commit()
            print("✓ Successfully added is_external column")
        else:
            print("✓ is_external column already exists")
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

