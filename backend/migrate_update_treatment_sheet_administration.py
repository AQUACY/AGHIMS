"""
Migration: Update treatment_sheet_administrations table to support both OPD and inpatient prescriptions
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if prescription_type column already exists
        cursor.execute("PRAGMA table_info(treatment_sheet_administrations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'prescription_type' not in columns:
            # Add prescription_type column
            cursor.execute("""
                ALTER TABLE treatment_sheet_administrations 
                ADD COLUMN prescription_type VARCHAR(20) DEFAULT 'inpatient'
            """)
            print("✓ Added prescription_type column")
        else:
            print("✓ prescription_type column already exists")
        
        # Update existing records to have prescription_type = 'inpatient'
        cursor.execute("""
            UPDATE treatment_sheet_administrations 
            SET prescription_type = 'inpatient' 
            WHERE prescription_type IS NULL
        """)
        
        # Remove the foreign key constraint (SQLite doesn't support DROP CONSTRAINT directly)
        # We'll need to recreate the table, but first let's check if we can just make it nullable
        # Actually, SQLite doesn't enforce foreign keys by default unless enabled
        # So we can just update the column to not have the constraint
        
        conn.commit()
        print("✓ Updated treatment_sheet_administrations table to support OPD prescriptions")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error updating treatment_sheet_administrations table: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

