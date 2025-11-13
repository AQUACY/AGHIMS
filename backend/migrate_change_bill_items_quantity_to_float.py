"""
Migration: Change bill_items.quantity from Integer to Float
This allows fractional quantities for services like additional services (e.g., 6.15 hours)
"""
from sqlalchemy import create_engine, text, inspect
from app.core.config import settings

def migrate():
    """Change bill_items.quantity column from Integer to Float"""
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
    )
    
    inspector = inspect(engine)
    
    # Check if table exists
    if "bill_items" not in inspector.get_table_names():
        print("✗ bill_items table does not exist")
        return
    
    print("Changing bill_items.quantity from Integer to Float...")
    
    with engine.connect() as conn:
        if "sqlite" in settings.DATABASE_URL:
            # SQLite doesn't support ALTER COLUMN directly, need to recreate table
            # First, check current column type
            result = conn.execute(text("PRAGMA table_info(bill_items)"))
            columns = {row[1]: row[2] for row in result.fetchall()}
            
            if columns.get('quantity') == 'REAL' or columns.get('quantity') == 'FLOAT':
                print("✓ quantity column is already Float")
                return
            
            # SQLite: Create new table with Float quantity, copy data, drop old, rename new
            conn.execute(text("""
                CREATE TABLE bill_items_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bill_id INTEGER NOT NULL,
                    item_code VARCHAR(50) NOT NULL,
                    item_name VARCHAR(500) NOT NULL,
                    category VARCHAR(50),
                    quantity REAL NOT NULL DEFAULT 1.0,
                    unit_price REAL NOT NULL,
                    total_price REAL NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bill_id) REFERENCES bills(id)
                )
            """))
            
            # Copy data, converting quantity to float
            conn.execute(text("""
                INSERT INTO bill_items_new 
                (id, bill_id, item_code, item_name, category, quantity, unit_price, total_price, created_at)
                SELECT 
                    id, bill_id, item_code, item_name, category, 
                    CAST(quantity AS REAL), unit_price, total_price, created_at
                FROM bill_items
            """))
            
            # Drop old table
            conn.execute(text("DROP TABLE bill_items"))
            
            # Rename new table
            conn.execute(text("ALTER TABLE bill_items_new RENAME TO bill_items"))
            
            # Recreate indexes
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_bill_items_bill_id ON bill_items(bill_id)"))
            
        else:
            # MySQL: Use ALTER COLUMN
            conn.execute(text("""
                ALTER TABLE bill_items 
                MODIFY COLUMN quantity DECIMAL(10,2) NOT NULL DEFAULT 1.0
            """))
        
        conn.commit()
        print("✓ Successfully changed bill_items.quantity to Float")

if __name__ == "__main__":
    migrate()

