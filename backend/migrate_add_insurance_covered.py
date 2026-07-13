"""
Migration script to add insurance_covered column to product_prices table
"""
import sqlite3
from pathlib import Path

def migrate():
    db_path = Path(__file__).parent / "hms.db"
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(product_prices)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'insurance_covered' not in columns:
            print("Adding insurance_covered column to product_prices table...")
            cursor.execute("ALTER TABLE product_prices ADD COLUMN insurance_covered VARCHAR(10) DEFAULT 'yes'")
            conn.commit()
            
            # Update existing records to have 'yes' as default (all products are covered by default)
            cursor.execute("UPDATE product_prices SET insurance_covered = 'yes' WHERE insurance_covered IS NULL")
            conn.commit()
            
            print("Successfully added insurance_covered column")
        else:
            print("insurance_covered column already exists")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

