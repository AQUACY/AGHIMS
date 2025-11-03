"""
Migration script to add receipt_items table
"""
from app.core.database import engine, Base
from app.models.bill import ReceiptItem

if __name__ == "__main__":
    print("Creating receipt_items table...")
    Base.metadata.create_all(bind=engine, tables=[ReceiptItem.__table__])
    print("✓ receipt_items table created successfully")
