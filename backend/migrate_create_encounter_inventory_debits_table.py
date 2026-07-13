"""
Migration: Create encounter_inventory_debits table
This table tracks products/consumables used for OPD encounters (e.g., Malaria RDT, UPT kits)
"""
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def migrate():
    """Create encounter_inventory_debits table"""
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
    
    inspector = inspect(engine)
    
    # Check if table already exists
    if "encounter_inventory_debits" in inspector.get_table_names():
        print("✓ encounter_inventory_debits table already exists")
        return
    
    print("Creating encounter_inventory_debits table...")
    
    with engine.connect() as conn:
        if "sqlite" in settings.DATABASE_URL:
            # SQLite syntax
            conn.execute(text("""
                CREATE TABLE encounter_inventory_debits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    encounter_id INTEGER NOT NULL,
                    department VARCHAR(100) NOT NULL,
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
                    FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                    FOREIGN KEY (used_by) REFERENCES users(id),
                    FOREIGN KEY (bill_item_id) REFERENCES bill_items(id)
                )
            """))
        else:
            # MySQL syntax
            conn.execute(text("""
                CREATE TABLE encounter_inventory_debits (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    encounter_id INT NOT NULL,
                    department VARCHAR(100) NOT NULL,
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
                    FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                    FOREIGN KEY (used_by) REFERENCES users(id),
                    FOREIGN KEY (bill_item_id) REFERENCES bill_items(id),
                    INDEX idx_encounter_id (encounter_id),
                    INDEX idx_department (department),
                    INDEX idx_product_code (product_code)
                )
            """))
        
        conn.commit()
        print("✓ Successfully created encounter_inventory_debits table")

if __name__ == "__main__":
    migrate()

