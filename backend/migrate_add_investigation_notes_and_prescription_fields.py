"""
Migration: Add notes field to investigations and new fields to prescriptions
- Add notes field to investigations table
- Add unit, frequency_value, and instructions fields to prescriptions table
"""
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path("hms.db")
    if not db_path.exists():
        print("Database file not found. Skipping migration.")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if notes column exists in investigations
        cursor.execute("PRAGMA table_info(investigations)")
        investigation_columns = [col[1] for col in cursor.fetchall()]
        
        if 'notes' not in investigation_columns:
            print("Adding 'notes' column to investigations table...")
            cursor.execute("ALTER TABLE investigations ADD COLUMN notes VARCHAR(1000)")
            print("✓ Added 'notes' column to investigations")
        else:
            print("✓ 'notes' column already exists in investigations")
        
        # Check prescription table columns
        cursor.execute("PRAGMA table_info(prescriptions)")
        prescription_columns = [col[1] for col in cursor.fetchall()]
        
        if 'unit' not in prescription_columns:
            print("Adding 'unit' column to prescriptions table...")
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN unit VARCHAR(50)")
            print("✓ Added 'unit' column to prescriptions")
        else:
            print("✓ 'unit' column already exists in prescriptions")
        
        if 'frequency_value' not in prescription_columns:
            print("Adding 'frequency_value' column to prescriptions table...")
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN frequency_value INTEGER")
            print("✓ Added 'frequency_value' column to prescriptions")
        else:
            print("✓ 'frequency_value' column already exists in prescriptions")
        
        if 'instructions' not in prescription_columns:
            print("Adding 'instructions' column to prescriptions table...")
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN instructions TEXT")
            print("✓ Added 'instructions' column to prescriptions")
        else:
            print("✓ 'instructions' column already exists in prescriptions")
        
        conn.commit()
        print("\nMigration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\nError during migration: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

