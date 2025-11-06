"""
Consultation endpoints (diagnoses, prescriptions, investigations)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File, Form, Response
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.models.user import User
from app.models.encounter import Encounter
from app.models.diagnosis import Diagnosis
from app.models.prescription import Prescription
from app.models.investigation import Investigation, InvestigationStatus
from app.models.lab_result import LabResult
from app.models.scan_result import ScanResult
from app.models.xray_result import XrayResult
from app.models.consultation_notes import ConsultationNotes
from app.models.admission import AdmissionRecommendation

router = APIRouter(prefix="/consultation", tags=["consultation"])

# Frequency mapping for prescriptions
FREQUENCY_MAPPING = {
    "Nocte": 1,
    "Stat": 1,
    "OD": 1,
    "daily": 1,
    "PRN": 1,
    "BDS": 2,
    "BID": 2,
    "QDS": 4,
    "QID": 4,
    "TID": 3,
    "TDS": 3,
    "5X": 5,
    "EVERY OTHER DAY": 1,
    "AT BED TIME": 1,
    "6 TIMES": 6
}


def auto_generate_bill_for_chief_diagnosis(
    db: Session,
    diagnosis: Diagnosis,
    encounter: Encounter,
    current_user_id: int
) -> bool:
    """
    DISABLED: Auto-generate bill for a chief diagnosis.
    This function is disabled for OPD consultations since the initial service request already covers the diagnosis billing.
    Returns False (no bill created).
    """
    # NOTE: Bill generation for diagnoses is disabled for OPD consultations
    # since the initial service request already covers the diagnosis billing.
    # This function is kept for backward compatibility but does nothing.
    return False


# Diagnosis schemas
class DiagnosisCreate(BaseModel):
    """Diagnosis creation model"""
    encounter_id: int
    icd10: Optional[str] = None
    diagnosis: str
    gdrg_code: Optional[str] = None
    is_provisional: bool = False
    is_chief: bool = False


class DiagnosisResponse(BaseModel):
    """Diagnosis response model"""
    id: int
    encounter_id: int
    icd10: Optional[str]
    diagnosis: str
    gdrg_code: Optional[str]
    is_provisional: bool
    is_chief: bool
    
    class Config:
        from_attributes = True


# Prescription schemas
class PrescriptionCreate(BaseModel):
    """Prescription creation model"""
    encounter_id: int
    medicine_code: str
    medicine_name: str
    dose: Optional[str] = None  # Numeric dose value (e.g., "500")
    unit: Optional[str] = None  # Unit of dose (e.g., "MG", "ML", "TAB")
    frequency: Optional[str] = None  # Frequency label (e.g., "BDS", "TDS", "OD")
    frequency_value: Optional[int] = None  # Numeric frequency value (e.g., 2 for BDS)
    duration: Optional[str] = None  # Duration (e.g., "7 DAYS")
    instructions: Optional[str] = None  # Instructions for the drug
    quantity: Optional[int] = None  # Auto-calculated: dose * frequency_value * duration
    unparsed: Optional[str] = None
    is_external: Optional[bool] = False  # True if prescription is to be filled outside (external pharmacy)


class PrescriptionResponse(BaseModel):
    """Prescription response model"""
    id: int
    encounter_id: int
    medicine_code: str
    medicine_name: str
    dose: Optional[str]
    unit: Optional[str] = None
    frequency: Optional[str]
    frequency_value: Optional[int] = None
    duration: Optional[str]
    instructions: Optional[str] = None
    quantity: int
    unparsed: Optional[str] = None
    prescribed_by: int
    is_external: bool = False
    prescriber_name: Optional[str] = None  # Full name of the prescriber
    prescriber_role: Optional[str] = None  # Role of the prescriber
    confirmed_by: Optional[int] = None
    dispensed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    service_date: datetime
    created_at: datetime
    is_dispensed: bool = False
    is_confirmed: bool = False
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to add is_dispensed and is_confirmed computed fields"""
        # Handle cases where confirmed_by and confirmed_at might not exist in old database records
        confirmed_by = getattr(obj, 'confirmed_by', None)
        confirmed_at = getattr(obj, 'confirmed_at', None)
        dispensed_by = getattr(obj, 'dispensed_by', None)
        unit = getattr(obj, 'unit', None)
        frequency_value = getattr(obj, 'frequency_value', None)
        instructions = getattr(obj, 'instructions', None)
        
        data = {
            "id": obj.id,
            "encounter_id": obj.encounter_id,
            "medicine_code": obj.medicine_code,
            "medicine_name": obj.medicine_name,
            "dose": obj.dose,
            "unit": unit,
            "frequency": obj.frequency,
            "frequency_value": frequency_value,
            "duration": obj.duration,
            "instructions": instructions,
            "quantity": obj.quantity,
            "unparsed": obj.unparsed,
            "prescribed_by": obj.prescribed_by,
            "confirmed_by": confirmed_by,
            "dispensed_by": dispensed_by,
            "confirmed_at": confirmed_at,
            "service_date": obj.service_date,
            "created_at": obj.created_at,
            "is_dispensed": dispensed_by is not None,
            "is_confirmed": confirmed_by is not None,
        }
        return cls(**data)


# Investigation schemas
class InvestigationCreate(BaseModel):
    """Investigation creation model"""
    encounter_id: int
    gdrg_code: str
    procedure_name: Optional[str] = None
    investigation_type: str  # lab, scan, xray
    notes: Optional[str] = None  # Notes/remarks from doctor
    price: Optional[str] = None  # Price of the investigation


class InvestigationResponse(BaseModel):
    """Investigation response model"""
    id: int
    encounter_id: int
    gdrg_code: str
    procedure_name: Optional[str]
    investigation_type: str
    notes: Optional[str]
    price: Optional[str] = None
    status: str
    confirmed_by: Optional[int] = None
    cancelled_by: Optional[int] = None
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


@router.post("/diagnosis", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
def create_diagnosis(
    diagnosis_data: DiagnosisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "Records"]))
):
    """Add a diagnosis to an encounter"""
    from app.models.icd10_drg_mapping import ICD10DRGMapping
    
    encounter = db.query(Encounter).filter(Encounter.id == diagnosis_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Convert None ICD-10 to empty string for database compatibility
    diagnosis_dict = diagnosis_data.dict()
    if diagnosis_dict.get('icd10') is None:
        diagnosis_dict['icd10'] = ''
    
    # Auto-map ICD-10 to DRG code if ICD-10 is provided but DRG is not
    if diagnosis_dict.get('icd10') and not diagnosis_dict.get('gdrg_code'):
        icd10_code = diagnosis_dict['icd10'].strip()
        if icd10_code:
            # Find first DRG code mapped to this ICD-10 code
            mapping = db.query(ICD10DRGMapping).filter(
                ICD10DRGMapping.icd10_code == icd10_code,
                ICD10DRGMapping.is_active == True
            ).first()
            
            if mapping:
                diagnosis_dict['gdrg_code'] = mapping.drg_code
                # Optionally update diagnosis description if it's empty
                if not diagnosis_dict.get('diagnosis') or not diagnosis_dict['diagnosis'].strip():
                    if mapping.icd10_description:
                        diagnosis_dict['diagnosis'] = mapping.icd10_description
    
    diagnosis = Diagnosis(**diagnosis_dict, created_by=current_user.id)
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    
    # NOTE: Bill generation for diagnoses is disabled for OPD consultations
    # since the initial service request already covers the diagnosis billing.
    # If diagnosis is marked as chief and has GDRG code, auto-generate bill
    # if diagnosis.is_chief and diagnosis.gdrg_code:
    #     auto_generate_bill_for_chief_diagnosis(db, diagnosis, encounter, current_user.id)
    
    return diagnosis


@router.get("/diagnosis/encounter/{encounter_id}", response_model=List[DiagnosisResponse])
def get_diagnoses(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all diagnoses for an encounter"""
    diagnoses = db.query(Diagnosis).filter(Diagnosis.encounter_id == encounter_id).all()
    return diagnoses


@router.put("/diagnosis/{diagnosis_id}", response_model=DiagnosisResponse)
def update_diagnosis(
    diagnosis_id: int,
    diagnosis_data: DiagnosisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Update a diagnosis"""
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    # Verify encounter exists
    encounter = db.query(Encounter).filter(Encounter.id == diagnosis_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Check if diagnosis is being marked as chief
    was_chief = diagnosis.is_chief
    is_now_chief = diagnosis_data.is_chief
    
    # Update diagnosis fields
    diagnosis.encounter_id = diagnosis_data.encounter_id
    diagnosis.icd10 = diagnosis_data.icd10 if diagnosis_data.icd10 else ''
    diagnosis.diagnosis = diagnosis_data.diagnosis
    diagnosis.gdrg_code = diagnosis_data.gdrg_code
    diagnosis.is_provisional = diagnosis_data.is_provisional
    diagnosis.is_chief = diagnosis_data.is_chief
    
    # NOTE: Bill generation for diagnoses is disabled for OPD consultations
    # since the initial service request already covers the diagnosis billing.
    # If diagnosis is marked as chief (and wasn't before), auto-generate bill
    # if is_now_chief and not was_chief and diagnosis.gdrg_code:
    #     auto_generate_bill_for_chief_diagnosis(db, diagnosis, encounter, current_user.id)
    
    db.commit()
    
    db.refresh(diagnosis)
    return diagnosis


@router.delete("/diagnosis/{diagnosis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diagnosis(
    diagnosis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Delete a diagnosis"""
    diagnosis = db.query(Diagnosis).filter(Diagnosis.id == diagnosis_id).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    db.delete(diagnosis)
    db.commit()
    return None


@router.post("/prescription", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_prescription(
    prescription_data: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "Pharmacy", "PA"]))
):
    """Add a prescription to an encounter"""
    try:
        encounter = db.query(Encounter).filter(Encounter.id == prescription_data.encounter_id).first()
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        # Get frequency value from mapping if frequency is provided
        frequency_value = None
        if prescription_data.frequency:
            frequency_value = FREQUENCY_MAPPING.get(prescription_data.frequency.strip(), None)
        
        # Auto-calculate quantity based on pharmacist logic
        # For MG: 100mg = 1 unit, so dose (in mg) / 100 = units per dose
        # Then: (dose_mg / 100) × frequency_value × duration
        # Example: 500mg, BDS (2), 2 days = (500/100) × 2 × 2 = 5 × 2 × 2 = 20
        # Only auto-calculate if quantity is not provided or is 0
        # This allows frontend to override the calculation if needed
        quantity = prescription_data.quantity
        if (not quantity or quantity <= 0) and prescription_data.dose and frequency_value and prescription_data.duration:
            try:
                dose_num = float(prescription_data.dose)
                if dose_num > 0:
                    # Extract duration number (e.g., "7 DAYS" -> 7, "2" -> 2)
                    duration_str = prescription_data.duration.strip() if prescription_data.duration else ""
                    duration_num = 1
                    if duration_str:
                        # First try to parse as a number directly
                        try:
                            direct_num = float(duration_str)
                            if direct_num > 0:
                                duration_num = int(direct_num)
                        except ValueError:
                            # Otherwise, extract number from string (e.g., "7 DAYS" -> 7)
                            import re
                            duration_match = re.search(r'\d+', duration_str)
                            if duration_match:
                                duration_num = int(duration_match.group())
                    
                    # Convert dose to units based on unit type
                    units_per_dose = dose_num
                    unit = prescription_data.unit.strip().upper() if prescription_data.unit else ""
                    if unit == "MG":
                        # For MG: 100mg = 1 unit
                        units_per_dose = dose_num / 100.0
                    elif unit == "MCG":
                        # For MCG: 1000mcg = 1 unit
                        units_per_dose = dose_num / 1000.0
                    # For other units (TAB, CAP, ML, etc.), use dose as-is (1 tablet = 1 unit)
                    
                    # Calculate: units per dose × frequency per day × number of days
                    calculated_quantity = int(units_per_dose * frequency_value * duration_num)
                    if calculated_quantity > 0:
                        quantity = calculated_quantity
            except (ValueError, TypeError) as e:
                print(f"Error calculating quantity: {e}")
                pass  # If calculation fails, use provided quantity or default below
        
        # Ensure quantity is set
        if not quantity or quantity <= 0:
            quantity = 1
        
        prescription_dict = prescription_data.dict()
        prescription_dict['frequency_value'] = frequency_value
        prescription_dict['quantity'] = quantity
        # Convert is_external boolean to integer (0 or 1) for SQLite
        if 'is_external' in prescription_dict:
            prescription_dict['is_external'] = 1 if prescription_dict['is_external'] else 0
        else:
            prescription_dict['is_external'] = 0
        
        prescription = Prescription(**prescription_dict, prescribed_by=current_user.id)
        db.add(prescription)
        
        # Auto-confirm external prescriptions (they don't need pharmacy confirmation)
        # Check is_external as integer (0 or 1) since SQLite stores it as INTEGER
        is_external = prescription_dict.get('is_external', 0)
        if is_external:
            prescription.confirmed_by = current_user.id
            prescription.confirmed_at = datetime.utcnow()
            print(f"Auto-confirmed external prescription {prescription.id} - no bill will be created")
        
        db.commit()
        db.refresh(prescription)
        return add_prescriber_info_to_response(prescription, db)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the error and re-raise as HTTPException with 500 status
        import traceback
        print(f"Error creating prescription: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating prescription: {str(e)}"
        )


def add_prescriber_info_to_response(prescription, db: Session) -> PrescriptionResponse:
    """Helper function to add prescriber information to a prescription response"""
    # Get prescriber information
    prescriber = db.query(User).filter(User.id == prescription.prescribed_by).first()
    prescriber_name = prescriber.full_name if prescriber else None
    prescriber_role = prescriber.role if prescriber else None
    
    # Create response with prescriber details
    # Convert is_external from integer (0/1) to boolean
    is_external = bool(prescription.is_external) if hasattr(prescription, 'is_external') else False
    
    # Compute is_confirmed and is_dispensed from confirmed_by and dispensed_by
    is_confirmed = prescription.confirmed_by is not None
    is_dispensed = prescription.dispensed_by is not None
    
    prescription_dict = {
        'id': prescription.id,
        'encounter_id': prescription.encounter_id,
        'medicine_code': prescription.medicine_code,
        'medicine_name': prescription.medicine_name,
        'dose': prescription.dose,
        'unit': prescription.unit,
        'frequency': prescription.frequency,
        'frequency_value': prescription.frequency_value,
        'duration': prescription.duration,
        'instructions': prescription.instructions,
        'quantity': prescription.quantity,
        'unparsed': prescription.unparsed,
        'prescribed_by': prescription.prescribed_by,
        'is_external': is_external,
        'prescriber_name': prescriber_name,
        'prescriber_role': prescriber_role,
        'confirmed_by': prescription.confirmed_by,
        'dispensed_by': prescription.dispensed_by,
        'confirmed_at': prescription.confirmed_at,
        'service_date': prescription.service_date,
        'created_at': prescription.created_at,
        'is_confirmed': is_confirmed,
        'is_dispensed': is_dispensed,
    }
    return PrescriptionResponse(**prescription_dict)


@router.get("/prescription/encounter/{encounter_id}", response_model=List[PrescriptionResponse])
def get_prescriptions(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all prescriptions for an encounter"""
    # Query prescriptions with prescriber information
    prescriptions = db.query(Prescription).filter(Prescription.encounter_id == encounter_id).all()
    
    result = []
    for p in prescriptions:
        result.append(add_prescriber_info_to_response(p, db))
    
    return result


@router.get("/prescription/patient/{card_number}/encounter/{encounter_id}", response_model=List[PrescriptionResponse])
def get_prescriptions_by_patient_card(
    card_number: str,
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get prescriptions for a patient (by card number) for a specific encounter"""
    from app.models.patient import Patient
    
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.card_number == card_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify encounter belongs to patient
    encounter = db.query(Encounter).filter(
        Encounter.id == encounter_id,
        Encounter.patient_id == patient.id
    ).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found or does not belong to this patient")
    
    # Get prescriptions for the encounter with prescriber information
    prescriptions = db.query(Prescription).filter(Prescription.encounter_id == encounter_id).all()
    
    result = []
    for p in prescriptions:
        result.append(add_prescriber_info_to_response(p, db))
    
    return result


class PrescriptionDispense(BaseModel):
    """Prescription dispense model - allows updating prescription details during dispense/confirmation"""
    dose: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    quantity: Optional[int] = None
    instructions: Optional[str] = None  # Instructions for the drug


@router.put("/prescription/{prescription_id}/dispense", response_model=PrescriptionResponse)
def dispense_prescription(
    prescription_id: int,
    dispense_data: Optional[PrescriptionDispense] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Admin"]))
):
    """Mark a prescription as dispensed - only allowed if bill is paid or bill amount is 0"""
    from app.models.bill import Bill, BillItem, ReceiptItem, Receipt
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.dispensed_by is not None:
        raise HTTPException(status_code=400, detail="Prescription has already been dispensed")
    
    if prescription.confirmed_by is None:
        raise HTTPException(status_code=400, detail="Prescription must be confirmed before dispense")
    
    # Check if bill for this prescription is paid or amount is 0
    # Find the bill item for this prescription
    bill_item = db.query(BillItem).filter(
        BillItem.item_code == prescription.medicine_code,
        BillItem.item_name.like(f"%{prescription.medicine_name}%")
    ).join(Bill).filter(
        Bill.encounter_id == prescription.encounter_id,
        Bill.is_paid == False
    ).first()
    
    if bill_item:
        # Check if bill item is fully paid
        total_paid = 0.0
        for receipt_item in db.query(ReceiptItem).filter(
            ReceiptItem.bill_item_id == bill_item.id
        ).join(Receipt).filter(Receipt.refunded == False).all():
            total_paid += receipt_item.amount_paid
        
        remaining_balance = bill_item.total_price - total_paid
        
        # Only allow dispense if bill amount is 0 or fully paid
        if bill_item.total_price > 0 and remaining_balance > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot dispense prescription. Bill not paid. Remaining balance: {remaining_balance:.2f}"
            )
    
    # Update prescription fields if provided
    if dispense_data:
        if dispense_data.dose is not None:
            prescription.dose = dispense_data.dose
        if dispense_data.frequency is not None:
            prescription.frequency = dispense_data.frequency
        if dispense_data.duration is not None:
            prescription.duration = dispense_data.duration
        if dispense_data.quantity is not None:
            if dispense_data.quantity <= 0:
                raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
            prescription.quantity = dispense_data.quantity
    
    prescription.dispensed_by = current_user.id
    prescription.service_date = datetime.utcnow()
    
    db.commit()
    db.refresh(prescription)
    return add_prescriber_info_to_response(prescription, db)


@router.put("/prescription/{prescription_id}/confirm", response_model=PrescriptionResponse)
def confirm_prescription(
    prescription_id: int,
    dispense_data: Optional[PrescriptionDispense] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Admin"]))
):
    """Confirm a prescription (allows pharmacy to update details) and automatically generate a bill item"""
    from app.models.bill import Bill, BillItem
    from app.services.price_list_service_v2 import get_price_from_all_tables
    import random
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Prevent confirming external prescriptions (they're auto-confirmed and not billed)
    # Check is_external as integer (0 or 1) since SQLite stores it as INTEGER
    is_external = bool(prescription.is_external) if hasattr(prescription, 'is_external') else False
    if is_external:
        raise HTTPException(
            status_code=400, 
            detail="External prescriptions are automatically confirmed and cannot be confirmed again. They are filled outside and not billed."
        )
    
    if prescription.confirmed_by is not None:
        raise HTTPException(status_code=400, detail="Prescription has already been confirmed")
    
    encounter = db.query(Encounter).filter(Encounter.id == prescription.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Allow pharmacy to update prescription details during confirmation
    if dispense_data:
        if dispense_data.dose is not None:
            prescription.dose = dispense_data.dose
        if dispense_data.frequency is not None:
            prescription.frequency = dispense_data.frequency
        if dispense_data.duration is not None:
            prescription.duration = dispense_data.duration
        if dispense_data.quantity is not None:
            if dispense_data.quantity <= 0:
                raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
            prescription.quantity = dispense_data.quantity
        if dispense_data.instructions is not None:
            prescription.instructions = dispense_data.instructions
    
    # Mark prescription as confirmed
    prescription.confirmed_by = current_user.id
    prescription.confirmed_at = datetime.utcnow()
    
    # Determine if insured based on encounter CCC number
    is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
    
    # Get price for the medicine (co-pay for insured, base rate for cash)
    # If insurance_covered="no", always uses base_rate regardless of insurance status
    print(f"DEBUG: Calling get_price_from_all_tables with code='{prescription.medicine_code}', is_insured={is_insured_encounter}")
    print(f"DEBUG: Prescription before price lookup - quantity={prescription.quantity}, medicine_code={prescription.medicine_code}")
    unit_price = get_price_from_all_tables(db, prescription.medicine_code, is_insured_encounter)
    
    # Ensure quantity is set (should already be set, but safety check)
    if not prescription.quantity or prescription.quantity <= 0:
        print(f"WARNING: Prescription quantity is {prescription.quantity}, setting to 1")
        prescription.quantity = 1
    
    total_price = unit_price * prescription.quantity
    
    # Debug: Log pricing information
    print(f"Prescription confirmation - Medicine: {prescription.medicine_code}, Is Insured: {is_insured_encounter}, Unit Price: {unit_price}, Total Price: {total_price}, Quantity: {prescription.quantity}")
    print(f"DEBUG: unit_price={unit_price}, quantity={prescription.quantity}, total_price={total_price}")
    print(f"DEBUG: Will create bill? {total_price > 0}")
    
    # Skip billing for external prescriptions (they are filled outside)
    # Check is_external as integer (0 or 1) since SQLite stores it as INTEGER
    is_external = bool(prescription.is_external) if hasattr(prescription, 'is_external') else False
    if is_external:
        print(f"Prescription {prescription_id} is external - skipping bill creation")
        db.commit()
        db.refresh(prescription)
        return add_prescriber_info_to_response(prescription, db)
    
    # Always create/add to bill if total_price > 0
    # This ensures bills are created even when insurance_covered="no" and base_rate is set
    if total_price > 0:
        print(f"Creating bill item - Unit Price: {unit_price}, Total Price: {total_price}")
        # Find or create a bill for this encounter
        existing_bill = db.query(Bill).filter(
            Bill.encounter_id == encounter.id,
            Bill.is_paid == False  # Only use unpaid bills
        ).first()
        
        if existing_bill:
            # Check if this prescription is already in the bill
            existing_item = db.query(BillItem).filter(
                BillItem.bill_id == existing_bill.id,
                BillItem.item_code == prescription.medicine_code,
                BillItem.item_name.like(f"%{prescription.medicine_name}%")
            ).first()
            
            if not existing_item:
                # Add bill item to existing bill
                bill_item = BillItem(
                    bill_id=existing_bill.id,
                    item_code=prescription.medicine_code,
                    item_name=f"Prescription: {prescription.medicine_name}",
                    category="product",
                    quantity=prescription.quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
                db.add(bill_item)
                existing_bill.total_amount += total_price
        else:
            # Create new bill
            bill_number = f"BILL-{random.randint(100000, 999999)}"
            bill = Bill(
                encounter_id=encounter.id,
                bill_number=bill_number,
                is_insured=is_insured_encounter,
                total_amount=total_price,
                created_by=current_user.id
            )
            db.add(bill)
            db.flush()
            
            # Create bill item
            bill_item = BillItem(
                bill_id=bill.id,
                item_code=prescription.medicine_code,
                item_name=f"Prescription: {prescription.medicine_name}",
                category="product",
                quantity=prescription.quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            db.add(bill_item)
            print(f"Bill and bill item created successfully")
    else:
        print(f"WARNING: Not creating bill - Unit Price: {unit_price}, Total Price: {total_price} (one or both are 0)")
    
    db.commit()
    db.refresh(prescription)
    return add_prescriber_info_to_response(prescription, db)


@router.put("/prescription/{prescription_id}/return", response_model=PrescriptionResponse)
def return_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Admin"]))
):
    """Return a dispensed prescription (undo dispense - patient couldn't pay)"""
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.dispensed_by is None:
        raise HTTPException(status_code=400, detail="Prescription has not been dispensed")
    
    prescription.dispensed_by = None
    prescription.service_date = datetime.utcnow()
    
    db.commit()
    db.refresh(prescription)
    return add_prescriber_info_to_response(prescription, db)


@router.get("/prescription/encounter/{encounter_id}/dispensed", response_model=List[PrescriptionResponse])
def get_dispensed_prescriptions(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get only dispensed prescriptions for an encounter (for billing)"""
    prescriptions = db.query(Prescription).filter(
        Prescription.encounter_id == encounter_id,
        Prescription.dispensed_by.isnot(None)
    ).all()
    return [add_prescriber_info_to_response(p, db) for p in prescriptions]


@router.put("/prescription/{prescription_id}", response_model=PrescriptionResponse)
def update_prescription(
    prescription_id: int,
    prescription_data: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Update a prescription"""
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Prevent editing if prescription is confirmed by pharmacy staff
    # Only Admin can override this restriction
    if prescription.confirmed_by is not None and current_user.role != "Admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot edit prescription that has been confirmed by pharmacy staff. Contact admin if changes are needed."
        )
    
    # Verify encounter exists
    encounter = db.query(Encounter).filter(Encounter.id == prescription_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get frequency value from mapping if frequency is provided
    frequency_value = None
    if prescription_data.frequency:
        frequency_value = FREQUENCY_MAPPING.get(prescription_data.frequency.strip(), None)
    
    # Auto-calculate quantity based on pharmacist logic
    # For MG: 100mg = 1 unit, so dose (in mg) / 100 = units per dose
    # Then: (dose_mg / 100) × frequency_value × duration
    # Example: 500mg, BDS (2), 2 days = (500/100) × 2 × 2 = 5 × 2 × 2 = 20
    # Only auto-calculate if quantity is not provided or is 0
    # This allows frontend to override the calculation if needed
    quantity = prescription_data.quantity
    if (not quantity or quantity <= 0) and prescription_data.dose and frequency_value and prescription_data.duration:
        try:
            dose_num = float(prescription_data.dose)
            if dose_num > 0:
                # Extract duration number (e.g., "7 DAYS" -> 7, "2" -> 2)
                duration_str = prescription_data.duration.strip()
                duration_num = 1
                if duration_str:
                    # First try to parse as a number directly
                    try:
                        direct_num = float(duration_str)
                        if direct_num > 0:
                            duration_num = int(direct_num)
                    except ValueError:
                        # Otherwise, extract number from string (e.g., "7 DAYS" -> 7)
                        import re
                        duration_match = re.search(r'\d+', duration_str)
                        if duration_match:
                            duration_num = int(duration_match.group())
                
                # Convert dose to units based on unit type
                units_per_dose = dose_num
                unit = prescription_data.unit.strip().upper() if prescription_data.unit else ""
                if unit == "MG":
                    # For MG: 100mg = 1 unit
                    units_per_dose = dose_num / 100.0
                elif unit == "MCG":
                    # For MCG: 1000mcg = 1 unit
                    units_per_dose = dose_num / 1000.0
                # For other units (TAB, CAP, ML, etc.), use dose as-is (1 tablet = 1 unit)
                
                # Calculate: units per dose × frequency per day × number of days
                calculated_quantity = int(units_per_dose * frequency_value * duration_num)
                if calculated_quantity > 0:
                    quantity = calculated_quantity
        except (ValueError, TypeError):
            pass  # If calculation fails, use provided quantity or default below
    
    # Ensure quantity is set
    if not quantity or quantity <= 0:
        quantity = 1
    
    # Update prescription fields
    prescription.encounter_id = prescription_data.encounter_id
    prescription.medicine_code = prescription_data.medicine_code
    prescription.medicine_name = prescription_data.medicine_name
    prescription.dose = prescription_data.dose
    prescription.unit = prescription_data.unit
    prescription.frequency = prescription_data.frequency
    prescription.frequency_value = frequency_value
    prescription.duration = prescription_data.duration
    prescription.instructions = prescription_data.instructions
    prescription.quantity = quantity
    prescription.unparsed = prescription_data.unparsed
    
    db.commit()
    db.refresh(prescription)
    return add_prescriber_info_to_response(prescription, db)


@router.delete("/prescription/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Delete a prescription"""
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Allow deletion of external prescriptions even if confirmed (they're going outside)
    # Check is_external as integer (0 or 1) since SQLite stores it as INTEGER
    is_external = bool(prescription.is_external) if hasattr(prescription, 'is_external') else False
    
    # Prevent deleting if prescription is confirmed by pharmacy staff (unless it's external)
    # Only Admin can override this restriction for non-external prescriptions
    if not is_external and prescription.confirmed_by is not None and current_user.role != "Admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete prescription that has been confirmed by pharmacy staff. Contact admin if deletion is needed."
        )
    
    db.delete(prescription)
    db.commit()
    return None


@router.post("/investigation", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
def create_investigation(
    investigation_data: InvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "Records"]))
):
    """Request an investigation (lab, scan, x-ray)"""
    from app.services.price_list_service_v2 import get_price_from_all_tables
    
    encounter = db.query(Encounter).filter(Encounter.id == investigation_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Auto-fetch price from price list if not provided
    price = investigation_data.price
    if not price and investigation_data.gdrg_code:
        # Check if patient is insured (has CCC number)
        is_insured = bool(encounter.ccc_number)
        try:
            price_value = get_price_from_all_tables(db, investigation_data.gdrg_code, is_insured)
            price = str(price_value) if price_value else None
        except Exception as e:
            # If price lookup fails, continue without price
            price = None
    
    investigation = Investigation(
        encounter_id=investigation_data.encounter_id,
        gdrg_code=investigation_data.gdrg_code,
        procedure_name=investigation_data.procedure_name,
        investigation_type=investigation_data.investigation_type,
        notes=investigation_data.notes,
        price=price,
        requested_by=current_user.id,
        status=InvestigationStatus.REQUESTED.value
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation


@router.get("/investigation/encounter/{encounter_id}", response_model=List[InvestigationResponse])
def get_investigations(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all investigations for an encounter"""
    investigations = db.query(Investigation).filter(Investigation.encounter_id == encounter_id).all()
    return investigations


class InvestigationCancel(BaseModel):
    """Investigation cancellation model"""
    reason: str  # Reason for cancellation (required)


@router.put("/investigation/{investigation_id}/cancel", response_model=InvestigationResponse)
def cancel_investigation(
    investigation_id: int,
    cancel_data: InvestigationCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Cancel an investigation (can cancel confirmed investigations)"""
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Don't allow cancelling already cancelled or completed investigations
    if investigation.status == InvestigationStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Investigation is already cancelled")
    
    if investigation.status == InvestigationStatus.COMPLETED.value:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed investigation")
    
    investigation.status = InvestigationStatus.CANCELLED.value
    investigation.cancelled_by = current_user.id
    investigation.cancellation_reason = cancel_data.reason
    investigation.cancelled_at = datetime.utcnow()
    
    db.commit()
    db.refresh(investigation)
    return investigation


@router.put("/investigation/{investigation_id}", response_model=InvestigationResponse)
def update_investigation(
    investigation_id: int,
    investigation_data: InvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Update an investigation"""
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Prevent editing if investigation is confirmed by staff
    # Only Admin can override this restriction
    if investigation.confirmed_by is not None and current_user.role != "Admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot edit investigation that has been confirmed by staff. Contact admin if changes are needed."
        )
    
    # Verify encounter exists
    encounter = db.query(Encounter).filter(Encounter.id == investigation_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Update investigation fields
    investigation.encounter_id = investigation_data.encounter_id
    investigation.gdrg_code = investigation_data.gdrg_code
    investigation.procedure_name = investigation_data.procedure_name
    investigation.investigation_type = investigation_data.investigation_type
    investigation.notes = investigation_data.notes
    investigation.price = investigation_data.price
    
    db.commit()
    db.refresh(investigation)
    return investigation


@router.delete("/investigation/{investigation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Delete an investigation"""
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Prevent deleting if investigation is confirmed by staff
    # Only Admin can override this restriction
    if investigation.confirmed_by is not None and current_user.role != "Admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete investigation that has been confirmed by staff. Contact admin if deletion is needed."
        )
    
    # Also check status for additional protection
    if investigation.status == InvestigationStatus.CONFIRMED.value and current_user.role != "Admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete investigation that has been confirmed. Contact admin if deletion is needed."
        )
    
    db.delete(investigation)
    db.commit()
    return None


@router.get("/investigation/patient/{card_number}/encounter/{encounter_id}", response_model=List[InvestigationResponse])
def get_investigations_by_patient_card(
    card_number: str,
    encounter_id: int,
    investigation_type: Optional[str] = None,  # Filter by type: lab, scan, xray
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get investigations for a patient (by card number) for a specific encounter"""
    from app.models.patient import Patient
    
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.card_number == card_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify encounter belongs to patient
    encounter = db.query(Encounter).filter(
        Encounter.id == encounter_id,
        Encounter.patient_id == patient.id
    ).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found or does not belong to this patient")
    
    # Build query
    query = db.query(Investigation).filter(Investigation.encounter_id == encounter_id)
    
    # Filter by investigation type if provided
    if investigation_type:
        query = query.filter(Investigation.investigation_type == investigation_type)
    
    investigations = query.all()
    return investigations


class InvestigationUpdateDetails(BaseModel):
    """Investigation update details model"""
    gdrg_code: str
    procedure_name: str
    investigation_type: Optional[str] = None
    notes: Optional[str] = None
    price: Optional[str] = None


@router.put("/investigation/{investigation_id}/update-details", response_model=InvestigationResponse)
def update_investigation_details(
    investigation_id: int,
    update_data: InvestigationUpdateDetails,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Scan", "Xray", "Admin"]))
):
    """Update investigation details (gdrg_code, procedure_name, investigation_type) - allows staff to change service"""
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Check permissions - only staff matching investigation type or Admin can update
    if current_user.role != "Admin":
        if investigation.investigation_type == "lab" and current_user.role != "Lab":
            raise HTTPException(status_code=403, detail="Only Lab staff can update lab investigations")
        elif investigation.investigation_type == "scan" and current_user.role != "Scan":
            raise HTTPException(status_code=403, detail="Only Scan staff can update scan investigations")
        elif investigation.investigation_type == "xray" and current_user.role != "Xray":
            raise HTTPException(status_code=403, detail="Only Xray staff can update xray investigations")
    
    # Update both gdrg_code and procedure_name together (required)
    investigation.gdrg_code = update_data.gdrg_code
    investigation.procedure_name = update_data.procedure_name
    
    # Update investigation_type if provided
    if update_data.investigation_type is not None:
        investigation.investigation_type = update_data.investigation_type
    
    # Update notes if provided
    if update_data.notes is not None:
        investigation.notes = update_data.notes
    
    # Update price if provided
    if update_data.price is not None:
        investigation.price = update_data.price
    
    db.commit()
    db.refresh(investigation)
    return investigation


@router.put("/investigation/{investigation_id}/confirm")
def confirm_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Scan", "Xray", "Admin"]))
):
    """Confirm an investigation request and automatically generate a bill item"""
    from app.models.bill import Bill, BillItem
    from app.services.price_list_service_v2 import get_price_from_all_tables
    import random
    
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Don't allow confirming cancelled investigations
    if investigation.status == InvestigationStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Cannot confirm a cancelled investigation")
    
    # Verify user role matches investigation type (Lab can confirm labs, etc.)
    if current_user.role != "Admin":
        if investigation.investigation_type == "lab" and current_user.role != "Lab":
            raise HTTPException(
                status_code=403,
                detail="Only Lab staff can confirm lab investigations"
            )
        elif investigation.investigation_type == "scan" and current_user.role != "Scan":
            raise HTTPException(
                status_code=403,
                detail="Only Scan staff can confirm scan investigations"
            )
        elif investigation.investigation_type == "xray" and current_user.role != "Xray":
            raise HTTPException(
                status_code=403,
                detail="Only Xray staff can confirm xray investigations"
            )
    
    # Get encounter to determine insurance status
    encounter = db.query(Encounter).filter(Encounter.id == investigation.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    investigation.status = InvestigationStatus.CONFIRMED.value
    investigation.confirmed_by = current_user.id
    
    # Determine if insured based on encounter CCC number
    is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
    
    # Get price for the investigation (co-pay for insured, base rate for cash)
    # Use the price stored on the investigation, or look it up from price list
    unit_price = 0.0
    if investigation.price:
        try:
            unit_price = float(investigation.price)
        except (ValueError, TypeError):
            unit_price = 0.0
    
    # If no price stored, look it up from price list using gdrg_code
    if unit_price == 0.0 and investigation.gdrg_code:
        unit_price = get_price_from_all_tables(db, investigation.gdrg_code, is_insured_encounter)
    
    total_price = unit_price  # Investigations are typically quantity 1
    
    # Always create/add to bill if total_price > 0
    if total_price > 0:
        # Find or create a bill for this encounter
        existing_bill = db.query(Bill).filter(
            Bill.encounter_id == encounter.id,
            Bill.is_paid == False  # Only use unpaid bills
        ).first()
        
        if existing_bill:
            # Check if this investigation is already in the bill
            existing_item = db.query(BillItem).filter(
                BillItem.bill_id == existing_bill.id,
                BillItem.item_code == investigation.gdrg_code,
                BillItem.item_name.like(f"%{investigation.procedure_name}%")
            ).first()
            
            if not existing_item:
                # Add bill item to existing bill
                bill_item = BillItem(
                    bill_id=existing_bill.id,
                    item_code=investigation.gdrg_code or "MISC",
                    item_name=f"Investigation: {investigation.procedure_name or investigation.gdrg_code}",
                    category=investigation.investigation_type or "procedure",  # Use investigation_type as category
                    quantity=1,
                    unit_price=unit_price,
                    total_price=total_price
                )
                db.add(bill_item)
                existing_bill.total_amount += total_price
        else:
            # Create new bill
            bill_number = f"BILL-{random.randint(100000, 999999)}"
            bill = Bill(
                encounter_id=encounter.id,
                bill_number=bill_number,
                is_insured=is_insured_encounter,
                total_amount=total_price,
                created_by=current_user.id
            )
            db.add(bill)
            db.flush()
            
            # Create bill item
            bill_item = BillItem(
                bill_id=bill.id,
                item_code=investigation.gdrg_code or "MISC",
                item_name=f"Investigation: {investigation.procedure_name or investigation.gdrg_code}",
                category=investigation.investigation_type or "procedure",  # Use investigation_type as category
                quantity=1,
                unit_price=unit_price,
                total_price=total_price
            )
            db.add(bill_item)
    
    db.commit()
    db.refresh(investigation)
    return {"investigation_id": investigation.id, "status": investigation.status}


# Lab Result schemas
class LabResultCreate(BaseModel):
    """Lab result creation model"""
    investigation_id: int
    results_text: Optional[str] = None


class LabResultResponse(BaseModel):
    """Lab result response model"""
    id: int
    investigation_id: int
    results_text: Optional[str]
    attachment_path: Optional[str]
    entered_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/lab-result", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    investigation_id: int = Form(...),
    results_text: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Admin"]))
):
    """Create or update lab result with optional file attachment"""
    # Verify investigation exists and is a lab investigation
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.investigation_type != "lab":
        raise HTTPException(status_code=400, detail="This endpoint is only for lab investigations")
    
    # Handle file upload
    attachment_path = None
    if attachment:
        import os
        import uuid
        from pathlib import Path
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/lab_results")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(attachment.filename).suffix if attachment.filename else ".pdf"
        file_name = f"{investigation_id}_{uuid.uuid4()}{file_ext}"
        file_path = upload_dir / file_name
        
        # Save file - UploadFile.read() returns bytes
        content = await attachment.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Store relative path for serving
        attachment_path = f"lab_results/{file_name}"
    
    # Check if result already exists
    existing_result = db.query(LabResult).filter(LabResult.investigation_id == investigation_id).first()
    
    if existing_result:
        # Update existing result
        existing_result.results_text = results_text
        if attachment_path:
            # Delete old attachment if exists
            old_path = Path("uploads") / existing_result.attachment_path
            if existing_result.attachment_path and old_path.exists():
                old_path.unlink()
            existing_result.attachment_path = attachment_path
        existing_result.updated_at = datetime.utcnow()
        
        # Mark investigation as completed if results are entered
        if results_text or attachment_path:
            investigation.status = InvestigationStatus.COMPLETED.value
    else:
        # Create new result
        lab_result = LabResult(
            investigation_id=investigation_id,
            results_text=results_text,
            attachment_path=attachment_path,
            entered_by=current_user.id
        )
        db.add(lab_result)
        
        # Mark investigation as completed if results are entered
        if results_text or attachment_path:
            investigation.status = InvestigationStatus.COMPLETED.value
    
    db.commit()
    if existing_result:
        db.refresh(existing_result)
        return existing_result
    else:
        db.refresh(lab_result)
        return lab_result


@router.get("/lab-result/investigation/{investigation_id}", response_model=Optional[LabResultResponse])
def get_lab_result(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lab result for an investigation"""
    result = db.query(LabResult).filter(LabResult.investigation_id == investigation_id).first()
    return result


@router.get("/lab-result/{investigation_id}/download")
def download_lab_result_attachment(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download lab result attachment file"""
    import os
    import mimetypes
    from pathlib import Path
    
    # Get lab result
    result = db.query(LabResult).filter(LabResult.investigation_id == investigation_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Lab result not found")
    
    if not result.attachment_path:
        raise HTTPException(status_code=404, detail="No attachment found for this lab result")
    
    # Build full file path
    file_path = Path("uploads") / result.attachment_path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        # Default to application/octet-stream if unknown
        mime_type = "application/octet-stream"
    
    # Read file
    with open(file_path, "rb") as f:
        file_content = f.read()
    
    # Get filename for download
    filename = file_path.name
    
    return Response(
        content=file_content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_content))
        }
    )


# Scan Result schemas
class ScanResultCreate(BaseModel):
    """Scan result creation model"""
    investigation_id: int
    results_text: Optional[str] = None


class ScanResultResponse(BaseModel):
    """Scan result response model"""
    id: int
    investigation_id: int
    results_text: Optional[str]
    attachment_path: Optional[str]
    entered_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/scan-result", response_model=ScanResultResponse, status_code=status.HTTP_201_CREATED)
async def create_scan_result(
    investigation_id: int = Form(...),
    results_text: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Scan", "Admin"]))
):
    """Create or update scan result with optional file attachment"""
    # Verify investigation exists and is a scan investigation
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.investigation_type != "scan":
        raise HTTPException(status_code=400, detail="This endpoint is only for scan investigations")
    
    # Handle file upload
    attachment_path = None
    if attachment:
        import os
        import uuid
        from pathlib import Path
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/scan_results")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(attachment.filename).suffix if attachment.filename else ".pdf"
        file_name = f"{investigation_id}_{uuid.uuid4()}{file_ext}"
        file_path = upload_dir / file_name
        
        # Save file - UploadFile.read() returns bytes
        content = await attachment.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Store relative path for serving
        attachment_path = f"scan_results/{file_name}"
    
    # Check if result already exists
    existing_result = db.query(ScanResult).filter(ScanResult.investigation_id == investigation_id).first()
    
    if existing_result:
        # Update existing result
        existing_result.results_text = results_text
        if attachment_path:
            # Delete old attachment if exists
            old_path = Path("uploads") / existing_result.attachment_path
            if existing_result.attachment_path and old_path.exists():
                old_path.unlink()
            existing_result.attachment_path = attachment_path
        existing_result.updated_at = datetime.utcnow()
        
        # Mark investigation as completed if results are entered
        if results_text or attachment_path:
            investigation.status = InvestigationStatus.COMPLETED.value
    else:
        # Create new result
        scan_result = ScanResult(
            investigation_id=investigation_id,
            results_text=results_text,
            attachment_path=attachment_path,
            entered_by=current_user.id
        )
        db.add(scan_result)
        
        # Mark investigation as completed if results are entered
        if results_text or attachment_path:
            investigation.status = InvestigationStatus.COMPLETED.value
    
    db.commit()
    if existing_result:
        db.refresh(existing_result)
        return existing_result
    else:
        db.refresh(scan_result)
        return scan_result


@router.get("/scan-result/investigation/{investigation_id}", response_model=Optional[ScanResultResponse])
def get_scan_result(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get scan result for an investigation"""
    result = db.query(ScanResult).filter(ScanResult.investigation_id == investigation_id).first()
    return result


@router.get("/scan-result/{investigation_id}/download")
def download_scan_result_attachment(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download scan result attachment file"""
    import mimetypes
    from pathlib import Path
    
    # Get scan result
    result = db.query(ScanResult).filter(ScanResult.investigation_id == investigation_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Scan result not found")
    
    if not result.attachment_path:
        raise HTTPException(status_code=404, detail="No attachment found for this scan result")
    
    # Build full file path
    file_path = Path("uploads") / result.attachment_path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "application/octet-stream"
    
    # Read file
    with open(file_path, "rb") as f:
        file_content = f.read()
    
    # Get filename for download
    filename = file_path.name
    
    return Response(
        content=file_content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_content))
        }
    )


# X-ray Result schemas
class XrayResultCreate(BaseModel):
    """X-ray result creation model"""
    investigation_id: int
    results_text: Optional[str] = None


class XrayResultResponse(BaseModel):
    """X-ray result response model"""
    id: int
    investigation_id: int
    results_text: Optional[str]
    attachment_path: Optional[str]
    entered_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/xray-result", response_model=XrayResultResponse, status_code=status.HTTP_201_CREATED)
async def create_xray_result(
    investigation_id: int = Form(...),
    results_text: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Xray", "Admin"]))
):
    """Create or update x-ray result with optional file attachment"""
    # Verify investigation exists and is an xray investigation
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.investigation_type != "xray":
        raise HTTPException(status_code=400, detail="This endpoint is only for x-ray investigations")
    
    # Handle file upload
    attachment_path = None
    if attachment:
        import os
        import uuid
        from pathlib import Path
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/xray_results")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_ext = Path(attachment.filename).suffix if attachment.filename else ".pdf"
        file_name = f"{investigation_id}_{uuid.uuid4()}{file_ext}"
        file_path = upload_dir / file_name
        
        # Save file - UploadFile.read() returns bytes
        content = await attachment.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Store relative path for serving
        attachment_path = f"xray_results/{file_name}"
    
    # Check if result already exists
    existing_result = db.query(XrayResult).filter(XrayResult.investigation_id == investigation_id).first()
    
    if existing_result:
        # Update existing result
        existing_result.results_text = results_text
        if attachment_path:
            # Delete old attachment if exists
            old_path = Path("uploads") / existing_result.attachment_path
            if existing_result.attachment_path and old_path.exists():
                old_path.unlink()
            existing_result.attachment_path = attachment_path
        existing_result.updated_at = datetime.utcnow()
        
        # Mark investigation as completed if results are entered
        if results_text or attachment_path:
            investigation.status = InvestigationStatus.COMPLETED.value
    else:
        # Create new result
        xray_result = XrayResult(
            investigation_id=investigation_id,
            results_text=results_text,
            attachment_path=attachment_path,
            entered_by=current_user.id
        )
        db.add(xray_result)
        
        # Mark investigation as completed if results are entered
        if results_text or attachment_path:
            investigation.status = InvestigationStatus.COMPLETED.value
    
    db.commit()
    if existing_result:
        db.refresh(existing_result)
        return existing_result
    else:
        db.refresh(xray_result)
        return xray_result


@router.get("/xray-result/investigation/{investigation_id}", response_model=Optional[XrayResultResponse])
def get_xray_result(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get x-ray result for an investigation"""
    result = db.query(XrayResult).filter(XrayResult.investigation_id == investigation_id).first()
    return result


@router.get("/xray-result/{investigation_id}/download")
def download_xray_result_attachment(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download x-ray result attachment file"""
    import mimetypes
    from pathlib import Path
    
    # Get x-ray result
    result = db.query(XrayResult).filter(XrayResult.investigation_id == investigation_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="X-ray result not found")
    
    if not result.attachment_path:
        raise HTTPException(status_code=404, detail="No attachment found for this x-ray result")
    
    # Build full file path
    file_path = Path("uploads") / result.attachment_path
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Determine MIME type
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if not mime_type:
        mime_type = "application/octet-stream"
    
    # Read file
    with open(file_path, "rb") as f:
        file_content = f.read()
    
    # Get filename for download
    filename = file_path.name
    
    return Response(
        content=file_content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_content))
        }
    )


# Consultation Notes schemas
class ConsultationNotesCreate(BaseModel):
    """Consultation notes creation/update model"""
    encounter_id: int
    presenting_complaints: Optional[str] = None
    doctor_notes: Optional[str] = None
    follow_up_date: Optional[str] = None  # ISO date string (YYYY-MM-DD)
    outcome: Optional[str] = None  # referred | discharged | recommended_for_admission
    admission_ward: Optional[str] = None  # required when outcome == recommended_for_admission


class ConsultationNotesResponse(BaseModel):
    """Consultation notes response model"""
    id: int
    encounter_id: int
    presenting_complaints: Optional[str]
    doctor_notes: Optional[str]
    follow_up_date: Optional[str] = None
    outcome: Optional[str] = None
    admission_ward: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/notes/encounter/{encounter_id}", response_model=Optional[ConsultationNotesResponse])
def get_consultation_notes(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get consultation notes for an encounter"""
    notes = db.query(ConsultationNotes).filter(ConsultationNotes.encounter_id == encounter_id).first()
    if notes:
        # Fetch admission recommendation if exists
        admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.encounter_id == encounter_id).first()
        # Serialize follow_up_date properly
        return {
            "id": notes.id,
            "encounter_id": notes.encounter_id,
            "presenting_complaints": notes.presenting_complaints,
            "doctor_notes": notes.doctor_notes,
            "follow_up_date": notes.follow_up_date.isoformat() if notes.follow_up_date else None,
            "outcome": notes.outcome,
            "admission_ward": (admission.ward if admission else None),
            "created_at": notes.created_at,
            "updated_at": notes.updated_at,
        }
    return None


@router.post("/notes", response_model=ConsultationNotesResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_consultation_notes(
    notes_data: ConsultationNotesCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Create or update consultation notes for an encounter"""
    encounter = db.query(Encounter).filter(Encounter.id == notes_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Check if notes already exist
    existing_notes = db.query(ConsultationNotes).filter(
        ConsultationNotes.encounter_id == notes_data.encounter_id
    ).first()
    
    from datetime import date as date_type
    follow_up_date = None
    if notes_data.follow_up_date and notes_data.follow_up_date.strip():
        try:
            follow_up_date = date_type.fromisoformat(notes_data.follow_up_date.strip())
        except (ValueError, AttributeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid follow_up_date format. Use YYYY-MM-DD. Error: {str(e)}")
    
    if existing_notes:
        # Update existing notes
        existing_notes.presenting_complaints = notes_data.presenting_complaints
        existing_notes.doctor_notes = notes_data.doctor_notes
        existing_notes.follow_up_date = follow_up_date
        existing_notes.outcome = notes_data.outcome
        existing_notes.updated_at = datetime.utcnow()
        # Handle admission recommendation
        admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.encounter_id == notes_data.encounter_id).first()
        if notes_data.outcome == "recommended_for_admission" and notes_data.admission_ward:
            if admission:
                admission.ward = notes_data.admission_ward
                admission.updated_at = datetime.utcnow()
            else:
                admission = AdmissionRecommendation(
                    encounter_id=notes_data.encounter_id,
                    ward=notes_data.admission_ward,
                    recommended_by=current_user.id
                )
                db.add(admission)
        else:
            # If outcome changed away from admission, remove admission record if exists
            if admission:
                db.delete(admission)
        db.commit()
        db.refresh(existing_notes)
        # Serialize response properly
        admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.encounter_id == notes_data.encounter_id).first()
        return {
            "id": existing_notes.id,
            "encounter_id": existing_notes.encounter_id,
            "presenting_complaints": existing_notes.presenting_complaints,
            "doctor_notes": existing_notes.doctor_notes,
            "follow_up_date": existing_notes.follow_up_date.isoformat() if existing_notes.follow_up_date else None,
            "outcome": existing_notes.outcome,
            "admission_ward": (admission.ward if admission else None),
            "created_at": existing_notes.created_at,
            "updated_at": existing_notes.updated_at,
        }
    else:
        # Create new notes
        notes = ConsultationNotes(
            encounter_id=notes_data.encounter_id,
            presenting_complaints=notes_data.presenting_complaints,
            doctor_notes=notes_data.doctor_notes,
            follow_up_date=follow_up_date,
            outcome=notes_data.outcome,
            created_by=current_user.id
        )
        db.add(notes)
        # Create admission recommendation if applicable
        if notes_data.outcome == "recommended_for_admission" and notes_data.admission_ward:
            admission = AdmissionRecommendation(
                encounter_id=notes_data.encounter_id,
                ward=notes_data.admission_ward,
                recommended_by=current_user.id
            )
            db.add(admission)
        db.commit()
        db.refresh(notes)
        # Serialize response properly
        admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.encounter_id == notes_data.encounter_id).first()
        return {
            "id": notes.id,
            "encounter_id": notes.encounter_id,
            "presenting_complaints": notes.presenting_complaints,
            "doctor_notes": notes.doctor_notes,
            "follow_up_date": notes.follow_up_date.isoformat() if notes.follow_up_date else None,
            "outcome": notes.outcome,
            "admission_ward": (admission.ward if admission else None),
            "created_at": notes.created_at,
            "updated_at": notes.updated_at,
        }



# Admission recommendations endpoints
class AdmissionRecommendationResponse(BaseModel):
    """Admission recommendation response model"""
    id: int
    encounter_id: int
    ward: str
    recommended_by: int
    created_at: datetime
    updated_at: datetime
    
    # Patient and encounter details
    patient_name: Optional[str] = None
    patient_surname: Optional[str] = None
    patient_other_names: Optional[str] = None
    patient_card_number: Optional[str] = None
    patient_gender: Optional[str] = None
    patient_date_of_birth: Optional[str] = None
    encounter_created_at: Optional[datetime] = None
    encounter_service_type: Optional[str] = None


@router.get("/admissions", response_model=List[AdmissionRecommendationResponse])
def get_admission_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "Admin"]))
):
    """Get all admission recommendations with patient and encounter details"""
    from app.models.patient import Patient
    
    try:
        admissions = db.query(AdmissionRecommendation)\
            .options(
                joinedload(AdmissionRecommendation.encounter).joinedload(Encounter.patient)
            )\
            .order_by(AdmissionRecommendation.created_at.desc())\
            .all()
        
        print(f"Found {len(admissions)} admission recommendations")  # Debug log
        
        result = []
        for admission in admissions:
            try:
                encounter = admission.encounter
                if not encounter:
                    print(f"Warning: Admission {admission.id} has no encounter")
                    continue
                
                patient = encounter.patient
                if not patient:
                    print(f"Warning: Encounter {encounter.id} has no patient")
                    continue
                
                result.append({
                    "id": admission.id,
                    "encounter_id": admission.encounter_id,
                    "ward": admission.ward,
                    "recommended_by": admission.recommended_by,
                    "created_at": admission.created_at,
                    "updated_at": admission.updated_at,
                    "patient_name": patient.name,
                    "patient_surname": patient.surname,
                    "patient_other_names": patient.other_names,
                    "patient_card_number": patient.card_number,
                    "patient_gender": patient.gender,
                    "patient_date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                    "encounter_created_at": encounter.created_at,
                    "encounter_service_type": encounter.department,
                })
            except Exception as e:
                print(f"Error processing admission {admission.id}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"Returning {len(result)} admission recommendations")  # Debug log
        return result
    except Exception as e:
        print(f"Error in get_admission_recommendations: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching admission recommendations: {str(e)}")