"""
Migration: Add discharge outcome, condition, partial discharge fields, and final orders to ward_admissions table (MySQL)
"""
import mysql.connector
from mysql.connector import Error
import os
from pathlib import Path


def migrate():
    """Migration entry point called by run_migrations.py"""
    # Get database connection details from environment
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = int(os.getenv('DB_PORT', 3306))
    db_name = os.getenv('DB_NAME', 'hms')
    db_user = os.getenv('DB_USER', 'root')
    db_password = os.getenv('DB_PASSWORD', '')
    
    try:
        print(f"Connecting to MySQL database: {db_name}@{db_host}:{db_port}")
        conn = mysql.connector.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        cursor = conn.cursor()
        
        # Check if ward_admissions table exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = 'ward_admissions'
        """, (db_name,))
        
        if cursor.fetchone()[0] == 0:
            print("Table ward_admissions does not exist. Skipping migration.")
            conn.close()
            return
        
        # Get existing columns
        print("Checking for discharge fields in ward_admissions...")
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'ward_admissions'
        """, (db_name,))
        columns = {row[0] for row in cursor.fetchall()}
        
        # Add discharge_outcome column if not exists
        if "discharge_outcome" not in columns:
            print("Adding 'discharge_outcome' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN discharge_outcome VARCHAR(50) NULL
            """)
            print("✓ Successfully added 'discharge_outcome' column")
        else:
            print("✓ Column 'discharge_outcome' already exists")
        
        # Add discharge_condition column if not exists
        if "discharge_condition" not in columns:
            print("Adding 'discharge_condition' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN discharge_condition VARCHAR(50) NULL
            """)
            print("✓ Successfully added 'discharge_condition' column")
        else:
            print("✓ Column 'discharge_condition' already exists")
        
        # Add partially_discharged_at column if not exists
        if "partially_discharged_at" not in columns:
            print("Adding 'partially_discharged_at' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN partially_discharged_at DATETIME NULL
            """)
            print("✓ Successfully added 'partially_discharged_at' column")
        else:
            print("✓ Column 'partially_discharged_at' already exists")
        
        # Add partially_discharged_by column if not exists
        if "partially_discharged_by" not in columns:
            print("Adding 'partially_discharged_by' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN partially_discharged_by INT NULL,
                ADD FOREIGN KEY (partially_discharged_by) REFERENCES users(id)
            """)
            print("✓ Successfully added 'partially_discharged_by' column")
        else:
            print("✓ Column 'partially_discharged_by' already exists")
        
        # Add final_orders column if not exists
        if "final_orders" not in columns:
            print("Adding 'final_orders' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN final_orders TEXT NULL
            """)
            print("✓ Successfully added 'final_orders' column")
        else:
            print("✓ Column 'final_orders' already exists")
        
        conn.commit()
        conn.close()
        print("\n✓ Migration completed successfully!")
        
    except Error as e:
        print(f"✗ MySQL Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"✗ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate()

