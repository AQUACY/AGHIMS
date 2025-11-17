"""
Migration script to create blood_transfusion_types and blood_transfusion_requests tables
"""
import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import engine, Base
from app.models.blood_transfusion_type import BloodTransfusionType
from app.models.blood_transfusion_request import BloodTransfusionRequest

def create_tables():
    """Create the blood transfusion tables"""
    print("Creating blood_transfusion_types table...")
    BloodTransfusionType.__table__.create(bind=engine, checkfirst=True)
    print("✓ blood_transfusion_types table created")
    
    print("Creating blood_transfusion_requests table...")
    BloodTransfusionRequest.__table__.create(bind=engine, checkfirst=True)
    print("✓ blood_transfusion_requests table created")
    
    print("\nMigration completed successfully!")

if __name__ == "__main__":
    create_tables()

