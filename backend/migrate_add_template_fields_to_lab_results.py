"""
Migration script to add template_id and template_data columns to lab_results and inpatient_lab_results tables
"""
import sqlite3
import os
import json

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    """Add template_id and template_data columns to lab results tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if lab_results table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lab_results'")
        if cursor.fetchone():
            # Check if template_id column already exists
            cursor.execute("PRAGMA table_info(lab_results)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'template_id' not in columns:
                print("Adding template_id and template_data columns to lab_results table...")
                cursor.execute("ALTER TABLE lab_results ADD COLUMN template_id INTEGER")
                cursor.execute("ALTER TABLE lab_results ADD COLUMN template_data TEXT")
                # Add foreign key constraint if possible (SQLite has limited ALTER TABLE support)
                # We'll add it via a new table if needed, but for now just add the column
                print("Successfully added template columns to lab_results table")
            else:
                print("template_id column already exists in lab_results table")
        else:
            print("lab_results table does not exist, skipping...")
        
        # Check if inpatient_lab_results table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='inpatient_lab_results'")
        if cursor.fetchone():
            # Check if template_id column already exists
            cursor.execute("PRAGMA table_info(inpatient_lab_results)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'template_id' not in columns:
                print("Adding template_id and template_data columns to inpatient_lab_results table...")
                cursor.execute("ALTER TABLE inpatient_lab_results ADD COLUMN template_id INTEGER")
                cursor.execute("ALTER TABLE inpatient_lab_results ADD COLUMN template_data TEXT")
                print("Successfully added template columns to inpatient_lab_results table")
            else:
                print("template_id column already exists in inpatient_lab_results table")
        else:
            print("inpatient_lab_results table does not exist, skipping...")
        
        # Check if lab_result_templates table exists, if not create it
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lab_result_templates'")
        if not cursor.fetchone():
            print("Creating lab_result_templates table...")
            cursor.execute("""
                CREATE TABLE lab_result_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    g_drg_code TEXT,
                    procedure_name TEXT NOT NULL,
                    template_name TEXT NOT NULL,
                    template_structure TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    updated_by INTEGER,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (created_by) REFERENCES users(id),
                    FOREIGN KEY (updated_by) REFERENCES users(id)
                )
            """)
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_lab_result_templates_procedure_name ON lab_result_templates(procedure_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS ix_lab_result_templates_g_drg_code ON lab_result_templates(g_drg_code)")
            print("Successfully created lab_result_templates table")
        else:
            print("lab_result_templates table already exists")
        
        conn.commit()
        print("Migration completed successfully!")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

