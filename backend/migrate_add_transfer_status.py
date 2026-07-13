"""
Migration: Add status and acceptance fields to ward_transfers table
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
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ward_transfers'")
        if not cursor.fetchone():
            print("Table ward_transfers does not exist. Skipping migration.")
            conn.close()
            return
        
        # Check for status column
        cursor.execute("PRAGMA table_info(ward_transfers)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if "status" not in columns:
            print("Adding 'status' column to ward_transfers table...")
            cursor.execute("""
                ALTER TABLE ward_transfers
                ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'
            """)
            print("Successfully added 'status' column")
        else:
            print("Column 'status' already exists")
        
        if "accepted_by" not in columns:
            print("Adding 'accepted_by' column to ward_transfers table...")
            cursor.execute("""
                ALTER TABLE ward_transfers
                ADD COLUMN accepted_by INTEGER
            """)
            print("Successfully added 'accepted_by' column")
        else:
            print("Column 'accepted_by' already exists")
        
        if "rejected_by" not in columns:
            print("Adding 'rejected_by' column to ward_transfers table...")
            cursor.execute("""
                ALTER TABLE ward_transfers
                ADD COLUMN rejected_by INTEGER
            """)
            print("Successfully added 'rejected_by' column")
        else:
            print("Column 'rejected_by' already exists")
        
        if "rejection_reason" not in columns:
            print("Adding 'rejection_reason' column to ward_transfers table...")
            cursor.execute("""
                ALTER TABLE ward_transfers
                ADD COLUMN rejection_reason TEXT
            """)
            print("Successfully added 'rejection_reason' column")
        else:
            print("Column 'rejection_reason' already exists")
        
        if "accepted_at" not in columns:
            print("Adding 'accepted_at' column to ward_transfers table...")
            cursor.execute("""
                ALTER TABLE ward_transfers
                ADD COLUMN accepted_at DATETIME
            """)
            print("Successfully added 'accepted_at' column")
        else:
            print("Column 'accepted_at' already exists")
        
        if "rejected_at" not in columns:
            print("Adding 'rejected_at' column to ward_transfers table...")
            cursor.execute("""
                ALTER TABLE ward_transfers
                ADD COLUMN rejected_at DATETIME
            """)
            print("Successfully added 'rejected_at' column")
        else:
            print("Column 'rejected_at' already exists")
        
        # Update existing transfers to 'accepted' status (for backward compatibility)
        # Only if status column was just added or exists
        cursor.execute("SELECT COUNT(*) FROM ward_transfers")
        row_count = cursor.fetchone()[0]
        if row_count > 0:
            cursor.execute("""
                UPDATE ward_transfers
                SET status = 'accepted'
                WHERE status IS NULL OR status = ''
            """)
            print(f"Updated {row_count} existing transfers to 'accepted' status")
        else:
            print("No existing transfers to update")
        
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

