"""
Migration script to allow multiple receipts per bill (remove unique constraint on bill_id)
"""
from app.core.database import engine
from sqlalchemy import text

if __name__ == "__main__":
    with engine.connect() as conn:
        try:
            # SQLite doesn't support DROP CONSTRAINT directly
            # We need to recreate the table without the unique constraint
            print("Migrating receipts table to allow multiple receipts per bill...")
            
            # Check if unique constraint exists by querying sqlite_master
            result = conn.execute(text("""
                SELECT sql FROM sqlite_master 
                WHERE type='table' AND name='receipts'
            """))
            table_sql = result.fetchone()
            
            if table_sql and 'UNIQUE' in table_sql[0]:
                print("Unique constraint found. Creating new table structure...")
                
                # Drop receipts_new if it exists from a previous failed migration
                conn.execute(text("DROP TABLE IF EXISTS receipts_new"))
                
                # Create new table
                conn.execute(text("""
                    CREATE TABLE receipts_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        bill_id INTEGER NOT NULL,
                        receipt_number VARCHAR NOT NULL UNIQUE,
                        amount_paid FLOAT NOT NULL,
                        payment_method VARCHAR,
                        issued_by INTEGER NOT NULL,
                        issued_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        refunded BOOLEAN DEFAULT 0,
                        refunded_at DATETIME,
                        refunded_by INTEGER,
                        FOREIGN KEY (bill_id) REFERENCES bills(id),
                        FOREIGN KEY (issued_by) REFERENCES users(id),
                        FOREIGN KEY (refunded_by) REFERENCES users(id)
                    )
                """))
                
                # Copy data (old table has 7 columns, new has 10)
                conn.execute(text("""
                    INSERT INTO receipts_new 
                    (id, bill_id, receipt_number, amount_paid, payment_method, issued_by, issued_at)
                    SELECT id, bill_id, receipt_number, amount_paid, payment_method, issued_by, issued_at
                    FROM receipts
                """))
                
                # Drop old table
                conn.execute(text("DROP TABLE receipts"))
                
                # Rename new table
                conn.execute(text("ALTER TABLE receipts_new RENAME TO receipts"))
                
                # Recreate indexes
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_receipts_bill_id ON receipts(bill_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_receipts_receipt_number ON receipts(receipt_number)"))
                
                conn.commit()
                print("✓ Migration completed successfully")
            else:
                print("No unique constraint found on bill_id. Table already allows multiple receipts.")
        except Exception as e:
            print(f"Error during migration: {e}")
            conn.rollback()
            raise
