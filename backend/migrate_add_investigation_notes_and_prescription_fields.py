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
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='investigations'")
        has_investigations = cursor.fetchone() is not None
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prescriptions'")
        has_prescriptions = cursor.fetchone() is not None

        if not has_investigations and not has_prescriptions:
            print("Neither investigations nor prescriptions table exists yet. Skipping migration.")
            return

        # Check if notes column exists in investigations
        investigation_columns = []
        if has_investigations:
            cursor.execute("PRAGMA table_info(investigations)")
            investigation_columns = [col[1] for col in cursor.fetchall()]
        
        if has_investigations and 'notes' not in investigation_columns:
            print("Adding 'notes' column to investigations table...")
            cursor.execute("ALTER TABLE investigations ADD COLUMN notes VARCHAR(1000)")
            print("✓ Added 'notes' column to investigations")
        elif has_investigations:
            print("✓ 'notes' column already exists in investigations")
        else:
            print("⚠ investigations table does not exist, skipping notes column")
        
        # Check prescription table columns
        prescription_columns = []
        if has_prescriptions:
            cursor.execute("PRAGMA table_info(prescriptions)")
            prescription_columns = [col[1] for col in cursor.fetchall()]
        
        if has_prescriptions and 'unit' not in prescription_columns:
            print("Adding 'unit' column to prescriptions table...")
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN unit VARCHAR(50)")
            print("✓ Added 'unit' column to prescriptions")
        elif has_prescriptions:
            print("✓ 'unit' column already exists in prescriptions")
        
        if has_prescriptions and 'frequency_value' not in prescription_columns:
            print("Adding 'frequency_value' column to prescriptions table...")
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN frequency_value INTEGER")
            print("✓ Added 'frequency_value' column to prescriptions")
        elif has_prescriptions:
            print("✓ 'frequency_value' column already exists in prescriptions")
        
        if has_prescriptions and 'instructions' not in prescription_columns:
            print("Adding 'instructions' column to prescriptions table...")
            cursor.execute("ALTER TABLE prescriptions ADD COLUMN instructions TEXT")
            print("✓ Added 'instructions' column to prescriptions")
        elif has_prescriptions:
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

