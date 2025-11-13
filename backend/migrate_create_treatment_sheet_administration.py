"""
Migration: Create treatment_sheet_administrations table
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Create treatment_sheet_administrations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS treatment_sheet_administrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ward_admission_id INTEGER NOT NULL,
                prescription_id INTEGER NOT NULL,
                administration_date DATE NOT NULL,
                administration_time TIME NOT NULL,
                given_by INTEGER NOT NULL,
                signature VARCHAR(500),
                notes VARCHAR(1000),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
                FOREIGN KEY (prescription_id) REFERENCES inpatient_prescriptions(id),
                FOREIGN KEY (given_by) REFERENCES users(id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_treatment_sheet_ward_admission 
            ON treatment_sheet_administrations(ward_admission_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_treatment_sheet_prescription 
            ON treatment_sheet_administrations(prescription_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_treatment_sheet_date_time 
            ON treatment_sheet_administrations(administration_date, administration_time)
        """)
        
        conn.commit()
        print("✓ Created treatment_sheet_administrations table and indexes")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error creating treatment_sheet_administrations table: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()

