"""
Migration script to add insurance_covered column to procedure_prices table
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

# Setup engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

def migrate():
    """Adds the 'insurance_covered' column to the procedure_prices table."""
    try:
        # First, check if the procedure_prices table exists
        if "sqlite" in settings.DATABASE_URL:
            with engine.connect() as connection:
                # Check if table exists
                result = connection.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='procedure_prices'"
                ))
                table_exists = result.fetchone() is not None
                
                if not table_exists:
                    print("✗ Error: 'procedure_prices' table does not exist in the database.")
                    print("\nPlease run 'python backend/init_db.py' first to create the database tables.")
                    print("The new column will be automatically included when tables are created.")
                    return
                
                # Get existing columns
                result = connection.execute(text("PRAGMA table_info(procedure_prices)"))
                columns = [row[1] for row in result.fetchall()]  # Column name is at index 1
                column_names = columns
        else:
            # For other databases (MySQL, PostgreSQL, etc.), use SQLAlchemy inspect
            from sqlalchemy import inspect as sql_inspect
            inspector = sql_inspect(engine)
            
            # Check if table exists
            if 'procedure_prices' not in inspector.get_table_names():
                print("✗ Error: 'procedure_prices' table does not exist in the database.")
                print("\nPlease run 'python backend/init_db.py' first to create the database tables.")
                print("The new column will be automatically included when tables are created.")
                return
            
            columns = inspector.get_columns('procedure_prices')
            column_names = [col['name'] for col in columns]

        if 'insurance_covered' not in column_names:
            with engine.begin() as connection:  # Use begin() for automatic transaction management
                # Add the column with default value 'yes'
                if "sqlite" in settings.DATABASE_URL:
                    connection.execute(
                        text("ALTER TABLE procedure_prices ADD COLUMN insurance_covered VARCHAR(10) DEFAULT 'yes'")
                    )
                else:
                    # For MySQL/PostgreSQL
                    connection.execute(
                        text("ALTER TABLE procedure_prices ADD COLUMN insurance_covered VARCHAR(10) DEFAULT 'yes'")
                    )
                
                # Update existing records to have 'yes' as default (all procedures are covered by default)
                connection.execute(
                    text("UPDATE procedure_prices SET insurance_covered = 'yes' WHERE insurance_covered IS NULL")
                )
                
            print("✓ 'insurance_covered' column added to 'procedure_prices' table.")
        else:
            print("✓ 'insurance_covered' column already exists in 'procedure_prices' table.")

        print("Migration complete!")

    except Exception as e:
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting database migration to add insurance_covered to procedure_prices...")
    migrate()

