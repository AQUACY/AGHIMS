"""
Migration: Create additional_services and inpatient_additional_services tables
Creates tables for admin-defined additional services and patient service usage tracking
"""
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def migrate():
    """Create additional_services and inpatient_additional_services tables if they don't exist"""
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
    
    inspector = inspect(engine)
    
    # Create additional_services table
    if "additional_services" not in inspector.get_table_names():
        print("Creating additional_services table...")
        
        with engine.connect() as conn:
            if "sqlite" in settings.DATABASE_URL:
                # SQLite version
                conn.execute(text("""
                    CREATE TABLE additional_services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        service_name VARCHAR(255) NOT NULL UNIQUE,
                        description TEXT,
                        price_per_unit REAL NOT NULL,
                        unit_type VARCHAR(50) NOT NULL DEFAULT 'hour',
                        is_active BOOLEAN DEFAULT 1,
                        created_by INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users(id)
                    )
                """))
                
                conn.execute(text("CREATE INDEX idx_additional_services_active ON additional_services(is_active)"))
            else:
                # MySQL version
                conn.execute(text("""
                    CREATE TABLE additional_services (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        service_name VARCHAR(255) NOT NULL UNIQUE,
                        description TEXT,
                        price_per_unit DECIMAL(10,2) NOT NULL,
                        unit_type VARCHAR(50) NOT NULL DEFAULT 'hour',
                        is_active BOOLEAN DEFAULT TRUE,
                        created_by INT NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES users(id),
                        INDEX idx_additional_services_active (is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
            
            conn.commit()
            print("✓ Successfully created additional_services table")
    else:
        print("✓ additional_services table already exists")
    
    # Create inpatient_additional_services table
    if "inpatient_additional_services" not in inspector.get_table_names():
        print("Creating inpatient_additional_services table...")
        
        with engine.connect() as conn:
            if "sqlite" in settings.DATABASE_URL:
                # SQLite version
                conn.execute(text("""
                    CREATE TABLE inpatient_additional_services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ward_admission_id INTEGER NOT NULL,
                        encounter_id INTEGER NOT NULL,
                        service_id INTEGER NOT NULL,
                        start_time DATETIME NOT NULL,
                        end_time DATETIME,
                        units_used REAL,
                        total_cost REAL,
                        is_billed BOOLEAN DEFAULT 0,
                        bill_item_id INTEGER,
                        notes TEXT,
                        started_by INTEGER NOT NULL,
                        stopped_by INTEGER,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
                        FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                        FOREIGN KEY (service_id) REFERENCES additional_services(id),
                        FOREIGN KEY (started_by) REFERENCES users(id),
                        FOREIGN KEY (stopped_by) REFERENCES users(id)
                    )
                """))
                
                conn.execute(text("CREATE INDEX idx_inpatient_additional_services_ward ON inpatient_additional_services(ward_admission_id)"))
                conn.execute(text("CREATE INDEX idx_inpatient_additional_services_service ON inpatient_additional_services(service_id)"))
                conn.execute(text("CREATE INDEX idx_inpatient_additional_services_billed ON inpatient_additional_services(is_billed)"))
            else:
                # MySQL version
                conn.execute(text("""
                    CREATE TABLE inpatient_additional_services (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        ward_admission_id INT NOT NULL,
                        encounter_id INT NOT NULL,
                        service_id INT NOT NULL,
                        start_time DATETIME NOT NULL,
                        end_time DATETIME,
                        units_used DECIMAL(10,2),
                        total_cost DECIMAL(10,2),
                        is_billed BOOLEAN DEFAULT FALSE,
                        bill_item_id INT,
                        notes TEXT,
                        started_by INT NOT NULL,
                        stopped_by INT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
                        FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                        FOREIGN KEY (service_id) REFERENCES additional_services(id),
                        FOREIGN KEY (started_by) REFERENCES users(id),
                        FOREIGN KEY (stopped_by) REFERENCES users(id),
                        INDEX idx_inpatient_additional_services_ward (ward_admission_id),
                        INDEX idx_inpatient_additional_services_service (service_id),
                        INDEX idx_inpatient_additional_services_billed (is_billed)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
            
            conn.commit()
            print("✓ Successfully created inpatient_additional_services table and indexes")
    else:
        print("✓ inpatient_additional_services table already exists")

if __name__ == "__main__":
    migrate()

