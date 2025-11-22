"""
Migration script to create Urine Chemistry lab result template
Run this script to create the Urine Chemistry template in the database
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import SessionLocal
from app.models.lab_result_template import LabResultTemplate
from app.models.user import User

def migrate():
    """Create Urine Chemistry template"""
    db = SessionLocal()
    
    try:
        # Get admin user (or first user)
        admin_user = db.query(User).filter(User.role == "Admin").first()
        if not admin_user:
            admin_user = db.query(User).first()
        
        if not admin_user:
            print("ERROR: No user found in database. Please run init_db.py first.")
            return
        
        # Check if template already exists
        existing = db.query(LabResultTemplate).filter(
            LabResultTemplate.procedure_name == "Urine Chemistry"
        ).first()
        
        if existing:
            print(f"Urine Chemistry template already exists (ID: {existing.id})")
            print("Skipping creation.")
            return
        
        # Define Urine Chemistry template structure
        urine_chemistry_template_structure = {
            "fields": [
                # URINE CHEMISTRY Section
                {
                    "name": "Bilirubin",
                    "label": "Bilirubin",
                    "type": "text",  # Will be rendered as select in frontend if options provided
                    "options": ["-ve", "+", "++", "+++", "++++"],
                    "order": 1,
                    "group": "Urine Chemistry",
                    "required": False
                },
                {
                    "name": "Urobilinogen",
                    "label": "Urobilinogen",
                    "type": "text",
                    "options": ["Normal", "Increase"],
                    "order": 2,
                    "group": "Urine Chemistry",
                    "required": False
                },
                {
                    "name": "Specific_Gravity",
                    "label": "Specific Gravity",
                    "type": "numeric",
                    "unit": "",
                    "order": 3,
                    "group": "Urine Chemistry",
                    "required": False,
                    "hint": "e.g., 1.00, 1.005"
                },
                {
                    "name": "PH",
                    "label": "pH",
                    "type": "text",
                    "options": ["5.0", "6.0", "6.5", "7.0", "7.5", "8.0", "8.5"],
                    "order": 4,
                    "group": "Urine Chemistry",
                    "required": False
                },
                {
                    "name": "Glucose",
                    "label": "Glucose",
                    "type": "text",
                    "options": ["-ve", "+", "++", "+++", "++++"],
                    "order": 5,
                    "group": "Urine Chemistry",
                    "required": False
                },
                {
                    "name": "Protein",
                    "label": "Protein",
                    "type": "text",
                    "options": ["-ve", "Trace", "+", "++", "+++", "++++"],
                    "order": 6,
                    "group": "Urine Chemistry",
                    "required": False
                },
                {
                    "name": "Nitrite",
                    "label": "Nitrite",
                    "type": "text",
                    "options": ["-ve", "+ve"],
                    "order": 7,
                    "group": "Urine Chemistry",
                    "required": False
                },
                {
                    "name": "Ketone",
                    "label": "Ketone",
                    "type": "text",
                    "options": ["-ve", "Trace (0.5)", "1.5", "4.0", "8.0", "16"],
                    "order": 8,
                    "group": "Urine Chemistry",
                    "required": False
                },
                {
                    "name": "Blood",
                    "label": "Blood",
                    "type": "text",
                    "options": ["-ve", "Trace (10)", "small (25)", "moderate (80)", "Large (200)"],
                    "order": 9,
                    "group": "Urine Chemistry",
                    "required": False,
                    "hint": "non-hemolyzed / hemolyzed"
                },
                {
                    "name": "Leucocytes",
                    "label": "Leucocytes",
                    "type": "text",
                    "options": ["-ve", "Trace (15)", "small (70)", "moderate (125)", "Large (500)"],
                    "order": 10,
                    "group": "Urine Chemistry",
                    "required": False
                },
                {
                    "name": "Appearance",
                    "label": "Appearance",
                    "type": "text",
                    "options": ["Clear", "Cloudy", "hazy", "bloody"],
                    "order": 11,
                    "group": "Urine Chemistry",
                    "required": False
                },
                {
                    "name": "Colour",
                    "label": "Colour",
                    "type": "text",
                    "options": ["amber", "Straw", "Light amber"],
                    "order": 12,
                    "group": "Urine Chemistry",
                    "required": False
                },
                
                # DEPOSIT Section - All text fields
                {
                    "name": "Deposit",
                    "label": "Deposit",
                    "type": "text",
                    "order": 13,
                    "group": "Deposit",
                    "required": False
                },
                {
                    "name": "PUS_Cell",
                    "label": "PUS Cell",
                    "type": "text",
                    "order": 14,
                    "group": "Deposit",
                    "required": False
                },
                {
                    "name": "Epithelial_Cell",
                    "label": "Epithelial Cell",
                    "type": "text",
                    "order": 15,
                    "group": "Deposit",
                    "required": False
                },
                {
                    "name": "RBC",
                    "label": "RBC",
                    "type": "text",
                    "order": 16,
                    "group": "Deposit",
                    "required": False
                },
                {
                    "name": "Cast",
                    "label": "Cast",
                    "type": "text",
                    "order": 17,
                    "group": "Deposit",
                    "required": False
                },
                {
                    "name": "Crystal",
                    "label": "Crystal",
                    "type": "text",
                    "order": 18,
                    "group": "Deposit",
                    "required": False
                },
                {
                    "name": "T_Vaginalis",
                    "label": "T. Vaginalis",
                    "type": "text",
                    "order": 19,
                    "group": "Deposit",
                    "required": False
                },
                {
                    "name": "Candida",
                    "label": "Candida",
                    "type": "text",
                    "order": 20,
                    "group": "Deposit",
                    "required": False
                },
                {
                    "name": "S_Haematobium",
                    "label": "S. Haematobium",
                    "type": "text",
                    "order": 21,
                    "group": "Deposit",
                    "required": False
                },
            ],
            "message_fields": [],
            "patient_fields": ["age", "ward", "doctor"]
        }
        
        # Create the template
        urine_template = LabResultTemplate(
            g_drg_code=None,  # Optional - can be set if needed for reference
            procedure_name="Urine Chemistry",  # PRIMARY MATCHING FIELD
            template_name="Urine Chemistry",
            template_structure=urine_chemistry_template_structure,
            created_by=admin_user.id,
            is_active=1
        )
        
        db.add(urine_template)
        db.commit()
        db.refresh(urine_template)
        
        print("=" * 70)
        print("Urine Chemistry template created successfully!")
        print("=" * 70)
        print(f"Template ID: {urine_template.id}")
        print(f"Template Name: {urine_template.template_name}")
        print(f"Procedure Name: {urine_template.procedure_name}")
        print(f"Total Fields: {len(urine_chemistry_template_structure['fields'])}")
        print()
        print("Fields created:")
        print(f"  Urine Chemistry: {len([f for f in urine_chemistry_template_structure['fields'] if f['group'] == 'Urine Chemistry'])} fields")
        print(f"  Deposit: {len([f for f in urine_chemistry_template_structure['fields'] if f['group'] == 'Deposit'])} fields")
        print("=" * 70)
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: Failed to create Urine Chemistry template: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Creating Urine Chemistry template...")
    migrate()
    print("Migration complete!")

