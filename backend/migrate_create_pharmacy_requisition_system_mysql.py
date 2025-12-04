"""
Migration: Create pharmacy requisition system tables (MySQL/SQLite compatible)
Creates: ward_stocks, pharmacy_requisitions, requisition_items, requisition_history
"""
import os
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text

def migrate():
    """Create pharmacy requisition system tables (MySQL/SQLite compatible)"""
    try:
        # Get database URL to determine database type
        db_url = str(engine.url)
        is_mysql = 'mysql' in db_url.lower() or 'pymysql' in db_url.lower()
        is_sqlite = 'sqlite' in db_url.lower()
        
        if not is_mysql and not is_sqlite:
            print(f"Unsupported database type: {db_url}")
            print("This migration supports MySQL and SQLite only.")
            return False
        
        with engine.connect() as conn:
            # 1. Create ward_stocks table
            print("Creating ward_stocks table...")
            if is_mysql:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ward_stocks (
                        id INTEGER AUTO_INCREMENT PRIMARY KEY,
                        ward VARCHAR(100) NOT NULL,
                        product_code VARCHAR(50) NOT NULL,
                        product_name VARCHAR(500) NOT NULL,
                        quantity FLOAT NOT NULL DEFAULT 0.0,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        INDEX idx_ward_stock_ward (ward),
                        INDEX idx_ward_stock_product_code (product_code),
                        UNIQUE INDEX idx_ward_stock_unique (ward, product_code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS ward_stocks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ward VARCHAR(100) NOT NULL,
                        product_code VARCHAR(50) NOT NULL,
                        product_name VARCHAR(500) NOT NULL,
                        quantity FLOAT NOT NULL DEFAULT 0.0,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ward_stock_ward ON ward_stocks(ward)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ward_stock_product_code ON ward_stocks(product_code)"))
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_ward_stock_unique ON ward_stocks(ward, product_code)"))
            print("✓ Created ward_stocks table")
            
            # 2. Create pharmacy_requisitions table
            print("Creating pharmacy_requisitions table...")
            if is_mysql:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS pharmacy_requisitions (
                        id INTEGER AUTO_INCREMENT PRIMARY KEY,
                        requisition_number VARCHAR(50) NOT NULL UNIQUE,
                        ward VARCHAR(100) NOT NULL,
                        requested_by INTEGER NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'pending',
                        approved_by INTEGER NULL,
                        approved_at DATETIME NULL,
                        rejection_reason TEXT NULL,
                        fulfilled_by INTEGER NULL,
                        fulfilled_at DATETIME NULL,
                        notes TEXT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        INDEX idx_requisition_ward (ward),
                        INDEX idx_requisition_status (status),
                        INDEX idx_requisition_number (requisition_number),
                        INDEX idx_requisition_created_at (created_at),
                        FOREIGN KEY (requested_by) REFERENCES users(id),
                        FOREIGN KEY (approved_by) REFERENCES users(id),
                        FOREIGN KEY (fulfilled_by) REFERENCES users(id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS pharmacy_requisitions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        requisition_number VARCHAR(50) NOT NULL UNIQUE,
                        ward VARCHAR(100) NOT NULL,
                        requested_by INTEGER NOT NULL,
                        status VARCHAR(50) NOT NULL DEFAULT 'pending',
                        approved_by INTEGER NULL,
                        approved_at DATETIME NULL,
                        rejection_reason TEXT NULL,
                        fulfilled_by INTEGER NULL,
                        fulfilled_at DATETIME NULL,
                        notes TEXT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        FOREIGN KEY (requested_by) REFERENCES users(id),
                        FOREIGN KEY (approved_by) REFERENCES users(id),
                        FOREIGN KEY (fulfilled_by) REFERENCES users(id)
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_requisition_ward ON pharmacy_requisitions(ward)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_requisition_status ON pharmacy_requisitions(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_requisition_number ON pharmacy_requisitions(requisition_number)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_requisition_created_at ON pharmacy_requisitions(created_at)"))
            print("✓ Created pharmacy_requisitions table")
            
            # 3. Create requisition_items table
            print("Creating requisition_items table...")
            if is_mysql:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS requisition_items (
                        id INTEGER AUTO_INCREMENT PRIMARY KEY,
                        requisition_id INTEGER NOT NULL,
                        product_code VARCHAR(50) NOT NULL,
                        product_name VARCHAR(500) NOT NULL,
                        requested_quantity FLOAT NOT NULL,
                        fulfilled_quantity FLOAT NOT NULL DEFAULT 0.0,
                        unit_price FLOAT NULL,
                        notes TEXT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        INDEX idx_requisition_item_requisition_id (requisition_id),
                        INDEX idx_requisition_item_product_code (product_code),
                        FOREIGN KEY (requisition_id) REFERENCES pharmacy_requisitions(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS requisition_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        requisition_id INTEGER NOT NULL,
                        product_code VARCHAR(50) NOT NULL,
                        product_name VARCHAR(500) NOT NULL,
                        requested_quantity FLOAT NOT NULL,
                        fulfilled_quantity FLOAT NOT NULL DEFAULT 0.0,
                        unit_price FLOAT NULL,
                        notes TEXT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        FOREIGN KEY (requisition_id) REFERENCES pharmacy_requisitions(id) ON DELETE CASCADE
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_requisition_item_requisition_id ON requisition_items(requisition_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_requisition_item_product_code ON requisition_items(product_code)"))
            print("✓ Created requisition_items table")
            
            # 4. Create requisition_history table
            print("Creating requisition_history table...")
            if is_mysql:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS requisition_history (
                        id INTEGER AUTO_INCREMENT PRIMARY KEY,
                        requisition_id INTEGER NOT NULL,
                        action VARCHAR(50) NOT NULL,
                        performed_by INTEGER NOT NULL,
                        notes TEXT NULL,
                        timestamp DATETIME NOT NULL,
                        item_id INTEGER NULL,
                        quantity_fulfilled FLOAT NULL,
                        INDEX idx_history_requisition_id (requisition_id),
                        INDEX idx_history_action (action),
                        INDEX idx_history_timestamp (timestamp),
                        FOREIGN KEY (requisition_id) REFERENCES pharmacy_requisitions(id) ON DELETE CASCADE,
                        FOREIGN KEY (performed_by) REFERENCES users(id),
                        FOREIGN KEY (item_id) REFERENCES requisition_items(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS requisition_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        requisition_id INTEGER NOT NULL,
                        action VARCHAR(50) NOT NULL,
                        performed_by INTEGER NOT NULL,
                        notes TEXT NULL,
                        timestamp DATETIME NOT NULL,
                        item_id INTEGER NULL,
                        quantity_fulfilled FLOAT NULL,
                        FOREIGN KEY (requisition_id) REFERENCES pharmacy_requisitions(id) ON DELETE CASCADE,
                        FOREIGN KEY (performed_by) REFERENCES users(id),
                        FOREIGN KEY (item_id) REFERENCES requisition_items(id) ON DELETE SET NULL
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_requisition_id ON requisition_history(requisition_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_action ON requisition_history(action)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON requisition_history(timestamp)"))
            print("✓ Created requisition_history table")
            
            # 5. Create notifications table
            print("Creating notifications table...")
            if is_mysql:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER AUTO_INCREMENT PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        notification_type VARCHAR(50) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        is_read BOOLEAN NOT NULL DEFAULT FALSE,
                        related_id INTEGER NULL,
                        related_type VARCHAR(100) NULL,
                        created_at DATETIME NOT NULL,
                        read_at DATETIME NULL,
                        INDEX idx_notification_user_id (user_id),
                        INDEX idx_notification_type (notification_type),
                        INDEX idx_notification_is_read (is_read),
                        INDEX idx_notification_created_at (created_at),
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """))
            else:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        notification_type VARCHAR(50) NOT NULL,
                        title VARCHAR(255) NOT NULL,
                        message TEXT NOT NULL,
                        is_read BOOLEAN NOT NULL DEFAULT FALSE,
                        related_id INTEGER NULL,
                        related_type VARCHAR(100) NULL,
                        created_at DATETIME NOT NULL,
                        read_at DATETIME NULL,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notification_user_id ON notifications(user_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notification_type ON notifications(notification_type)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notification_is_read ON notifications(is_read)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_notification_created_at ON notifications(created_at)"))
            print("✓ Created notifications table")
            
            conn.commit()
            print("\n✓ All migrations completed successfully!")
            return True
            
    except Exception as e:
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)

