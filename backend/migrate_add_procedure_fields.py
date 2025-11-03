"""
Database migration script to add procedure fields to encounters table
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Setup engine and session
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

def run_migration():
    """Adds the 'procedure_g_drg_code' and 'procedure_name' columns to the encounters table."""
    try:
        # First, check if the encounters table exists
        if "sqlite" in settings.DATABASE_URL:
            with engine.connect() as connection:
                # Check if table exists
                result = connection.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='encounters'"
                ))
                table_exists = result.fetchone() is not None
                
                if not table_exists:
                    print("✗ Error: 'encounters' table does not exist in the database.")
                    print("\nPlease run 'python backend/init_db.py' first to create the database tables.")
                    print("The new columns will be automatically included when tables are created.")
                    return
                
                # Get existing columns
                result = connection.execute(text("PRAGMA table_info(encounters)"))
                columns = [row[1] for row in result.fetchall()]  # Column name is at index 1
                column_names = columns
        else:
            # For other databases, use SQLAlchemy inspect
            from sqlalchemy import inspect as sql_inspect
            inspector = sql_inspect(engine)
            
            # Check if table exists
            if 'encounters' not in inspector.get_table_names():
                print("✗ Error: 'encounters' table does not exist in the database.")
                print("\nPlease run 'python backend/init_db.py' first to create the database tables.")
                print("The new columns will be automatically included when tables are created.")
                return
            
            columns = inspector.get_columns('encounters')
            column_names = [col['name'] for col in columns]

        if 'procedure_g_drg_code' not in column_names:
            with engine.connect() as connection:
                # Add the column
                connection.execute(
                    text("ALTER TABLE encounters ADD COLUMN procedure_g_drg_code VARCHAR")
                )
                connection.commit()
            print("✓ 'procedure_g_drg_code' column added to 'encounters' table.")
        else:
            print("✓ 'procedure_g_drg_code' column already exists in 'encounters' table.")

        if 'procedure_name' not in column_names:
            with engine.connect() as connection:
                # Add the column
                connection.execute(
                    text("ALTER TABLE encounters ADD COLUMN procedure_name VARCHAR")
                )
                connection.commit()
            print("✓ 'procedure_name' column added to 'encounters' table.")
        else:
            print("✓ 'procedure_name' column already exists in 'encounters' table.")

        print("Migration complete!")

    except Exception as e:
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting database migration to add procedure fields to encounters...")
    run_migration()

