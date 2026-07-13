"""
Migration script to create vendors and store_stocks tables
"""
import pymysql
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from current directory
    load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', 'localhost'),
    'user': os.getenv('DB_USER') or os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('DB_NAME') or os.getenv('MYSQL_DATABASE', 'hms'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def create_vendors_table(connection):
    """Create vendors table"""
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'vendors'
        """, (DB_CONFIG['database'],))
        result = cursor.fetchone()
        table_exists = result['count'] > 0
        
        if table_exists:
            print("✓ vendors table already exists")
        else:
            # Create vendors table
            print("Creating vendors table...")
            cursor.execute("""
                CREATE TABLE vendors (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    contact_person VARCHAR(255),
                    phone VARCHAR(50),
                    email VARCHAR(255),
                    address TEXT,
                    notes TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_name (name),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ Created vendors table")


def create_store_stocks_table(connection):
    """Create store_stocks table"""
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'store_stocks'
        """, (DB_CONFIG['database'],))
        result = cursor.fetchone()
        table_exists = result['count'] > 0
        
        if table_exists:
            print("✓ store_stocks table already exists")
        else:
            # Create store_stocks table
            print("Creating store_stocks table...")
            cursor.execute("""
                CREATE TABLE store_stocks (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    store_id INT NOT NULL,
                    product_code VARCHAR(50) NOT NULL,
                    product_name VARCHAR(500) NOT NULL,
                    vendor_id INT NOT NULL,
                    batch_number VARCHAR(100) NOT NULL,
                    expiry_date DATE NOT NULL,
                    quantity FLOAT NOT NULL DEFAULT 0.0,
                    unit_price FLOAT,
                    receipt_number VARCHAR(100),
                    notes TEXT,
                    status ENUM('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED') NOT NULL DEFAULT 'PENDING',
                    created_by INT NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    approved_by INT,
                    approved_at DATETIME,
                    rejection_reason TEXT,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (store_id) REFERENCES stores(id),
                    FOREIGN KEY (vendor_id) REFERENCES vendors(id),
                    FOREIGN KEY (created_by) REFERENCES users(id),
                    FOREIGN KEY (approved_by) REFERENCES users(id),
                    INDEX idx_store_id (store_id),
                    INDEX idx_product_code (product_code),
                    INDEX idx_vendor_id (vendor_id),
                    INDEX idx_batch_number (batch_number),
                    INDEX idx_expiry_date (expiry_date),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at),
                    UNIQUE INDEX idx_store_stock_unique (store_id, product_code, batch_number)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ Created store_stocks table")


def migrate():
    """Migration function called by run_migrations.py"""
    print("=" * 60)
    print("Vendors and Store Stock Migration Script")
    print("=" * 60)
    print()
    
    conn = None
    try:
        # Connect to database
        print("Connecting to database...")
        conn = pymysql.connect(**DB_CONFIG)
        print("✓ Connected to database")
        print()
        
        # Step 1: Create vendors table
        print("Step 1: Creating vendors table...")
        create_vendors_table(conn)
        print()
        
        # Step 2: Create store_stocks table
        print("Step 2: Creating store_stocks table...")
        create_store_stocks_table(conn)
        print()
        
        # Commit changes
        conn.commit()
        print("✓ Migration completed successfully!")
        
    except pymysql.Error as e:
        print(f"\n✗ MySQL Error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
            print("Database connection closed")


if __name__ == '__main__':
    migrate()

