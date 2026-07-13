"""
Migration: add extended vitals fields
Fields: respiration, bmi, spo2, rbs, fbs, upt, rdt_malaria, retro_rdt
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy import text
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "hms.db"


def add_column_if_missing(conn, table: str, column_def: str, column_name: str):
    result = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    cols = {row[1] for row in result}
    if column_name not in cols:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_def}"))


def migrate():
    """Add extended vitals fields (SQLite version)"""
    print("=" * 60)
    print("Migration: Add extended vitals fields")
    print("=" * 60)
    print()
    
    # Check if SQLite database exists
    if not DB_PATH.exists():
        print("⚠ SQLite database not found. This migration is SQLite-specific.")
        print("  For MySQL, use migrate_update_vitals_fields_mysql.py instead.")
        print("  Skipping this migration.")
        return
    
    try:
        engine = create_engine(f"sqlite:///{DB_PATH}")
        
        # Check if vitals table exists without reflecting all tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='vitals'
            """))
            if result.fetchone() is None:
                print("⚠ vitals table does not exist, skipping")
                return
        
        # Use direct approach to avoid issues with broken foreign keys in other tables
        # This avoids meta.reflect() which tries to reflect all tables
        with engine.begin() as conn:
            # Check columns directly using PRAGMA
            result = conn.execute(text("PRAGMA table_info(vitals)"))
            existing_cols = {row[1] for row in result.fetchall()}
            
            columns_to_add = [
                ("respiration", "INTEGER"),
                ("bmi", "FLOAT"),
                ("spo2", "INTEGER"),
                ("rbs", "FLOAT"),
                ("fbs", "FLOAT"),
                ("upt", "TEXT"),
                ("rdt_malaria", "TEXT"),
                ("retro_rdt", "TEXT"),
            ]
            
            for col_name, col_type in columns_to_add:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE vitals ADD COLUMN {col_name} {col_type}"))
                    print(f"✓ Added {col_name} column")
                else:
                    print(f"✓ Column {col_name} already exists")
        
        print("✓ Migration completed successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate()


