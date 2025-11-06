"""
Patient management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
import csv
import io
from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.models.user import User
from app.models.patient import Patient
from app.models.encounter import Encounter, EncounterStatus
from app.utils.card_number import generate_card_number, generate_ccc_number

router = APIRouter(prefix="/patients", tags=["patients"])


class PatientCreate(BaseModel):
    """Patient creation model"""
    name: str
    surname: Optional[str] = None
    other_names: Optional[str] = None
    gender: str
    age: Optional[int] = None
    date_of_birth: Optional[date] = None
    insured: bool = False
    insurance_id: Optional[str] = None
    insurance_start_date: Optional[date] = None
    insurance_end_date: Optional[date] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    # Emergency contact details
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    # Additional demographic information
    marital_status: Optional[str] = None
    educational_level: Optional[str] = None
    occupation: Optional[str] = None


class PatientResponse(BaseModel):
    """Patient response model"""
    id: int
    name: str
    surname: Optional[str]
    other_names: Optional[str]
    gender: str
    age: Optional[int]
    date_of_birth: Optional[date]
    card_number: str
    insured: bool
    insurance_id: Optional[str]
    insurance_start_date: Optional[date] = None
    insurance_end_date: Optional[date] = None
    contact: Optional[str]
    address: Optional[str] = None
    # Emergency contact details
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    # Additional demographic information
    marital_status: Optional[str] = None
    educational_level: Optional[str] = None
    occupation: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Records", "Admin"]))
):
    """Register a new patient"""
    # Generate card number
    card_number = generate_card_number(db)
    
    # Create patient
    patient = Patient(
        **patient_data.dict(),
        card_number=card_number
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    return patient


@router.post("/import", status_code=status.HTTP_200_OK)
async def import_patients_from_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """
    Import patients from CSV file
    
    CSV should have the following columns:
    name, surname, other_names, gender, age, date_of_birth, card_number, 
    insured, insurance_id, insurance_start_date, insurance_end_date, 
    ccc_number, contact, address
    
    Required fields: name, gender
    Optional fields: all others
    If card_number is not provided, it will be auto-generated.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV file")
    
    # Read CSV content
    content = await file.read()
    try:
        text_content = content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text_content = content.decode('latin-1')
        except:
            raise HTTPException(status_code=400, detail="Unable to decode CSV file. Please ensure it's UTF-8 or Latin-1 encoded.")
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(text_content))
    
    results = {
        "success": [],
        "errors": [],
        "total": 0,
        "imported": 0,
        "failed": 0
    }
    
    # Process each row
    for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is header
        results["total"] += 1
        
        try:
            # Extract and validate required fields
            name = row.get('name', '').strip()
            gender = row.get('gender', '').strip().upper()
            
            if not name:
                raise ValueError("Name is required")
            
            if gender not in ['M', 'F']:
                raise ValueError(f"Gender must be 'M' or 'F', got '{gender}'")
            
            # Extract optional fields
            surname = row.get('surname', '').strip() or None
            other_names = row.get('other_names', '').strip() or None
            
            # Parse age
            age = None
            if row.get('age', '').strip():
                try:
                    age = int(row.get('age').strip())
                except ValueError:
                    pass  # Invalid age, leave as None
            
            # Parse date_of_birth
            date_of_birth = None
            if row.get('date_of_birth', '').strip():
                try:
                    dob_str = row.get('date_of_birth').strip()
                    # Try multiple date formats
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']:
                        try:
                            date_of_birth = datetime.strptime(dob_str, fmt).date()
                            break
                        except ValueError:
                            continue
                    if date_of_birth is None:
                        raise ValueError(f"Invalid date format for date_of_birth: {dob_str}")
                except Exception as e:
                    raise ValueError(f"Invalid date_of_birth: {str(e)}")
            
            # Get card_number or generate
            card_number = row.get('card_number', '').strip() or None
            
            # Parse insured (boolean)
            insured = False
            insured_str = row.get('insured', '').strip().upper()
            if insured_str in ['TRUE', '1', 'YES', 'Y']:
                insured = True
            
            # Insurance fields
            insurance_id = row.get('insurance_id', '').strip() or None
            insurance_start_date = None
            insurance_end_date = None
            
            if row.get('insurance_start_date', '').strip():
                try:
                    ins_start_str = row.get('insurance_start_date').strip()
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']:
                        try:
                            insurance_start_date = datetime.strptime(ins_start_str, fmt).date()
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass  # Invalid date, leave as None
            
            if row.get('insurance_end_date', '').strip():
                try:
                    ins_end_str = row.get('insurance_end_date').strip()
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']:
                        try:
                            insurance_end_date = datetime.strptime(ins_end_str, fmt).date()
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass  # Invalid date, leave as None
            
            # CCC number
            ccc_number = row.get('ccc_number', '').strip() or None
            
            # Contact and address
            contact = row.get('contact', '').strip() or None
            address = row.get('address', '').strip() or None
            
            # Check if card_number already exists if provided
            if card_number:
                existing_patient = db.query(Patient).filter(Patient.card_number == card_number).first()
                if existing_patient:
                    raise ValueError(f"Card number '{card_number}' already exists")
            else:
                # Generate card number if not provided
                card_number = generate_card_number(db)
            
            # Create patient
            patient = Patient(
                name=name,
                surname=surname,
                other_names=other_names,
                gender=gender,
                age=age,
                date_of_birth=date_of_birth,
                card_number=card_number,
                insured=insured,
                insurance_id=insurance_id,
                insurance_start_date=insurance_start_date,
                insurance_end_date=insurance_end_date,
                ccc_number=ccc_number,
                contact=contact,
                address=address
            )
            
            db.add(patient)
            db.flush()  # Flush to get patient ID without committing
            
            results["success"].append({
                "row": row_num,
                "name": name,
                "card_number": card_number,
                "id": patient.id
            })
            results["imported"] += 1
            
        except Exception as e:
            results["errors"].append({
                "row": row_num,
                "error": str(e),
                "data": row
            })
            results["failed"] += 1
            continue
    
    # Commit all successful imports
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to commit imports: {str(e)}")
    
    return results


# IMPORTANT: Specific routes must come BEFORE parameterized routes like /{patient_id}
# Otherwise FastAPI will match /search/name as /{patient_id} where patient_id="search"

@router.get("/card/{card_number}", response_model=List[PatientResponse])
def get_patient_by_card(
    card_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Allow all authenticated users
):
    """Search patients by card number (case-insensitive, partial match) - returns list of matches"""
    if not card_number or not card_number.strip():
        return []
    
    # Clean the search term - remove spaces but keep dashes and case
    # We'll use case-insensitive matching with func.upper()
    search_term = card_number.strip().replace(' ', '')
    
    if not search_term:
        return []
    
    # For SQLite: Use func.upper() on both sides for case-insensitive comparison
    # SQLite's LIKE is case-sensitive by default, so we normalize both to uppercase
    search_term_upper = search_term.upper()
    
    # Use func.upper() for case-insensitive comparison (works reliably with SQLite)
    # This converts both the database column and search term to uppercase before comparing
    # The LIKE with % wildcards will match partial strings including those with dashes
    try:
        patients = db.query(Patient).filter(
            func.upper(Patient.card_number).like(f"%{search_term_upper}%")
        ).all()
        
        # Debug logging (remove in production)
        print(f"Search term: '{search_term}', Upper: '{search_term_upper}', Found: {len(patients)} patients")
        
        # Ensure we always return a list, even if it's empty or has one item
        # Convert SQLAlchemy result list to Python list to ensure proper JSON serialization
        return list(patients) if patients else []
    except Exception as e:
        # Log the error and return empty list
        print(f"Error in card number search: {e}")
        return []


@router.get("/search/ccc", response_model=List[PatientResponse])
def search_patient_by_ccc(
    ccc_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Allow all authenticated users
):
    """Search patients by CCC number, Ghana card number, or insurance ID - returns list of matches"""
    if not ccc_number or not ccc_number.strip():
        return []
    
    # Clean the search term - remove spaces
    search_term = ccc_number.strip().replace(' ', '')
    
    if not search_term:
        return []
    
    # Use case-insensitive matching
    search_term_upper = search_term.upper()
    
    try:
        # Search in both ccc_number and insurance_id fields
        # This allows searching by CCC number, Ghana card number, or NHIS insurance ID
        patients = db.query(Patient).filter(
            or_(
                func.upper(func.coalesce(Patient.ccc_number, '')).like(f"%{search_term_upper}%"),
                func.upper(func.coalesce(Patient.insurance_id, '')).like(f"%{search_term_upper}%")
            )
        ).all()
        
        # Debug logging (remove in production)
        print(f"CCC/Insurance search term: '{search_term}', Upper: '{search_term_upper}', Found: {len(patients)} patients")
        
        # Ensure we always return a list, even if it's empty or has one item
        return list(patients) if patients else []
    except Exception as e:
        # Log the error and return empty list
        print(f"Error in CCC/Insurance number search: {e}")
        import traceback
        traceback.print_exc()
        return []


@router.get("/search/name", response_model=List[PatientResponse])
def search_patient_by_name(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Allow all authenticated users
):
    """Search patients by name (case-insensitive, matches first name, surname, or other names)"""
    if not name or not name.strip():
        return []
    
    # Normalize search term - trim and convert to lowercase
    search_term = name.strip().lower()
    
    # Remove multiple spaces and split for better matching
    search_terms = [term for term in search_term.split() if term]
    
    if not search_terms:
        return []
    
    # Build query conditions - match any of the search terms across all name fields
    # For multiple terms, use OR logic: if any term matches any field, include the patient
    # This is more flexible - "godwin boadi" will match patients with "Godwin" or "Boadi" anywhere
    
    # Build conditions for each search term - each term can match any name field
    term_conditions = []
    for term in search_terms:
        # For each term, check if it matches name, surname, or other_names
        # Use or_ to match any of these fields for this term
        term_match = or_(
            func.lower(Patient.name).like(f"%{term}%"),
            func.lower(func.coalesce(Patient.surname, '')).like(f"%{term}%"),
            func.lower(func.coalesce(Patient.other_names, '')).like(f"%{term}%")
        )
        term_conditions.append(term_match)
    
    # Use OR logic between all terms: if ANY term matches ANY field, include the patient
    # This allows "godwin boadi" to match patients with either "godwin" or "boadi"
    try:
        if term_conditions:
            filter_condition = or_(*term_conditions)
            
            # Debug: print the SQL query
            print(f"Name search - Term: '{search_term}', Terms: {search_terms}")
            
            patients = db.query(Patient).filter(filter_condition).all()
            
            # Debug: print query results
            print(f"Query returned {len(patients)} patients")
            for p in patients[:3]:  # Print first 3 for debugging
                print(f"  - ID: {p.id}, Name: {p.name}, Surname: {p.surname}")
        else:
            print("No filter condition generated - no search terms")
            patients = []
        
        # Ensure we always return a list, even if it's empty or has one item
        return list(patients) if patients else []
    except Exception as e:
        # Log the error and return empty list
        print(f"Error in name search: {e}")
        import traceback
        traceback.print_exc()
        return []


@router.get("/search/contact", response_model=List[PatientResponse])
def search_patient_by_contact(
    contact_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Allow all authenticated users
):
    """Search patients by contact number (case-insensitive, partial match) - returns list of matches"""
    if not contact_number or not contact_number.strip():
        return []
    
    # Clean the search term - remove spaces and common formatting characters
    search_term = contact_number.strip().replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    if not search_term:
        return []
    
    try:
        # Search in both contact and emergency_contact_number fields
        # Use case-insensitive matching with LIKE
        patients = db.query(Patient).filter(
            or_(
                func.coalesce(Patient.contact, '').like(f"%{search_term}%"),
                func.coalesce(Patient.emergency_contact_number, '').like(f"%{search_term}%")
            )
        ).all()
        
        # Debug logging
        print(f"Contact search term: '{contact_number}', Cleaned: '{search_term}', Found: {len(patients)} patients")
        
        # Ensure we always return a list, even if it's empty or has one item
        return list(patients) if patients else []
    except Exception as e:
        # Log the error and return empty list
        print(f"Error in contact number search: {e}")
        return []


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Allow all authenticated users
):
    """Get patient by ID"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Records", "Admin"]))
):
    """Update patient information"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    for key, value in patient_data.dict().items():
        setattr(patient, key, value)
    
    db.commit()
    db.refresh(patient)
    return patient


@router.post("/{patient_id}/encounter", status_code=status.HTTP_201_CREATED)
def create_encounter(
    patient_id: int,
    service_type: str,  # Service Type (Department/Clinic)
    ccc_number: Optional[str] = None,
    procedure_g_drg_code: Optional[str] = None,  # G-DRG code of selected procedure
    procedure_name: Optional[str] = None,  # Service Name of selected procedure
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Records", "Admin"]))
):
    """Create a new encounter for a patient with Service Type (Department) and Procedure"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Business rule: If an insured patient already has an insured encounter
    # in the same clinic (department) today, any subsequent encounter today
    # must be cash-and-carry (no CCC allowed for the new encounter).
    forced_cash = False
    if patient.insured:
        # If any insured encounter exists today for this patient, force cash for this new encounter
        existing_insured_today = db.query(Encounter).filter(
            Encounter.patient_id == patient_id,
            Encounter.archived == False,
            Encounter.ccc_number.isnot(None),
            Encounter.ccc_number != "",
            func.date(Encounter.created_at) == date.today()
        ).first()
        if existing_insured_today:
            # Force cash: ignore any provided CCC for this new encounter
            ccc_number = None
            forced_cash = True
        elif not ccc_number:
            # First insured encounter today requires CCC
            raise HTTPException(
                status_code=400,
                detail="CCC number is required for insured patients"
            )
    else:
        # Not insured: ensure CCC is not set even if provided mistakenly
        ccc_number = None
    
    # Use provided CCC number or leave as None (don't auto-generate)
    # Only update patient's CCC number if provided
    if ccc_number:
        patient.ccc_number = ccc_number
    
    # Create encounter
    encounter = Encounter(
        patient_id=patient_id,
        ccc_number=ccc_number,
        status=EncounterStatus.DRAFT.value,
        department=service_type,  # Store Service Type as department
        procedure_g_drg_code=procedure_g_drg_code,
        procedure_name=procedure_name,
        created_by=current_user.id
    )
    db.add(encounter)
    db.flush()  # Use flush instead of commit to get encounter.id without committing yet
    
    # Auto-create bill for the encounter service if procedure is provided
    if procedure_g_drg_code:
        from app.models.bill import Bill, BillItem
        from app.models.procedure_price import ProcedurePrice
        from app.models.surgery_price import SurgeryPrice
        from app.models.unmapped_drg_price import UnmappedDRGPrice
        from app.services.price_list_service_v2 import get_price_from_all_tables
        import random
        
        try:
            # Determine if insured based on encounter CCC number
            is_insured_encounter = ccc_number is not None and ccc_number.strip() != ""
            
            # Determine category by checking which table the procedure belongs to
            category = "procedure"  # Default
            # Check if it's a surgery
            surgery = db.query(SurgeryPrice).filter(
                SurgeryPrice.g_drg_code == procedure_g_drg_code,
                SurgeryPrice.is_active == True
            ).first()
            if surgery:
                category = "surgery"
            else:
                # Check if it's a procedure
                procedure = db.query(ProcedurePrice).filter(
                    ProcedurePrice.g_drg_code == procedure_g_drg_code,
                    ProcedurePrice.is_active == True
                ).first()
                if procedure:
                    category = "procedure"
                else:
                    # Check if it's unmapped DRG
                    unmapped = db.query(UnmappedDRGPrice).filter(
                        UnmappedDRGPrice.g_drg_code == procedure_g_drg_code,
                        UnmappedDRGPrice.is_active == True
                    ).first()
                    if unmapped:
                        category = "drg"
            
            # Get price for the procedure - pass service_type to get the correct price for this department/clinic
            unit_price = get_price_from_all_tables(db, procedure_g_drg_code, is_insured_encounter, service_type)
            
            # Always create bill when procedure is provided
            # If price is 0, still create bill with 0 amount (price may be added to price list later)
            # Generate bill number
            bill_number = f"BILL-{random.randint(100000, 999999)}"
            
            # Create bill
            bill = Bill(
                encounter_id=encounter.id,
                bill_number=bill_number,
                is_insured=is_insured_encounter,
                total_amount=unit_price if unit_price > 0 else 0.0,
                created_by=current_user.id
            )
            db.add(bill)
            db.flush()
            
            # Create bill item for the procedure/service
            bill_item = BillItem(
                bill_id=bill.id,
                item_code=procedure_g_drg_code,
                item_name=procedure_name or f"Service: {procedure_g_drg_code}",
                category=category,
                quantity=1,
                unit_price=unit_price if unit_price > 0 else 0.0,
                total_price=unit_price if unit_price > 0 else 0.0
            )
            db.add(bill_item)
        except Exception as e:
            # Log error but don't fail encounter creation
            # The bill can be created manually later if needed
            import logging
            logging.error(f"Failed to auto-create bill for encounter {encounter.id}: {str(e)}")
            # Continue with encounter creation even if bill creation fails
    
    db.commit()
    db.refresh(encounter)
    
    return {
        "encounter_id": encounter.id,
        "ccc_number": ccc_number,
        "status": encounter.status,
        "service_type": service_type,
        "procedure_name": procedure_name,
        "forced_cash": forced_cash,
        "message": ("An insured encounter already exists for this clinic today. This new encounter has been set to cash-and-carry." if forced_cash else "")
    }

