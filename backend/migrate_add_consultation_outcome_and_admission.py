"""
Migration: add outcome to consultation_notes and create admission_recommendations table (SQLite version)
"""
import sqlite3
from pathlib import Path
from datetime import datetime

def migrate():
    """Add outcome column to consultation_notes and create admission_recommendations table"""
    print("=" * 60)
    print("Migration: Add outcome to consultation_notes and create admission_recommendations")
    print("=" * 60)
    print()
    
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print("⚠ SQLite database not found. This migration is SQLite-specific.")
        print("  For MySQL, use migrate_add_consultation_outcome_and_admission_mysql.py instead.")
        print("  Skipping this migration.")
        return
    
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        # 1) Add outcome column to consultation_notes if not exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='consultation_notes'")
        if cursor.fetchone():
            cursor.execute("PRAGMA table_info(consultation_notes)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'outcome' not in columns:
                cursor.execute("ALTER TABLE consultation_notes ADD COLUMN outcome TEXT")
                print("✓ Added outcome column to consultation_notes")
            else:
                print("✓ outcome column already exists in consultation_notes")
        else:
            print("⚠ consultation_notes table does not exist, skipping")
        
        # 2) Create admission_recommendations table if not exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='admission_recommendations'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE admission_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    encounter_id INTEGER NOT NULL UNIQUE,
                    ward TEXT NOT NULL,
                    recommended_by INTEGER NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                    FOREIGN KEY (recommended_by) REFERENCES users(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_admission_recommendations_encounter_id ON admission_recommendations(encounter_id)")
            print("✓ Created admission_recommendations table")
        else:
            print("✓ admission_recommendations table already exists")
        
        conn.commit()
        
    except sqlite3.Error as e:
        print(f"✗ Database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()
    
    print()
    print("=" * 60)
    print("Migration completed successfully!")
    print("=" * 60)

if __name__ == "__main__":
    migrate()


