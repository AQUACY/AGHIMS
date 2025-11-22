"""
Migration script to create FBC (Full Blood Count) template
Based on the template structure from the lab report image
"""
import os
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Import all models to ensure relationships are properly configured
# This prevents SQLAlchemy relationship resolution errors
# Import Base first to register all models
from app.core.database import Base
# Then import all models - this ensures all relationships are registered
import app.models  # This imports all models from __init__.py including DoctorNoteEntry

from app.models.lab_result_template import LabResultTemplate
from app.models.user import User

# Database path
db_path = os.path.join(os.path.dirname(__file__), 'hms.db')

def migrate():
    """Create FBC template"""
    engine = create_engine(f'sqlite:///{db_path}')
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check if template already exists (by procedure name - primary matching field)
        existing = session.query(LabResultTemplate).filter(
            LabResultTemplate.procedure_name == 'Full Blood Count'
        ).first()
        
        if existing:
            print("FBC template already exists. Skipping migration.")
            session.close()
            return
        
        # Get first admin user for created_by
        admin_user = session.query(User).filter(
            User.role == 'Admin'
        ).first()
        
        if not admin_user:
            print("No admin user found. Please create an admin user first.")
            session.close()
            return
        
        # FBC template structure based on the image
        fbc_template_structure = {
            "fields": [
                # Basic Parameters
                {"name": "WBC", "label": "White Blood Cell Count", "type": "numeric", "unit": "10^3/uL", "reference_min": 3.00, "reference_max": 15.00, "order": 1, "group": "Basic Parameters", "required": False},
                {"name": "RBC", "label": "Red Blood Cell Count", "type": "numeric", "unit": "10^6/uL", "reference_min": 2.50, "reference_max": 5.50, "order": 2, "group": "Basic Parameters", "required": False},
                {"name": "HGB", "label": "Hemoglobin", "type": "numeric", "unit": "g/dL", "reference_min": 8.0, "reference_max": 17.0, "order": 3, "group": "Basic Parameters", "required": False},
                {"name": "HCT", "label": "Hematocrit", "type": "numeric", "unit": "%", "reference_min": 26.0, "reference_max": 50.0, "order": 4, "group": "Basic Parameters", "required": False},
                {"name": "MCV", "label": "Mean Corpuscular Volume", "type": "numeric", "unit": "FL", "reference_min": 86.0, "reference_max": 110.0, "order": 5, "group": "Basic Parameters", "required": False},
                {"name": "MCH", "label": "Mean Corpuscular Hemoglobin", "type": "numeric", "unit": "pg", "reference_min": 26.0, "reference_max": 38.0, "order": 6, "group": "Basic Parameters", "required": False},
                {"name": "MCHC", "label": "Mean Corpuscular Hemoglobin Concentration", "type": "numeric", "unit": "g/dL", "reference_min": 31.0, "reference_max": 37.0, "order": 7, "group": "Basic Parameters", "required": False},
                {"name": "PLT", "label": "Platelet Count", "type": "numeric", "unit": "10^3/uL", "reference_min": 150, "reference_max": 450, "order": 8, "group": "Basic Parameters", "required": False},
                
                # Red Cell Indices
                {"name": "RDW-SD", "label": "Red Cell Distribution Width (SD)", "type": "numeric", "unit": "fL", "reference_min": 37.0, "reference_max": 54.0, "order": 9, "group": "Red Cell Indices", "required": False},
                {"name": "RDW-CV", "label": "Red Cell Distribution Width (CV)", "type": "numeric", "unit": "%", "reference_min": 11.0, "reference_max": 16.0, "order": 10, "group": "Red Cell Indices", "required": False},
                {"name": "MicroR", "label": "Microcytic Red Cells", "type": "numeric", "unit": "%", "reference_min": 0.0, "reference_max": 999.9, "order": 11, "group": "Red Cell Indices", "required": False},
                {"name": "MacroR", "label": "Macrocytic Red Cells", "type": "numeric", "unit": "%", "reference_min": 0.0, "reference_max": 999.9, "order": 12, "group": "Red Cell Indices", "required": False},
                
                # Platelet Indices
                {"name": "PDW", "label": "Platelet Distribution Width", "type": "numeric", "unit": "FL", "reference_min": 9.0, "reference_max": 17.0, "order": 13, "group": "Platelet Indices", "required": False},
                {"name": "MPV", "label": "Mean Platelet Volume", "type": "numeric", "unit": "FL", "reference_min": 9.0, "reference_max": 13.0, "order": 14, "group": "Platelet Indices", "required": False},
                {"name": "P-LCR", "label": "Platelet Large Cell Ratio", "type": "numeric", "unit": "%", "reference_min": 13.0, "reference_max": 43.0, "order": 15, "group": "Platelet Indices", "required": False},
                {"name": "PCT", "label": "Plateletcrit", "type": "numeric", "unit": "%", "reference_min": 0.17, "reference_max": 0.35, "order": 16, "group": "Platelet Indices", "required": False},
                
                # Differential Count (Absolute)
                {"name": "NEUT#", "label": "Neutrophils (Absolute)", "type": "numeric", "unit": "10^3/uL", "reference_min": 1.50, "reference_max": 7.00, "order": 17, "group": "Differential Count (Absolute)", "required": False},
                {"name": "LYMPH#", "label": "Lymphocytes (Absolute)", "type": "numeric", "unit": "10^3/uL", "reference_min": 1.00, "reference_max": 3.70, "order": 18, "group": "Differential Count (Absolute)", "required": False},
                {"name": "MONO#", "label": "Monocytes (Absolute)", "type": "numeric", "unit": "10^3/uL", "reference_min": 0.00, "reference_max": 0.70, "order": 19, "group": "Differential Count (Absolute)", "required": False},
                {"name": "EO#", "label": "Eosinophils (Absolute)", "type": "numeric", "unit": "10^3/uL", "reference_min": 0.00, "reference_max": 0.40, "order": 20, "group": "Differential Count (Absolute)", "required": False},
                {"name": "BASO#", "label": "Basophils (Absolute)", "type": "numeric", "unit": "10^3/uL", "reference_min": 0.00, "reference_max": 0.10, "order": 21, "group": "Differential Count (Absolute)", "required": False},
                
                # Differential Count (Percentage)
                {"name": "NEUT%", "label": "Neutrophils (%)", "type": "numeric", "unit": "%", "reference_min": 37.0, "reference_max": 72.0, "order": 22, "group": "Differential Count (%)", "required": False},
                {"name": "LYMPH%", "label": "Lymphocytes (%)", "type": "numeric", "unit": "%", "reference_min": 20.0, "reference_max": 50.0, "order": 23, "group": "Differential Count (%)", "required": False},
                {"name": "MONO%", "label": "Monocytes (%)", "type": "numeric", "unit": "%", "reference_min": 0.0, "reference_max": 14.0, "order": 24, "group": "Differential Count (%)", "required": False},
                {"name": "EO%", "label": "Eosinophils (%)", "type": "numeric", "unit": "%", "reference_min": 0.0, "reference_max": 6.0, "order": 25, "group": "Differential Count (%)", "required": False},
                {"name": "BASO%", "label": "Basophils (%)", "type": "numeric", "unit": "%", "reference_min": 0.0, "reference_max": 1.0, "order": 26, "group": "Differential Count (%)", "required": False},
                
                # Additional Parameters
                {"name": "IG#", "label": "Immature Granulocytes (Absolute)", "type": "numeric", "unit": "10^3/uL", "reference_min": 0.00, "reference_max": 7.00, "order": 27, "group": "Additional Parameters", "required": False},
                {"name": "IG%", "label": "Immature Granulocytes (%)", "type": "numeric", "unit": "%", "reference_min": 0.0, "reference_max": 72.0, "order": 28, "group": "Additional Parameters", "required": False},
            ],
            "message_fields": [
                {"name": "WBC IP Message", "label": "WBC IP Message", "type": "text", "order": 1, "required": False},
                {"name": "RBC IP Message", "label": "RBC IP Message", "type": "text", "order": 2, "required": False},
                {"name": "PLT IP Message", "label": "PLT IP Message", "type": "text", "order": 3, "required": False},
            ],
            "patient_fields": ["age", "ward", "doctor"]
        }
        
        # Create the template
        # Templates are matched by procedure_name, not G-DRG code
        fbc_template = LabResultTemplate(
            g_drg_code=None,  # Optional - can be set if needed for reference
            procedure_name="Full Blood Count",  # PRIMARY MATCHING FIELD
            template_name="FBC",
            template_structure=fbc_template_structure,
            created_by=admin_user.id,
            is_active=1
        )
        
        session.add(fbc_template)
        session.commit()
        
        print("FBC template created successfully!")
        print(f"Template ID: {fbc_template.id}")
        print("Template matched by procedure name: 'Full Blood Count'")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    migrate()

