"""
Migration script to add diagnoses_data column to consultation_templates table
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

# Setup engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

def migrate():
    """Adds the 'diagnoses_data' column to the consultation_templates table."""
    try:
        # First, check if the consultation_templates table exists
        if "sqlite" in settings.DATABASE_URL:
            with engine.connect() as connection:
                # Check if table exists
                result = connection.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='consultation_templates'"
                ))
                table_exists = result.fetchone() is not None
                
                if not table_exists:
                    print("✗ Error: 'consultation_templates' table does not exist in the database.")
                    print("\nPlease run the consultation templates table creation migration first.")
                    return
                
                # Get existing columns
                result = connection.execute(text("PRAGMA table_info(consultation_templates)"))
                columns = [row[1] for row in result.fetchall()]  # Column name is at index 1
                column_names = columns
        else:
            # For other databases (MySQL, PostgreSQL, etc.), use SQLAlchemy inspect
            from sqlalchemy import inspect as sql_inspect
            inspector = sql_inspect(engine)
            
            # Check if table exists
            if 'consultation_templates' not in inspector.get_table_names():
                print("✗ Error: 'consultation_templates' table does not exist in the database.")
                print("\nPlease run the consultation templates table creation migration first.")
                return
            
            columns = inspector.get_columns('consultation_templates')
            column_names = [col['name'] for col in columns]

        if 'diagnoses_data' not in column_names:
            with engine.connect() as connection:
                # Add the column (TEXT type for JSON storage)
                if "sqlite" in settings.DATABASE_URL:
                    connection.execute(
                        text("ALTER TABLE consultation_templates ADD COLUMN diagnoses_data TEXT")
                    )
                else:
                    # For MySQL/PostgreSQL - use TEXT or LONGTEXT for MySQL
                    if "mysql" in settings.DATABASE_URL.lower():
                        connection.execute(
                            text("ALTER TABLE consultation_templates ADD COLUMN diagnoses_data LONGTEXT")
                        )
                    else:
                        # PostgreSQL
                        connection.execute(
                            text("ALTER TABLE consultation_templates ADD COLUMN diagnoses_data TEXT")
                        )
                connection.commit()
                
            print("✓ 'diagnoses_data' column added to 'consultation_templates' table.")
        else:
            print("✓ 'diagnoses_data' column already exists in 'consultation_templates' table.")

        print("Migration complete!")

    except Exception as e:
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting database migration to add diagnoses_data to consultation_templates...")
    migrate()

