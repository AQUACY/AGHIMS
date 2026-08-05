"""
Initialize default module settings in the database
Run this script to create default module settings for all system modules
"""
from app.core.database import SessionLocal
from sqlalchemy import text
from app.core.config import settings
import pymysql
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Default modules configuration
DEFAULT_MODULES = [
    {
        "module_key": "patients",
        "module_name": "Patient Management",
        "description": "Patient registration, search, and profile management",
        "category": "core",
        "display_order": 1
    },
    {
        "module_key": "encounters",
        "module_name": "Encounters",
        "description": "Patient encounter management and calendar",
        "category": "core",
        "display_order": 2
    },
    {
        "module_key": "vitals",
        "module_name": "Vitals",
        "description": "Patient vital signs recording",
        "category": "clinical",
        "display_order": 3
    },
    {
        "module_key": "consultation",
        "module_name": "Consultation",
        "description": "Doctor consultation, diagnoses, and prescriptions",
        "category": "clinical",
        "display_order": 4
    },
    {
        "module_key": "billing",
        "module_name": "Billing",
        "description": "Bill generation and payment processing",
        "category": "administrative",
        "display_order": 5
    },
    {
        "module_key": "pharmacy",
        "module_name": "Pharmacy",
        "description": "Pharmacy operations, dispensing, and inventory",
        "category": "clinical",
        "display_order": 6
    },
    {
        "module_key": "lab",
        "module_name": "Laboratory",
        "description": "Lab investigations and results",
        "category": "clinical",
        "display_order": 7
    },
    {
        "module_key": "scan",
        "module_name": "Scan",
        "description": "Scan investigations and results",
        "category": "clinical",
        "display_order": 8
    },
    {
        "module_key": "xray",
        "module_name": "X-Ray",
        "description": "X-Ray investigations and results",
        "category": "clinical",
        "display_order": 9
    },
    {
        "module_key": "claims",
        "module_name": "Claims",
        "description": "NHIA claims generation and management",
        "category": "administrative",
        "display_order": 10
    },
    {
        "module_key": "ipd",
        "module_name": "Inpatient Department (IPD)",
        "description": "Inpatient ward management, admissions, and care",
        "category": "clinical",
        "display_order": 11
    },
    {
        "module_key": "price_list",
        "module_name": "Price List Management",
        "description": "Manage procedure, surgery, product, and DRG prices",
        "category": "administrative",
        "display_order": 12
    },
    {
        "module_key": "inventory",
        "module_name": "Inventory Management",
        "description": "Store stock and inventory management",
        "category": "administrative",
        "display_order": 13
    },
    {
        "module_key": "staff",
        "module_name": "Staff Management",
        "description": "User and staff account management",
        "category": "administrative",
        "display_order": 14
    },
    {
        "module_key": "audit_logs",
        "module_name": "Audit Logs",
        "description": "System activity and audit trail",
        "category": "administrative",
        "display_order": 15
    },
    {
        "module_key": "database",
        "module_name": "Database Management",
        "description": "Database backup, sync, and maintenance",
        "category": "administrative",
        "display_order": 16
    },
    {
        "module_key": "mis_reports",
        "module_name": "MIS Reports",
        "description": "Management Information System reports",
        "category": "reports",
        "display_order": 17
    },
    {
        "module_key": "icd10_mapping",
        "module_name": "ICD10-DRG Mapping",
        "description": "ICD10 to DRG code mapping management",
        "category": "administrative",
        "display_order": 18
    },
    {
        "module_key": "wards",
        "module_name": "Ward Management",
        "description": "Ward and bed configuration",
        "category": "administrative",
        "display_order": 19
    },
    {
        "module_key": "stores",
        "module_name": "Store Management",
        "description": "Store configuration and management",
        "category": "administrative",
        "display_order": 20
    },
    {
        "module_key": "blood_transfusion",
        "module_name": "Blood Transfusion",
        "description": "Blood transfusion request management",
        "category": "clinical",
        "display_order": 21
    },
    {
        "module_key": "additional_services",
        "module_name": "Additional Services",
        "description": "Additional service configuration for IPD",
        "category": "administrative",
        "display_order": 22
    },
    {
        "module_key": "ghims",
        "module_name": "GHIMS Card Numbers",
        "description": "When enabled, new patients use manual GHIMS card numbers (e.g. E-0032-26050735) instead of auto-generated HMS cards. When disabled, HMS auto-generates card numbers as usual.",
        "category": "core",
        "display_order": 23
    },
    {
        "module_key": "ai_claims_vetting",
        "module_name": "AI Claims Vetting",
        "description": "Optional AI-assisted claims vetting for ZOOM specialty cleanup, Ghana Card→HIN, and later clinical validation. Recommendations require human approval.",
        "category": "administrative",
        "display_order": 24
    },
]


def init_module_settings():
    """Initialize default module settings using direct database connection"""
    # Get database connection details
    db_host = os.getenv('DB_HOST') or os.getenv('MYSQL_HOST', 'localhost')
    db_user = os.getenv('DB_USER') or os.getenv('MYSQL_USER', 'root')
    db_name = os.getenv('DB_NAME') or os.getenv('MYSQL_DATABASE', 'hms')
    db_password = os.getenv('DB_PASSWORD') or os.getenv('MYSQL_PASSWORD', '')
    
    # Check if using SQLite or MySQL
    is_sqlite = 'sqlite' in settings.DATABASE_URL.lower()
    
    conn = None
    cursor = None
    
    try:
        if is_sqlite:
            # Use SQLAlchemy session for SQLite
            from app.core.database import SessionLocal
            from app.models.module_settings import ModuleSettings
            
            db = SessionLocal()
            try:
                print("Initializing module settings (SQLite)...")
                
                for module_data in DEFAULT_MODULES:
                    existing = db.query(ModuleSettings).filter(
                        ModuleSettings.module_key == module_data["module_key"]
                    ).first()
                    
                    if not existing:
                        module = ModuleSettings(
                            module_key=module_data["module_key"],
                            module_name=module_data["module_name"],
                            description=module_data.get("description", ""),
                            is_active=module_data["module_key"] not in ("ghims", "ai_claims_vetting"),
                            allow_read=True,
                            allow_create=True,
                            allow_update=True,
                            allow_delete=True,
                            category=module_data.get("category", "core"),
                            display_order=module_data.get("display_order", 0)
                        )
                        db.add(module)
                        print(f"✓ Created module setting: {module_data['module_name']}")
                    else:
                        if existing.display_order != module_data.get("display_order", 0):
                            existing.display_order = module_data.get("display_order", 0)
                            print(f"✓ Updated display order for: {module_data['module_name']}")
                
                db.commit()
                print("\n✓ Module settings initialization complete!")
            finally:
                db.close()
        else:
            # Use direct MySQL connection to avoid model import issues
            print("Initializing module settings (MySQL)...")
            conn = pymysql.connect(
                host=db_host,
                user=db_user,
                password=db_password,
                database=db_name,
                charset='utf8mb4'
            )
            cursor = conn.cursor()
            
            # Ensure table exists (create if it doesn't)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS module_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    module_key VARCHAR(100) UNIQUE NOT NULL,
                    module_name VARCHAR(200) NOT NULL,
                    description TEXT,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    allow_read BOOLEAN NOT NULL DEFAULT TRUE,
                    allow_create BOOLEAN NOT NULL DEFAULT TRUE,
                    allow_update BOOLEAN NOT NULL DEFAULT TRUE,
                    allow_delete BOOLEAN NOT NULL DEFAULT TRUE,
                    category VARCHAR(50),
                    display_order INT DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_module_key (module_key)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)
            print("✓ Verified module_settings table exists")
            
            for module_data in DEFAULT_MODULES:
                # Check if module exists
                cursor.execute("""
                    SELECT id FROM module_settings 
                    WHERE module_key = %s
                """, (module_data["module_key"],))
                existing = cursor.fetchone()
                
                if not existing:
                    ghims_active = module_data["module_key"] not in ("ghims", "ai_claims_vetting")
                    cursor.execute("""
                        INSERT INTO module_settings 
                        (module_key, module_name, description, is_active, allow_read, 
                         allow_create, allow_update, allow_delete, category, display_order)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        module_data["module_key"],
                        module_data["module_name"],
                        module_data.get("description", ""),
                        ghims_active,
                        True,  # allow_read
                        True,  # allow_create
                        True,  # allow_update
                        True,  # allow_delete
                        module_data.get("category", "core"),
                        module_data.get("display_order", 0)
                    ))
                    print(f"✓ Created module setting: {module_data['module_name']}")
                else:
                    # Update display order if changed
                    cursor.execute("""
                        UPDATE module_settings 
                        SET display_order = %s 
                        WHERE module_key = %s AND display_order != %s
                    """, (module_data.get("display_order", 0), module_data["module_key"], module_data.get("display_order", 0)))
                    if cursor.rowcount > 0:
                        print(f"✓ Updated display order for: {module_data['module_name']}")
            
            conn.commit()
            print("\n✓ Module settings initialization complete!")
        
    except Exception as e:
        print(f"✗ Error initializing module settings: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    init_module_settings()
