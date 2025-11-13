"""
Migration script to create tables for inpatient clinical review components
Creates tables for inpatient diagnoses, prescriptions, and investigations
"""
import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "hms.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create inpatient_diagnoses table
    print("Creating inpatient_diagnoses table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inpatient_diagnoses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clinical_review_id INTEGER NOT NULL,
            icd10 VARCHAR(50) NOT NULL,
            diagnosis TEXT NOT NULL,
            gdrg_code VARCHAR(50),
            diagnosis_status VARCHAR(20),
            is_provisional BOOLEAN DEFAULT 0,
            is_chief BOOLEAN DEFAULT 0,
            created_by INTEGER NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (clinical_review_id) REFERENCES inpatient_clinical_reviews(id) ON DELETE CASCADE,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    """)
    print("✓ Created inpatient_diagnoses table")

    # Create inpatient_prescriptions table
    print("Creating inpatient_prescriptions table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inpatient_prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clinical_review_id INTEGER NOT NULL,
            medicine_code VARCHAR(50) NOT NULL,
            medicine_name VARCHAR(500) NOT NULL,
            dose VARCHAR(100),
            unit VARCHAR(50),
            frequency VARCHAR(100),
            frequency_value INTEGER,
            duration VARCHAR(100),
            instructions TEXT,
            quantity INTEGER NOT NULL,
            unparsed TEXT,
            prescribed_by INTEGER NOT NULL,
            confirmed_by INTEGER,
            dispensed_by INTEGER,
            confirmed_at DATETIME,
            is_external INTEGER NOT NULL DEFAULT 0,
            service_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (clinical_review_id) REFERENCES inpatient_clinical_reviews(id) ON DELETE CASCADE,
            FOREIGN KEY (prescribed_by) REFERENCES users(id),
            FOREIGN KEY (confirmed_by) REFERENCES users(id),
            FOREIGN KEY (dispensed_by) REFERENCES users(id)
        )
    """)
    print("✓ Created inpatient_prescriptions table")

    # Create inpatient_investigations table
    print("Creating inpatient_investigations table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inpatient_investigations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clinical_review_id INTEGER NOT NULL,
            service_type VARCHAR(100),
            gdrg_code VARCHAR(50) NOT NULL,
            procedure_name VARCHAR(500),
            investigation_type VARCHAR(50) NOT NULL,
            notes VARCHAR(1000),
            price VARCHAR(50),
            status VARCHAR(50) NOT NULL DEFAULT 'requested',
            service_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            requested_by INTEGER NOT NULL,
            confirmed_by INTEGER,
            completed_by INTEGER,
            cancelled_by INTEGER,
            cancellation_reason VARCHAR(1000),
            cancelled_at DATETIME,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (clinical_review_id) REFERENCES inpatient_clinical_reviews(id) ON DELETE CASCADE,
            FOREIGN KEY (requested_by) REFERENCES users(id),
            FOREIGN KEY (confirmed_by) REFERENCES users(id),
            FOREIGN KEY (completed_by) REFERENCES users(id),
            FOREIGN KEY (cancelled_by) REFERENCES users(id)
        )
    """)
    print("✓ Created inpatient_investigations table")

    conn.commit()
    print("\n✓ Migration completed successfully!")

except sqlite3.Error as e:
    print(f"Database error: {e}")
    conn.rollback()
finally:
    if conn:
        conn.close()

