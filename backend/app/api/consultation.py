"""
Consultation endpoints (diagnoses, prescriptions, investigations)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File, Form, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
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
    diagnosis_status: Optional[str] = None  # 'new', 'old', or 'recurring'
    is_provisional: bool = False
    is_chief: bool = False


class DiagnosisResponse(BaseModel):
    """Diagnosis response model"""
    id: int
    encounter_id: int
    icd10: Optional[str]
    diagnosis: str
    gdrg_code: Optional[str]
    diagnosis_status: Optional[str]
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
    dispenser_name: Optional[str] = None  # Full name of the dispenser
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
    encounter_id: Optional[int] = None  # Optional for direct walk-in services
    patient_id: Optional[int] = None  # Required if encounter_id is not provided (for direct services)
    patient_card_number: Optional[str] = None  # Alternative to patient_id for direct services
    gdrg_code: str
    procedure_name: Optional[str] = None
    investigation_type: str  # lab, scan, xray
    notes: Optional[str] = None  # Notes/remarks from doctor
    price: Optional[str] = None  # Price of the investigation
    is_insured: Optional[bool] = False  # For direct services without encounter
    ccc_number: Optional[str] = None  # For direct services without encounter


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
    completed_by: Optional[int] = None
    cancelled_by: Optional[int] = None
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    created_at: datetime
    # Patient and encounter info for list view
    patient_name: Optional[str] = None
    patient_card_number: Optional[str] = None
    encounter_date: Optional[datetime] = None
    # User names for display
    confirmed_by_name: Optional[str] = None
    completed_by_name: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("/diagnosis", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
def create_diagnosis(
    diagnosis_data: DiagnosisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin", "Records"]))
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
    
    # Auto-add ICD-10 code to system if it doesn't exist
    icd10_code = diagnosis_dict.get('icd10', '').strip()
    if icd10_code:
        # Check if ICD-10 code exists in mappings
        existing_mapping = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.icd10_code == icd10_code
        ).first()
        
        if not existing_mapping:
            # Add new ICD-10 code to system (without DRG mapping - unmapped)
            new_icd10 = ICD10DRGMapping(
                drg_code='',  # Empty DRG code means unmapped
                drg_description='',
                icd10_code=icd10_code,
                icd10_description=diagnosis_dict.get('diagnosis', '').strip() or '',
                notes='Auto-added from diagnosis entry',
                remarks='',
                is_active=True
            )
            db.add(new_icd10)
            db.flush()  # Flush to get the ID but don't commit yet
    
    # Auto-map ICD-10 to DRG code if ICD-10 is provided but DRG is not
    if icd10_code and not diagnosis_dict.get('gdrg_code'):
        # Find first DRG code mapped to this ICD-10 code (with non-empty DRG code)
        mapping = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.icd10_code == icd10_code,
            ICD10DRGMapping.is_active == True,
            ICD10DRGMapping.drg_code != '',
            ICD10DRGMapping.drg_code.isnot(None)
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
    current_user: User = Depends(require_role(["Doctor", "Admin", "Pharmacy", "Pharmacy Head", "PA"]))
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
    """Helper function to add prescriber and dispenser information to a prescription response"""
    # Get prescriber information
    prescriber = db.query(User).filter(User.id == prescription.prescribed_by).first()
    prescriber_name = prescriber.full_name if prescriber else None
    prescriber_role = prescriber.role if prescriber else None
    
    # Get dispenser information
    dispenser = db.query(User).filter(User.id == prescription.dispensed_by).first() if prescription.dispensed_by else None
    dispenser_name = dispenser.full_name if dispenser else None
    
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
        'dispenser_name': dispenser_name,
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
    is_external: Optional[bool] = None  # Mark prescription as external (to be filled outside)


@router.put("/prescription/{prescription_id}/dispense", response_model=PrescriptionResponse)
def dispense_prescription(
    prescription_id: int,
    dispense_data: Optional[PrescriptionDispense] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
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
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Confirm a prescription (allows pharmacy to update details) and automatically generate a bill item"""
    from app.models.bill import Bill, BillItem
    from app.services.price_list_service_v2 import get_price_from_all_tables
    import random
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Prevent confirming already external prescriptions (they're auto-confirmed and not billed)
    # Check is_external as integer (0 or 1) since SQLite stores it as INTEGER
    current_is_external = bool(prescription.is_external) if hasattr(prescription, 'is_external') else False
    if current_is_external:
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
    # Also allow marking as external if drug is not in stock
    mark_as_external = False
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
        if dispense_data.is_external is not None:
            mark_as_external = dispense_data.is_external
            # Convert boolean to integer (0 or 1) for SQLite
            prescription.is_external = 1 if mark_as_external else 0
    
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
    if is_external or mark_as_external:
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


@router.put("/prescription/{prescription_id}/unconfirm", response_model=PrescriptionResponse)
def unconfirm_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Revert a confirmed prescription back to pending status (undo confirmation)"""
    from app.models.bill import Bill, BillItem
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.confirmed_by is None:
        raise HTTPException(status_code=400, detail="Prescription has not been confirmed")
    
    # Prevent unconfirming if prescription has been dispensed
    if prescription.dispensed_by is not None:
        raise HTTPException(
            status_code=400, 
            detail="Cannot revert a prescription that has already been dispensed. Please return it first."
        )
    
    # Prevent unconfirming external prescriptions
    is_external = bool(prescription.is_external) if hasattr(prescription, 'is_external') else False
    if is_external:
        raise HTTPException(
            status_code=400,
            detail="Cannot revert external prescriptions. They are automatically confirmed and not billed."
        )
    
    # Find and remove the bill item that was created during confirmation
    # Find all unpaid bills for this encounter
    encounter = db.query(Encounter).filter(Encounter.id == prescription.encounter_id).first()
    if encounter:
        unpaid_bills = db.query(Bill).filter(
            Bill.encounter_id == encounter.id,
            Bill.is_paid == False
        ).all()
        
        for bill in unpaid_bills:
            # Find the bill item for this prescription
            bill_item = db.query(BillItem).filter(
                BillItem.bill_id == bill.id,
                BillItem.item_code == prescription.medicine_code,
                BillItem.item_name.like(f"%{prescription.medicine_name}%")
            ).first()
            
            if bill_item:
                # Check if this bill item has been paid (has receipts)
                # If the bill item has any payments, we can't remove it
                from app.models.bill import Receipt, ReceiptItem
                receipt_items = db.query(ReceiptItem).join(Receipt).filter(
                    Receipt.bill_id == bill.id,
                    ReceiptItem.bill_item_id == bill_item.id
                ).all()
                
                if receipt_items:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot revert prescription. The bill item has already been paid. Please refund the payment first."
                    )
                
                # Remove the bill item and update bill total
                bill.total_amount -= bill_item.total_price
                if bill.total_amount < 0:
                    bill.total_amount = 0
                
                db.delete(bill_item)
                
                # If bill has no items left and total is 0, we can optionally delete the bill
                # But for now, we'll just leave it with 0 total
                remaining_items = db.query(BillItem).filter(BillItem.bill_id == bill.id).count()
                if remaining_items == 0 and bill.total_amount == 0:
                    # Optionally delete empty bill, but for now we'll keep it
                    pass
                
                break  # Found and removed the bill item, exit loop
    
    # Revert prescription confirmation
    prescription.confirmed_by = None
    prescription.confirmed_at = None
    
    db.commit()
    db.refresh(prescription)
    return add_prescriber_info_to_response(prescription, db)


@router.put("/prescription/{prescription_id}/return", response_model=PrescriptionResponse)
def return_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
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


class BulkConfirmInvestigations(BaseModel):
    """Model for bulk confirming multiple investigations"""
    investigation_ids: List[int]  # List of investigation IDs to confirm


@router.put("/investigations/bulk-confirm")
def bulk_confirm_investigations(
    bulk_data: BulkConfirmInvestigations,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Scan", "Xray", "Admin", "Lab Head", "Scan Head", "Xray Head"]))
):
    """Bulk confirm multiple investigation requests"""
    if not bulk_data.investigation_ids:
        raise HTTPException(status_code=400, detail="No investigation IDs provided")
    
    investigations = db.query(Investigation).filter(
        Investigation.id.in_(bulk_data.investigation_ids)
    ).all()
    
    if len(investigations) != len(bulk_data.investigation_ids):
        raise HTTPException(status_code=404, detail="Some investigations not found")
    
    confirmed_count = 0
    errors = []
    
    for investigation in investigations:
        try:
            # Don't allow confirming cancelled investigations
            if investigation.status == InvestigationStatus.CANCELLED.value:
                errors.append(f"Investigation {investigation.id} is cancelled")
                continue
            
            # Don't allow confirming already confirmed or completed investigations
            if investigation.status in [InvestigationStatus.CONFIRMED.value, InvestigationStatus.COMPLETED.value]:
                errors.append(f"Investigation {investigation.id} is already {investigation.status}")
                continue
            
            # Verify user role matches investigation type
            if current_user.role not in ["Admin", "Lab Head", "Scan Head", "Xray Head"]:
                if investigation.investigation_type == "lab" and current_user.role != "Lab":
                    errors.append(f"Only Lab staff can confirm investigation {investigation.id}")
                    continue
                elif investigation.investigation_type == "scan" and current_user.role != "Scan":
                    errors.append(f"Only Scan staff can confirm investigation {investigation.id}")
                    continue
                elif investigation.investigation_type == "xray" and current_user.role != "Xray":
                    errors.append(f"Only Xray staff can confirm investigation {investigation.id}")
                    continue
            
            # Confirm the investigation and generate bill (same logic as single confirm)
            investigation.status = InvestigationStatus.CONFIRMED.value
            investigation.confirmed_by = current_user.id
            
            # Generate bill if investigation has an encounter
            if investigation.encounter_id:
                from app.models.bill import Bill, BillItem
                from app.services.price_list_service_v2 import get_price_from_all_tables
                import random
                
                encounter = db.query(Encounter).filter(Encounter.id == investigation.encounter_id).first()
                if encounter:
                    is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
                    
                    # Get price for the investigation
                    unit_price = 0.0
                    if investigation.gdrg_code:
                        # Determine service type based on investigation type
                        service_type = None
                        if investigation.investigation_type == "lab":
                            service_type = "Lab"
                        elif investigation.investigation_type == "scan":
                            service_type = "Scan"
                        elif investigation.investigation_type == "xray":
                            service_type = "X-ray"
                        
                        try:
                            unit_price = get_price_from_all_tables(db, investigation.gdrg_code, is_insured_encounter, service_type)
                        except Exception as e:
                            print(f"ERROR bulk_confirm: Failed to get price for investigation {investigation.id}: {e}")
                            # Fallback to stored price
                            if investigation.price:
                                try:
                                    unit_price = float(investigation.price)
                                except (ValueError, TypeError):
                                    unit_price = 0.0
                    else:
                        # No gdrg_code, try stored price
                        if investigation.price:
                            try:
                                unit_price = float(investigation.price)
                            except (ValueError, TypeError):
                                unit_price = 0.0
                    
                    total_price = unit_price
                    
                    # Create/add to bill if price > 0
                    if total_price > 0:
                        existing_bill = db.query(Bill).filter(
                            Bill.encounter_id == encounter.id,
                            Bill.is_paid == False
                        ).first()
                        
                        if existing_bill:
                            # Check if already in bill
                            existing_item = db.query(BillItem).filter(
                                BillItem.bill_id == existing_bill.id,
                                BillItem.item_code == investigation.gdrg_code,
                                BillItem.item_name.like(f"%{investigation.procedure_name}%")
                            ).first()
                            
                            if not existing_item:
                                bill_item = BillItem(
                                    bill_id=existing_bill.id,
                                    item_code=investigation.gdrg_code or "MISC",
                                    item_name=f"Investigation: {investigation.procedure_name or investigation.gdrg_code}",
                                    category=investigation.investigation_type or "procedure",
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
                            
                            bill_item = BillItem(
                                bill_id=bill.id,
                                item_code=investigation.gdrg_code or "MISC",
                                item_name=f"Investigation: {investigation.procedure_name or investigation.gdrg_code}",
                                category=investigation.investigation_type or "procedure",
                                quantity=1,
                                unit_price=unit_price,
                                total_price=total_price
                            )
                            db.add(bill_item)
            
            confirmed_count += 1
            
        except Exception as e:
            errors.append(f"Error confirming investigation {investigation.id}: {str(e)}")
    
    db.commit()
    
    return {
        "confirmed_count": confirmed_count,
        "total_requested": len(bulk_data.investigation_ids),
        "errors": errors if errors else None
    }


@router.post("/investigation", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
def create_investigation(
    investigation_data: InvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin", "Records", "Scan", "Scan Head", "Xray", "Xray Head", "Lab", "Lab Head"]))
):
    """Request an investigation (lab, scan, x-ray). Can be from consultation (with encounter_id) or direct walk-in (without encounter_id)"""
    from app.services.price_list_service_v2 import get_price_from_all_tables
    from app.models.patient import Patient
    
    encounter = None
    is_insured = False
    
    # Handle investigation with encounter (from consultation)
    if investigation_data.encounter_id:
        encounter = db.query(Encounter).filter(Encounter.id == investigation_data.encounter_id).first()
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        is_insured = bool(encounter.ccc_number)
    # Handle direct walk-in service (without encounter)
    else:
        # Must provide either patient_id or patient_card_number
        patient = None
        if investigation_data.patient_id:
            patient = db.query(Patient).filter(Patient.id == investigation_data.patient_id).first()
        elif investigation_data.patient_card_number:
            patient = db.query(Patient).filter(Patient.card_number == investigation_data.patient_card_number).first()
        else:
            raise HTTPException(
                status_code=400,
                detail="For direct services, either patient_id or patient_card_number must be provided"
            )
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Use provided insurance info or patient's insurance status
        if investigation_data.is_insured is not None:
            is_insured = investigation_data.is_insured
        else:
            is_insured = patient.insured or bool(investigation_data.ccc_number)
    
    # Auto-fetch price from price list if not provided
    price = investigation_data.price
    if not price and investigation_data.gdrg_code:
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


@router.get("/investigation/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a single investigation by ID with patient and encounter info"""
    from app.models.patient import Patient
    
    investigation = (
        db.query(Investigation)
        .join(Encounter, Investigation.encounter_id == Encounter.id)
        .join(Patient, Encounter.patient_id == Patient.id)
        .filter(Investigation.id == investigation_id)
        .first()
    )
    
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Get user names
    confirmed_by_name = None
    if investigation.confirmed_by:
        confirmed_user = db.query(User).filter(User.id == investigation.confirmed_by).first()
        confirmed_by_name = confirmed_user.full_name if confirmed_user else None
    
    completed_by_name = None
    if investigation.completed_by:
        completed_user = db.query(User).filter(User.id == investigation.completed_by).first()
        completed_by_name = completed_user.full_name if completed_user else None
    
    inv_dict = {
        "id": investigation.id,
        "encounter_id": investigation.encounter_id,
        "gdrg_code": investigation.gdrg_code,
        "procedure_name": investigation.procedure_name,
        "investigation_type": investigation.investigation_type,
        "notes": investigation.notes,
        "price": investigation.price,
        "status": investigation.status,
        "confirmed_by": investigation.confirmed_by,
        "completed_by": investigation.completed_by,
        "cancelled_by": investigation.cancelled_by,
        "cancellation_reason": investigation.cancellation_reason,
        "cancelled_at": investigation.cancelled_at,
        "created_at": investigation.created_at,
        "patient_name": f"{investigation.encounter.patient.name} {investigation.encounter.patient.surname or ''}".strip(),
        "patient_card_number": investigation.encounter.patient.card_number,
        "encounter_date": investigation.encounter.created_at,
        "confirmed_by_name": confirmed_by_name,
        "completed_by_name": completed_by_name,
    }
    return InvestigationResponse(**inv_dict)


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


@router.get("/investigation/list/{investigation_type}", response_model=List[InvestigationResponse])
def get_investigations_by_type(
    investigation_type: str,  # lab, scan, xray
    status: Optional[str] = None,  # requested, confirmed, completed, cancelled
    search: Optional[str] = None,  # Search by card number or patient name
    date: Optional[str] = None,  # Filter by date (YYYY-MM-DD), defaults to today
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get investigations by type with filters
    Used by Lab, Scan, and X-ray pages to show service requests
    """
    from app.models.patient import Patient
    from datetime import datetime, date as date_class, timedelta
    
    # Validate investigation type
    valid_types = ["lab", "scan", "xray"]
    if investigation_type.lower() not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid investigation_type. Must be one of: {', '.join(valid_types)}")
    
    # Build base query with joins
    query = (
        db.query(Investigation)
        .join(Encounter, Investigation.encounter_id == Encounter.id)
        .join(Patient, Encounter.patient_id == Patient.id)
    )
    
    # Filter by investigation type
    query = query.filter(Investigation.investigation_type == investigation_type.lower())
    
    # Filter by status
    if status:
        valid_statuses = ["requested", "confirmed", "completed", "cancelled"]
        if status.lower() not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        query = query.filter(Investigation.status == status.lower())
    
    # Filter by date (default to today)
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}")
    else:
        filter_date = date_class.today()
    
    # Filter by date (using encounter created_at date)
    start_of_day = datetime.combine(filter_date, datetime.min.time())
    end_of_day = datetime.combine(filter_date, datetime.max.time())
    query = query.filter(Encounter.created_at >= start_of_day, Encounter.created_at <= end_of_day)
    
    # Search by card number or patient name
    if search:
        search_term = f"%{search.strip()}%"
        from sqlalchemy import or_
        # Search in card number, name, or surname
        # For full name search, we'll check if search term matches name or surname separately
        query = query.filter(
            or_(
                Patient.card_number.ilike(search_term),
                Patient.name.ilike(search_term),
                Patient.surname.ilike(search_term)
            )
        )
    
    # Order by created_at descending (newest first)
    query = query.order_by(Investigation.created_at.desc())
    
    investigations = query.all()
    
    # Build response with patient info and user names
    result = []
    for inv in investigations:
        # Get user names
        confirmed_by_name = None
        if inv.confirmed_by:
            confirmed_user = db.query(User).filter(User.id == inv.confirmed_by).first()
            confirmed_by_name = confirmed_user.full_name if confirmed_user else None
        
        completed_by_name = None
        if inv.completed_by:
            completed_user = db.query(User).filter(User.id == inv.completed_by).first()
            completed_by_name = completed_user.full_name if completed_user else None
        
        inv_dict = {
            "id": inv.id,
            "encounter_id": inv.encounter_id,
            "gdrg_code": inv.gdrg_code,
            "procedure_name": inv.procedure_name,
            "investigation_type": inv.investigation_type,
            "notes": inv.notes,
            "price": inv.price,
            "status": inv.status,
            "confirmed_by": inv.confirmed_by,
            "completed_by": inv.completed_by,
            "cancelled_by": inv.cancelled_by,
            "cancellation_reason": inv.cancellation_reason,
            "cancelled_at": inv.cancelled_at,
            "created_at": inv.created_at,
            "patient_name": f"{inv.encounter.patient.name} {inv.encounter.patient.surname or ''}".strip(),
            "patient_card_number": inv.encounter.patient.card_number,
            "encounter_date": inv.encounter.created_at,
            "confirmed_by_name": confirmed_by_name,
            "completed_by_name": completed_by_name,
        }
        result.append(InvestigationResponse(**inv_dict))
    
    return result


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
    current_user: User = Depends(require_role(["Lab", "Scan", "Xray", "Admin", "Lab Head", "Scan Head", "Xray Head"]))
):
    """Update investigation details (gdrg_code, procedure_name, investigation_type) - allows staff to change service"""
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Check permissions - only staff matching investigation type or Admin/Head can update
    if current_user.role not in ["Admin", "Lab Head", "Scan Head", "Xray Head"]:
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


@router.put("/investigation/{investigation_id}/revert-status")
def revert_investigation_status(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab Head", "Scan Head", "Xray Head", "Admin"]))
):
    """Revert investigation status from completed to confirmed (to allow editing results) - Admin and Head roles only"""
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Only allow reverting from completed to confirmed
    if investigation.status != InvestigationStatus.COMPLETED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot revert status. Current status is '{investigation.status}'. Only completed investigations can be reverted."
        )
    
    # Verify investigation type matches (each Head can only revert their own investigation type)
    if current_user.role == "Lab Head" and investigation.investigation_type != "lab":
        raise HTTPException(
            status_code=403,
            detail="Lab Head can only revert lab investigations"
        )
    elif current_user.role == "Scan Head" and investigation.investigation_type != "scan":
        raise HTTPException(
            status_code=403,
            detail="Scan Head can only revert scan investigations"
        )
    elif current_user.role == "Xray Head" and investigation.investigation_type != "xray":
        raise HTTPException(
            status_code=403,
            detail="Xray Head can only revert xray investigations"
        )
    
    # Revert status to confirmed
    investigation.status = InvestigationStatus.CONFIRMED.value
    # Clear completed_by when reverting
    investigation.completed_by = None
    
    db.commit()
    db.refresh(investigation)
    
    return {"investigation_id": investigation.id, "status": investigation.status, "message": "Status reverted to confirmed"}


class InvestigationRevertToRequested(BaseModel):
    """Model for reverting investigation from confirmed to requested"""
    reason: str  # Reason for reverting (required)


@router.put("/investigation/{investigation_id}/revert-to-requested")
def revert_investigation_to_requested(
    investigation_id: int,
    revert_data: InvestigationRevertToRequested,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Revert investigation status from confirmed to requested - Admin only"""
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Only allow reverting from confirmed to requested
    if investigation.status != InvestigationStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot revert status. Current status is '{investigation.status}'. Only confirmed investigations can be reverted to requested."
        )
    
    # Revert status to requested
    investigation.status = InvestigationStatus.REQUESTED.value
    # Clear confirmed_by when reverting
    investigation.confirmed_by = None
    # Store revert reason in cancellation_reason field (reusing existing field)
    investigation.cancellation_reason = f"Reverted to requested by Admin: {revert_data.reason}"
    investigation.cancelled_by = current_user.id
    investigation.cancelled_at = datetime.utcnow()
    
    db.commit()
    db.refresh(investigation)
    
    return {"investigation_id": investigation.id, "status": investigation.status, "message": "Status reverted to requested"}


@router.put("/investigation/{investigation_id}/confirm")
def confirm_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Scan", "Xray", "Admin", "Lab Head", "Scan Head", "Xray Head"]))
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
    if current_user.role not in ["Admin", "Lab Head", "Scan Head", "Xray Head"]:
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
    
    # Get encounter to determine insurance status (if exists)
    encounter = None
    is_insured_encounter = False
    
    if investigation.encounter_id:
        encounter = db.query(Encounter).filter(Encounter.id == investigation.encounter_id).first()
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        # Determine if insured based on encounter CCC number
        is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
    else:
        # Direct service without encounter - cannot auto-generate bill item
        # Just confirm the investigation
        investigation.status = InvestigationStatus.CONFIRMED.value
        investigation.confirmed_by = current_user.id
        db.commit()
        db.refresh(investigation)
        return {"investigation_id": investigation.id, "status": investigation.status}
    
    investigation.status = InvestigationStatus.CONFIRMED.value
    investigation.confirmed_by = current_user.id
    
    # Get price for the investigation (co-pay for insured, base rate for cash)
    # Always look up price from price list to ensure correct pricing based on current insurance status
    unit_price = 0.0
    
    if investigation.gdrg_code:
        # Determine service type based on investigation type for better price lookup
        service_type = None
        if investigation.investigation_type == "lab":
            service_type = "Lab"
        elif investigation.investigation_type == "scan":
            service_type = "Scan"
        elif investigation.investigation_type == "xray":
            service_type = "X-ray"
        
        # Always look up price from price list to get correct price based on insurance status
        try:
            unit_price = get_price_from_all_tables(db, investigation.gdrg_code, is_insured_encounter, service_type)
            print(f"DEBUG confirm_investigation: Looked up price for gdrg_code='{investigation.gdrg_code}', is_insured={is_insured_encounter}, service_type='{service_type}', price={unit_price}")
        except Exception as e:
            print(f"ERROR confirm_investigation: Failed to get price from price list: {e}")
            # If lookup fails, try using stored price as fallback
            if investigation.price:
                try:
                    unit_price = float(investigation.price)
                    print(f"DEBUG confirm_investigation: Using stored price as fallback: {unit_price}")
                except (ValueError, TypeError):
                    unit_price = 0.0
    else:
        # No gdrg_code, try using stored price
        if investigation.price:
            try:
                unit_price = float(investigation.price)
                print(f"DEBUG confirm_investigation: Using stored price (no gdrg_code): {unit_price}")
            except (ValueError, TypeError):
                unit_price = 0.0
    
    # If still no price, log warning but continue (bill won't be created)
    if unit_price == 0.0:
        print(f"WARNING confirm_investigation: No price found for investigation {investigation.id}, gdrg_code='{investigation.gdrg_code}', procedure_name='{investigation.procedure_name}'")
    
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
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    # User names for display
    entered_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("/lab-result", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    investigation_id: int = Form(...),
    results_text: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Lab Head", "Admin"]))
):
    """Create or update lab result with optional file attachment"""
    # Verify investigation exists and is a lab investigation
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.investigation_type != "lab":
        raise HTTPException(status_code=400, detail="This endpoint is only for lab investigations")
    
    # If investigation is completed, only Admin and Lab Head can edit
    if investigation.status == InvestigationStatus.COMPLETED.value:
        if current_user.role not in ["Admin", "Lab Head"]:
            raise HTTPException(
                status_code=403,
                detail="Only Admin and Lab Head can edit completed investigations. Please contact Lab Head to revert the status."
            )
    
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
        existing_result.updated_by = current_user.id  # Track who updated
        existing_result.updated_at = datetime.utcnow()
        
        # Mark investigation as completed if results are entered
        if results_text or attachment_path:
            investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_by = current_user.id  # Track who completed
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
            investigation.completed_by = current_user.id  # Track who completed
    
    db.commit()
    if existing_result:
        db.refresh(existing_result)
        # Get user names for response
        entered_user = db.query(User).filter(User.id == existing_result.entered_by).first()
        updated_user = db.query(User).filter(User.id == existing_result.updated_by).first() if existing_result.updated_by else None
        result_dict = {
            "id": existing_result.id,
            "investigation_id": existing_result.investigation_id,
            "results_text": existing_result.results_text,
            "attachment_path": existing_result.attachment_path,
            "entered_by": existing_result.entered_by,
            "updated_by": existing_result.updated_by,
            "created_at": existing_result.created_at,
            "updated_at": existing_result.updated_at,
            "entered_by_name": entered_user.full_name if entered_user else None,
            "updated_by_name": updated_user.full_name if updated_user else None,
        }
        return LabResultResponse(**result_dict)
    else:
        db.refresh(lab_result)
        # Get user names for response
        entered_user = db.query(User).filter(User.id == lab_result.entered_by).first()
        result_dict = {
            "id": lab_result.id,
            "investigation_id": lab_result.investigation_id,
            "results_text": lab_result.results_text,
            "attachment_path": lab_result.attachment_path,
            "entered_by": lab_result.entered_by,
            "updated_by": lab_result.updated_by,
            "created_at": lab_result.created_at,
            "updated_at": lab_result.updated_at,
            "entered_by_name": entered_user.full_name if entered_user else None,
            "updated_by_name": None,
        }
        return LabResultResponse(**result_dict)


@router.get("/lab-result/investigation/{investigation_id}", response_model=Optional[LabResultResponse])
def get_lab_result(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get lab result for an investigation"""
    result = db.query(LabResult).filter(LabResult.investigation_id == investigation_id).first()
    if not result:
        return None
    
    # Get user names
    entered_user = db.query(User).filter(User.id == result.entered_by).first()
    updated_user = db.query(User).filter(User.id == result.updated_by).first() if result.updated_by else None
    
    result_dict = {
        "id": result.id,
        "investigation_id": result.investigation_id,
        "results_text": result.results_text,
        "attachment_path": result.attachment_path,
        "entered_by": result.entered_by,
        "updated_by": result.updated_by,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "entered_by_name": entered_user.full_name if entered_user else None,
        "updated_by_name": updated_user.full_name if updated_user else None,
    }
    return LabResultResponse(**result_dict)


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
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    # User names for display
    entered_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("/scan-result", response_model=ScanResultResponse, status_code=status.HTTP_201_CREATED)
async def create_scan_result(
    investigation_id: int = Form(...),
    results_text: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Scan", "Scan Head", "Admin"]))
):
    """Create or update scan result with optional file attachment"""
    # Verify investigation exists and is a scan investigation
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.investigation_type != "scan":
        raise HTTPException(status_code=400, detail="This endpoint is only for scan investigations")
    
    # If investigation is completed, only Admin and Scan Head can edit
    if investigation.status == InvestigationStatus.COMPLETED.value:
        if current_user.role not in ["Admin", "Scan Head"]:
            raise HTTPException(
                status_code=403,
                detail="Only Admin and Scan Head can edit completed investigations. Please contact Scan Head to revert the status."
            )
    
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
        existing_result.updated_by = current_user.id  # Track who updated
        existing_result.updated_at = datetime.utcnow()
        
        # Mark investigation as completed if results are entered
        if results_text or attachment_path:
            investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session
            db.add(investigation)
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
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session
            db.add(investigation)
    
    db.commit()
    # Refresh investigation to ensure completed_by is updated
    db.refresh(investigation)
    if existing_result:
        db.refresh(existing_result)
        # Get user names for response
        entered_user = db.query(User).filter(User.id == existing_result.entered_by).first()
        updated_user = db.query(User).filter(User.id == existing_result.updated_by).first() if existing_result.updated_by else None
        result_dict = {
            "id": existing_result.id,
            "investigation_id": existing_result.investigation_id,
            "results_text": existing_result.results_text,
            "attachment_path": existing_result.attachment_path,
            "entered_by": existing_result.entered_by,
            "updated_by": existing_result.updated_by,
            "created_at": existing_result.created_at,
            "updated_at": existing_result.updated_at,
            "entered_by_name": entered_user.full_name if entered_user else None,
            "updated_by_name": updated_user.full_name if updated_user else None,
        }
        return ScanResultResponse(**result_dict)
    else:
        db.refresh(scan_result)
        # Get user names for response
        entered_user = db.query(User).filter(User.id == scan_result.entered_by).first()
        result_dict = {
            "id": scan_result.id,
            "investigation_id": scan_result.investigation_id,
            "results_text": scan_result.results_text,
            "attachment_path": scan_result.attachment_path,
            "entered_by": scan_result.entered_by,
            "updated_by": scan_result.updated_by,
            "created_at": scan_result.created_at,
            "updated_at": scan_result.updated_at,
            "entered_by_name": entered_user.full_name if entered_user else None,
            "updated_by_name": None,
        }
        return ScanResultResponse(**result_dict)


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
    updated_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    # User names for display
    entered_by_name: Optional[str] = None
    updated_by_name: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("/xray-result", response_model=XrayResultResponse, status_code=status.HTTP_201_CREATED)
async def create_xray_result(
    investigation_id: int = Form(...),
    results_text: Optional[str] = Form(None),
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Xray", "Xray Head", "Admin"]))
):
    """Create or update x-ray result with optional file attachment"""
    # Verify investigation exists and is an xray investigation
    investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.investigation_type != "xray":
        raise HTTPException(status_code=400, detail="This endpoint is only for x-ray investigations")
    
    # If investigation is completed, only Admin and Xray Head can edit
    if investigation.status == InvestigationStatus.COMPLETED.value:
        if current_user.role not in ["Admin", "Xray Head"]:
            raise HTTPException(
                status_code=403,
                detail="Only Admin and Xray Head can edit completed investigations. Please contact Xray Head to revert the status."
            )
    
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
        existing_result.updated_by = current_user.id  # Track who updated
        existing_result.updated_at = datetime.utcnow()
        
        # Mark investigation as completed if results are entered
        if results_text or attachment_path:
            investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session
            db.add(investigation)
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
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session
            db.add(investigation)
    
    db.commit()
    # Refresh investigation to ensure completed_by is updated
    db.refresh(investigation)
    if existing_result:
        db.refresh(existing_result)
        # Get user names for response
        entered_user = db.query(User).filter(User.id == existing_result.entered_by).first()
        updated_user = db.query(User).filter(User.id == existing_result.updated_by).first() if existing_result.updated_by else None
        result_dict = {
            "id": existing_result.id,
            "investigation_id": existing_result.investigation_id,
            "results_text": existing_result.results_text,
            "attachment_path": existing_result.attachment_path,
            "entered_by": existing_result.entered_by,
            "updated_by": existing_result.updated_by,
            "created_at": existing_result.created_at,
            "updated_at": existing_result.updated_at,
            "entered_by_name": entered_user.full_name if entered_user else None,
            "updated_by_name": updated_user.full_name if updated_user else None,
        }
        return XrayResultResponse(**result_dict)
    else:
        db.refresh(xray_result)
        # Get user names for response
        entered_user = db.query(User).filter(User.id == xray_result.entered_by).first()
        result_dict = {
            "id": xray_result.id,
            "investigation_id": xray_result.investigation_id,
            "results_text": xray_result.results_text,
            "attachment_path": xray_result.attachment_path,
            "entered_by": xray_result.entered_by,
            "updated_by": xray_result.updated_by,
            "created_at": xray_result.created_at,
            "updated_at": xray_result.updated_at,
            "entered_by_name": entered_user.full_name if entered_user else None,
            "updated_by_name": None,
        }
        return XrayResultResponse(**result_dict)


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
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Patient and encounter details
    patient_name: Optional[str] = None
    patient_surname: Optional[str] = None
    patient_other_names: Optional[str] = None
    patient_card_number: Optional[str] = None
    patient_gender: Optional[str] = None
    patient_date_of_birth: Optional[str] = None
    patient_emergency_contact_name: Optional[str] = None
    patient_emergency_contact_relationship: Optional[str] = None
    patient_emergency_contact_number: Optional[str] = None
    encounter_created_at: Optional[datetime] = None
    encounter_service_type: Optional[str] = None
    encounter_ccc_number: Optional[str] = None
    finalized_by_name: Optional[str] = None  # Name of doctor/PA who finalized
    finalized_by_role: Optional[str] = None  # Role of doctor/PA who finalized
    finalized_at: Optional[datetime] = None  # When consultation was finalized
    cancelled: Optional[int] = None  # 0 = not cancelled, 1 = cancelled
    cancelled_by: Optional[int] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None


@router.get("/admissions", response_model=List[AdmissionRecommendationResponse])
def get_admission_recommendations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
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
                
                # Get finalized_by user info if encounter is finalized
                finalized_by_name = None
                finalized_by_role = None
                if encounter.finalized_by:
                    finalized_user = db.query(User).filter(User.id == encounter.finalized_by).first()
                    if finalized_user:
                        finalized_by_name = finalized_user.full_name
                        finalized_by_role = finalized_user.role
                
                # Debug log for emergency contact
                print(f"Patient {patient.card_number} emergency contact: name={patient.emergency_contact_name}, relationship={patient.emergency_contact_relationship}, number={patient.emergency_contact_number}")
                
                result.append({
                    "id": admission.id,
                    "encounter_id": admission.encounter_id,
                    "ward": admission.ward,
                    "recommended_by": admission.recommended_by,
                    "confirmed_by": admission.confirmed_by,
                    "confirmed_at": admission.confirmed_at,
                    "created_at": admission.created_at,
                    "updated_at": admission.updated_at,
                    "patient_name": patient.name,
                    "patient_surname": patient.surname,
                    "patient_other_names": patient.other_names,
                    "patient_card_number": patient.card_number,
                    "patient_gender": patient.gender,
                    "patient_date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                    "patient_emergency_contact_name": patient.emergency_contact_name if patient.emergency_contact_name else None,
                    "patient_emergency_contact_relationship": patient.emergency_contact_relationship if patient.emergency_contact_relationship else None,
                    "patient_emergency_contact_number": patient.emergency_contact_number if patient.emergency_contact_number else None,
                    "encounter_created_at": encounter.created_at,
                    "encounter_service_type": encounter.department,
                    "encounter_ccc_number": encounter.ccc_number if encounter.ccc_number else None,
                    "finalized_by_name": finalized_by_name,
                    "finalized_by_role": finalized_by_role,
                    "finalized_at": encounter.finalized_at,
                    "cancelled": admission.cancelled,
                    "cancelled_by": admission.cancelled_by,
                    "cancelled_at": admission.cancelled_at,
                    "cancellation_reason": admission.cancellation_reason if admission.cancellation_reason else None,
                })
            except Exception as e:
                print(f"Error processing admission {admission.id}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"Returning {len(result)} admission recommendations")  # Debug log
        
        # Debug: Log first admission to check emergency contact fields
        if result:
            first_admission = result[0]
            print(f"First admission emergency contact: name={first_admission.get('patient_emergency_contact_name')}, relationship={first_admission.get('patient_emergency_contact_relationship')}, number={first_admission.get('patient_emergency_contact_number')}")
        
        return result
    except Exception as e:
        print(f"Error in get_admission_recommendations: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching admission recommendations: {str(e)}")


class ConfirmAdmissionRequest(BaseModel):
    ccc_number: Optional[str] = None
    emergency_contact_name: str
    emergency_contact_relationship: str
    emergency_contact_number: str
    bed_id: int
    doctor_id: int


@router.put("/admissions/{admission_id}/confirm")
def confirm_admission(
    admission_id: int,
    form_data: ConfirmAdmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Confirm an admission recommendation with complete form data"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    from app.models.bed import Bed
    from app.models.patient import Patient
    
    admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission recommendation not found")
    
    if admission.confirmed_by is not None:
        raise HTTPException(status_code=400, detail="Admission has already been confirmed")
    
    # Check if ward admission already exists
    existing_ward_admission = db.query(WardAdmission).filter(
        WardAdmission.encounter_id == admission.encounter_id,
        WardAdmission.discharged_at.is_(None)
    ).first()
    
    if existing_ward_admission:
        raise HTTPException(status_code=400, detail="Patient is already admitted to a ward")
    
    # Verify bed exists and is available
    bed = db.query(Bed).filter(Bed.id == form_data.bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    
    if bed.ward != admission.ward:
        raise HTTPException(status_code=400, detail=f"Bed does not belong to ward {admission.ward}")
    
    if bed.is_occupied:
        raise HTTPException(status_code=400, detail="Bed is already occupied")
    
    # Verify doctor exists
    doctor = db.query(User).filter(User.id == form_data.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Get encounter to check for existing CCC
    encounter = db.query(Encounter).filter(Encounter.id == admission.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Use CCC from form or from encounter
    ccc_to_use = form_data.ccc_number or encounter.ccc_number
    
    # Update encounter CCC if provided in form
    if form_data.ccc_number and not encounter.ccc_number:
        encounter.ccc_number = form_data.ccc_number
    
    # Update patient emergency contact if not already set
    patient = encounter.patient
    if patient:
        if not patient.emergency_contact_name:
            patient.emergency_contact_name = form_data.emergency_contact_name
            patient.emergency_contact_relationship = form_data.emergency_contact_relationship
            patient.emergency_contact_number = form_data.emergency_contact_number
    
    # Mark admission as confirmed
    admission.confirmed_by = current_user.id
    admission.confirmed_at = datetime.utcnow()
    admission.updated_at = datetime.utcnow()
    
    # Mark bed as occupied
    bed.is_occupied = True
    bed.updated_at = datetime.utcnow()
    
    # Create ward admission record
    ward_admission = WardAdmission(
        admission_recommendation_id=admission.id,
        encounter_id=admission.encounter_id,
        ward=admission.ward,
        bed_id=form_data.bed_id,
        ccc_number=ccc_to_use,
        emergency_contact_name=form_data.emergency_contact_name,
        emergency_contact_relationship=form_data.emergency_contact_relationship,
        emergency_contact_number=form_data.emergency_contact_number,
        doctor_id=form_data.doctor_id,
        admitted_by=current_user.id,
        admitted_at=datetime.utcnow()
    )
    db.add(ward_admission)
    
    db.commit()
    db.refresh(admission)
    db.refresh(ward_admission)
    db.refresh(bed)
    
    return {
        "id": admission.id,
        "encounter_id": admission.encounter_id,
        "ward": admission.ward,
        "bed_id": ward_admission.bed_id,
        "doctor_id": ward_admission.doctor_id,
        "confirmed_by": admission.confirmed_by,
        "confirmed_at": admission.confirmed_at,
        "ward_admission_id": ward_admission.id,
        "message": "Admission confirmed successfully"
    }


@router.put("/admissions/{admission_id}/revert-confirmation")
def revert_admission_confirmation(
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Revert admission confirmation - removes from ward and returns to recommendation state"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    
    admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission recommendation not found")
    
    if admission.confirmed_by is None:
        raise HTTPException(status_code=400, detail="Admission is not confirmed")
    
    # Check if patient is still in ward (not discharged)
    ward_admission = db.query(WardAdmission).filter(
        WardAdmission.admission_recommendation_id == admission.id,
        WardAdmission.discharged_at.is_(None)
    ).first()
    
    if ward_admission:
        # Free up the bed
        if ward_admission.bed_id:
            from app.models.bed import Bed
            bed = db.query(Bed).filter(Bed.id == ward_admission.bed_id).first()
            if bed:
                bed.is_occupied = False
                bed.updated_at = datetime.utcnow()
        
        # Delete the ward admission record
        db.delete(ward_admission)
    
    # Revert confirmation status
    admission.confirmed_by = None
    admission.confirmed_at = None
    admission.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(admission)
    
    return {
        "id": admission.id,
        "encounter_id": admission.encounter_id,
        "ward": admission.ward,
        "message": "Admission confirmation reverted successfully"
    }


# Ward admissions endpoints
class WardAdmissionResponse(BaseModel):
    """Ward admission response model"""
    id: int
    encounter_id: int
    ward: str
    admitted_by: int
    admitted_at: datetime
    discharged_at: Optional[datetime] = None
    discharged_by: Optional[int] = None
    
    # Patient and encounter details
    patient_name: Optional[str] = None
    patient_surname: Optional[str] = None
    patient_other_names: Optional[str] = None
    patient_card_number: Optional[str] = None
    patient_gender: Optional[str] = None
    patient_date_of_birth: Optional[str] = None
    encounter_created_at: Optional[datetime] = None
    encounter_service_type: Optional[str] = None
    admitted_by_name: Optional[str] = None
    admitted_by_role: Optional[str] = None
    
    # Emergency contact details (from ward_admission or patient)
    emergency_contact_name: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    
    # Admission documentation
    admission_notes: Optional[str] = None
    # Note: clinical_review, nurses_notes, nurses_mid_documentation, and vitals are now in separate tables
    # They will be loaded separately via their respective endpoints


@router.get("/ward-admissions", response_model=List[WardAdmissionResponse])
def get_ward_admissions(
    ward: Optional[str] = None,
    include_discharged: Optional[bool] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get ward admissions - by default only shows active (non-discharged) patients"""
    from app.models.ward_admission import WardAdmission
    from app.models.patient import Patient
    
    try:
        query = db.query(WardAdmission)
        
        # Filter by discharged status
        if not include_discharged:
            query = query.filter(WardAdmission.discharged_at.is_(None))  # Only active admissions
        
        # Filter by ward if provided
        if ward:
            query = query.filter(WardAdmission.ward == ward)
        
        ward_admissions = query.options(
            joinedload(WardAdmission.encounter).joinedload(Encounter.patient),
            joinedload(WardAdmission.bed)
        ).order_by(WardAdmission.admitted_at.desc()).all()
        
        result = []
        for ward_admission in ward_admissions:
            try:
                encounter = ward_admission.encounter
                if not encounter:
                    continue
                
                patient = encounter.patient
                if not patient:
                    continue
                
                # Get admitted_by user info
                admitted_by_name = None
                admitted_by_role = None
                if ward_admission.admitted_by:
                    admitted_user = db.query(User).filter(User.id == ward_admission.admitted_by).first()
                    if admitted_user:
                        admitted_by_name = admitted_user.full_name
                        admitted_by_role = admitted_user.role
                
                # Get discharged_by user info if discharged
                discharged_by_name = None
                discharged_by_role = None
                if ward_admission.discharged_by:
                    discharged_user = db.query(User).filter(User.id == ward_admission.discharged_by).first()
                    if discharged_user:
                        discharged_by_name = discharged_user.full_name
                        discharged_by_role = discharged_user.role
                
                # Get emergency contact directly from patient table
                # Emergency contact is stored in patient registration, not in ward_admission
                emergency_contact_name = patient.emergency_contact_name
                emergency_contact_relationship = patient.emergency_contact_relationship
                emergency_contact_number = patient.emergency_contact_number
                
                # Get bed information
                bed_number = None
                if ward_admission.bed_id and ward_admission.bed:
                    bed_number = ward_admission.bed.bed_number
                
                # Debug log for emergency contact
                print(f"Ward admission {ward_admission.id} - Patient {patient.card_number}: emergency_contact_name={emergency_contact_name}, relationship={emergency_contact_relationship}, number={emergency_contact_number}")
                
                result.append({
                    "id": ward_admission.id,
                    "encounter_id": ward_admission.encounter_id,
                    "ward": ward_admission.ward,
                    "bed_id": ward_admission.bed_id,
                    "bed_number": bed_number,
                    "admitted_by": ward_admission.admitted_by,
                    "admitted_at": ward_admission.admitted_at,
                    "discharged_at": ward_admission.discharged_at,
                    "discharged_by": ward_admission.discharged_by,
                    "patient_name": patient.name,
                    "patient_surname": patient.surname,
                    "patient_other_names": patient.other_names,
                    "patient_card_number": patient.card_number,
                    "patient_gender": patient.gender,
                    "patient_date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                    "encounter_created_at": encounter.created_at,
                    "encounter_service_type": encounter.department,
                    "admitted_by_name": admitted_by_name,
                    "admitted_by_role": admitted_by_role,
                    "discharged_by_name": discharged_by_name,
                    "discharged_by_role": discharged_by_role,
                    "emergency_contact_name": emergency_contact_name,
                    "emergency_contact_relationship": emergency_contact_relationship,
                    "emergency_contact_number": emergency_contact_number,
                    "admission_notes": ward_admission.admission_notes,
                    # Note: clinical_review, nurses_notes, nurses_mid_documentation, and vitals are now in separate tables
                })
            except Exception as e:
                print(f"Error processing ward admission {ward_admission.id}: {str(e)}")
                continue
        
        # Debug: Log first result to check emergency contact fields
        if result:
            first_result = result[0]
            print(f"First ward admission result - emergency contact: name={first_result.get('emergency_contact_name')}, relationship={first_result.get('emergency_contact_relationship')}, number={first_result.get('emergency_contact_number')}")
            print(f"First result keys: {list(first_result.keys())}")
        
        return result
    except Exception as e:
        print(f"Error in get_ward_admissions: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching ward admissions: {str(e)}")


@router.put("/ward-admissions/{ward_admission_id}/discharge")
def discharge_patient(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Discharge a patient from the ward"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    from app.models.bed import Bed
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Patient has already been discharged")
    
    # Free up the bed
    if ward_admission.bed_id:
        bed = db.query(Bed).filter(Bed.id == ward_admission.bed_id).first()
        if bed:
            bed.is_occupied = False
            bed.updated_at = datetime.utcnow()
    
    # Mark as discharged
    ward_admission.discharged_at = datetime.utcnow()
    ward_admission.discharged_by = current_user.id
    ward_admission.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ward_admission)
    
    return {
        "id": ward_admission.id,
        "encounter_id": ward_admission.encounter_id,
        "ward": ward_admission.ward,
        "discharged_at": ward_admission.discharged_at,
        "discharged_by": ward_admission.discharged_by,
        "message": "Patient discharged successfully"
    }


class UpdateAdmissionNotesRequest(BaseModel):
    notes: Optional[str] = None


@router.put("/ward-admissions/{ward_admission_id}/admission-notes")
def update_admission_notes(
    ward_admission_id: int,
    request: UpdateAdmissionNotesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Update admission notes"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Cannot update notes for discharged patient")
    
    ward_admission.admission_notes = request.notes
    ward_admission.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ward_admission)
    
    return {
        "id": ward_admission.id,
        "admission_notes": ward_admission.admission_notes,
        "message": "Admission notes updated successfully"
    }


# Nurse Notes endpoints
class CreateNurseNoteRequest(BaseModel):
    notes: str


@router.post("/ward-admissions/{ward_admission_id}/nurse-notes")
def create_nurse_note(
    ward_admission_id: int,
    request: CreateNurseNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Create a new nurse note"""
    from app.models.ward_admission import WardAdmission
    from app.models.nurse_note import NurseNote
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Cannot add notes for discharged patient")
    
    nurse_note = NurseNote(
        ward_admission_id=ward_admission_id,
        notes=request.notes,
        created_by=current_user.id
    )
    
    db.add(nurse_note)
    db.commit()
    db.refresh(nurse_note)
    
    return {
        "id": nurse_note.id,
        "ward_admission_id": nurse_note.ward_admission_id,
        "notes": nurse_note.notes,
        "created_by": nurse_note.created_by,
        "created_at": nurse_note.created_at,
        "message": "Nurse note created successfully"
    }


@router.get("/ward-admissions/{ward_admission_id}/nurse-notes")
def get_nurse_notes(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all nurse notes for a ward admission"""
    from app.models.ward_admission import WardAdmission
    from app.models.nurse_note import NurseNote
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    nurse_notes = db.query(NurseNote).filter(
        NurseNote.ward_admission_id == ward_admission_id
    ).order_by(NurseNote.created_at.desc()).all()
    
    result = []
    for note in nurse_notes:
        creator = db.query(User).filter(User.id == note.created_by).first()
        strikethrough_by_user = None
        if note.strikethrough_by:
            strikethrough_by_user = db.query(User).filter(User.id == note.strikethrough_by).first()
        
        result.append({
            "id": note.id,
            "notes": note.notes,
            "created_by": note.created_by,
            "created_by_name": creator.full_name if creator else None,
            "created_at": note.created_at,
            "strikethrough": note.strikethrough,
            "strikethrough_by": note.strikethrough_by,
            "strikethrough_by_name": strikethrough_by_user.full_name if strikethrough_by_user else None,
            "strikethrough_at": note.strikethrough_at,
        })
    
    return result


# Nurse Mid Documentation endpoints
class CreateNurseMidDocumentationRequest(BaseModel):
    patient_problems_diagnosis: Optional[str] = None
    aim_of_care: Optional[str] = None
    nursing_assessment: Optional[str] = None
    nursing_orders: Optional[str] = None
    nursing_intervention: Optional[str] = None
    evaluation: Optional[str] = None
    documentation: Optional[str] = None  # Keep for backward compatibility


@router.post("/ward-admissions/{ward_admission_id}/nurse-mid-documentations")
def create_nurse_mid_documentation(
    ward_admission_id: int,
    request: CreateNurseMidDocumentationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Create a new nurse mid documentation"""
    from app.models.ward_admission import WardAdmission
    from app.models.nurse_mid_documentation import NurseMidDocumentation
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Cannot add documentation for discharged patient")
    
    nurse_mid_doc = NurseMidDocumentation(
        ward_admission_id=ward_admission_id,
        patient_problems_diagnosis=request.patient_problems_diagnosis,
        aim_of_care=request.aim_of_care,
        nursing_assessment=request.nursing_assessment,
        nursing_orders=request.nursing_orders,
        nursing_intervention=request.nursing_intervention,
        evaluation=request.evaluation,
        documentation=request.documentation,  # For backward compatibility
        created_by=current_user.id
    )
    
    db.add(nurse_mid_doc)
    db.commit()
    db.refresh(nurse_mid_doc)
    
    return {
        "id": nurse_mid_doc.id,
        "ward_admission_id": nurse_mid_doc.ward_admission_id,
        "patient_problems_diagnosis": nurse_mid_doc.patient_problems_diagnosis,
        "aim_of_care": nurse_mid_doc.aim_of_care,
        "nursing_assessment": nurse_mid_doc.nursing_assessment,
        "nursing_orders": nurse_mid_doc.nursing_orders,
        "nursing_intervention": nurse_mid_doc.nursing_intervention,
        "evaluation": nurse_mid_doc.evaluation,
        "documentation": nurse_mid_doc.documentation,  # For backward compatibility
        "created_by": nurse_mid_doc.created_by,
        "created_at": nurse_mid_doc.created_at,
        "message": "Nurse mid documentation created successfully"
    }


@router.get("/ward-admissions/{ward_admission_id}/nurse-mid-documentations")
def get_nurse_mid_documentations(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all nurse mid documentations for a ward admission"""
    from app.models.ward_admission import WardAdmission
    from app.models.nurse_mid_documentation import NurseMidDocumentation
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    nurse_mid_docs = db.query(NurseMidDocumentation).filter(
        NurseMidDocumentation.ward_admission_id == ward_admission_id
    ).order_by(NurseMidDocumentation.created_at.desc()).all()
    
    result = []
    for doc in nurse_mid_docs:
        creator = db.query(User).filter(User.id == doc.created_by).first()
        result.append({
            "id": doc.id,
            "patient_problems_diagnosis": doc.patient_problems_diagnosis,
            "aim_of_care": doc.aim_of_care,
            "nursing_assessment": doc.nursing_assessment,
            "nursing_orders": doc.nursing_orders,
            "nursing_intervention": doc.nursing_intervention,
            "evaluation": doc.evaluation,
            "documentation": doc.documentation,  # For backward compatibility
            "created_by": doc.created_by,
            "created_by_name": creator.full_name if creator else None,
            "created_at": doc.created_at,
        })
    
    return result


@router.put("/ward-admissions/{ward_admission_id}/nurse-mid-documentations/{documentation_id}")
def update_nurse_mid_documentation(
    ward_admission_id: int,
    documentation_id: int,
    request: CreateNurseMidDocumentationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Update a nurse mid documentation"""
    from app.models.ward_admission import WardAdmission
    from app.models.nurse_mid_documentation import NurseMidDocumentation
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    nurse_mid_doc = db.query(NurseMidDocumentation).filter(
        NurseMidDocumentation.id == documentation_id,
        NurseMidDocumentation.ward_admission_id == ward_admission_id
    ).first()
    
    if not nurse_mid_doc:
        raise HTTPException(status_code=404, detail="Nurse mid documentation not found")
    
    # Check permissions: user can edit their own documentation, admin can edit any
    if current_user.role != "Admin" and nurse_mid_doc.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only edit your own documentation. Admin can edit any documentation."
        )
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Cannot edit documentation for discharged patient")
    
    # Update fields
    nurse_mid_doc.patient_problems_diagnosis = request.patient_problems_diagnosis
    nurse_mid_doc.aim_of_care = request.aim_of_care
    nurse_mid_doc.nursing_assessment = request.nursing_assessment
    nurse_mid_doc.nursing_orders = request.nursing_orders
    nurse_mid_doc.nursing_intervention = request.nursing_intervention
    nurse_mid_doc.evaluation = request.evaluation
    nurse_mid_doc.documentation = request.documentation  # For backward compatibility
    
    db.commit()
    db.refresh(nurse_mid_doc)
    
    return {
        "id": nurse_mid_doc.id,
        "ward_admission_id": nurse_mid_doc.ward_admission_id,
        "patient_problems_diagnosis": nurse_mid_doc.patient_problems_diagnosis,
        "aim_of_care": nurse_mid_doc.aim_of_care,
        "nursing_assessment": nurse_mid_doc.nursing_assessment,
        "nursing_orders": nurse_mid_doc.nursing_orders,
        "nursing_intervention": nurse_mid_doc.nursing_intervention,
        "evaluation": nurse_mid_doc.evaluation,
        "documentation": nurse_mid_doc.documentation,  # For backward compatibility
        "created_by": nurse_mid_doc.created_by,
        "created_at": nurse_mid_doc.created_at,
        "message": "Nurse mid documentation updated successfully"
    }


# Inpatient Vitals endpoints
class CreateInpatientVitalRequest(BaseModel):
    temperature: Optional[float] = None
    blood_pressure_systolic: Optional[int] = None
    blood_pressure_diastolic: Optional[int] = None
    pulse: Optional[int] = None
    respiratory_rate: Optional[int] = None
    oxygen_saturation: Optional[float] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    notes: Optional[str] = None


@router.post("/ward-admissions/{ward_admission_id}/vitals")
def create_inpatient_vital(
    ward_admission_id: int,
    request: CreateInpatientVitalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Create a new vital record for an inpatient"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_vital import InpatientVital
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Cannot add vitals for discharged patient")
    
    # Calculate BMI if weight and height are provided
    bmi = None
    if request.weight and request.height and request.height > 0:
        bmi = request.weight / ((request.height / 100) ** 2)
    
    vital = InpatientVital(
        ward_admission_id=ward_admission_id,
        temperature=request.temperature,
        blood_pressure_systolic=request.blood_pressure_systolic,
        blood_pressure_diastolic=request.blood_pressure_diastolic,
        pulse=request.pulse,
        respiratory_rate=request.respiratory_rate,
        oxygen_saturation=request.oxygen_saturation,
        weight=request.weight,
        height=request.height,
        bmi=bmi,
        notes=request.notes,
        recorded_by=current_user.id
    )
    
    db.add(vital)
    db.commit()
    db.refresh(vital)
    
    return {
        "id": vital.id,
        "ward_admission_id": vital.ward_admission_id,
        "temperature": vital.temperature,
        "blood_pressure_systolic": vital.blood_pressure_systolic,
        "blood_pressure_diastolic": vital.blood_pressure_diastolic,
        "pulse": vital.pulse,
        "respiratory_rate": vital.respiratory_rate,
        "oxygen_saturation": vital.oxygen_saturation,
        "weight": vital.weight,
        "height": vital.height,
        "bmi": vital.bmi,
        "notes": vital.notes,
        "recorded_by": vital.recorded_by,
        "recorded_at": vital.recorded_at,
        "message": "Vital record created successfully"
    }


@router.get("/ward-admissions/{ward_admission_id}/vitals")
def get_inpatient_vitals(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all vital records for a ward admission"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_vital import InpatientVital
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    vitals = db.query(InpatientVital).filter(
        InpatientVital.ward_admission_id == ward_admission_id
    ).order_by(InpatientVital.recorded_at.desc()).all()
    
    result = []
    for vital in vitals:
        recorder = db.query(User).filter(User.id == vital.recorded_by).first()
        result.append({
            "id": vital.id,
            "temperature": vital.temperature,
            "blood_pressure_systolic": vital.blood_pressure_systolic,
            "blood_pressure_diastolic": vital.blood_pressure_diastolic,
            "pulse": vital.pulse,
            "respiratory_rate": vital.respiratory_rate,
            "oxygen_saturation": vital.oxygen_saturation,
            "weight": vital.weight,
            "height": vital.height,
            "bmi": vital.bmi,
            "notes": vital.notes,
            "recorded_by": vital.recorded_by,
            "recorded_by_name": recorder.full_name if recorder else None,
            "recorded_at": vital.recorded_at,
        })
    
    return result


@router.put("/ward-admissions/{ward_admission_id}/nurse-notes/{note_id}/strikethrough")
def toggle_nurse_note_strikethrough(
    ward_admission_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Toggle strikethrough status of a nurse note"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    from app.models.nurse_note import NurseNote
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    nurse_note = db.query(NurseNote).filter(
        NurseNote.id == note_id,
        NurseNote.ward_admission_id == ward_admission_id
    ).first()
    
    if not nurse_note:
        raise HTTPException(status_code=404, detail="Nurse note not found")
    
    # Check permissions: user can strikethrough their own notes, admin can strikethrough any
    if current_user.role != "Admin" and nurse_note.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only strikethrough your own notes. Admin can strikethrough any note."
        )
    
    # Toggle strikethrough status
    if nurse_note.strikethrough == 0:
        nurse_note.strikethrough = 1
        nurse_note.strikethrough_by = current_user.id
        nurse_note.strikethrough_at = datetime.utcnow()
    else:
        nurse_note.strikethrough = 0
        nurse_note.strikethrough_by = None
        nurse_note.strikethrough_at = None
    
    nurse_note.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(nurse_note)
    
    return {
        "id": nurse_note.id,
        "strikethrough": nurse_note.strikethrough,
        "message": "Nurse note strikethrough status updated successfully"
    }


# Inpatient Clinical Review endpoints
class CreateInpatientClinicalReviewRequest(BaseModel):
    review_notes: Optional[str] = None


@router.post("/ward-admissions/{ward_admission_id}/clinical-reviews")
def create_inpatient_clinical_review(
    ward_admission_id: int,
    request: CreateInpatientClinicalReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin"]))
):
    """Create a new clinical review for an inpatient"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Cannot add clinical review for discharged patient")
    
    clinical_review = InpatientClinicalReview(
        ward_admission_id=ward_admission_id,
        review_notes=request.review_notes,
        reviewed_by=current_user.id
    )
    
    db.add(clinical_review)
    db.commit()
    db.refresh(clinical_review)
    
    reviewer = db.query(User).filter(User.id == clinical_review.reviewed_by).first()
    
    return {
        "id": clinical_review.id,
        "ward_admission_id": clinical_review.ward_admission_id,
        "review_notes": clinical_review.review_notes,
        "reviewed_by": clinical_review.reviewed_by,
        "reviewed_by_name": reviewer.full_name if reviewer else None,
        "reviewed_at": clinical_review.reviewed_at,
        "message": "Clinical review created successfully"
    }


@router.get("/ward-admissions/{ward_admission_id}/clinical-reviews")
def get_inpatient_clinical_reviews(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all clinical reviews for a ward admission"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_reviews = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).order_by(InpatientClinicalReview.reviewed_at.desc()).all()
    
    result = []
    for review in clinical_reviews:
        reviewer = db.query(User).filter(User.id == review.reviewed_by).first()
        result.append({
            "id": review.id,
            "review_notes": review.review_notes,
            "reviewed_by": review.reviewed_by,
            "reviewed_by_name": reviewer.full_name if reviewer else None,
            "reviewed_at": review.reviewed_at,
        })
    
    return result


class DirectAdmissionRequest(BaseModel):
    """Request for direct admission (without recommendation)"""
    patient_id: Optional[int] = None
    patient_card_number: Optional[str] = None
    ward: str
    ccc_number: Optional[str] = None
    emergency_contact_name: str
    emergency_contact_relationship: str
    emergency_contact_number: str
    bed_id: int
    doctor_id: int
    admission_notes: Optional[str] = None


@router.post("/admissions/direct")
def create_direct_admission(
    form_data: DirectAdmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Create a direct admission without a recommendation"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    from app.models.bed import Bed
    from app.models.patient import Patient
    from app.models.encounter import Encounter, EncounterStatus, Department
    
    # Get patient
    patient = None
    if form_data.patient_id:
        patient = db.query(Patient).filter(Patient.id == form_data.patient_id).first()
    elif form_data.patient_card_number:
        patient = db.query(Patient).filter(Patient.card_number == form_data.patient_card_number).first()
    else:
        raise HTTPException(status_code=400, detail="Either patient_id or patient_card_number must be provided")
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check if patient is already admitted
    existing_ward_admission = db.query(WardAdmission).join(Encounter).filter(
        Encounter.patient_id == patient.id,
        WardAdmission.discharged_at.is_(None)
    ).first()
    
    if existing_ward_admission:
        raise HTTPException(status_code=400, detail="Patient is already admitted to a ward")
    
    # Verify bed exists and is available
    bed = db.query(Bed).filter(Bed.id == form_data.bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    
    if bed.ward != form_data.ward:
        raise HTTPException(status_code=400, detail=f"Bed does not belong to ward {form_data.ward}")
    
    if bed.is_occupied:
        raise HTTPException(status_code=400, detail="Bed is already occupied")
    
    # Verify doctor exists
    doctor = db.query(User).filter(User.id == form_data.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Create or get existing encounter for this admission
    # Check for existing non-finalized encounter first
    encounter = db.query(Encounter).filter(
        Encounter.patient_id == patient.id,
        Encounter.status != EncounterStatus.FINALIZED.value
    ).order_by(Encounter.created_at.desc()).first()
    
    if not encounter:
        # Create new encounter for admission
        # Use IN_CONSULTATION status for inpatient encounters
        encounter = Encounter(
            patient_id=patient.id,
            department=form_data.ward,  # Use ward as department for inpatient
            status=EncounterStatus.IN_CONSULTATION.value,
            ccc_number=form_data.ccc_number,
            created_by=current_user.id
        )
        db.add(encounter)
        db.flush()  # Get encounter ID
    
    # Update encounter CCC if provided
    if form_data.ccc_number and not encounter.ccc_number:
        encounter.ccc_number = form_data.ccc_number
    
    # Update patient emergency contact if not already set
    if not patient.emergency_contact_name:
        patient.emergency_contact_name = form_data.emergency_contact_name
        patient.emergency_contact_relationship = form_data.emergency_contact_relationship
        patient.emergency_contact_number = form_data.emergency_contact_number
    
    # Create admission recommendation
    admission_recommendation = AdmissionRecommendation(
        encounter_id=encounter.id,
        ward=form_data.ward,
        recommended_by=current_user.id,
        confirmed_by=current_user.id,  # Auto-confirm for direct admission
        confirmed_at=datetime.utcnow()
    )
    db.add(admission_recommendation)
    db.flush()  # Get admission_recommendation ID
    
    # Mark bed as occupied
    bed.is_occupied = True
    bed.updated_at = datetime.utcnow()
    
    # Create ward admission record
    ward_admission = WardAdmission(
        admission_recommendation_id=admission_recommendation.id,
        encounter_id=encounter.id,
        ward=form_data.ward,
        bed_id=form_data.bed_id,
        ccc_number=form_data.ccc_number or encounter.ccc_number,
        emergency_contact_name=form_data.emergency_contact_name,
        emergency_contact_relationship=form_data.emergency_contact_relationship,
        emergency_contact_number=form_data.emergency_contact_number,
        doctor_id=form_data.doctor_id,
        admitted_by=current_user.id,
        admission_notes=form_data.admission_notes,
        admitted_at=datetime.utcnow()
    )
    db.add(ward_admission)
    
    db.commit()
    db.refresh(admission_recommendation)
    db.refresh(ward_admission)
    db.refresh(bed)
    
    return {
        "id": admission_recommendation.id,
        "encounter_id": encounter.id,
        "ward": form_data.ward,
        "bed_id": ward_admission.bed_id,
        "doctor_id": ward_admission.doctor_id,
        "ward_admission_id": ward_admission.id,
        "message": "Patient admitted successfully"
    }


def calculate_age(date_of_birth):
    """Calculate age from date of birth"""
    if not date_of_birth:
        return None
    from datetime import date
    today = date.today()
    return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))


@router.get("/ward-admissions/daily-state/{ward}")
def get_daily_ward_state(
    ward: str,
    date: Optional[str] = None,  # Date in YYYY-MM-DD format, defaults to today
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get daily ward state statistics for a specific ward"""
    from datetime import datetime, timedelta
    from app.models.ward_admission import WardAdmission
    from app.models.ward_transfer import WardTransfer
    from app.models.bed import Bed
    
    # Parse date or use today
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = datetime.now().date()
    
    # Start and end of target date
    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())
    
    # Previous day
    previous_day = target_date - timedelta(days=1)
    start_of_previous_day = datetime.combine(previous_day, datetime.min.time())
    end_of_previous_day = datetime.combine(previous_day, datetime.max.time())
    
    # Get all ward admissions for this ward (including discharged)
    all_admissions = db.query(WardAdmission).filter(
        WardAdmission.ward == ward
    ).options(
        joinedload(WardAdmission.encounter).joinedload(Encounter.patient)
    ).all()
    
    # Remained Previous Day: Patients who were admitted before previous day and not discharged by end of previous day
    remained_previous_day = db.query(WardAdmission).filter(
        WardAdmission.ward == ward,
        WardAdmission.admitted_at < start_of_previous_day,
        or_(
            WardAdmission.discharged_at.is_(None),
            WardAdmission.discharged_at > end_of_previous_day
        )
    ).count()
    
    # New Admissions on target date (not transfers)
    new_admissions = db.query(WardAdmission).filter(
        WardAdmission.ward == ward,
        WardAdmission.admitted_at >= start_of_day,
        WardAdmission.admitted_at <= end_of_day
    ).options(
        joinedload(WardAdmission.encounter).joinedload(Encounter.patient)
    ).all()
    
    # Transfers TO this ward on target date (only accepted transfers)
    transfers_to_ward = db.query(WardTransfer).filter(
        WardTransfer.to_ward == ward,
        WardTransfer.status == "accepted",  # Only count accepted transfers
        WardTransfer.transferred_at >= start_of_day,
        WardTransfer.transferred_at <= end_of_day
    ).options(
        joinedload(WardTransfer.ward_admission).joinedload(WardAdmission.encounter).joinedload(Encounter.patient)
    ).all()
    
    # Total Admissions = New Admissions + Transfers In
    total_admissions = len(new_admissions) + len(transfers_to_ward)
    
    # Discharges on target date
    discharges = db.query(WardAdmission).filter(
        WardAdmission.ward == ward,
        WardAdmission.discharged_at >= start_of_day,
        WardAdmission.discharged_at <= end_of_day,
        WardAdmission.death_recorded_at.is_(None)  # Exclude deaths from discharges
    ).options(
        joinedload(WardAdmission.encounter).joinedload(Encounter.patient)
    ).all()
    
    # Deaths on target date
    deaths = db.query(WardAdmission).filter(
        WardAdmission.ward == ward,
        WardAdmission.death_recorded_at >= start_of_day,
        WardAdmission.death_recorded_at <= end_of_day
    ).options(
        joinedload(WardAdmission.encounter).joinedload(Encounter.patient)
    ).all()
    
    # Transfers FROM this ward on target date (only accepted transfers)
    transfers_from_ward = db.query(WardTransfer).filter(
        WardTransfer.from_ward == ward,
        WardTransfer.status == "accepted",  # Only count accepted transfers
        WardTransfer.transferred_at >= start_of_day,
        WardTransfer.transferred_at <= end_of_day
    ).count()
    
    # Remained at Midnight: Patients admitted before end of day and not discharged/dead by end of day
    remained_at_midnight = db.query(WardAdmission).filter(
        WardAdmission.ward == ward,
        WardAdmission.admitted_at <= end_of_day,
        or_(
            WardAdmission.discharged_at.is_(None),
            WardAdmission.discharged_at > end_of_day
        ),
        or_(
            WardAdmission.death_recorded_at.is_(None),
            WardAdmission.death_recorded_at > end_of_day
        )
    ).count()
    
    # Empty Beds: Total beds in ward minus occupied beds
    total_beds = db.query(Bed).filter(
        Bed.ward == ward,
        Bed.is_active == True
    ).count()
    
    occupied_beds = db.query(WardAdmission).filter(
        WardAdmission.ward == ward,
        WardAdmission.discharged_at.is_(None),
        WardAdmission.death_recorded_at.is_(None)
    ).count()
    
    empty_beds = total_beds - occupied_beds
    
    # Format admission data
    admission_data = []
    for admission in new_admissions:
        patient = admission.encounter.patient if admission.encounter else None
        if patient:
            admission_data.append({
                "id": admission.id,
                "office_no": admission.id,  # Using admission ID as office number
                "name": f"{patient.name} {patient.surname}",
                "age": calculate_age(patient.date_of_birth) if patient.date_of_birth else None,
                "gender": patient.gender,
                "male": 1 if patient.gender and patient.gender.lower() == "male" else 0,
                "female": 1 if patient.gender and patient.gender.lower() == "female" else 0,
                "official": 1 if admission.ccc_number else 0,  # Official if has CCC
                "non_official": 0 if admission.ccc_number else 1,
            })
    
    # Format transfer data
    transfer_data = []
    for transfer in transfers_to_ward:
        patient = transfer.ward_admission.encounter.patient if transfer.ward_admission.encounter else None
        if patient:
            transfer_data.append({
                "id": transfer.id,
                "office_no": transfer.ward_admission.id,
                "name": f"{patient.name} {patient.surname}",
                "age": calculate_age(patient.date_of_birth) if patient.date_of_birth else None,
                "gender": patient.gender,
                "male": 1 if patient.gender and patient.gender.lower() == "male" else 0,
                "female": 1 if patient.gender and patient.gender.lower() == "female" else 0,
                "official": 1 if transfer.ward_admission.ccc_number else 0,
                "non_official": 0 if transfer.ward_admission.ccc_number else 1,
                "from_ward": transfer.from_ward,
            })
    
    # Format discharge data
    discharge_data = []
    for discharge in discharges:
        patient = discharge.encounter.patient if discharge.encounter else None
        if patient:
            discharge_data.append({
                "id": discharge.id,
                "office_no": discharge.id,
                "name": f"{patient.name} {patient.surname}",
                "age": calculate_age(patient.date_of_birth) if patient.date_of_birth else None,
                "gender": patient.gender,
                "male": 1 if patient.gender and patient.gender.lower() == "male" else 0,
                "female": 1 if patient.gender and patient.gender.lower() == "female" else 0,
                "official": 1 if discharge.ccc_number else 0,
                "non_official": 0 if discharge.ccc_number else 1,
            })
    
    # Format death data
    death_data = []
    for death in deaths:
        patient = death.encounter.patient if death.encounter else None
        if patient:
            death_data.append({
                "id": death.id,
                "office_no": death.id,
                "name": f"{patient.name} {patient.surname}",
                "age": calculate_age(patient.date_of_birth) if patient.date_of_birth else None,
                "gender": patient.gender,
                "male": 1 if patient.gender and patient.gender.lower() == "male" else 0,
                "female": 1 if patient.gender and patient.gender.lower() == "female" else 0,
                "official": 1 if death.ccc_number else 0,
                "non_official": 0 if death.ccc_number else 1,
            })
    
    return {
        "ward": ward,
        "date": target_date.isoformat(),
        "statistics": {
            "remained_previous_day": remained_previous_day,
            "new_admissions": len(new_admissions),
            "transfers_in": len(transfers_to_ward),
            "total_admissions": total_admissions,
            "transfers_out": transfers_from_ward,
            "total_discharges": len(discharges),
            "total_deaths": len(deaths),
            "remained_at_midnight": remained_at_midnight,
            "empty_beds": empty_beds,
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
        },
        "admissions": admission_data,
        "transfers_in": transfer_data,
        "discharges": discharge_data,
        "deaths": death_data,
    }


class TransferPatientRequest(BaseModel):
    """Request to transfer a patient between wards or beds"""
    ward_admission_id: int
    from_ward: str
    to_ward: str
    bed_id: int
    transfer_reason: Optional[str] = None


@router.post("/ward-admissions/transfer")
def transfer_patient(
    form_data: TransferPatientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Transfer a patient between wards or beds"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    from app.models.ward_transfer import WardTransfer
    from app.models.bed import Bed
    
    # Get the ward admission
    ward_admission = db.query(WardAdmission).filter(
        WardAdmission.id == form_data.ward_admission_id
    ).first()
    
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at:
        raise HTTPException(status_code=400, detail="Cannot transfer a discharged patient")
    
    if ward_admission.death_recorded_at:
        raise HTTPException(status_code=400, detail="Cannot transfer a deceased patient")
    
    # Verify bed exists and is available (only check if not a ward transfer, as bed will be checked on acceptance)
    bed = db.query(Bed).filter(Bed.id == form_data.bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    
    if bed.ward != form_data.to_ward:
        raise HTTPException(status_code=400, detail=f"Bed does not belong to ward {form_data.to_ward}")
    
    # Check if transferring to a different ward
    is_ward_transfer = form_data.from_ward != form_data.to_ward
    
    if not is_ward_transfer:
        # For same-ward bed transfers, check if bed is available
        if bed.is_occupied:
            raise HTTPException(status_code=400, detail="Bed is already occupied")
    
    # Check if there's already a pending transfer for this patient
    if is_ward_transfer:
        existing_pending_transfer = db.query(WardTransfer).filter(
            WardTransfer.ward_admission_id == form_data.ward_admission_id,
            WardTransfer.status == "pending"
        ).first()
        
        if existing_pending_transfer:
            raise HTTPException(
                status_code=400,
                detail=f"Patient already has a pending transfer request. Please wait for it to be accepted or rejected before creating another transfer."
            )
    
    if is_ward_transfer:
        # For ward transfers, create a pending transfer record
        # Don't update ward admission or beds yet - wait for acceptance
        transfer = WardTransfer(
            ward_admission_id=ward_admission.id,
            from_ward=form_data.from_ward,
            to_ward=form_data.to_ward,
            transfer_reason=form_data.transfer_reason,
            status="pending",
            transferred_by=current_user.id,
            transferred_at=datetime.utcnow()
        )
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        
        return {
            "id": transfer.id,
            "ward_admission_id": ward_admission.id,
            "from_ward": form_data.from_ward,
            "to_ward": form_data.to_ward,
            "bed_id": form_data.bed_id,
            "status": "pending",
            "message": "Transfer request created. Waiting for receiving ward to accept."
        }
    else:
        # For same-ward bed transfers, process immediately
        # Free up the old bed if it exists
        if ward_admission.bed_id:
            old_bed = db.query(Bed).filter(Bed.id == ward_admission.bed_id).first()
            if old_bed:
                old_bed.is_occupied = False
                old_bed.updated_at = datetime.utcnow()
        
        # Mark new bed as occupied
        bed.is_occupied = True
        bed.updated_at = datetime.utcnow()
        
        # Update ward admission
        ward_admission.bed_id = form_data.bed_id
        ward_admission.updated_at = datetime.utcnow()
        
        # Create transfer record (auto-accepted for same-ward transfers)
        transfer = WardTransfer(
            ward_admission_id=ward_admission.id,
            from_ward=form_data.from_ward,
            to_ward=form_data.to_ward,
            transfer_reason=form_data.transfer_reason,
            status="accepted",
            transferred_by=current_user.id,
            accepted_by=current_user.id,
            transferred_at=datetime.utcnow(),
            accepted_at=datetime.utcnow()
        )
        db.add(transfer)
        
        db.commit()
        db.refresh(ward_admission)
        db.refresh(transfer)
        db.refresh(bed)
        
        return {
            "id": transfer.id,
            "ward_admission_id": ward_admission.id,
            "from_ward": form_data.from_ward,
            "to_ward": form_data.to_ward,
            "bed_id": form_data.bed_id,
            "status": "accepted",
            "message": "Patient transferred successfully"
        }


@router.get("/ward-admissions/pending-transfers")
def get_pending_transfers(
    ward: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get pending transfer requests for a ward"""
    from app.models.ward_transfer import WardTransfer
    from app.models.ward_admission import WardAdmission
    
    query = db.query(WardTransfer).filter(
        WardTransfer.status == "pending"
    )
    
    if ward:
        query = query.filter(WardTransfer.to_ward == ward)
    
    transfers = query.options(
        joinedload(WardTransfer.ward_admission).joinedload(WardAdmission.encounter).joinedload(Encounter.patient),
        joinedload(WardTransfer.transferrer)
    ).order_by(WardTransfer.transferred_at.desc()).all()
    
    result = []
    for transfer in transfers:
        ward_admission = transfer.ward_admission
        encounter = ward_admission.encounter if ward_admission else None
        patient = encounter.patient if encounter else None
        
        if not patient:
            continue
        
        result.append({
            "id": transfer.id,
            "ward_admission_id": ward_admission.id,
            "from_ward": transfer.from_ward,
            "to_ward": transfer.to_ward,
            "transfer_reason": transfer.transfer_reason,
            "status": transfer.status,
            "transferred_by_name": transfer.transferrer.full_name if transfer.transferrer else None,
            "transferred_at": transfer.transferred_at,
            "patient_name": patient.name,
            "patient_surname": patient.surname,
            "patient_card_number": patient.card_number,
            "patient_gender": patient.gender,
            "current_ward": ward_admission.ward,
            "current_bed_id": ward_admission.bed_id,
        })
    
    return result


class AcceptTransferRequest(BaseModel):
    """Request to accept a transfer"""
    bed_id: int  # Bed to assign in the receiving ward


@router.post("/ward-admissions/transfers/{transfer_id}/accept")
def accept_transfer(
    transfer_id: int,
    form_data: AcceptTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Accept a pending transfer request"""
    from datetime import datetime
    from app.models.ward_transfer import WardTransfer
    from app.models.ward_admission import WardAdmission
    from app.models.bed import Bed
    
    # Get the transfer
    transfer = db.query(WardTransfer).filter(
        WardTransfer.id == transfer_id
    ).first()
    
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    if transfer.status != "pending":
        raise HTTPException(status_code=400, detail=f"Transfer is already {transfer.status}")
    
    # Verify the user has permission to accept transfers for the receiving ward
    # (This is handled by the role requirement, but you could add ward-specific checks)
    
    # Get the ward admission
    ward_admission = db.query(WardAdmission).filter(
        WardAdmission.id == transfer.ward_admission_id
    ).first()
    
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    # Verify bed exists and is available
    bed = db.query(Bed).filter(Bed.id == form_data.bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    
    if bed.ward != transfer.to_ward:
        raise HTTPException(status_code=400, detail=f"Bed does not belong to ward {transfer.to_ward}")
    
    if bed.is_occupied:
        raise HTTPException(status_code=400, detail="Bed is already occupied")
    
    # Free up the old bed if it exists
    if ward_admission.bed_id:
        old_bed = db.query(Bed).filter(Bed.id == ward_admission.bed_id).first()
        if old_bed:
            old_bed.is_occupied = False
            old_bed.updated_at = datetime.utcnow()
    
    # Mark new bed as occupied
    bed.is_occupied = True
    bed.updated_at = datetime.utcnow()
    
    # Update ward admission
    ward_admission.ward = transfer.to_ward
    ward_admission.bed_id = form_data.bed_id
    ward_admission.updated_at = datetime.utcnow()
    
    # Update transfer status
    transfer.status = "accepted"
    transfer.accepted_by = current_user.id
    transfer.accepted_at = datetime.utcnow()
    transfer.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(ward_admission)
    db.refresh(transfer)
    db.refresh(bed)
    
    return {
        "id": transfer.id,
        "ward_admission_id": ward_admission.id,
        "from_ward": transfer.from_ward,
        "to_ward": transfer.to_ward,
        "bed_id": form_data.bed_id,
        "status": "accepted",
        "message": "Transfer accepted successfully"
    }


class RejectTransferRequest(BaseModel):
    """Request to reject a transfer"""
    rejection_reason: Optional[str] = None


@router.post("/ward-admissions/transfers/{transfer_id}/reject")
def reject_transfer(
    transfer_id: int,
    form_data: RejectTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Reject a pending transfer request"""
    from datetime import datetime
    from app.models.ward_transfer import WardTransfer
    
    # Get the transfer
    transfer = db.query(WardTransfer).filter(
        WardTransfer.id == transfer_id
    ).first()
    
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    if transfer.status != "pending":
        raise HTTPException(status_code=400, detail=f"Transfer is already {transfer.status}")
    
    # Update transfer status
    transfer.status = "rejected"
    transfer.rejected_by = current_user.id
    transfer.rejection_reason = form_data.rejection_reason
    transfer.rejected_at = datetime.utcnow()
    transfer.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(transfer)
    
    return {
        "id": transfer.id,
        "status": "rejected",
        "message": "Transfer rejected successfully"
    }


@router.get("/ward-admissions/{ward_admission_id}/transfers")
def get_ward_admission_transfers(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all transfers for a specific ward admission"""
    from app.models.ward_admission import WardAdmission
    from app.models.ward_transfer import WardTransfer
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    transfers = db.query(WardTransfer).filter(
        WardTransfer.ward_admission_id == ward_admission_id
    ).options(
        joinedload(WardTransfer.transferrer),
        joinedload(WardTransfer.accepter),
        joinedload(WardTransfer.rejecter)
    ).order_by(WardTransfer.transferred_at.desc()).all()
    
    result = []
    for transfer in transfers:
        result.append({
            "id": transfer.id,
            "from_ward": transfer.from_ward,
            "to_ward": transfer.to_ward,
            "transfer_reason": transfer.transfer_reason,
            "status": transfer.status,
            "transferred_by": transfer.transferred_by,
            "transferred_by_name": transfer.transferrer.full_name if transfer.transferrer else None,
            "transferred_at": transfer.transferred_at,
            "accepted_by": transfer.accepted_by,
            "accepted_by_name": transfer.accepter.full_name if transfer.accepter else None,
            "accepted_at": transfer.accepted_at,
            "rejected_by": transfer.rejected_by,
            "rejected_by_name": transfer.rejecter.full_name if transfer.rejecter else None,
            "rejection_reason": transfer.rejection_reason,
            "rejected_at": transfer.rejected_at,
        })
    
    return result


class CancelAdmissionRequest(BaseModel):
    reason: str


@router.put("/admissions/{admission_id}/cancel")
def cancel_admission(
    admission_id: int,
    cancel_data: CancelAdmissionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Cancel an admission recommendation with a reason"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    
    admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=404, detail="Admission recommendation not found")
    
    if admission.cancelled == 1:
        raise HTTPException(status_code=400, detail="Admission has already been cancelled")
    
    # If confirmed, revert confirmation first (remove from ward)
    if admission.confirmed_by is not None:
        ward_admission = db.query(WardAdmission).filter(
            WardAdmission.admission_recommendation_id == admission.id,
            WardAdmission.discharged_at.is_(None)
        ).first()
        
        if ward_admission:
            # Delete the ward admission record
            db.delete(ward_admission)
        
        # Revert confirmation status
        admission.confirmed_by = None
        admission.confirmed_at = None
    
    # Mark as cancelled
    admission.cancelled = 1
    admission.cancelled_by = current_user.id
    admission.cancelled_at = datetime.utcnow()
    admission.cancellation_reason = cancel_data.reason
    admission.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(admission)
    
    return {
        "id": admission.id,
        "encounter_id": admission.encounter_id,
        "ward": admission.ward,
        "cancelled": admission.cancelled,
        "cancelled_by": admission.cancelled_by,
        "cancelled_at": admission.cancelled_at,
        "cancellation_reason": admission.cancellation_reason,
        "message": "Admission cancelled successfully"
    }


# Bed management endpoints
class BedResponse(BaseModel):
    id: int
    ward: str
    bed_number: str
    is_occupied: bool
    is_active: bool


@router.get("/wards", response_model=List[str])
def get_wards(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get list of unique wards from admission recommendations"""
    from sqlalchemy import distinct
    
    wards = db.query(distinct(AdmissionRecommendation.ward)).filter(
        AdmissionRecommendation.ward.isnot(None)
    ).order_by(AdmissionRecommendation.ward).all()
    
    return [ward[0] for ward in wards if ward[0]]


@router.get("/beds", response_model=List[BedResponse])
def get_beds(
    ward: Optional[str] = None,
    available_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get beds, optionally filtered by ward and availability"""
    from app.models.bed import Bed
    
    query = db.query(Bed).filter(Bed.is_active == True)
    
    if ward:
        query = query.filter(Bed.ward == ward)
    
    if available_only:
        query = query.filter(Bed.is_occupied == False)
    
    beds = query.order_by(Bed.bed_number).all()
    return beds


class BedCreate(BaseModel):
    ward: str
    bed_number: str
    is_active: bool = True


@router.post("/beds", response_model=BedResponse, status_code=status.HTTP_201_CREATED)
def create_bed(
    bed_data: BedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Create a new bed in the system - Admin only"""
    from app.models.bed import Bed
    
    # Check if bed with same number in same ward already exists
    existing_bed = db.query(Bed).filter(
        Bed.ward == bed_data.ward,
        Bed.bed_number == bed_data.bed_number,
        Bed.is_active == True
    ).first()
    
    if existing_bed:
        raise HTTPException(
            status_code=400,
            detail=f"Bed {bed_data.bed_number} already exists in {bed_data.ward}"
        )
    
    bed = Bed(
        ward=bed_data.ward,
        bed_number=bed_data.bed_number,
        is_active=bed_data.is_active,
        is_occupied=False
    )
    db.add(bed)
    db.commit()
    db.refresh(bed)
    
    return bed


@router.put("/beds/{bed_id}", response_model=BedResponse)
def update_bed(
    bed_id: int,
    bed_data: BedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update a bed - Admin only"""
    from app.models.bed import Bed
    
    bed = db.query(Bed).filter(Bed.id == bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    
    # Check if bed with same number in same ward already exists (excluding current bed)
    existing_bed = db.query(Bed).filter(
        Bed.ward == bed_data.ward,
        Bed.bed_number == bed_data.bed_number,
        Bed.id != bed_id,
        Bed.is_active == True
    ).first()
    
    if existing_bed:
        raise HTTPException(
            status_code=400,
            detail=f"Bed {bed_data.bed_number} already exists in {bed_data.ward}"
        )
    
    bed.ward = bed_data.ward
    bed.bed_number = bed_data.bed_number
    bed.is_active = bed_data.is_active
    bed.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(bed)
    
    return bed


@router.delete("/beds/{bed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bed(
    bed_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete (soft delete) a bed - Admin only"""
    from app.models.bed import Bed
    
    bed = db.query(Bed).filter(Bed.id == bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")
    
    if bed.is_occupied:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete bed that is currently occupied"
        )
    
    # Soft delete
    bed.is_active = False
    bed.updated_at = datetime.utcnow()
    
    db.commit()
    
    return None


# Doctor list endpoint
class DoctorResponse(BaseModel):
    id: int
    full_name: str
    role: str
    username: str


@router.get("/doctors", response_model=List[DoctorResponse])
def get_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get list of all doctors"""
    doctors = db.query(User).filter(
        User.role.in_(["Doctor", "PA"]),
        User.is_active == True
    ).order_by(User.full_name).all()
    
    return [
        {
            "id": doctor.id,
            "full_name": doctor.full_name or doctor.username,
            "role": doctor.role,
            "username": doctor.username
        }
        for doctor in doctors
    ]


# Cancel admission endpoint (for AM page)
@router.delete("/ward-admissions/{ward_admission_id}")
def cancel_ward_admission(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Cancel/delete a ward admission - removes all admission records"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    from app.models.bed import Bed
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    # Free up the bed
    if ward_admission.bed_id:
        bed = db.query(Bed).filter(Bed.id == ward_admission.bed_id).first()
        if bed:
            bed.is_occupied = False
            bed.updated_at = datetime.utcnow()
    
    # Revert admission recommendation confirmation
    admission = db.query(AdmissionRecommendation).filter(
        AdmissionRecommendation.id == ward_admission.admission_recommendation_id
    ).first()
    
    if admission:
        admission.confirmed_by = None
        admission.confirmed_at = None
        admission.updated_at = datetime.utcnow()
    
    # Delete ward admission record
    db.delete(ward_admission)
    
    db.commit()
    
    return {
        "message": "Admission cancelled successfully. All records have been removed."
    }