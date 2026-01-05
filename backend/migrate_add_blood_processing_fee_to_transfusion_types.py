"""
Migration script to add blood_processing_fee_gdrg_code column to blood_transfusion_types table
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

# Setup engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

def migrate():
    """Adds the 'blood_processing_fee_gdrg_code' column to the blood_transfusion_types table."""
    try:
        # First, check if the blood_transfusion_types table exists
        if "sqlite" in settings.DATABASE_URL:
            with engine.connect() as connection:
                # Check if table exists
                result = connection.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='blood_transfusion_types'"
                ))
                table_exists = result.fetchone() is not None
                
                if not table_exists:
                    print("✗ Error: 'blood_transfusion_types' table does not exist in the database.")
                    print("\nPlease run the blood transfusion tables creation migration first.")
                    return
                
                # Get existing columns
                result = connection.execute(text("PRAGMA table_info(blood_transfusion_types)"))
                columns = [row[1] for row in result.fetchall()]  # Column name is at index 1
                column_names = columns
        else:
            # For other databases (MySQL, PostgreSQL, etc.), use SQLAlchemy inspect
            from sqlalchemy import inspect as sql_inspect
            inspector = sql_inspect(engine)
            
            # Check if table exists
            if 'blood_transfusion_types' not in inspector.get_table_names():
                print("✗ Error: 'blood_transfusion_types' table does not exist in the database.")
                print("\nPlease run the blood transfusion tables creation migration first.")
                return
            
            columns = inspector.get_columns('blood_transfusion_types')
            column_names = [col['name'] for col in columns]

        if 'blood_processing_fee_gdrg_code' not in column_names:
            with engine.connect() as connection:
                # Add the column (VARCHAR(50) for G-DRG code)
                if "sqlite" in settings.DATABASE_URL:
                    connection.execute(
                        text("ALTER TABLE blood_transfusion_types ADD COLUMN blood_processing_fee_gdrg_code VARCHAR(50)")
                    )
                else:
                    # For MySQL/PostgreSQL
                    if "mysql" in settings.DATABASE_URL.lower():
                        connection.execute(
                            text("ALTER TABLE blood_transfusion_types ADD COLUMN blood_processing_fee_gdrg_code VARCHAR(50) NULL")
                        )
                    else:
                        # PostgreSQL
                        connection.execute(
                            text("ALTER TABLE blood_transfusion_types ADD COLUMN blood_processing_fee_gdrg_code VARCHAR(50)")
                        )
                connection.commit()
                
            print("✓ 'blood_processing_fee_gdrg_code' column added to 'blood_transfusion_types' table.")
        else:
            print("✓ 'blood_processing_fee_gdrg_code' column already exists in 'blood_transfusion_types' table.")

        print("Migration complete!")

    except Exception as e:
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting database migration to add blood_processing_fee_gdrg_code to blood_transfusion_types...")
    migrate()

