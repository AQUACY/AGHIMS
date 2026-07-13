"""
Migration: Create inpatient_inventory_debits table
This table tracks products/consumables used for ward admissions (e.g., gloves, gauze, infusion sets)
"""
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def migrate():
    """Create inpatient_inventory_debits table"""
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
    
    inspector = inspect(engine)
    
    # Check if table already exists
    if "inpatient_inventory_debits" in inspector.get_table_names():
        print("✓ inpatient_inventory_debits table already exists")
        return
    
    print("Creating inpatient_inventory_debits table...")
    
    with engine.connect() as conn:
        if "sqlite" in settings.DATABASE_URL:
            # SQLite syntax
            conn.execute(text("""
                CREATE TABLE inpatient_inventory_debits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ward_admission_id INTEGER NOT NULL,
                    encounter_id INTEGER NOT NULL,
                    product_code VARCHAR(50) NOT NULL,
                    product_name VARCHAR(500) NOT NULL,
                    quantity REAL NOT NULL DEFAULT 1.0,
                    unit_price REAL NOT NULL,
                    total_price REAL NOT NULL,
                    notes TEXT,
                    is_billed BOOLEAN DEFAULT 0,
                    bill_item_id INTEGER,
                    used_by INTEGER NOT NULL,
                    used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
                    FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                    FOREIGN KEY (used_by) REFERENCES users(id),
                    FOREIGN KEY (bill_item_id) REFERENCES bill_items(id)
                )
            """))
        else:
            # MySQL syntax
            conn.execute(text("""
                CREATE TABLE inpatient_inventory_debits (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    ward_admission_id INT NOT NULL,
                    encounter_id INT NOT NULL,
                    product_code VARCHAR(50) NOT NULL,
                    product_name VARCHAR(500) NOT NULL,
                    quantity DECIMAL(10,2) NOT NULL DEFAULT 1.0,
                    unit_price DECIMAL(10,2) NOT NULL,
                    total_price DECIMAL(10,2) NOT NULL,
                    notes TEXT,
                    is_billed BOOLEAN DEFAULT FALSE,
                    bill_item_id INT,
                    used_by INT NOT NULL,
                    used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
                    FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                    FOREIGN KEY (used_by) REFERENCES users(id),
                    FOREIGN KEY (bill_item_id) REFERENCES bill_items(id),
                    INDEX idx_ward_admission_id (ward_admission_id),
                    INDEX idx_encounter_id (encounter_id),
                    INDEX idx_product_code (product_code)
                )
            """))
        
        conn.commit()
        print("✓ Successfully created inpatient_inventory_debits table")

if __name__ == "__main__":
    migrate()

