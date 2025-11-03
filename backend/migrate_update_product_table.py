"""
Database migration script to update product_prices table structure
Adds new columns and renames existing ones for product-specific structure
"""
from sqlalchemy import create_engine, text
from app.core.config import settings

# Setup engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

def run_migration():
    """Updates product_prices table to match new structure"""
    try:
        # Check if table exists
        if "sqlite" in settings.DATABASE_URL:
            with engine.connect() as connection:
                # Check if table exists
                result = connection.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='product_prices'"
                ))
                table_exists = result.fetchone() is not None
                
                if not table_exists:
                    print("✗ 'product_prices' table does not exist.")
                    print("Run 'python backend/init_db.py' to create tables with new structure.")
                    return
                
                # Get existing columns
                result = connection.execute(text("PRAGMA table_info(product_prices)"))
                columns = {row[1]: row for row in result.fetchall()}  # Column name as key
                
                # Add new columns if they don't exist
                new_columns = {
                    'sub_category_1': 'VARCHAR',
                    'sub_category_2': 'VARCHAR',
                    'product_id': 'VARCHAR',
                    'product_name': 'VARCHAR',
                    'medication_code': 'VARCHAR',
                    'formulation': 'VARCHAR',
                    'strength': 'VARCHAR',
                    'claim_amount': 'FLOAT',
                    'nhia_claim': 'VARCHAR',
                    'bill_effective': 'VARCHAR',
                }
                
                for col_name, col_type in new_columns.items():
                    if col_name not in columns:
                        connection.execute(text(
                            f"ALTER TABLE product_prices ADD COLUMN {col_name} {col_type}"
                        ))
                        print(f"✓ Added column '{col_name}' to 'product_prices' table.")
                    else:
                        print(f"✓ Column '{col_name}' already exists.")
                
                # Migrate data if old columns exist
                if 'g_drg_code' in columns and 'medication_code' not in columns:
                    # Copy g_drg_code to medication_code
                    connection.execute(text(
                        "UPDATE product_prices SET medication_code = g_drg_code WHERE medication_code IS NULL"
                    ))
                    print("✓ Migrated g_drg_code data to medication_code.")
                
                if 'service_name' in columns and 'product_name' not in columns:
                    # Copy service_name to product_name
                    connection.execute(text(
                        "UPDATE product_prices SET product_name = service_name WHERE product_name IS NULL"
                    ))
                    print("✓ Migrated service_name data to product_name.")
                
                connection.commit()
                
        else:
            # For other databases, similar logic
            from sqlalchemy import inspect as sql_inspect
            inspector = sql_inspect(engine)
            
            if 'product_prices' not in inspector.get_table_names():
                print("✗ 'product_prices' table does not exist.")
                print("Run 'python backend/init_db.py' to create tables with new structure.")
                return
            
            # Similar migration for other databases
            print("Migration for non-SQLite databases - manual migration may be required.")
        
        print("Migration complete!")

    except Exception as e:
        print(f"✗ Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting database migration to update product_prices table structure...")
    run_migration()

