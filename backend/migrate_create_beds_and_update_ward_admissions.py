"""
Migration: create beds table and update ward_admissions with new fields
"""
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "hms.db"


def upgrade():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # 1. Create beds table if not exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='beds'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE beds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ward VARCHAR(100) NOT NULL,
                    bed_number VARCHAR(50) NOT NULL,
                    is_occupied INTEGER DEFAULT 0 NOT NULL,
                    is_active INTEGER DEFAULT 1 NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_beds_ward ON beds(ward)")
            cursor.execute("CREATE INDEX idx_beds_is_occupied ON beds(is_occupied)")
            cursor.execute("CREATE INDEX idx_beds_is_active ON beds(is_active)")
            
            conn.commit()
            print("✓ Created beds table")
            print("✓ Created indexes on beds table")
        else:
            print("✓ beds table already exists")
        
        # 2. Check if ward_admissions table exists before updating
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ward_admissions'")
        if not cursor.fetchone():
            print("Table ward_admissions does not exist. Skipping column additions.")
            print("Migration completed successfully")
            return
        
        # Update ward_admissions table with new columns
        cursor.execute("PRAGMA table_info(ward_admissions)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        # Add bed_id column if not exists
        if "bed_id" not in existing_cols:
            cursor.execute("ALTER TABLE ward_admissions ADD COLUMN bed_id INTEGER")
            conn.commit()
            print("✓ Added bed_id column to ward_admissions")
        else:
            print("✓ bed_id column already exists")
        
        # Add ccc_number column if not exists
        if "ccc_number" not in existing_cols:
            cursor.execute("ALTER TABLE ward_admissions ADD COLUMN ccc_number VARCHAR(50)")
            conn.commit()
            print("✓ Added ccc_number column to ward_admissions")
        else:
            print("✓ ccc_number column already exists")
        
        # Add emergency_contact_name column if not exists
        if "emergency_contact_name" not in existing_cols:
            cursor.execute("ALTER TABLE ward_admissions ADD COLUMN emergency_contact_name VARCHAR(255)")
            conn.commit()
            print("✓ Added emergency_contact_name column to ward_admissions")
        else:
            print("✓ emergency_contact_name column already exists")
        
        # Add emergency_contact_relationship column if not exists
        if "emergency_contact_relationship" not in existing_cols:
            cursor.execute("ALTER TABLE ward_admissions ADD COLUMN emergency_contact_relationship VARCHAR(100)")
            conn.commit()
            print("✓ Added emergency_contact_relationship column to ward_admissions")
        else:
            print("✓ emergency_contact_relationship column already exists")
        
        # Add emergency_contact_number column if not exists
        if "emergency_contact_number" not in existing_cols:
            cursor.execute("ALTER TABLE ward_admissions ADD COLUMN emergency_contact_number VARCHAR(100)")
            conn.commit()
            print("✓ Added emergency_contact_number column to ward_admissions")
        else:
            print("✓ emergency_contact_number column already exists")
        
        # Add doctor_id column if not exists
        if "doctor_id" not in existing_cols:
            cursor.execute("ALTER TABLE ward_admissions ADD COLUMN doctor_id INTEGER")
            conn.commit()
            print("✓ Added doctor_id column to ward_admissions")
        else:
            print("✓ doctor_id column already exists")
        
        print("Migration completed successfully")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def migrate():
    """Migration entry point called by run_migrations.py"""
    upgrade()


def downgrade():
    print("Downgrade not implemented for SQLite")


if __name__ == "__main__":
    upgrade()

