"""
Migration script to add claim detail tables
"""
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print("Database not found!")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Create claim_diagnoses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claim_diagnoses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                diagnosis_id INTEGER,
                description TEXT NOT NULL,
                icd10 VARCHAR NOT NULL,
                gdrg_code VARCHAR,
                is_chief BOOLEAN DEFAULT 0,
                display_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                FOREIGN KEY (diagnosis_id) REFERENCES diagnoses(id)
            )
        """)
        
        # Create claim_investigations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claim_investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                investigation_id INTEGER,
                description TEXT,
                gdrg_code VARCHAR NOT NULL,
                service_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                investigation_type VARCHAR,
                display_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                FOREIGN KEY (investigation_id) REFERENCES investigations(id)
            )
        """)
        
        # Create claim_prescriptions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claim_prescriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                prescription_id INTEGER,
                description TEXT NOT NULL,
                code VARCHAR NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                total_cost REAL NOT NULL,
                service_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                dose VARCHAR,
                frequency VARCHAR,
                duration VARCHAR,
                unparsed TEXT,
                display_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
                FOREIGN KEY (prescription_id) REFERENCES prescriptions(id)
            )
        """)
        
        # Create claim_procedures table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claim_procedures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id INTEGER NOT NULL,
                description TEXT,
                gdrg_code VARCHAR,
                service_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                display_order INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claim_diagnoses_claim_id ON claim_diagnoses(claim_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claim_investigations_claim_id ON claim_investigations(claim_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claim_prescriptions_claim_id ON claim_prescriptions(claim_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claim_procedures_claim_id ON claim_procedures(claim_id)")
        
        conn.commit()
        print("Migration completed successfully!")
        print("- Created claim_diagnoses table")
        print("- Created claim_investigations table")
        print("- Created claim_prescriptions table")
        print("- Created claim_procedures table")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

