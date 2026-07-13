"""
Migration: Create receipt_items table
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine, Base
from app.models.bill import ReceiptItem

def migrate():
    """Create receipt_items table"""
    print("=" * 60)
    print("Migration: Create receipt_items table")
    print("=" * 60)
    print()
    
    try:
        print("Creating receipt_items table...")
        Base.metadata.create_all(bind=engine, tables=[ReceiptItem.__table__])
        print("✓ receipt_items table created successfully")
        print()
        print("=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    migrate()
