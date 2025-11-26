"""
Migration script to create consultation_templates table (MySQL)
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
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        
        if cursor is None:
            raise Exception("Failed to create database cursor")
        
        print("✓ Connected to database")
        
        # Check if table already exists
        try:
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'consultation_templates'
            """, (db_name,))
            result = cursor.fetchone()
            table_exists = result is not None
        except Exception as e:
            print(f"Error checking table existence: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        if table_exists:
            print("✓ Table 'consultation_templates' already exists")
        else:
            # Create consultation_templates table
            print("Creating 'consultation_templates' table...")
            cursor.execute("""
                CREATE TABLE consultation_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    created_by INT NOT NULL,
                    is_shared BOOLEAN NOT NULL DEFAULT FALSE,
                    prescriptions_data TEXT,
                    investigations_data TEXT,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id),
                    INDEX idx_created_by (created_by),
                    INDEX idx_is_shared (is_shared)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ Created 'consultation_templates' table")
        
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
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
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

