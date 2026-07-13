"""
Migration: add cancellation fields to admission_recommendations table (MySQL compatible)
This migration works for both SQLite and MySQL databases
"""
from app.core.config import settings
from app.core.database import engine
from sqlalchemy import text, inspect


def migrate():
    """Add cancellation fields to admission_recommendations table if they don't exist"""
    try:
        # Check if table exists
        inspector = inspect(engine)
        if 'admission_recommendations' not in inspector.get_table_names():
            print("Table admission_recommendations does not exist. Skipping migration.")
            return
        
        # Get existing columns
        columns = [col['name'] for col in inspector.get_columns('admission_recommendations')]
        existing_cols = set(columns)
        
        # Add cancelled column if not exists
        if "cancelled" not in existing_cols:
            print("Adding cancelled column to admission_recommendations...")
            
            with engine.connect() as conn:
                if settings.DATABASE_MODE.lower() == "mysql":
                    # MySQL syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN cancelled INT DEFAULT 0 NOT NULL"))
                else:
                    # SQLite syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN cancelled INTEGER DEFAULT 0 NOT NULL"))
                conn.commit()
            
            print("✓ Added cancelled column to admission_recommendations")
        else:
            print("✓ cancelled column already exists")
        
        # Add cancelled_by column if not exists
        if "cancelled_by" not in existing_cols:
            print("Adding cancelled_by column to admission_recommendations...")
            
            with engine.connect() as conn:
                if settings.DATABASE_MODE.lower() == "mysql":
                    # MySQL syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN cancelled_by INT NULL"))
                else:
                    # SQLite syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN cancelled_by INTEGER"))
                conn.commit()
            
            print("✓ Added cancelled_by column to admission_recommendations")
        else:
            print("✓ cancelled_by column already exists")
        
        # Add cancelled_at column if not exists
        if "cancelled_at" not in existing_cols:
            print("Adding cancelled_at column to admission_recommendations...")
            
            with engine.connect() as conn:
                if settings.DATABASE_MODE.lower() == "mysql":
                    # MySQL syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN cancelled_at DATETIME NULL"))
                else:
                    # SQLite syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN cancelled_at DATETIME"))
                conn.commit()
            
            print("✓ Added cancelled_at column to admission_recommendations")
        else:
            print("✓ cancelled_at column already exists")
        
        # Add cancellation_reason column if not exists
        if "cancellation_reason" not in existing_cols:
            print("Adding cancellation_reason column to admission_recommendations...")
            
            with engine.connect() as conn:
                if settings.DATABASE_MODE.lower() == "mysql":
                    # MySQL syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN cancellation_reason VARCHAR(500) NULL"))
                else:
                    # SQLite syntax
                    conn.execute(text("ALTER TABLE admission_recommendations ADD COLUMN cancellation_reason VARCHAR(500)"))
                conn.commit()
            
            print("✓ Added cancellation_reason column to admission_recommendations")
        else:
            print("✓ cancellation_reason column already exists")
        
        print("Migration completed successfully")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate()

