"""
Migration script to add release fields to inpatient_inventory_debits table
Adds: is_released, released_by, released_at columns
"""
import pymysql
import os
import sys
from getpass import getpass

def migrate():
    # Get database connection details from environment or prompt
    db_host = os.getenv('DB_HOST', 'localhost')
    db_user = os.getenv('DB_USER', 'root')
    db_name = os.getenv('DB_NAME', 'hms')
    
    # Get password from environment or prompt
    db_password = os.getenv('DB_PASSWORD')
    if not db_password:
        db_password = getpass('Enter database password: ')
    
    # Initialize conn and cursor to None
    conn = None
    cursor = None
    
    try:
        # Connect to MySQL database
        print(f"Connecting to MySQL database '{db_name}' on {db_host}...")
        conn = pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            charset='utf8mb4',
            cursorclass=None  # Use default cursor (returns tuples)
        )
        cursor = conn.cursor()
        
        print("✓ Connected to database")
        
        # Check if columns already exist
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'inpatient_inventory_debits' 
            AND COLUMN_NAME IN ('is_released', 'released_by', 'released_at')
        """, (db_name,))
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add is_released column if it doesn't exist
        if 'is_released' not in existing_columns:
            print("Adding 'is_released' column...")
            cursor.execute("""
                ALTER TABLE inpatient_inventory_debits 
                ADD COLUMN is_released BOOLEAN DEFAULT FALSE NOT NULL
            """)
            print("✓ Added 'is_released' column")
        else:
            print("✓ Column 'is_released' already exists")
        
        # Add released_by column if it doesn't exist
        if 'released_by' not in existing_columns:
            print("Adding 'released_by' column...")
            cursor.execute("""
                ALTER TABLE inpatient_inventory_debits 
                ADD COLUMN released_by INT NULL
            """)
            print("✓ Added 'released_by' column")
        else:
            print("✓ Column 'released_by' already exists")
        
        # Add released_at column if it doesn't exist
        if 'released_at' not in existing_columns:
            print("Adding 'released_at' column...")
            cursor.execute("""
                ALTER TABLE inpatient_inventory_debits 
                ADD COLUMN released_at DATETIME NULL
            """)
            print("✓ Added 'released_at' column")
        else:
            print("✓ Column 'released_at' already exists")
        
        # Add foreign key constraint for released_by if it doesn't exist
        cursor.execute("""
            SELECT CONSTRAINT_NAME 
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'inpatient_inventory_debits' 
            AND CONSTRAINT_NAME = 'inpatient_inventory_debits_ibfk_released_by'
        """, (db_name,))
        fk_exists = cursor.fetchone()
        
        if not fk_exists and 'released_by' not in existing_columns:
            print("Adding foreign key constraint for 'released_by'...")
            try:
                cursor.execute("""
                    ALTER TABLE inpatient_inventory_debits 
                    ADD CONSTRAINT inpatient_inventory_debits_ibfk_released_by 
                    FOREIGN KEY (released_by) REFERENCES users(id)
                """)
                print("✓ Added foreign key constraint for 'released_by'")
            except pymysql.err.OperationalError as e:
                if 'Duplicate key name' in str(e) or 'already exists' in str(e):
                    print("⚠ Foreign key constraint already exists, skipping...")
                else:
                    raise
        elif fk_exists:
            print("✓ Foreign key constraint for 'released_by' already exists")
        
        # Commit changes
        conn.commit()
        print("\n✓ Migration completed successfully!")
        
    except pymysql.Error as e:
        print(f"\n✗ MySQL Error during migration: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("Database connection closed")

if __name__ == '__main__':
    migrate()

