"""
Migration script to add template_id and template_data columns to lab_results and inpatient_lab_results tables (MySQL)
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
        
        # Check if lab_results table exists
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'lab_results'
        """, (db_name,))
        lab_results_exists = cursor.fetchone()
        
        if lab_results_exists:
            # Check if template_id column already exists in lab_results
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'lab_results' 
                AND COLUMN_NAME = 'template_id'
            """, (db_name,))
            template_id_exists = cursor.fetchone()
            
            if not template_id_exists:
                print("Adding template_id and template_data columns to lab_results table...")
                cursor.execute("ALTER TABLE lab_results ADD COLUMN template_id INT NULL")
                cursor.execute("ALTER TABLE lab_results ADD COLUMN template_data JSON NULL")
                print("✓ Successfully added template columns to lab_results table")
            else:
                print("✓ template_id column already exists in lab_results table")
        else:
            print("⚠ lab_results table does not exist, skipping...")
        
        # Check if inpatient_lab_results table exists
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'inpatient_lab_results'
        """, (db_name,))
        inpatient_lab_results_exists = cursor.fetchone()
        
        if inpatient_lab_results_exists:
            # Check if template_id column already exists in inpatient_lab_results
            cursor.execute("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'inpatient_lab_results' 
                AND COLUMN_NAME = 'template_id'
            """, (db_name,))
            template_id_exists = cursor.fetchone()
            
            if not template_id_exists:
                print("Adding template_id and template_data columns to inpatient_lab_results table...")
                cursor.execute("ALTER TABLE inpatient_lab_results ADD COLUMN template_id INT NULL")
                cursor.execute("ALTER TABLE inpatient_lab_results ADD COLUMN template_data JSON NULL")
                print("✓ Successfully added template columns to inpatient_lab_results table")
            else:
                print("✓ template_id column already exists in inpatient_lab_results table")
        else:
            print("⚠ inpatient_lab_results table does not exist, skipping...")
        
        # Check if lab_result_templates table exists, if not create it
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'lab_result_templates'
        """, (db_name,))
        templates_table_exists = cursor.fetchone()
        
        if not templates_table_exists:
            print("Creating lab_result_templates table...")
            cursor.execute("""
                CREATE TABLE lab_result_templates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    g_drg_code VARCHAR(50),
                    procedure_name VARCHAR(255) NOT NULL,
                    template_name VARCHAR(255) NOT NULL,
                    template_structure JSON NOT NULL,
                    created_by INT NOT NULL,
                    updated_by INT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    is_active TINYINT(1) DEFAULT 1,
                    FOREIGN KEY (created_by) REFERENCES users(id),
                    FOREIGN KEY (updated_by) REFERENCES users(id),
                    INDEX idx_procedure_name (procedure_name),
                    INDEX idx_g_drg_code (g_drg_code)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ Successfully created lab_result_templates table")
        else:
            print("✓ lab_result_templates table already exists")
        
        # Add foreign key constraints for template_id if they don't exist
        if lab_results_exists:
            try:
                cursor.execute("""
                    SELECT CONSTRAINT_NAME 
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'lab_results' 
                    AND COLUMN_NAME = 'template_id'
                    AND REFERENCED_TABLE_NAME = 'lab_result_templates'
                """, (db_name,))
                fk_exists = cursor.fetchone()
                
                if not fk_exists:
                    print("Adding foreign key constraint for lab_results.template_id...")
                    cursor.execute("""
                        ALTER TABLE lab_results 
                        ADD CONSTRAINT fk_lab_results_template_id 
                        FOREIGN KEY (template_id) REFERENCES lab_result_templates(id)
                    """)
                    print("✓ Successfully added foreign key constraint for lab_results.template_id")
                else:
                    print("✓ Foreign key constraint already exists for lab_results.template_id")
            except Exception as e:
                print(f"⚠ Could not add foreign key constraint for lab_results.template_id: {e}")
                print("  This is OK if the constraint already exists or if there are data issues")
        
        if inpatient_lab_results_exists:
            try:
                cursor.execute("""
                    SELECT CONSTRAINT_NAME 
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = %s 
                    AND TABLE_NAME = 'inpatient_lab_results' 
                    AND COLUMN_NAME = 'template_id'
                    AND REFERENCED_TABLE_NAME = 'lab_result_templates'
                """, (db_name,))
                fk_exists = cursor.fetchone()
                
                if not fk_exists:
                    print("Adding foreign key constraint for inpatient_lab_results.template_id...")
                    cursor.execute("""
                        ALTER TABLE inpatient_lab_results 
                        ADD CONSTRAINT fk_inpatient_lab_results_template_id 
                        FOREIGN KEY (template_id) REFERENCES lab_result_templates(id)
                    """)
                    print("✓ Successfully added foreign key constraint for inpatient_lab_results.template_id")
                else:
                    print("✓ Foreign key constraint already exists for inpatient_lab_results.template_id")
            except Exception as e:
                print(f"⚠ Could not add foreign key constraint for inpatient_lab_results.template_id: {e}")
                print("  This is OK if the constraint already exists or if there are data issues")
        
        conn.commit()
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error during migration: {e}")
        import traceback
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

if __name__ == "__main__":
    print("=" * 70)
    print("Migration: Add template_id and template_data to lab results tables")
    print("=" * 70)
    print("\n⚠ WARNING: Always backup your database before running migrations!")
    print("\nThis migration will:")
    print("  1. Add template_id column to lab_results table (if missing)")
    print("  2. Add template_data column to lab_results table (if missing)")
    print("  3. Add template_id column to inpatient_lab_results table (if missing)")
    print("  4. Add template_data column to inpatient_lab_results table (if missing)")
    print("  5. Create lab_result_templates table (if missing)")
    print("  6. Add foreign key constraints (if missing)")
    print("\n" + "=" * 70)
    
    response = input("\nDo you want to continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        sys.exit(0)
    
    migrate()

