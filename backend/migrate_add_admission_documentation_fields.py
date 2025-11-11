"""
Migration: Add clinical_review, nurses_notes, and nurses_mid_documentation columns to ward_admissions table
"""
import sqlite3
import os
from pathlib import Path


def migrate():
    """Migration entry point called by run_migrations.py"""
    # Get database path
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    print(f"Connecting to database: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ward_admissions'")
        if not cursor.fetchone():
            print("Table ward_admissions does not exist. Skipping migration.")
            conn.close()
            return
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(ward_admissions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ("clinical_review", "TEXT"),
            ("nurses_notes", "TEXT"),
            ("nurses_mid_documentation", "TEXT"),
        ]
        
        for column_name, column_type in new_columns:
            if column_name in columns:
                print(f"Column '{column_name}' already exists in ward_admissions table")
            else:
                print(f"Adding '{column_name}' column to ward_admissions table...")
                cursor.execute(f"""
                    ALTER TABLE ward_admissions
                    ADD COLUMN {column_name} {column_type}
                """)
                print(f"Successfully added '{column_name}' column to ward_admissions table")
        
        conn.commit()
        conn.close()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate()

