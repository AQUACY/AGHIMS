"""
Migration script to:
1. Add department_type column to wards table
2. Create stores table and populate with initial stores
3. Create department_staff_assignments table
4. Create store_staff_assignments table
5. Update pharmacy_requisitions table to add department_id and store_id
6. Add store_id column to ward_stocks table
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

# Initial stores to create
INITIAL_STORES = [
    {'name': 'Main Store', 'description': 'Main hospital store'},
    {'name': 'Pharmacy Store', 'description': 'Pharmacy store for medications and medical supplies'}
]


def add_department_type_to_wards(connection):
    """Add department_type column to wards table"""
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = 'wards'
            AND column_name = 'department_type'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        column_exists = result['count'] > 0
        
        if not column_exists:
            print("Adding department_type column to wards table...")
            cursor.execute("""
                ALTER TABLE wards 
                ADD COLUMN department_type VARCHAR(50) NULL 
                AFTER name
            """)
            connection.commit()
            
            # Update existing wards to have type 'ward' BEFORE making it NOT NULL
            cursor.execute("""
                UPDATE wards 
                SET department_type = 'ward' 
                WHERE department_type IS NULL OR department_type = ''
            """)
            connection.commit()
            
            # Now make it NOT NULL with default
            cursor.execute("""
                ALTER TABLE wards 
                MODIFY COLUMN department_type VARCHAR(50) NOT NULL DEFAULT 'ward'
            """)
            cursor.execute("""
                ALTER TABLE wards 
                ADD INDEX idx_department_type (department_type)
            """)
            connection.commit()
            print("✓ Added department_type column to wards table")
            print("✓ Updated existing wards to type 'ward'")
        else:
            print("✓ department_type column already exists")
            # Ensure all existing wards have a department_type value
            cursor.execute("""
                UPDATE wards 
                SET department_type = 'ward' 
                WHERE department_type IS NULL OR department_type = ''
            """)
            connection.commit()
            print("✓ Ensured all existing wards have department_type set")


def create_stores_table(connection):
    """Create the stores table if it doesn't exist"""
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'stores'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        table_exists = result['count'] > 0
        
        if not table_exists:
            print("Creating stores table...")
            cursor.execute("""
                CREATE TABLE stores (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    description VARCHAR(500) NULL,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    INDEX idx_name (name),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            connection.commit()
            print("✓ Stores table created successfully")
        else:
            print("✓ Stores table already exists")


def populate_stores(connection):
    """Populate stores table with initial stores"""
    with connection.cursor() as cursor:
        now = datetime.now()
        
        for store_data in INITIAL_STORES:
            # Check if store already exists
            cursor.execute("SELECT id FROM stores WHERE name = %s", (store_data['name'],))
            existing = cursor.fetchone()
            
            if not existing:
                print(f"Adding store: {store_data['name']}")
                cursor.execute("""
                    INSERT INTO stores (name, description, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (store_data['name'], store_data['description'], True, now, now))
                connection.commit()
                print(f"  ✓ Added: {store_data['name']}")
            else:
                print(f"  ⊙ Already exists: {store_data['name']}")


def create_department_staff_assignments_table(connection):
    """Create department_staff_assignments table"""
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'department_staff_assignments'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        table_exists = result['count'] > 0
        
        if not table_exists:
            print("Creating department_staff_assignments table...")
            
            # Create table WITHOUT foreign keys first (much faster, avoids locks)
            # Foreign keys can be added later if needed, but they're not critical for functionality
            cursor.execute("""
                CREATE TABLE department_staff_assignments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    department_id INT NOT NULL,
                    user_id INT NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    INDEX idx_department_id (department_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_role (role),
                    UNIQUE KEY unique_department_user_role (department_id, user_id, role)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            connection.commit()
            print("  ✓ Table structure created (without foreign keys for faster creation)")
            print("  Note: Foreign keys are optional and can be added later if needed")
            print("✓ department_staff_assignments table created successfully")
        else:
            print("✓ department_staff_assignments table already exists")


def create_store_staff_assignments_table(connection):
    """Create store_staff_assignments table"""
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'store_staff_assignments'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        table_exists = result['count'] > 0
        
        if not table_exists:
            print("Creating store_staff_assignments table...")
            
            # Create table WITHOUT foreign keys first (much faster, avoids locks)
            # Foreign keys can be added later if needed, but they're not critical for functionality
            cursor.execute("""
                CREATE TABLE store_staff_assignments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    store_id INT NOT NULL,
                    user_id INT NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    INDEX idx_store_id (store_id),
                    INDEX idx_user_id (user_id),
                    INDEX idx_role (role),
                    UNIQUE KEY unique_store_user_role (store_id, user_id, role)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            connection.commit()
            print("  ✓ Table structure created (without foreign keys for faster creation)")
            print("  Note: Foreign keys are optional and can be added later if needed")
            print("✓ store_staff_assignments table created successfully")
        else:
            print("✓ store_staff_assignments table already exists")


def update_pharmacy_requisitions_table(connection):
    """Update pharmacy_requisitions table to add department_id and store_id"""
    with connection.cursor() as cursor:
        # Check if columns exist
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = 'pharmacy_requisitions'
            AND column_name = 'department_id'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        department_id_exists = result['count'] > 0
        
        if not department_id_exists:
            print("Adding department_id and store_id to pharmacy_requisitions table...")
            
            # Add department_id column (nullable first, then we'll populate it)
            cursor.execute("""
                ALTER TABLE pharmacy_requisitions 
                ADD COLUMN department_id INT NULL 
                AFTER requisition_number
            """)
            
            # Add store_id column (nullable first)
            cursor.execute("""
                ALTER TABLE pharmacy_requisitions 
                ADD COLUMN store_id INT NULL 
                AFTER department_id
            """)
            
            # Add indexes
            cursor.execute("""
                ALTER TABLE pharmacy_requisitions 
                ADD INDEX idx_department_id (department_id)
            """)
            cursor.execute("""
                ALTER TABLE pharmacy_requisitions 
                ADD INDEX idx_store_id (store_id)
            """)
            
            # Try to populate department_id from ward name (if wards table exists)
            # This is a best-effort migration - may need manual intervention
            cursor.execute("""
                UPDATE pharmacy_requisitions pr
                INNER JOIN wards w ON pr.ward = w.name
                SET pr.department_id = w.id
                WHERE pr.department_id IS NULL AND pr.ward IS NOT NULL
            """)
            
            # Set default store_id to Pharmacy Store (if it exists)
            cursor.execute("""
                UPDATE pharmacy_requisitions pr
                INNER JOIN stores s ON s.name = 'Pharmacy Store'
                SET pr.store_id = s.id
                WHERE pr.store_id IS NULL
            """)
            
            connection.commit()
            print("✓ Added department_id and store_id columns to pharmacy_requisitions")
            print("  Note: Please verify department_id and store_id are correctly populated")
        else:
            print("✓ department_id and store_id columns already exist in pharmacy_requisitions")


def add_store_id_to_ward_stocks(connection):
    """Add store_id column to ward_stocks table"""
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.columns 
            WHERE table_schema = %s 
            AND table_name = 'ward_stocks'
            AND column_name = 'store_id'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        column_exists = result['count'] > 0
        
        if not column_exists:
            print("Adding store_id column to ward_stocks table...")
            # Add column and index first (without foreign key to avoid locks)
            cursor.execute("""
                ALTER TABLE ward_stocks 
                ADD COLUMN store_id INT NULL 
                AFTER ward
            """)
            connection.commit()
            
            # Add index separately
            try:
                cursor.execute("""
                    ALTER TABLE ward_stocks 
                    ADD INDEX idx_store_id (store_id)
                """)
                connection.commit()
            except pymysql.Error as e:
                if "Duplicate key name" in str(e) or "already exists" in str(e).lower():
                    print("  ⊙ Index already exists")
                else:
                    print(f"  ⚠ Warning: Could not add index: {e}")
            
            print("✓ store_id column added to ward_stocks table")
            print("  Note: Foreign key constraint skipped for faster migration")
            
            # Try to populate store_id from requisitions
            # This is a best-effort attempt - may not work for all records
            print("Attempting to populate store_id from requisitions...")
            try:
                cursor.execute("""
                    UPDATE ward_stocks ws
                    INNER JOIN pharmacy_requisitions pr ON ws.ward = pr.ward
                    SET ws.store_id = pr.store_id
                    WHERE ws.store_id IS NULL
                    AND pr.store_id IS NOT NULL
                    LIMIT 1000
                """)
                updated = cursor.rowcount
                connection.commit()
                if updated > 0:
                    print(f"✓ Populated store_id for {updated} ward_stocks records")
            except Exception as e:
                print(f"⚠ Warning: Could not populate store_id from requisitions: {e}")
        else:
            print("✓ store_id column already exists in ward_stocks table")


def migrate():
    """Migration function called by run_migrations.py"""
    print("=" * 60)
    print("Department and Store Management Migration Script")
    print("=" * 60)
    print()
    
    try:
        # Connect to database
        print("Connecting to database...")
        connection = pymysql.connect(**DB_CONFIG)
        print("✓ Connected to database")
        print()
        
        # Step 1: Add department_type to wards
        print("Step 1: Adding department_type to wards table...")
        add_department_type_to_wards(connection)
        print()
        
        # Step 2: Create stores table
        print("Step 2: Creating stores table...")
        create_stores_table(connection)
        print()
        
        # Step 3: Populate stores
        print("Step 3: Populating initial stores...")
        populate_stores(connection)
        print()
        
        # Step 4: Create department_staff_assignments table
        print("Step 4: Creating department_staff_assignments table...")
        create_department_staff_assignments_table(connection)
        print()
        
        # Step 5: Create store_staff_assignments table
        print("Step 5: Creating store_staff_assignments table...")
        create_store_staff_assignments_table(connection)
        print()
        
        # Step 6: Update pharmacy_requisitions table
        print("Step 6: Updating pharmacy_requisitions table...")
        update_pharmacy_requisitions_table(connection)
        print()
        
        # Step 7: Add store_id to ward_stocks
        print("Step 7: Adding store_id to ward_stocks table...")
        add_store_id_to_ward_stocks(connection)
        print()
        
        # Verify
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM stores WHERE is_active = TRUE")
            result = cursor.fetchone()
            store_count = result['count']
            
            cursor.execute("SELECT name FROM stores WHERE is_active = TRUE ORDER BY name")
            stores = cursor.fetchall()
            
            print(f"✓ Migration completed successfully!")
            print(f"  Total active stores: {store_count}")
            print()
            print("Active stores:")
            for store in stores:
                print(f"  - {store['name']}")
        
        connection.close()
        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        
    except pymysql.Error as e:
        print(f"✗ Database error: {e}")
        raise
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Main function for direct script execution"""
    try:
        migrate()
        return 0
    except Exception as e:
        return 1


if __name__ == "__main__":
    exit(main())

