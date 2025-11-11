"""
Migration: Add admission_notes column to ward_admissions table
"""
import sqlite3
import os
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
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(ward_admissions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if "admission_notes" in columns:
        print("Column 'admission_notes' already exists in ward_admissions table")
    else:
        print("Adding 'admission_notes' column to ward_admissions table...")
        cursor.execute("""
            ALTER TABLE ward_admissions
            ADD COLUMN admission_notes TEXT
        """)
        conn.commit()
        print("Successfully added 'admission_notes' column to ward_admissions table")
    
    conn.close()
    print("Migration completed successfully!")
    
except Exception as e:
    print(f"Error during migration: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

