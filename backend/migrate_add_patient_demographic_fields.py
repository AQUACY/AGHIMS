"""
Migration script to add emergency contact and demographic fields to patients table
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
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(patients)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ('emergency_contact_name', 'VARCHAR(255)'),
            ('emergency_contact_relationship', 'VARCHAR(100)'),
            ('emergency_contact_number', 'VARCHAR(100)'),
            ('marital_status', 'VARCHAR(50)'),
            ('educational_level', 'VARCHAR(100)'),
            ('occupation', 'VARCHAR(255)')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in columns:
                print(f"Adding {column_name} column to patients table...")
                cursor.execute(f"ALTER TABLE patients ADD COLUMN {column_name} {column_type}")
                conn.commit()
                print(f"✓ Successfully added {column_name} column")
            else:
                print(f"✓ {column_name} column already exists")
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

