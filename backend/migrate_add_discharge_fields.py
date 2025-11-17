"""
Migration: Add discharge outcome, condition, partial discharge fields, and final orders to ward_admissions table
"""
import sqlite3
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
        
        # Check if ward_admissions table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ward_admissions'")
        if not cursor.fetchone():
            print("Table ward_admissions does not exist. Skipping migration.")
            conn.close()
            return
        
        # Get existing columns
        print("Checking for discharge fields in ward_admissions...")
        cursor.execute("PRAGMA table_info(ward_admissions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add discharge_outcome column if not exists
        if "discharge_outcome" not in columns:
            print("Adding 'discharge_outcome' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN discharge_outcome TEXT
            """)
            print("✓ Successfully added 'discharge_outcome' column")
        else:
            print("✓ Column 'discharge_outcome' already exists")
        
        # Add discharge_condition column if not exists
        if "discharge_condition" not in columns:
            print("Adding 'discharge_condition' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN discharge_condition TEXT
            """)
            print("✓ Successfully added 'discharge_condition' column")
        else:
            print("✓ Column 'discharge_condition' already exists")
        
        # Add partially_discharged_at column if not exists
        if "partially_discharged_at" not in columns:
            print("Adding 'partially_discharged_at' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN partially_discharged_at DATETIME
            """)
            print("✓ Successfully added 'partially_discharged_at' column")
        else:
            print("✓ Column 'partially_discharged_at' already exists")
        
        # Add partially_discharged_by column if not exists
        if "partially_discharged_by" not in columns:
            print("Adding 'partially_discharged_by' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN partially_discharged_by INTEGER
            """)
            print("✓ Successfully added 'partially_discharged_by' column")
        else:
            print("✓ Column 'partially_discharged_by' already exists")
        
        # Add final_orders column if not exists
        if "final_orders" not in columns:
            print("Adding 'final_orders' column to ward_admissions table...")
            cursor.execute("""
                ALTER TABLE ward_admissions
                ADD COLUMN final_orders TEXT
            """)
            print("✓ Successfully added 'final_orders' column")
        else:
            print("✓ Column 'final_orders' already exists")
        
        conn.commit()
        conn.close()
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        print(f"✗ Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate()

