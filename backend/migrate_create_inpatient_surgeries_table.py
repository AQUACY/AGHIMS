"""
Migration: Create inpatient_surgeries table
Creates table for storing surgery details for admitted patients
"""
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def migrate():
    """Create inpatient_surgeries table if it doesn't exist"""
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
    
    inspector = inspect(engine)
    
    # Check if table already exists
    if "inpatient_surgeries" in inspector.get_table_names():
        print("✓ inpatient_surgeries table already exists")
        return
    
    print("Creating inpatient_surgeries table...")
    
    with engine.connect() as conn:
        if "sqlite" in settings.DATABASE_URL:
            # SQLite version
            conn.execute(text("""
                CREATE TABLE inpatient_surgeries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ward_admission_id INTEGER NOT NULL,
                    encounter_id INTEGER NOT NULL,
                    g_drg_code VARCHAR(50),
                    surgery_name VARCHAR(500) NOT NULL,
                    surgery_type VARCHAR(100),
                    surgeon_name VARCHAR(255),
                    assistant_surgeon VARCHAR(255),
                    anesthesia_type VARCHAR(100),
                    surgery_date DATETIME,
                    surgery_notes TEXT,
                    operative_notes TEXT,
                    post_operative_notes TEXT,
                    complications TEXT,
                    is_completed BOOLEAN DEFAULT 0,
                    completed_at DATETIME,
                    completed_by INTEGER,
                    created_by INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
                    FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                    FOREIGN KEY (completed_by) REFERENCES users(id),
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            """))
            
            # Create indexes
            conn.execute(text("CREATE INDEX idx_inpatient_surgeries_ward_admission ON inpatient_surgeries(ward_admission_id)"))
            conn.execute(text("CREATE INDEX idx_inpatient_surgeries_encounter ON inpatient_surgeries(encounter_id)"))
            conn.execute(text("CREATE INDEX idx_inpatient_surgeries_completed ON inpatient_surgeries(is_completed)"))
            
        else:
            # MySQL version
            conn.execute(text("""
                CREATE TABLE inpatient_surgeries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ward_admission_id INT NOT NULL,
                    encounter_id INT NOT NULL,
                    g_drg_code VARCHAR(50),
                    surgery_name VARCHAR(500) NOT NULL,
                    surgery_type VARCHAR(100),
                    surgeon_name VARCHAR(255),
                    assistant_surgeon VARCHAR(255),
                    anesthesia_type VARCHAR(100),
                    surgery_date DATETIME,
                    surgery_notes TEXT,
                    operative_notes TEXT,
                    post_operative_notes TEXT,
                    complications TEXT,
                    is_completed BOOLEAN DEFAULT FALSE,
                    completed_at DATETIME,
                    completed_by INT,
                    created_by INT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
                    FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                    FOREIGN KEY (completed_by) REFERENCES users(id),
                    FOREIGN KEY (created_by) REFERENCES users(id),
                    INDEX idx_inpatient_surgeries_ward_admission (ward_admission_id),
                    INDEX idx_inpatient_surgeries_encounter (encounter_id),
                    INDEX idx_inpatient_surgeries_completed (is_completed)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
        
        conn.commit()
        print("✓ Successfully created inpatient_surgeries table and indexes")

if __name__ == "__main__":
    migrate()

