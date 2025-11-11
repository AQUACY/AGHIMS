"""
Migration: Create ward_transfers table and add death fields to ward_admissions
"""
import sqlite3
from pathlib import Path

# Get database path
db_path = Path(__file__).parent / "hms.db"

if not db_path.exists():
    print(f"Database not found at {db_path}")
    exit(1)

print(f"Connecting to database: {db_path}")

try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create ward_transfers table
    print("Creating ward_transfers table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ward_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_admission_id INTEGER NOT NULL,
            from_ward TEXT NOT NULL,
            to_ward TEXT NOT NULL,
            transfer_reason TEXT,
            transferred_by INTEGER NOT NULL,
            transferred_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
            FOREIGN KEY (transferred_by) REFERENCES users(id)
        )
    """)
    print("Successfully created ward_transfers table")
    
    # Add death fields to ward_admissions
    print("Checking for death fields in ward_admissions...")
    cursor.execute("PRAGMA table_info(ward_admissions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "death_recorded_at" not in columns:
        print("Adding 'death_recorded_at' column to ward_admissions table...")
        cursor.execute("""
            ALTER TABLE ward_admissions
            ADD COLUMN death_recorded_at DATETIME
        """)
        print("Successfully added 'death_recorded_at' column")
    else:
        print("Column 'death_recorded_at' already exists")
    
    if "death_recorded_by" not in columns:
        print("Adding 'death_recorded_by' column to ward_admissions table...")
        cursor.execute("""
            ALTER TABLE ward_admissions
            ADD COLUMN death_recorded_by INTEGER
        """)
        print("Successfully added 'death_recorded_by' column")
    else:
        print("Column 'death_recorded_by' already exists")
    
    conn.commit()
    conn.close()
    print("Migration completed successfully!")
    
except Exception as e:
    print(f"Error during migration: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

