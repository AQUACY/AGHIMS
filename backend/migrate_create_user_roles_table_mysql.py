"""
Migration script to create user_roles table for multi-role support
Run this script to add support for users having multiple roles
"""
import pymysql
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from current directory
    load_dotenv()

def migrate():
    """Create user_roles table"""
    print("Starting migration: Create user_roles table...")
    
    # Get database connection details from environment (support both DB_* and MYSQL_*)
    db_host = os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', 'localhost')
    db_user = os.getenv('DB_USER') or os.getenv('MYSQL_USER', 'root')
    db_name = os.getenv('DB_NAME') or os.getenv('MYSQL_DATABASE', 'hms')
    
    # Get password from environment (no prompting)
    db_password = os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', '')
    
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
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = 'user_roles'
        """, (db_name,))
        result = cursor.fetchone()
        
        if result[0] > 0:
            print("Table 'user_roles' already exists. Skipping creation.")
            return
        
        # Create user_roles table
        print("Creating user_roles table...")
        cursor.execute("""
            CREATE TABLE user_roles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                role VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL,
                UNIQUE KEY unique_user_role (user_id, role),
                INDEX idx_user_id (user_id),
                INDEX idx_role (role)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        print("✓ Successfully created user_roles table")
        
    except pymysql.Error as e:
        print(f"ERROR: Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"ERROR: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            try:
                conn.close()
            except pymysql.Error:
                pass
            print("Database connection closed")

if __name__ == "__main__":
    migrate()

