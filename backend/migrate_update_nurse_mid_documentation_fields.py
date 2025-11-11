"""
Migration script to update nurse_mid_documentations table
Adds 6 new fields for structured nurse mid documentation
"""
import sqlite3
from pathlib import Path


def migrate():
    """Migration entry point called by run_migrations.py"""
    db_path = Path(__file__).parent / "hms.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    print(f"Connecting to database: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nurse_mid_documentations'")
        if not cursor.fetchone():
            print("Table nurse_mid_documentations does not exist. Skipping migration.")
            conn.close()
            return

        # Check existing columns
        cursor.execute("PRAGMA table_info(nurse_mid_documentations)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Existing columns: {columns}")

        # Update existing documentation column to allow NULL
        if "documentation" in columns:
            print("Updating documentation column to allow NULL...")
            # SQLite doesn't support ALTER COLUMN directly, so we need to recreate the table
            # But first, let's check if we can just update the constraint
            # Actually, SQLite doesn't support modifying NOT NULL constraints easily
            # We'll need to recreate the table or use a workaround
            # For now, let's try to update existing NULL values to empty string if needed
            cursor.execute("""
                UPDATE nurse_mid_documentations 
                SET documentation = '' 
                WHERE documentation IS NULL
            """)
            print("✓ Updated documentation column (set NULL values to empty string)")
        
        # Add new columns if they don't exist
        new_columns = [
            ("patient_problems_diagnosis", "TEXT"),
            ("aim_of_care", "TEXT"),
            ("nursing_assessment", "TEXT"),
            ("nursing_orders", "TEXT"),
            ("nursing_intervention", "TEXT"),
            ("evaluation", "TEXT"),
        ]

        for column_name, column_type in new_columns:
            if column_name not in columns:
                print(f"Adding column {column_name}...")
                cursor.execute(f"""
                    ALTER TABLE nurse_mid_documentations
                    ADD COLUMN {column_name} {column_type}
                """)
                print(f"✓ Added {column_name} column")
            else:
                print(f"{column_name} column already exists.")
        
        # SQLite doesn't support ALTER COLUMN to change NOT NULL constraint
        # We need to recreate the table to allow NULL for documentation column
        # But this is complex, so let's use a workaround: set a default empty string
        # Actually, the best approach is to recreate the table
        print("\nRecreating table to allow NULL for documentation column...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nurse_mid_documentations_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ward_admission_id INTEGER NOT NULL,
                patient_problems_diagnosis TEXT,
                aim_of_care TEXT,
                nursing_assessment TEXT,
                nursing_orders TEXT,
                nursing_intervention TEXT,
                evaluation TEXT,
                documentation TEXT,
                created_by INTEGER NOT NULL,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                FOREIGN KEY (ward_admission_id) REFERENCES ward_admissions(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
        """)
        
        # Copy data from old table to new table
        cursor.execute("""
            INSERT INTO nurse_mid_documentations_new 
            SELECT 
                id, ward_admission_id, 
                patient_problems_diagnosis, aim_of_care, nursing_assessment,
                nursing_orders, nursing_intervention, evaluation,
                COALESCE(documentation, '') as documentation,
                created_by, created_at, updated_at
            FROM nurse_mid_documentations
        """)
        
        # Drop old table
        cursor.execute("DROP TABLE nurse_mid_documentations")
        
        # Rename new table
        cursor.execute("ALTER TABLE nurse_mid_documentations_new RENAME TO nurse_mid_documentations")
        
        print("✓ Table recreated with NULL allowed for documentation column")

        conn.commit()
        print("\n✓ Migration completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    migrate()

