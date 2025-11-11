"""
Migration: Create tables for inpatient documentation
- nurse_notes
- nurse_mid_documentations
- inpatient_vitals
- inpatient_clinical_reviews
"""
import sqlite3
from pathlib import Path

# Get database path
db_path = Path(__file__).parent / "hms.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create nurse_notes table
    print("Creating nurse_notes table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nurse_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_admission_id INTEGER NOT NULL,
            notes TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    print("Successfully created nurse_notes table")
    
    # Create nurse_mid_documentations table
    print("Creating nurse_mid_documentations table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nurse_mid_documentations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_admission_id INTEGER NOT NULL,
            documentation TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    print("Successfully created nurse_mid_documentations table")
    
    # Create inpatient_vitals table
    print("Creating inpatient_vitals table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inpatient_vitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_admission_id INTEGER NOT NULL,
            temperature REAL,
            blood_pressure_systolic INTEGER,
            blood_pressure_diastolic INTEGER,
            pulse INTEGER,
            respiratory_rate INTEGER,
            oxygen_saturation REAL,
            weight REAL,
            height REAL,
            bmi REAL,
            notes TEXT,
            recorded_by INTEGER NOT NULL,
            recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
            FOREIGN KEY (recorded_by) REFERENCES users(id)
        )
    """)
    print("Successfully created inpatient_vitals table")
    
    # Create inpatient_clinical_reviews table
    print("Creating inpatient_clinical_reviews table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inpatient_clinical_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_admission_id INTEGER NOT NULL,
            review_notes TEXT,
            reviewed_by INTEGER NOT NULL,
            reviewed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
            FOREIGN KEY (reviewed_by) REFERENCES users(id)
        )
    """)
    print("Successfully created inpatient_clinical_reviews table")
    
    # Remove old columns from ward_admissions if they exist
    print("Checking for old columns in ward_admissions...")
    cursor.execute("PRAGMA table_info(ward_admissions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    columns_to_remove = ['clinical_review', 'nurses_notes', 'nurses_mid_documentation']
    for col in columns_to_remove:
        if col in columns:
            print(f"Note: Column '{col}' exists in ward_admissions. It will remain but is no longer used.")
            print(f"  Data migration may be needed if you want to preserve existing data.")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")
    
except Exception as e:
    print(f"Error during migration: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

