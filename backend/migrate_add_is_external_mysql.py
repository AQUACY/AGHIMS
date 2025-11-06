"""
Migration: Add is_external column to prescriptions table (MySQL compatible)
This migration works for both SQLite and MySQL databases
"""
from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text, inspect

def migrate():
    """Add is_external column to prescriptions table if it doesn't exist"""
    try:
        # Check if column exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('prescriptions')]
        
        if 'is_external' not in columns:
            print("Adding is_external column to prescriptions table...")
            
            # Use raw SQL to add column
            # MySQL uses INT, SQLite uses INTEGER - both work
            with engine.connect() as conn:
                if settings.DATABASE_MODE.lower() == "mysql":
                    # MySQL syntax
                    conn.execute(text("ALTER TABLE prescriptions ADD COLUMN is_external INT DEFAULT 0 NOT NULL"))
                else:
                    # SQLite syntax
                    conn.execute(text("ALTER TABLE prescriptions ADD COLUMN is_external INTEGER DEFAULT 0"))
                conn.commit()
            
            print("✓ Successfully added is_external column")
        else:
            print("✓ is_external column already exists")
            
    except Exception as e:
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate()

