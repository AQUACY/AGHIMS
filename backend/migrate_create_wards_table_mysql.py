"""
Migration script to create wards table and populate with initial wards
Run this script to create the wards table and add the initial ward list
"""
import pymysql
import os
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'hms'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Initial wards to create
INITIAL_WARDS = [
    'Male Ward',
    'Female Ward',
    'Maternity Ward',
    'Accident & Emergency Ward',
    'Kids Ward',
    'Nicu',
    'Detention & Observation Ward'
]


def create_wards_table(connection):
    """Create the wards table if it doesn't exist"""
    with connection.cursor() as cursor:
        # Check if table exists
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_name = 'wards'
        """, (DB_CONFIG['database'],))
        
        result = cursor.fetchone()
        table_exists = result['count'] > 0
        
        if not table_exists:
            print("Creating wards table...")
            cursor.execute("""
                CREATE TABLE wards (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    is_active BOOLEAN DEFAULT TRUE NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    INDEX idx_name (name),
                    INDEX idx_is_active (is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            connection.commit()
            print("✓ Wards table created successfully")
        else:
            print("✓ Wards table already exists")


def populate_wards(connection):
    """Populate wards table with initial wards"""
    with connection.cursor() as cursor:
        now = datetime.now()
        
        for ward_name in INITIAL_WARDS:
            # Check if ward already exists
            cursor.execute("SELECT id FROM wards WHERE name = %s", (ward_name,))
            existing = cursor.fetchone()
            
            if not existing:
                print(f"Adding ward: {ward_name}")
                cursor.execute("""
                    INSERT INTO wards (name, is_active, created_at, updated_at)
                    VALUES (%s, %s, %s, %s)
                """, (ward_name, True, now, now))
                connection.commit()
                print(f"  ✓ Added: {ward_name}")
            else:
                print(f"  ⊙ Already exists: {ward_name}")


def main():
    """Main migration function"""
    print("=" * 60)
    print("Ward Management Migration Script")
    print("=" * 60)
    print()
    
    try:
        # Connect to database
        print("Connecting to database...")
        connection = pymysql.connect(**DB_CONFIG)
        print("✓ Connected to database")
        print()
        
        # Create wards table
        create_wards_table(connection)
        print()
        
        # Populate initial wards
        print("Populating initial wards...")
        populate_wards(connection)
        print()
        
        # Verify wards
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM wards WHERE is_active = TRUE")
            result = cursor.fetchone()
            active_count = result['count']
            
            cursor.execute("SELECT name FROM wards WHERE is_active = TRUE ORDER BY name")
            wards = cursor.fetchall()
            
            print(f"✓ Migration completed successfully!")
            print(f"  Total active wards: {active_count}")
            print()
            print("Active wards:")
            for ward in wards:
                print(f"  - {ward['name']}")
        
        connection.close()
        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        
    except pymysql.Error as e:
        print(f"✗ Database error: {e}")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

