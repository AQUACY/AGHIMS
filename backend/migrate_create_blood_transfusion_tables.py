"""
Migration: Create blood_transfusion_types and blood_transfusion_requests tables
"""
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import from app
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine, Base
from app.models.blood_transfusion_type import BloodTransfusionType
from app.models.blood_transfusion_request import BloodTransfusionRequest

def migrate():
    """Create the blood transfusion tables"""
    print("=" * 60)
    print("Migration: Create blood transfusion tables")
    print("=" * 60)
    print()
    
    try:
        print("Creating blood_transfusion_types table...")
        BloodTransfusionType.__table__.create(bind=engine, checkfirst=True)
        print("✓ blood_transfusion_types table created")
        
        print("Creating blood_transfusion_requests table...")
        BloodTransfusionRequest.__table__.create(bind=engine, checkfirst=True)
        print("✓ blood_transfusion_requests table created")
        
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

