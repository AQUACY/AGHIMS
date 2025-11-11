"""
Migration: create ward_admissions table to track active ward admissions
"""
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "hms.db"


def upgrade():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ward_admissions'")
        if cursor.fetchone():
            print("Table ward_admissions already exists. Skipping migration.")
            return
        
        # Create ward_admissions table
        cursor.execute("""
            CREATE TABLE ward_admissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admission_recommendation_id INTEGER NOT NULL UNIQUE,
                encounter_id INTEGER NOT NULL UNIQUE,
                ward VARCHAR(100) NOT NULL,
                admitted_by INTEGER NOT NULL,
                admitted_at DATETIME NOT NULL,
                discharged_at DATETIME,
                discharged_by INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admission_recommendation_id) REFERENCES admission_recommendations(id),
                FOREIGN KEY (encounter_id) REFERENCES encounters(id),
                FOREIGN KEY (admitted_by) REFERENCES users(id),
                FOREIGN KEY (discharged_by) REFERENCES users(id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX idx_ward_admissions_ward ON ward_admissions(ward)")
        cursor.execute("CREATE INDEX idx_ward_admissions_encounter_id ON ward_admissions(encounter_id)")
        cursor.execute("CREATE INDEX idx_ward_admissions_discharged_at ON ward_admissions(discharged_at)")
        
        conn.commit()
        print("✓ Created ward_admissions table")
        print("✓ Created indexes on ward_admissions table")
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
    # SQLite doesn't support dropping columns easily
    print("Downgrade not implemented for SQLite")


if __name__ == "__main__":
    upgrade()

