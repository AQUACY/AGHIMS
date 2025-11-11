"""
Migration: add confirmed_by and confirmed_at columns to admission_recommendations table (MySQL compatible)
This migration works for both SQLite and MySQL databases
"""
from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text, inspect


def migrate():
    """Add confirmed_by and confirmed_at columns to admission_recommendations table if they don't exist"""
    try:
        # Check if table exists
        inspector = inspect(engine)
        if 'admission_recommendations' not in inspector.get_table_names():
            print("Table admission_recommendations does not exist. Skipping migration.")
            return
        
        # Get existing columns
        columns = [col['name'] for col in inspector.get_columns('admission_recommendations')]
        existing_cols = set(columns)
        
        # Add confirmed_by column if not exists
        if "confirmed_by" not in existing_cols:
            print("Adding confirmed_by column to admission_recommendations...")
            
            with engine.connect() as conn:
                if settings.DATABASE_MODE.lower() == "mysql":
                    # MySQL syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN confirmed_by INT NULL"))
                    conn.execute(text("ALTER TABLE admission_recommendations ADD INDEX idx_confirmed_by (confirmed_by)"))
                else:
                    # SQLite syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN confirmed_by INTEGER"))
                conn.commit()
            
            print("✓ Added confirmed_by column to admission_recommendations")
        else:
            print("✓ confirmed_by column already exists")
        
        # Add confirmed_at column if not exists
        if "confirmed_at" not in existing_cols:
            print("Adding confirmed_at column to admission_recommendations...")
            
            with engine.connect() as conn:
                if settings.DATABASE_MODE.lower() == "mysql":
                    # MySQL syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN confirmed_at DATETIME NULL"))
                else:
                    # SQLite syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN confirmed_at DATETIME"))
                conn.commit()
            
            print("✓ Added confirmed_at column to admission_recommendations")
        else:
            print("✓ confirmed_at column already exists")
        
        print("Migration completed successfully")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate()

