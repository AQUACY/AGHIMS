"""
Migration script to add strikethrough fields to nurse_notes table
"""
import sqlite3
from pathlib import Path

# Database path
db_path = Path(__file__).parent / "hms.db"

def migrate():
    """Add strikethrough fields to nurse_notes table"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(nurse_notes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'strikethrough' not in columns:
            print("Adding strikethrough column to nurse_notes table...")
            cursor.execute("""
                ALTER TABLE nurse_notes
                ADD COLUMN strikethrough INTEGER DEFAULT 0 NOT NULL
            """)
            print("✓ Added strikethrough column")
        else:
            print("strikethrough column already exists")
        
        if 'strikethrough_by' not in columns:
            print("Adding strikethrough_by column to nurse_notes table...")
            cursor.execute("""
                ALTER TABLE nurse_notes
                ADD COLUMN strikethrough_by INTEGER
            """)
            print("✓ Added strikethrough_by column")
        else:
            print("strikethrough_by column already exists")
        
        if 'strikethrough_at' not in columns:
            print("Adding strikethrough_at column to nurse_notes table...")
            cursor.execute("""
                ALTER TABLE nurse_notes
                ADD COLUMN strikethrough_at DATETIME
            """)
            print("✓ Added strikethrough_at column")
        else:
            print("strikethrough_at column already exists")
        
        # Add foreign key constraint if not exists
        # Note: SQLite doesn't support adding foreign keys via ALTER TABLE
        # The foreign key relationship is handled at the application level
        
        conn.commit()
        print("\n✓ Migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

