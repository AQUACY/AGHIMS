"""
Consultation endpoints (diagnoses, prescriptions, investigations)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File, Form, Response, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import or_, and_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.core.database import get_db
from app.core.datetime_utils import utcnow, today
from app.core.dependencies import require_role, get_current_user
from app.models.user import User
from app.models.encounter import Encounter, EncounterStatus
from app.models.diagnosis import Diagnosis
from app.models.prescription import Prescription
from app.models.investigation import Investigation, InvestigationStatus
from app.models.lab_result import LabResult
from app.models.inpatient_lab_result import InpatientLabResult
from app.models.scan_result import ScanResult
from app.models.inpatient_scan_result import InpatientScanResult
from app.models.xray_result import XrayResult
from app.models.inpatient_xray_result import InpatientXrayResult
from app.models.consultation_notes import ConsultationNotes
from app.models.admission import AdmissionRecommendation
from app.models.doctor_note_entry import DoctorNoteEntry

router = APIRouter(prefix="/consultation", tags=["consultation"])


def _generate_and_store_sample_id(db: Session, investigation, entered_by_user_id: int):
    """
    Generate a sample ID for a lab investigation and create a minimal lab_result record.
    This allows staff to write the ID on the sample and feed it into the analyzer before payment.
    """
    from app.models.lab_result import LabResult
    from app.models.inpatient_lab_result import InpatientLabResult
    from datetime import datetime
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Check if lab_result already exists and has a sample_no
        # First determine if this is OPD or IPD
        from app.models.inpatient_investigation import InpatientInvestigation
        
        if isinstance(investigation, InpatientInvestigation):
            # IPD investigation - check IPD lab results only
            existing_ipd_result = db.query(InpatientLabResult).filter(
                InpatientLabResult.investigation_id == investigation.id
            ).first()
            
            if existing_ipd_result and existing_ipd_result.template_data:
                existing_template_data = existing_ipd_result.template_data
                if isinstance(existing_template_data, dict):
                    if existing_template_data.get('sample_no'):
                        logger.info(f"IPD investigation {investigation.id} already has sample_no: {existing_template_data.get('sample_no')}")
                        return  # Sample ID already exists
                else:
                    try:
                        template_data = json.loads(existing_template_data)
                        if template_data.get('sample_no'):
                            logger.info(f"IPD investigation {investigation.id} already has sample_no: {template_data.get('sample_no')}")
                            return  # Sample ID already exists
                    except (json.JSONDecodeError, TypeError):
                        pass
        else:
            # OPD investigation - check OPD lab results only
            existing_opd_result = db.query(LabResult).filter(
                LabResult.investigation_id == investigation.id
            ).first()
            
            if existing_opd_result and existing_opd_result.template_data:
                existing_template_data = existing_opd_result.template_data
                if isinstance(existing_template_data, dict):
                    if existing_template_data.get('sample_no'):
                        logger.info(f"OPD investigation {investigation.id} already has sample_no: {existing_template_data.get('sample_no')}")
                        return  # Sample ID already exists
                else:
                    try:
                        template_data = json.loads(existing_template_data)
                        if template_data.get('sample_no'):
                            logger.info(f"OPD investigation {investigation.id} already has sample_no: {template_data.get('sample_no')}")
                            return  # Sample ID already exists
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        # Generate sample ID
        now = utcnow()
        year = now.year % 100  # Last 2 digits of year (e.g., 25 for 2025)
        month = now.month
        
        # Format: YYMM
        year_month_prefix = f"{year:02d}{month:02d}"
        
        # Find the highest sample number for this year/month from all lab results
        max_sample_num = 0
        
        # Check OPD lab results
        opd_results = db.query(LabResult).filter(
            LabResult.template_data.isnot(None)
        ).all()
        
        for result in opd_results:
            if result.template_data:
                try:
                    template_data = result.template_data if isinstance(result.template_data, dict) else json.loads(result.template_data)
                    sample_no = template_data.get('sample_no', '')
                    if sample_no and len(sample_no) == 8 and sample_no[:4] == year_month_prefix:
                        try:
                            sample_num = int(sample_no[4:])
                            if sample_num > max_sample_num:
                                max_sample_num = sample_num
                        except ValueError:
                            pass
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Check IPD lab results
        ipd_results = db.query(InpatientLabResult).filter(
            InpatientLabResult.template_data.isnot(None)
        ).all()
        
        for result in ipd_results:
            if result.template_data:
                try:
                    template_data = result.template_data if isinstance(result.template_data, dict) else json.loads(result.template_data)
                    sample_no = template_data.get('sample_no', '')
                    if sample_no and len(sample_no) == 8 and sample_no[:4] == year_month_prefix:
                        try:
                            sample_num = int(sample_no[4:])
                            if sample_num > max_sample_num:
                                max_sample_num = sample_num
                        except ValueError:
                            pass
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Generate next sample number
        next_sample_num = max_sample_num + 1
        
        # Format: YYMMNNNNN (8 digits total)
        sample_id = f"{year_month_prefix}{next_sample_num:05d}"
        
        # Create or update lab_result record with sample ID
        template_data = {
            "sample_no": sample_id,
            "field_values": {},
            "messages": {},
            "validated_by": ""
        }
        
        # Check if investigation is OPD or IPD by checking the type
        if isinstance(investigation, InpatientInvestigation):
            # IPD investigation
            existing_lab_result = db.query(InpatientLabResult).filter(
                InpatientLabResult.investigation_id == investigation.id
            ).first()
            
            if existing_lab_result:
                # Update existing record
                if existing_lab_result.template_data:
                    existing_data = existing_lab_result.template_data if isinstance(existing_lab_result.template_data, dict) else json.loads(existing_lab_result.template_data)
                    existing_data['sample_no'] = sample_id
                    existing_lab_result.template_data = existing_data
                    logger.info(f"Updated IPD lab_result with sample_id={sample_id} for investigation_id={investigation.id}")
                else:
                    existing_lab_result.template_data = template_data
                    logger.info(f"Set IPD lab_result template_data with sample_id={sample_id} for investigation_id={investigation.id}")
            else:
                # Create new record
                lab_result = InpatientLabResult(
                    investigation_id=investigation.id,
                    template_data=template_data,
                    entered_by=entered_by_user_id
                )
                db.add(lab_result)
                db.flush()  # Flush to ensure the record is created in the database
                logger.info(f"Created IPD lab_result with sample_id={sample_id} for investigation_id={investigation.id}")
        else:
            # OPD investigation (Investigation model)
            existing_lab_result = db.query(LabResult).filter(
                LabResult.investigation_id == investigation.id
            ).first()
            
            if existing_lab_result:
                # Update existing record
                if existing_lab_result.template_data:
                    existing_data = existing_lab_result.template_data if isinstance(existing_lab_result.template_data, dict) else json.loads(existing_lab_result.template_data)
                    existing_data['sample_no'] = sample_id
                    existing_lab_result.template_data = existing_data
                    logger.info(f"Updated OPD lab_result with sample_id={sample_id} for investigation_id={investigation.id}")
                else:
                    existing_lab_result.template_data = template_data
                    logger.info(f"Set OPD lab_result template_data with sample_id={sample_id} for investigation_id={investigation.id}")
            else:
                # Create new record
                lab_result = LabResult(
                    investigation_id=investigation.id,
                    template_data=template_data,
                    entered_by=entered_by_user_id
                )
                db.add(lab_result)
                db.flush()  # Flush to ensure the record is created in the database
                logger.info(f"Created OPD lab_result with sample_id={sample_id} for investigation_id={investigation.id}")
    
    except Exception as e:
        logger.error(f"Error generating and storing sample ID for investigation {investigation.id}: {str(e)}", exc_info=True)
        # Don't raise - allow investigation confirmation to continue even if sample ID generation fails
        # The sample ID can be generated later when results are entered


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
    patient_card_number: Optional[str] = None  # For direct prescriptions - card number of newly created patient
    
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
    # For patients without card number (walk-in)
    patient_name: Optional[str] = None  # Patient name for walk-in without card
    patient_phone: Optional[str] = None  # Patient phone for walk-in without card
    patient_age: Optional[int] = None  # Patient age for walk-in without card
    patient_gender: Optional[str] = None  # Patient gender for walk-in without card
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
    encounter_id: Optional[int] = None  # Optional for direct walk-in services
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
            prescription.confirmed_at = utcnow()
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


class DirectPrescriptionCreate(BaseModel):
    """Direct prescription creation model (walk-in, no consultation)"""
    medicine_code: str
    medicine_name: str
    dose: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    frequency_value: Optional[int] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    quantity: Optional[int] = None
    unparsed: Optional[str] = None
    # Patient identification - either patient_id, patient_card_number, or patient details
    patient_id: Optional[int] = None
    patient_card_number: Optional[str] = None
    patient_name: Optional[str] = None  # Full name (first + last + other)
    patient_phone: Optional[str] = None
    patient_age: Optional[int] = None
    patient_dob: Optional[str] = None  # Date of birth (YYYY-MM-DD)
    patient_gender: Optional[str] = None
    is_direct_service: Optional[bool] = True  # Always True for direct prescriptions


@router.post("/prescription/direct", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_direct_prescription(
    prescription_data: DirectPrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Create a direct prescription (walk-in, no consultation). Always uses base_rate pricing (no co-payment)."""
    from app.models.patient import Patient
    from app.models.encounter import Encounter, EncounterStatus
    from app.utils.card_number import generate_card_number
    from datetime import date, datetime
    from app.services.price_list_service_v2 import get_price_from_all_tables
    from app.models.bill import Bill, BillItem, Receipt
    import random
    
    # Get or create patient
    patient = None
    if prescription_data.patient_id:
        patient = db.query(Patient).filter(Patient.id == prescription_data.patient_id).first()
    elif prescription_data.patient_card_number:
        patient = db.query(Patient).filter(Patient.card_number == prescription_data.patient_card_number).first()
    elif prescription_data.patient_name and prescription_data.patient_phone:
        # Patient without card number - create a temporary patient record
        # Parse patient name (first name, last name, other names)
        name_parts = prescription_data.patient_name.strip().split()
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        other_names = " ".join(name_parts[2:]) if len(name_parts) > 2 else ""
        
        # Calculate date of birth
        date_of_birth = None
        if prescription_data.patient_dob:
            try:
                date_of_birth = datetime.strptime(prescription_data.patient_dob, "%Y-%m-%d").date()
            except ValueError:
                pass
        elif prescription_data.patient_age:
            # Calculate approximate DOB from age
            from datetime import date
            today_date = today()
            birth_year = today_date.year - prescription_data.patient_age
            date_of_birth = date(birth_year, 1, 1)  # Use January 1st as approximate DOB
        
        # Generate a card number for the new patient
        card_number = generate_card_number(db)
        
        # Create new patient record
        patient = Patient(
            name=first_name,
            surname=last_name,
            other_names=other_names if other_names else None,
            gender=prescription_data.patient_gender or "Other",
            age=prescription_data.patient_age,
            date_of_birth=date_of_birth,
            card_number=card_number,
            contact=prescription_data.patient_phone,
            insured=False,  # Direct prescriptions are always cash (base_rate)
            ccc_number=None
        )
        db.add(patient)
        db.flush()  # Get patient ID without committing yet
    else:
        raise HTTPException(
            status_code=400,
            detail="For direct prescriptions, provide either: (1) patient_id, (2) patient_card_number, or (3) patient_name and patient_phone"
        )
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found or could not be created")
    
    # Check if there's an existing unpaid direct service encounter for this patient
    # Reuse it to group all prescriptions together
    encounter = db.query(Encounter).filter(
        Encounter.patient_id == patient.id,
        Encounter.department == "Direct Service",
        Encounter.status == EncounterStatus.DRAFT.value
    ).order_by(Encounter.created_at.desc()).first()
    
    # If no existing encounter, create a new one
    if not encounter:
        encounter = Encounter(
            patient_id=patient.id,
            department="Direct Service",  # Mark as direct service
            status=EncounterStatus.DRAFT.value,  # Draft status for direct services
            ccc_number=None,  # Direct prescriptions are always cash (no insurance)
            created_by=current_user.id
        )
        db.add(encounter)
        db.flush()  # Get encounter ID without committing yet
    
    # Get frequency value from mapping if frequency is provided
    frequency_value = None
    if prescription_data.frequency:
        frequency_value = FREQUENCY_MAPPING.get(prescription_data.frequency.strip(), None)
    
    # Auto-calculate quantity if not provided
    quantity = prescription_data.quantity
    if (not quantity or quantity <= 0) and prescription_data.dose and frequency_value and prescription_data.duration:
        try:
            dose_num = float(prescription_data.dose)
            if dose_num > 0:
                # Extract duration number
                duration_str = prescription_data.duration.strip() if prescription_data.duration else ""
                duration_num = 1
                if duration_str:
                    try:
                        direct_num = float(duration_str)
                        if direct_num > 0:
                            duration_num = int(direct_num)
                    except ValueError:
                        import re
                        duration_match = re.search(r'\d+', duration_str)
                        if duration_match:
                            duration_num = int(duration_match.group())
                
                # Convert dose to units based on unit type
                units_per_dose = dose_num
                unit = prescription_data.unit.strip().upper() if prescription_data.unit else ""
                if unit == "MG":
                    units_per_dose = dose_num / 100.0
                elif unit == "MCG":
                    units_per_dose = dose_num / 1000.0
                
                # Calculate: units per dose × frequency per day × number of days
                calculated_quantity = int(units_per_dose * frequency_value * duration_num)
                if calculated_quantity > 0:
                    quantity = calculated_quantity
        except (ValueError, TypeError):
            pass
    
    # Ensure quantity is set
    if not quantity or quantity <= 0:
        quantity = 1
    
    # Create prescription
    prescription_dict = {
        'encounter_id': encounter.id,
        'medicine_code': prescription_data.medicine_code,
        'medicine_name': prescription_data.medicine_name,
        'dose': prescription_data.dose,
        'unit': prescription_data.unit,
        'frequency': prescription_data.frequency,
        'frequency_value': frequency_value,
        'duration': prescription_data.duration,
        'instructions': prescription_data.instructions,
        'quantity': quantity,
        'unparsed': prescription_data.unparsed,
        'is_external': 0,  # Not external, will be dispensed here
    }
    
    prescription = Prescription(**prescription_dict, prescribed_by=current_user.id)
    db.add(prescription)
    db.flush()  # Get prescription ID
    
    # Auto-confirm direct prescriptions (client pays first, then dispensed later)
    # Direct prescriptions are always base_rate (no co-payment)
    is_insured = False  # Always False for direct prescriptions
    unit_price = get_price_from_all_tables(db, prescription.medicine_code, is_insured)
    
    # Auto-confirm (but NOT auto-dispense - client must pay first)
    prescription.confirmed_by = current_user.id
    prescription.confirmed_at = utcnow()
    
    # Create bill item for the prescription (base_rate pricing)
    # Find or create an unpaid bill for this encounter
    existing_bill = db.query(Bill).filter(
        Bill.encounter_id == encounter.id,
        Bill.is_paid == False
    ).first()
    
    if not existing_bill:
        # Generate unique bill number
        max_attempts = 100
        bill_number = None
        for _ in range(max_attempts):
            candidate = f"BILL-{random.randint(100000, 999999)}"
            existing_bill_check = db.query(Bill).filter(
                Bill.bill_number == candidate
            ).first()
            if not existing_bill_check:
                bill_number = candidate
                break
        
        if not bill_number:
            # Fallback: use timestamp-based approach
            import time
            timestamp = int(time.time() * 1000) % 1000000
            bill_number = f"BILL-{timestamp:06d}"
        
        bill = Bill(
            encounter_id=encounter.id,
            bill_number=bill_number,
            total_amount=0.0,  # Will be calculated from items
            is_paid=False,
            created_by=current_user.id
        )
        db.add(bill)
        db.flush()
    else:
        bill = existing_bill
    
    # Add prescription as bill item
    total_price = unit_price * prescription.quantity
    bill_item = BillItem(
        bill_id=bill.id,
        item_name=prescription.medicine_name,
        item_code=prescription.medicine_code,
        category="product",  # Pharmacy items are products
        quantity=prescription.quantity,
        unit_price=unit_price,
        total_price=total_price
    )
    db.add(bill_item)
    
    # Update bill total
    bill.total_amount = (bill.total_amount or 0.0) + total_price
    
    db.commit()
    db.refresh(prescription)
    
    # Return prescription with patient card number if it was newly created
    response = add_prescriber_info_to_response(prescription, db)
    
    # Add patient card number to response if patient was newly created
    if patient and not prescription_data.patient_id and not prescription_data.patient_card_number:
        # Patient was newly created, include card number in response
        # Update the response object directly
        response.patient_card_number = patient.card_number
    
    return response


def add_prescriber_info_to_response(prescription, db: Session) -> PrescriptionResponse:
    """Helper function to add prescriber and dispenser information to a prescription response"""
    # Get prescriber information (handle missing user gracefully)
    prescriber_name = None
    prescriber_role = None
    try:
        prescriber = db.query(User).filter(User.id == prescription.prescribed_by).first()
        if prescriber:
            prescriber_name = prescriber.full_name
            prescriber_role = prescriber.role
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not load prescriber info for prescription {prescription.id}: {str(e)}")
    
    # Get dispenser information (handle missing user gracefully)
    dispenser_name = None
    try:
        if prescription.dispensed_by:
            dispenser = db.query(User).filter(User.id == prescription.dispensed_by).first()
            if dispenser:
                dispenser_name = dispenser.full_name
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not load dispenser info for prescription {prescription.id}: {str(e)}")
    
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
    """Get all prescriptions for an encounter (works even if encounter is archived)"""
    # Verify encounter exists (but don't require it to be non-archived - prescriptions should still be accessible)
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Query prescriptions with prescriber information, ordered by creation time
    # Don't filter by archived status - prescriptions should be accessible even if encounter is archived
    prescriptions = db.query(Prescription).filter(
        Prescription.encounter_id == encounter_id
    ).order_by(Prescription.created_at.desc()).all()
    
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
    
    # Verify encounter belongs to patient (include archived encounters - they may still have prescriptions to dispense)
    encounter = db.query(Encounter).filter(
        Encounter.id == encounter_id,
        Encounter.patient_id == patient.id
    ).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found or does not belong to this patient")
    
    # Get prescriptions for the encounter with prescriber information
    # Don't filter by archived status - prescriptions should be accessible even if encounter is archived
    prescriptions = db.query(Prescription).filter(Prescription.encounter_id == encounter_id).order_by(Prescription.created_at.desc()).all()
    
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
    add_to_ipd_bill: Optional[bool] = True  # For IPD prescriptions: whether to add to IPD bill


@router.put("/prescription/{prescription_id}/dispense", response_model=PrescriptionResponse)
def dispense_prescription(
    prescription_id: int,
    dispense_data: Optional[PrescriptionDispense] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Mark a prescription as dispensed - only allowed if bill is paid or bill amount is 0 (except for inpatients)"""
    from app.models.bill import Bill, BillItem, ReceiptItem, Receipt
    from app.models.ward_admission import WardAdmission
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.dispensed_by is not None:
        raise HTTPException(status_code=400, detail="Prescription has already been dispensed")
    
    if prescription.confirmed_by is None:
        raise HTTPException(status_code=400, detail="Prescription must be confirmed before dispense")
    
    # Check if this is an inpatient prescription (encounter is linked to a ward admission)
    is_inpatient = db.query(WardAdmission).filter(
        WardAdmission.encounter_id == prescription.encounter_id
    ).first() is not None
    
    # For inpatients, skip payment check - medications are added to IPD bills and paid at discharge
    if not is_inpatient:
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
    prescription.service_date = utcnow()
    
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
    prescription.confirmed_at = utcnow()
    
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
    
    # Check if prescription is external (external prescriptions are not billed, so skip bill item removal)
    is_external = bool(prescription.is_external) if hasattr(prescription, 'is_external') else False
    
    # Find and remove the bill item that was created during confirmation (only for non-external prescriptions)
    # External prescriptions are not billed, so no bill items to remove
    if not is_external:
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
    
    # Revert prescription confirmation and clear external flag
    prescription.confirmed_by = None
    prescription.confirmed_at = None
    if hasattr(prescription, 'is_external'):
        prescription.is_external = 0  # Clear external flag so it can be confirmed again
    
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
    prescription.service_date = utcnow()
    
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
            
            # Generate and store sample ID for lab investigations
            if investigation.investigation_type == "lab":
                _generate_and_store_sample_id(db, investigation, current_user.id)
            
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
                            unit_price = get_price_from_all_tables(db, investigation.gdrg_code, is_insured_encounter, service_type, investigation.procedure_name)
                            print(f"DEBUG bulk_confirm: Looked up price for investigation {investigation.id}, gdrg_code='{investigation.gdrg_code}', procedure_name='{investigation.procedure_name}', is_insured={is_insured_encounter}, service_type='{service_type}', price={unit_price}")
                            
                            # If lookup returns 0.0, it means price wasn't found
                            if unit_price == 0.0:
                                print(f"WARNING bulk_confirm: Price lookup returned 0.0 for investigation {investigation.id}, gdrg_code='{investigation.gdrg_code}', service_type='{service_type}'")
                                # Only use stored price if it exists and lookup returned 0
                                if investigation.price:
                                    try:
                                        stored_price = float(investigation.price)
                                        if stored_price > 0:
                                            print(f"WARNING bulk_confirm: Using stored price '{stored_price}' as fallback for investigation {investigation.id}")
                                            unit_price = stored_price
                                    except (ValueError, TypeError):
                                        pass
                        except Exception as e:
                            print(f"ERROR bulk_confirm: Failed to get price for investigation {investigation.id}: {e}")
                            # Fallback to stored price only if exception occurred
                            if investigation.price:
                                try:
                                    unit_price = float(investigation.price)
                                    print(f"WARNING bulk_confirm: Using stored price '{unit_price}' as fallback after exception for investigation {investigation.id}")
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
        # Must provide either patient_id, patient_card_number, or patient name/phone/age
        patient = None
        if investigation_data.patient_id:
            patient = db.query(Patient).filter(Patient.id == investigation_data.patient_id).first()
        elif investigation_data.patient_card_number:
            patient = db.query(Patient).filter(Patient.card_number == investigation_data.patient_card_number).first()
        elif investigation_data.patient_name and investigation_data.patient_phone and investigation_data.patient_age:
            # Patient without card number - create a temporary patient record
            from app.utils.card_number import generate_card_number
            from datetime import date, timedelta
            
            # Generate a card number for the new patient
            card_number = generate_card_number(db)
            
            # Calculate date of birth from age (approximate)
            today_date = today()
            birth_year = today_date.year - investigation_data.patient_age
            date_of_birth = date(birth_year, 1, 1)  # Use January 1st as approximate DOB
            
            # Create new patient record
            patient = Patient(
                name=investigation_data.patient_name,
                surname="",  # Not provided
                gender=investigation_data.patient_gender or "Other",
                age=investigation_data.patient_age,
                date_of_birth=date_of_birth,
                card_number=card_number,
                contact=investigation_data.patient_phone,
                insured=investigation_data.is_insured or False,
                ccc_number=investigation_data.ccc_number if investigation_data.is_insured else None
            )
            db.add(patient)
            db.flush()  # Get patient ID without committing yet
        else:
            raise HTTPException(
                status_code=400,
                detail="For direct services, provide either: (1) patient_id, (2) patient_card_number, or (3) patient_name, patient_phone, and patient_age"
            )
        
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found or could not be created")
        
        # Use provided insurance info or patient's insurance status
        if investigation_data.is_insured is not None:
            is_insured = investigation_data.is_insured
        else:
            is_insured = patient.insured or bool(investigation_data.ccc_number)
        
        # Create a minimal encounter for direct services so the investigation can be linked to the patient
        # This ensures the investigation appears in queries and maintains data consistency
        from app.models.encounter import EncounterStatus
        encounter = Encounter(
            patient_id=patient.id,
            department="Direct Service",  # Mark as direct service
            status=EncounterStatus.DRAFT.value,  # Draft status for direct services
            ccc_number=investigation_data.ccc_number if investigation_data.is_insured else None,
            created_by=current_user.id
        )
        db.add(encounter)
        db.flush()  # Get encounter ID without committing yet
    
    # Auto-fetch price from price list if not provided
    price = investigation_data.price
    if not price and investigation_data.gdrg_code:
        try:
            # Determine service type based on investigation type for accurate price lookup
            service_type = None
            if investigation_data.investigation_type == "lab":
                service_type = "Lab"
            elif investigation_data.investigation_type == "scan":
                service_type = "Scan"
            elif investigation_data.investigation_type == "xray":
                service_type = "X-ray"
            
            price_value = get_price_from_all_tables(db, investigation_data.gdrg_code, is_insured, service_type, investigation_data.procedure_name)
            price = str(price_value) if price_value else None
            print(f"DEBUG create_investigation: Looked up price for gdrg_code='{investigation_data.gdrg_code}', procedure_name='{investigation_data.procedure_name}', is_insured={is_insured}, service_type='{service_type}', price={price_value}")
        except Exception as e:
            # If price lookup fails, continue without price
            print(f"ERROR create_investigation: Failed to get price from price list: {e}")
            price = None
    
    investigation = Investigation(
        encounter_id=encounter.id if encounter else investigation_data.encounter_id,
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
        "patient_name": f"{investigation.encounter.patient.name or ''} {investigation.encounter.patient.surname or ''} {investigation.encounter.patient.other_names or ''}".strip(),
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
    investigation.cancelled_at = utcnow()
    
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
            "patient_name": f"{inv.encounter.patient.name or ''} {inv.encounter.patient.surname or ''} {inv.encounter.patient.other_names or ''}".strip(),
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
    if current_user.role not in ["Admin", "Lab Head", "Scan Head", "Xray Head", "Scan"]:
        if investigation.investigation_type == "lab" and current_user.role != "Lab":
            raise HTTPException(status_code=403, detail="Only Lab staff can update lab investigations")
        elif investigation.investigation_type == "scan" and current_user.role != "Scan" and current_user.role != "Scan Head":
            raise HTTPException(status_code=403, detail="Only Scan staff and Scan Head can update scan investigations")
        elif investigation.investigation_type == "xray" and current_user.role != "Xray" and current_user.role != "Xray Head":
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
    investigation.cancelled_at = utcnow()
    
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
    
    # Generate and store sample ID for lab investigations
    if investigation.investigation_type == "lab":
        _generate_and_store_sample_id(db, investigation, current_user.id)
    
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
        # Pass procedure_name to match exact procedure when G-DRG codes map to multiple procedures
        try:
            unit_price = get_price_from_all_tables(db, investigation.gdrg_code, is_insured_encounter, service_type, investigation.procedure_name)
            print(f"DEBUG confirm_investigation: Looked up price for gdrg_code='{investigation.gdrg_code}', procedure_name='{investigation.procedure_name}', is_insured={is_insured_encounter}, service_type='{service_type}', price={unit_price}")
            
            # If lookup returns 0.0, it means price wasn't found - don't use stored price, log warning
            if unit_price == 0.0:
                print(f"WARNING confirm_investigation: Price lookup returned 0.0 for gdrg_code='{investigation.gdrg_code}', service_type='{service_type}'. Price not found in pricelist.")
                # Only use stored price if it exists and lookup returned 0 (price not in pricelist)
                if investigation.price:
                    try:
                        stored_price = float(investigation.price)
                        if stored_price > 0:
                            print(f"WARNING confirm_investigation: Using stored price '{stored_price}' as fallback (price not found in pricelist)")
                            unit_price = stored_price
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            print(f"ERROR confirm_investigation: Failed to get price from price list: {e}")
            # If lookup throws exception, try using stored price as fallback
            if investigation.price:
                try:
                    unit_price = float(investigation.price)
                    print(f"DEBUG confirm_investigation: Using stored price as fallback after exception: {unit_price}")
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
    
    print(f"DEBUG confirm_investigation: unit_price={unit_price}, total_price={total_price}, encounter_id={encounter.id if encounter else None}")
    
    # Always create/add to bill if total_price > 0
    if total_price > 0:
        try:
            # Find or create a bill for this encounter
            existing_bill = db.query(Bill).filter(
                Bill.encounter_id == encounter.id,
                Bill.is_paid == False  # Only use unpaid bills
            ).first()
            
            print(f"DEBUG confirm_investigation: existing_bill={existing_bill.id if existing_bill else None}")
            
            if existing_bill:
                # Check if this investigation is already in the bill
                existing_item = db.query(BillItem).filter(
                    BillItem.bill_id == existing_bill.id,
                    BillItem.item_code == investigation.gdrg_code,
                    BillItem.item_name.like(f"%{investigation.procedure_name}%")
                ).first()
                
                print(f"DEBUG confirm_investigation: existing_item={existing_item.id if existing_item else None}")
                
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
                    print(f"DEBUG confirm_investigation: Added bill item to existing bill. New total_amount={existing_bill.total_amount}")
                else:
                    print(f"DEBUG confirm_investigation: Bill item already exists, skipping")
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
                print(f"DEBUG confirm_investigation: Created new bill {bill.id} with bill_number={bill_number}")
                
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
                print(f"DEBUG confirm_investigation: Created bill item with unit_price={unit_price}, total_price={total_price}")
        except Exception as e:
            print(f"ERROR confirm_investigation: Exception during bill creation: {str(e)}")
            import traceback
            traceback.print_exc()
            # Don't fail the confirmation if bill creation fails, but log it
    else:
        print(f"WARNING confirm_investigation: Not creating bill because total_price={total_price} (must be > 0)")
    
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
    template_id: Optional[int] = None
    results_text: Optional[str]
    template_data: Optional[dict] = None  # Structured template data
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


@router.post("/lab-result/sample-id", response_model=LabResultResponse, status_code=status.HTTP_200_OK)
def save_sample_id(
    investigation_id: int = Body(...),
    sample_no: str = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Lab Head", "Admin"]))
):
    """
    Save sample ID for a lab investigation without payment check.
    This is the only data that can be saved before payment.
    """
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Saving sample_no={sample_no} for investigation_id={investigation_id}")
    
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    
    investigation = None
    is_inpatient = False
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        investigation = ipd_investigation
        is_inpatient = True
    else:
        # Not IPD, check OPD
        investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.investigation_type != "lab":
        raise HTTPException(status_code=400, detail="This endpoint is only for lab investigations")
    
    # Create or update lab_result record with just the sample ID
    template_data = {
        "sample_no": sample_no,
        "field_values": {},
        "messages": {},
        "validated_by": ""
    }
    
    result = None
    if is_inpatient:
        # IPD investigation
        existing_lab_result = db.query(InpatientLabResult).filter(
            InpatientLabResult.investigation_id == investigation_id
        ).first()
        
        if existing_lab_result:
            # Update existing record
            if existing_lab_result.template_data:
                existing_data = existing_lab_result.template_data if isinstance(existing_lab_result.template_data, dict) else json.loads(existing_lab_result.template_data)
                # Create a new dict to ensure SQLAlchemy detects the change
                updated_data = existing_data.copy()
                updated_data['sample_no'] = sample_no
                existing_lab_result.template_data = updated_data
                flag_modified(existing_lab_result, 'template_data')  # Tell SQLAlchemy the JSON column changed
            else:
                existing_lab_result.template_data = template_data
                flag_modified(existing_lab_result, 'template_data')  # Tell SQLAlchemy the JSON column changed
            result = existing_lab_result
        else:
            # Create new record
            lab_result = InpatientLabResult(
                investigation_id=investigation_id,
                template_data=template_data,
                entered_by=current_user.id
            )
            db.add(lab_result)
            result = lab_result
    else:
        # OPD investigation
        existing_lab_result = db.query(LabResult).filter(
            LabResult.investigation_id == investigation_id
        ).first()
        
        if existing_lab_result:
            # Update existing record
            if existing_lab_result.template_data:
                existing_data = existing_lab_result.template_data if isinstance(existing_lab_result.template_data, dict) else json.loads(existing_lab_result.template_data)
                # Create a new dict to ensure SQLAlchemy detects the change
                updated_data = existing_data.copy()
                updated_data['sample_no'] = sample_no
                existing_lab_result.template_data = updated_data
                flag_modified(existing_lab_result, 'template_data')  # Tell SQLAlchemy the JSON column changed
            else:
                existing_lab_result.template_data = template_data
                flag_modified(existing_lab_result, 'template_data')  # Tell SQLAlchemy the JSON column changed
            result = existing_lab_result
        else:
            # Create new record
            lab_result = LabResult(
                investigation_id=investigation_id,
                template_data=template_data,
                entered_by=current_user.id
            )
            db.add(lab_result)
            result = lab_result
    
    try:
        db.commit()
        db.refresh(result)  # Refresh to get the latest data from database
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving sample ID: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to save sample ID: {str(e)}")
    
    if not result:
        raise HTTPException(status_code=500, detail="Failed to save sample ID")
    
    # Verify sample_no was saved correctly
    # Query fresh from database to ensure we have the latest data
    if is_inpatient:
        fresh_result = db.query(InpatientLabResult).filter(InpatientLabResult.investigation_id == investigation_id).first()
    else:
        fresh_result = db.query(LabResult).filter(LabResult.investigation_id == investigation_id).first()
    
    if fresh_result:
        result = fresh_result
    
    saved_sample_no = None
    if result.template_data:
        if isinstance(result.template_data, dict):
            saved_sample_no = result.template_data.get('sample_no', '')
        else:
            try:
                saved_data = json.loads(result.template_data)
                saved_sample_no = saved_data.get('sample_no', '')
            except:
                pass
    
    logger.info(f"Sample ID save attempt. investigation_id={investigation_id}, input_sample_no={sample_no}, saved_sample_no={saved_sample_no}, template_data={result.template_data}")
    
    # Only raise error if we explicitly tried to save but it didn't work
    # Allow empty sample_no if it wasn't in the original data (edge case)
    if saved_sample_no != sample_no:
        logger.error(f"ERROR: Sample ID mismatch. Expected={sample_no}, Got={saved_sample_no}. Template data: {result.template_data}")
        # Don't raise error - just log it. The sample_no might still be saved but not yet visible
        # Return the result anyway so frontend can check
    
    # Get user names
    entered_user = db.query(User).filter(User.id == result.entered_by).first()
    updated_user = db.query(User).filter(User.id == result.updated_by).first() if result.updated_by else None
    
    result_dict = {
        "id": result.id,
        "investigation_id": result.investigation_id,
        "template_id": result.template_id,
        "results_text": result.results_text,
        "template_data": result.template_data,
        "attachment_path": result.attachment_path,
        "entered_by": result.entered_by,
        "updated_by": result.updated_by,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "entered_by_name": entered_user.full_name if entered_user else None,
        "updated_by_name": updated_user.full_name if updated_user else None,
    }
    return LabResultResponse(**result_dict)


@router.post("/lab-result", response_model=LabResultResponse, status_code=status.HTTP_201_CREATED)
async def create_lab_result(
    investigation_id: int = Form(...),
    results_text: Optional[str] = Form(None),
    template_id: Optional[int] = Form(None),
    template_data: Optional[str] = Form(None),  # JSON string
    attachment: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Lab Head", "Admin"]))
):
    """Create or update lab result with optional file attachment and template data"""
    import json
    import logging
    
    logger = logging.getLogger(__name__)
    
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    from app.models.lab_result_template import LabResultTemplate
    
    investigation = None
    is_inpatient = False
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        investigation = ipd_investigation
        is_inpatient = True
    else:
        # Not IPD, check OPD
        investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.investigation_type != "lab":
        raise HTTPException(status_code=400, detail="This endpoint is only for lab investigations")
    
    # Check payment status for OPD investigations (IPD doesn't require payment check)
    if not is_inpatient:
        from app.models.bill import Bill, BillItem, Receipt, ReceiptItem
        from app.models.encounter import Encounter
        
        # Get encounter for this investigation
        encounter = db.query(Encounter).filter(Encounter.id == investigation.encounter_id).first()
        
        if encounter:
            # Check if patient is insured (has CCC number) - insured patients may have 0 bills
            is_insured = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
            
            # Find bill items for this investigation
            bills = db.query(Bill).filter(Bill.encounter_id == encounter.id).all()
            investigation_paid = False
            investigation_free = False
            
            for bill in bills:
                for bill_item in bill.bill_items:
                    # Match by G-DRG code or procedure name
                    matches_code = bill_item.item_code == investigation.gdrg_code
                    investigation_name = investigation.procedure_name or ''
                    investigation_code = investigation.gdrg_code or ''
                    matches_name = bill_item.item_name and (
                        investigation_name in bill_item.item_name or
                        investigation_code in bill_item.item_name or
                        f"Investigation: {investigation_name}" in bill_item.item_name or
                        f"Investigation: {investigation_code}" in bill_item.item_name
                    )
                    
                    if matches_code or matches_name:
                        total_price = bill_item.total_price or 0
                        if total_price == 0:
                            investigation_free = True
                            investigation_paid = True
                        else:
                            # Calculate amount paid for this bill item from receipts
                            amount_paid = 0.0
                            for receipt in bill.receipts:
                                if not receipt.refunded:  # Only count non-refunded receipts
                                    for receipt_item in receipt.receipt_items:
                                        if receipt_item.bill_item_id == bill_item.id:
                                            amount_paid += receipt_item.amount_paid or 0.0
                            
                            # Calculate remaining balance
                            remaining_balance = total_price - amount_paid
                            is_paid = remaining_balance <= 0.01  # Allow 0.01 tolerance for rounding
                            
                            if is_paid:
                                investigation_paid = True
                        break
                
                if investigation_paid:
                    break
            
            # If no bill item found and patient is not insured, require payment
            if not investigation_paid and not investigation_free:
                if not is_insured:
                    raise HTTPException(
                        status_code=402,
                        detail="Payment required. This investigation must be paid for before results can be entered. Please process payment at the billing desk."
                    )
                # For insured patients without bill items, allow (might be fully covered)
    
    # Parse template_data if provided
    parsed_template_data = None
    if template_data:
        try:
            parsed_template_data = json.loads(template_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in template_data")
    
    # Validate template_id if provided
    if template_id:
        template = db.query(LabResultTemplate).filter(
            LabResultTemplate.id == template_id,
            LabResultTemplate.is_active == 1
        ).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found or inactive")
        # If template_data is provided, ensure template procedure_name matches
        if parsed_template_data and investigation.procedure_name and template.procedure_name != investigation.procedure_name:
            raise HTTPException(
                status_code=400,
                detail=f"Template procedure name ({template.procedure_name}) does not match investigation procedure name ({investigation.procedure_name})"
            )
    elif parsed_template_data:
        # If template_data is provided but no template_id, try to find template by procedure name
        if investigation.procedure_name:
            template = db.query(LabResultTemplate).filter(
                LabResultTemplate.procedure_name == investigation.procedure_name,
                LabResultTemplate.is_active == 1
            ).first()
            if template:
                template_id = template.id
    
    # If investigation is completed, only Admin and Lab Head can edit
    if is_inpatient:
        from app.models.inpatient_investigation import InpatientInvestigationStatus
        if investigation.status == InpatientInvestigationStatus.COMPLETED.value:
            if current_user.role not in ["Admin", "Lab Head"]:
                raise HTTPException(
                    status_code=403,
                    detail="Only Admin and Lab Head can edit completed investigations. Please contact Lab Head to revert the status."
                )
    else:
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
    
    # Handle IPD and OPD investigations separately due to FK constraints
    if is_inpatient:
        # Use InpatientLabResult for IPD investigations
        existing_result = db.query(InpatientLabResult).filter(InpatientLabResult.investigation_id == investigation_id).first()
    else:
        # Use LabResult for OPD investigations
        existing_result = db.query(LabResult).filter(LabResult.investigation_id == investigation_id).first()
    
    if existing_result:
        # Update existing result
        existing_result.results_text = results_text
        if template_id is not None:
            existing_result.template_id = template_id
        if parsed_template_data is not None:
            # Merge with existing template_data to preserve sample_no and other fields
            if existing_result.template_data:
                existing_data = existing_result.template_data if isinstance(existing_result.template_data, dict) else json.loads(existing_result.template_data)
                # ALWAYS preserve sample_no from existing data if it exists and is non-empty
                # Sample ID should never be overwritten with empty value
                existing_sample_no = existing_data.get('sample_no', '')
                new_sample_no = parsed_template_data.get('sample_no', '')
                # IMPORTANT: If new sample_no is provided and non-empty, ALWAYS use it
                # This allows users to regenerate sample IDs if needed
                if new_sample_no and isinstance(new_sample_no, str) and new_sample_no.strip() != '':
                    # New one is provided and non-empty, use it (even if existing one exists)
                    parsed_template_data['sample_no'] = new_sample_no.strip()
                    logger.info(f"Using new sample_no={new_sample_no} for investigation_id={investigation_id} (replacing existing={existing_sample_no})")
                elif existing_sample_no and isinstance(existing_sample_no, str) and existing_sample_no.strip() != '':
                    # No new sample_no provided, preserve existing one
                    parsed_template_data['sample_no'] = existing_sample_no
                    logger.info(f"Preserved existing sample_no={existing_sample_no} for investigation_id={investigation_id}")
                else:
                    # Neither exists, leave it empty (will be generated later if needed)
                    logger.info(f"No sample_no provided or existing for investigation_id={investigation_id}")
                # Merge field_values - new values override existing ones, but keep existing if new is empty
                if 'field_values' in existing_data and existing_data['field_values']:
                    if 'field_values' not in parsed_template_data:
                        parsed_template_data['field_values'] = existing_data['field_values'].copy()
                    elif parsed_template_data['field_values']:
                        # Merge: start with existing, then update with new non-empty values
                        merged_field_values = existing_data['field_values'].copy()
                        for key, value in parsed_template_data['field_values'].items():
                            if value is not None and value != '':
                                merged_field_values[key] = value
                        parsed_template_data['field_values'] = merged_field_values
                    else:
                        # New field_values is empty dict, keep existing
                        parsed_template_data['field_values'] = existing_data['field_values'].copy()
                # Merge messages similarly
                if 'messages' in existing_data and existing_data['messages']:
                    if 'messages' not in parsed_template_data:
                        parsed_template_data['messages'] = existing_data['messages'].copy()
                    elif parsed_template_data['messages']:
                        merged_messages = existing_data['messages'].copy()
                        for key, value in parsed_template_data['messages'].items():
                            if value is not None and value != '':
                                merged_messages[key] = value
                        parsed_template_data['messages'] = merged_messages
                    else:
                        # New messages is empty dict, keep existing
                        parsed_template_data['messages'] = existing_data['messages'].copy()
            existing_result.template_data = parsed_template_data
        if attachment_path:
            # Delete old attachment if exists
            if existing_result.attachment_path:
                old_path = Path("uploads") / existing_result.attachment_path
                if old_path.exists():
                    old_path.unlink()
            existing_result.attachment_path = attachment_path
        existing_result.updated_by = current_user.id  # Track who updated
        existing_result.updated_at = utcnow()
        
        # Mark investigation as completed if results are entered
        if results_text or parsed_template_data or attachment_path:
            if is_inpatient:
                from app.models.inpatient_investigation import InpatientInvestigationStatus
                investigation.status = InpatientInvestigationStatus.COMPLETED.value
            else:
                investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session for update
            db.add(investigation)
    else:
        # Create new result
        if is_inpatient:
            lab_result = InpatientLabResult(
                investigation_id=investigation_id,
                template_id=template_id,
                results_text=results_text,
                template_data=parsed_template_data,
                attachment_path=attachment_path,
                entered_by=current_user.id
            )
        else:
            lab_result = LabResult(
                investigation_id=investigation_id,
                template_id=template_id,
                results_text=results_text,
                template_data=parsed_template_data,
                attachment_path=attachment_path,
                entered_by=current_user.id
            )
        db.add(lab_result)
        
        # Mark investigation as completed if results are entered
        if results_text or parsed_template_data or attachment_path:
            if is_inpatient:
                from app.models.inpatient_investigation import InpatientInvestigationStatus
                investigation.status = InpatientInvestigationStatus.COMPLETED.value
            else:
                investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session for update
            db.add(investigation)
    
    db.commit()
    # Refresh investigation to ensure status and completed_by are updated
    db.refresh(investigation)
    if existing_result:
        db.refresh(existing_result)
        # Get user names for response
        entered_user = db.query(User).filter(User.id == existing_result.entered_by).first()
        updated_user = db.query(User).filter(User.id == existing_result.updated_by).first() if existing_result.updated_by else None
        result_dict = {
            "id": existing_result.id,
            "investigation_id": existing_result.investigation_id,
            "template_id": existing_result.template_id,
            "results_text": existing_result.results_text,
            "template_data": existing_result.template_data,
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
            "template_id": lab_result.template_id,
            "results_text": lab_result.results_text,
            "template_data": lab_result.template_data,
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
    """Get lab result for an investigation (supports both OPD and IPD investigations)"""
    # IMPORTANT: Check if this is an IPD investigation FIRST
    # LabResult.investigation_id has FK constraint to investigations.id (OPD only)
    # So IPD investigation IDs cannot be stored in LabResult table
    # We must check investigation type BEFORE querying LabResult to avoid ID collisions
    from app.models.inpatient_investigation import InpatientInvestigation
    import logging
    
    logger = logging.getLogger(__name__)
    
    # ALWAYS check IPD first to prevent ID collision issues
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    
    if ipd_investigation:
        logger.info(f"Found IPD investigation {investigation_id}, type: {ipd_investigation.investigation_type}")
        # This is definitely an IPD investigation - ONLY query InpatientLabResult table
        # Do NOT fall back to OPD LabResult table even if no IPD result exists
        if ipd_investigation.investigation_type != "lab":
            logger.info(f"IPD investigation {investigation_id} is not a lab investigation, returning None")
            return None
        
        # Use raw SQL query to avoid template_id column issue if it doesn't exist in database
        # Check if template_id column exists first, then use appropriate query
        from sqlalchemy import text, inspect
        
        # Check if template_id column exists in the table
        has_template_id = False
        try:
            inspector = inspect(db.bind)
            columns_info = inspector.get_columns('inpatient_lab_results')
            if columns_info and isinstance(columns_info, list):
                columns = [col.get('name', '') for col in columns_info if isinstance(col, dict)]
                has_template_id = 'template_id' in columns
        except Exception as e:
            # If inspection fails, assume column doesn't exist and use raw SQL
            logger.warning(f"Failed to inspect columns, assuming template_id doesn't exist: {e}")
            has_template_id = False
        
        if has_template_id:
            # Column exists, use normal ORM query
            result = db.query(InpatientLabResult).filter(InpatientLabResult.investigation_id == investigation_id).first()
            
            if not result:
                logger.info(f"No IPD lab result found for investigation {investigation_id}, returning None")
                return None
            
            entered_user = db.query(User).filter(User.id == result.entered_by).first()
            updated_user = db.query(User).filter(User.id == result.updated_by).first() if result.updated_by else None
            
            result_dict = {
                "id": result.id,
                "investigation_id": result.investigation_id,
                "template_id": result.template_id,
                "results_text": result.results_text,
                "template_data": result.template_data,
                "attachment_path": result.attachment_path,
                "entered_by": result.entered_by,
                "updated_by": result.updated_by,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
                "entered_by_name": entered_user.full_name if entered_user else None,
                "updated_by_name": updated_user.full_name if updated_user else None,
            }
            return LabResultResponse(**result_dict)
        else:
            # Column doesn't exist, use raw SQL query without template_id
            logger.info(f"template_id column not found, using raw SQL query")
            result_row = db.execute(
                text("""
                    SELECT id, investigation_id, results_text, template_data, 
                           attachment_path, entered_by, updated_by, created_at, updated_at
                    FROM inpatient_lab_results 
                    WHERE investigation_id = :investigation_id
                    LIMIT 1
                """),
                {"investigation_id": investigation_id}
            ).first()
            
            if not result_row:
                logger.info(f"No IPD lab result found for investigation {investigation_id}, returning None")
                return None
            
            # Build result dict from raw query
            entered_user = db.query(User).filter(User.id == result_row.entered_by).first()
            updated_user = db.query(User).filter(User.id == result_row.updated_by).first() if result_row.updated_by else None
            
            result_dict = {
                "id": result_row.id,
                "investigation_id": result_row.investigation_id,
                "template_id": None,  # Column doesn't exist in database
                "results_text": result_row.results_text,
                "template_data": result_row.template_data,
                "attachment_path": result_row.attachment_path,
                "entered_by": result_row.entered_by,
                "updated_by": result_row.updated_by,
                "created_at": result_row.created_at,
                "updated_at": result_row.updated_at,
                "entered_by_name": entered_user.full_name if entered_user else None,
                "updated_by_name": updated_user.full_name if updated_user else None,
            }
            return LabResultResponse(**result_dict)
    
    # Not an IPD investigation - check OPD
    logger.info(f"Investigation {investigation_id} is not IPD, checking OPD")
    opd_investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not opd_investigation:
        logger.info(f"No OPD investigation found for {investigation_id}, returning None")
        return None
    
    if opd_investigation.investigation_type != "lab":
        logger.info(f"OPD investigation {investigation_id} is not a lab investigation, returning None")
        return None
    
    # Query OPD LabResult table
    result = db.query(LabResult).filter(LabResult.investigation_id == investigation_id).first()
    
    if not result:
        logger.info(f"No OPD lab result found for investigation {investigation_id}, returning None")
        return None
    
    logger.info(f"Found OPD lab result for investigation {investigation_id}")
    # Get user names
    entered_user = db.query(User).filter(User.id == result.entered_by).first()
    updated_user = db.query(User).filter(User.id == result.updated_by).first() if result.updated_by else None
    
    result_dict = {
        "id": result.id,
        "investigation_id": result.investigation_id,
        "template_id": result.template_id,
        "results_text": result.results_text,
        "template_data": result.template_data,
        "attachment_path": result.attachment_path,
        "entered_by": result.entered_by,
        "updated_by": result.updated_by,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "entered_by_name": entered_user.full_name if entered_user else None,
        "updated_by_name": updated_user.full_name if updated_user else None,
    }
    return LabResultResponse(**result_dict)


@router.get("/lab-result/investigation/{investigation_id}/template")
def get_lab_result_template_for_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get the active template for a lab investigation's procedure name"""
    from app.models.inpatient_investigation import InpatientInvestigation
    from app.models.lab_result_template import LabResultTemplate
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        investigation = ipd_investigation
    else:
        investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.investigation_type != "lab":
        return None
    
    # Get template for this procedure name
    if not investigation.procedure_name:
        return None
    
    template = db.query(LabResultTemplate).filter(
        LabResultTemplate.procedure_name == investigation.procedure_name,
        LabResultTemplate.is_active == 1
    ).first()
    
    if not template:
        return None
    
    # Get user names
    created_user = db.query(User).filter(User.id == template.created_by).first()
    updated_user = db.query(User).filter(User.id == template.updated_by).first() if template.updated_by else None
    
    return {
        "id": template.id,
        "g_drg_code": template.g_drg_code,
        "procedure_name": template.procedure_name,
        "template_name": template.template_name,
        "template_structure": template.template_structure,
        "created_by": template.created_by,
        "updated_by": template.updated_by,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
        "is_active": template.is_active,
        "created_by_name": created_user.full_name if created_user else None,
        "updated_by_name": updated_user.full_name if updated_user else None,
    }


@router.get("/lab-result/{investigation_id}/download")
def download_lab_result_attachment(
    investigation_id: int,
    view: bool = Query(False, description="If true, open in browser instead of downloading"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download or view lab result attachment file"""
    import os
    import mimetypes
    from pathlib import Path
    
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        # Use InpatientLabResult for IPD
        result = db.query(InpatientLabResult).filter(InpatientLabResult.investigation_id == investigation_id).first()
    else:
        # Use LabResult for OPD
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
    
    # Use inline for PDFs and images when viewing, attachment for others or when downloading
    is_pdf_or_image = mime_type.startswith('image/') or mime_type == 'application/pdf'
    disposition = 'inline' if (view and is_pdf_or_image) else 'attachment'
    
    return Response(
        content=file_content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Content-Length": str(len(file_content))
        }
    )


@router.delete("/lab-result/{investigation_id}/attachment")
def delete_lab_result_attachment(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Lab Head", "Admin"]))
):
    """Delete lab result attachment"""
    from pathlib import Path
    
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        # Use InpatientLabResult for IPD
        result = db.query(InpatientLabResult).filter(InpatientLabResult.investigation_id == investigation_id).first()
    else:
        # Use LabResult for OPD
        result = db.query(LabResult).filter(LabResult.investigation_id == investigation_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Lab result not found")
    
    if not result.attachment_path:
        raise HTTPException(status_code=404, detail="No attachment found for this lab result")
    
    # Delete the physical file
    file_path = Path("uploads") / result.attachment_path
    if file_path.exists():
        file_path.unlink()
    
    # Update the result
    result.attachment_path = None
    result.updated_by = current_user.id
    result.updated_at = utcnow()
    
    db.commit()
    db.refresh(result)
    
    return {"message": "Attachment deleted successfully", "investigation_id": investigation_id}


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
    attachments: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Scan", "Scan Head", "Admin"]))
):
    """Create or update scan result with optional file attachment"""
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Ensure investigation_id is an integer
    try:
        investigation_id = int(investigation_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid investigation_id type: {type(investigation_id)}, value: {investigation_id}")
        raise HTTPException(status_code=400, detail=f"Invalid investigation ID: {investigation_id}")
    
    logger.info(f"Creating scan result for investigation_id: {investigation_id} (type: {type(investigation_id)})")
    
    investigation = None
    is_inpatient = False
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        logger.info(f"Found IPD investigation {investigation_id}, type: {ipd_investigation.investigation_type}")
        investigation = ipd_investigation
        is_inpatient = True
    else:
        # Not IPD, check OPD
        logger.info(f"Investigation {investigation_id} not found in IPD, checking OPD")
        investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if not investigation:
            logger.error(f"Investigation {investigation_id} not found in both IPD and OPD tables")
            raise HTTPException(status_code=404, detail=f"Investigation not found: {investigation_id}")
    
    if investigation.investigation_type != "scan":
        raise HTTPException(status_code=400, detail="This endpoint is only for scan investigations")
    
    # If investigation is completed, only Admin and Scan Head can edit
    if is_inpatient:
        from app.models.inpatient_investigation import InpatientInvestigationStatus
        if investigation.status == InpatientInvestigationStatus.COMPLETED.value:
            if current_user.role not in ["Admin", "Scan Head"]:
                raise HTTPException(
                    status_code=403,
                    detail="Only Admin and Scan Head can edit completed investigations. Please contact Scan Head to revert the status."
                )
    else:
        if investigation.status == InvestigationStatus.COMPLETED.value:
            if current_user.role not in ["Admin", "Scan Head"]:
                raise HTTPException(
                    status_code=403,
                    detail="Only Admin and Scan Head can edit completed investigations. Please contact Scan Head to revert the status."
                )
    
    # Handle multiple file uploads
    import os
    import uuid
    import json
    from pathlib import Path
    
    uploaded_paths = []
    if attachments:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/scan_results")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each uploaded file
        for attachment in attachments:
            if attachment:
                # Preserve original filename, but sanitize it and handle conflicts
                original_filename = attachment.filename or "unnamed_file.pdf"
                # Sanitize filename: remove path components and keep only safe characters
                safe_filename = Path(original_filename).name
                # Replace spaces and special chars that might cause issues
                safe_filename = safe_filename.replace(' ', '_')
                
                # Check if file already exists and add number suffix if needed
                base_name = Path(safe_filename).stem
                file_ext = Path(safe_filename).suffix or ".pdf"
                file_name = safe_filename
                counter = 1
                while (upload_dir / file_name).exists():
                    file_name = f"{base_name}_{counter}{file_ext}"
                    counter += 1
                
                file_path = upload_dir / file_name
                
                # Save file - UploadFile.read() returns bytes
                content = await attachment.read()
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                
                # Store relative path for serving (with original filename preserved)
                uploaded_paths.append(f"scan_results/{file_name}")
    
    # Determine final attachment_path (JSON array or None)
    attachment_path = json.dumps(uploaded_paths) if uploaded_paths else None
    
    # Handle IPD and OPD investigations separately due to FK constraints
    if is_inpatient:
        # Use InpatientScanResult for IPD investigations
        existing_result = db.query(InpatientScanResult).filter(InpatientScanResult.investigation_id == investigation_id).first()
    else:
        # Use ScanResult for OPD investigations
        existing_result = db.query(ScanResult).filter(ScanResult.investigation_id == investigation_id).first()
    
    if existing_result:
        # Update existing result
        existing_result.results_text = results_text
        if uploaded_paths:
            # Merge with existing attachments
            existing_attachments = []
            if existing_result.attachment_path:
                try:
                    existing_attachments = json.loads(existing_result.attachment_path)
                    if not isinstance(existing_attachments, list):
                        existing_attachments = [existing_result.attachment_path]
                except:
                    # If not JSON, treat as single attachment
                    existing_attachments = [existing_result.attachment_path]
            # Combine existing and new attachments
            all_attachments = existing_attachments + uploaded_paths
            existing_result.attachment_path = json.dumps(all_attachments)
        existing_result.updated_by = current_user.id  # Track who updated
        existing_result.updated_at = utcnow()
        
        # Mark investigation as completed if results are entered
        if results_text or uploaded_paths:
            if is_inpatient:
                from app.models.inpatient_investigation import InpatientInvestigationStatus
                investigation.status = InpatientInvestigationStatus.COMPLETED.value
            else:
                investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session
            db.add(investigation)
    else:
        # Create new result
        if is_inpatient:
            scan_result = InpatientScanResult(
                investigation_id=investigation_id,
                results_text=results_text,
                attachment_path=attachment_path,
                entered_by=current_user.id
            )
        else:
            scan_result = ScanResult(
                investigation_id=investigation_id,
                results_text=results_text,
                attachment_path=attachment_path,
                entered_by=current_user.id
            )
        db.add(scan_result)
        
        # Mark investigation as completed if results are entered
        if results_text or uploaded_paths:
            if is_inpatient:
                from app.models.inpatient_investigation import InpatientInvestigationStatus
                investigation.status = InpatientInvestigationStatus.COMPLETED.value
            else:
                investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session
            db.add(investigation)
    
    db.commit()
    # Refresh investigation to ensure status and completed_by are updated
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
    """Get scan result for an investigation (supports both OPD and IPD investigations)"""
    # IMPORTANT: Check if this is an IPD investigation FIRST
    from app.models.inpatient_investigation import InpatientInvestigation
    import logging
    
    logger = logging.getLogger(__name__)
    
    # ALWAYS check IPD first to prevent ID collision issues
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    
    if ipd_investigation:
        logger.info(f"Found IPD investigation {investigation_id}, type: {ipd_investigation.investigation_type}")
        # This is definitely an IPD investigation - ONLY query InpatientScanResult table
        if ipd_investigation.investigation_type != "scan":
            logger.info(f"IPD investigation {investigation_id} is not a scan investigation, returning None")
            return None
        
        result = db.query(InpatientScanResult).filter(InpatientScanResult.investigation_id == investigation_id).first()
        
        if not result:
            logger.info(f"No IPD scan result found for investigation {investigation_id}, returning None")
            return None
        
        logger.info(f"Found IPD scan result for investigation {investigation_id}")
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
        return ScanResultResponse(**result_dict)
    
    # Not an IPD investigation - check OPD
    logger.info(f"Investigation {investigation_id} is not IPD, checking OPD")
    opd_investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not opd_investigation:
        logger.info(f"No OPD investigation found for {investigation_id}, returning None")
        return None
    
    if opd_investigation.investigation_type != "scan":
        logger.info(f"OPD investigation {investigation_id} is not a scan investigation, returning None")
        return None
    
    # Query OPD ScanResult table
    result = db.query(ScanResult).filter(ScanResult.investigation_id == investigation_id).first()
    
    if not result:
        logger.info(f"No OPD scan result found for investigation {investigation_id}, returning None")
        return None
    
    logger.info(f"Found OPD scan result for investigation {investigation_id}")
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
    return ScanResultResponse(**result_dict)


@router.get("/scan-result/{investigation_id}/download")
def download_scan_result_attachment(
    investigation_id: int,
    attachment_path: Optional[str] = Query(None),
    view: bool = Query(False, description="If true, open in browser instead of downloading"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download scan result attachment file"""
    import mimetypes
    import json
    from pathlib import Path
    
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        # Use InpatientScanResult for IPD
        result = db.query(InpatientScanResult).filter(InpatientScanResult.investigation_id == investigation_id).first()
    else:
        # Use ScanResult for OPD
        result = db.query(ScanResult).filter(ScanResult.investigation_id == investigation_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Scan result not found")
    
    if not result.attachment_path:
        raise HTTPException(status_code=404, detail="No attachment found for this scan result")
    
    # Parse attachment_path (can be JSON array or single string)
    attachment_paths = []
    try:
        parsed = json.loads(result.attachment_path)
        attachment_paths = parsed if isinstance(parsed, list) else [result.attachment_path]
    except:
        attachment_paths = [result.attachment_path]
    
    # Use provided attachment_path or first one
    target_path = attachment_path if attachment_path and attachment_path in attachment_paths else attachment_paths[0]
    
    # Build full file path
    file_path = Path("uploads") / target_path
    
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
    
    # Use inline for PDFs and images when viewing, attachment for others or when downloading
    is_pdf_or_image = mime_type.startswith('image/') or mime_type == 'application/pdf'
    disposition = 'inline' if (view and is_pdf_or_image) else 'attachment'
    
    return Response(
        content=file_content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Content-Length": str(len(file_content))
        }
    )


@router.delete("/scan-result/{investigation_id}/attachment")
def delete_scan_result_attachment(
    investigation_id: int,
    attachment_path: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Scan", "Scan Head", "Admin"]))
):
    """Delete a specific attachment from scan result"""
    import json
    from pathlib import Path
    
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        # Use InpatientScanResult for IPD
        result = db.query(InpatientScanResult).filter(InpatientScanResult.investigation_id == investigation_id).first()
    else:
        # Use ScanResult for OPD
        result = db.query(ScanResult).filter(ScanResult.investigation_id == investigation_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="Scan result not found")
    
    if not result.attachment_path:
        raise HTTPException(status_code=404, detail="No attachments found")
    
    # Parse attachment_path (can be JSON array or single string)
    attachment_paths = []
    try:
        parsed = json.loads(result.attachment_path)
        attachment_paths = parsed if isinstance(parsed, list) else [result.attachment_path]
    except:
        attachment_paths = [result.attachment_path]
    
    # Remove the specified attachment
    if attachment_path not in attachment_paths:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    attachment_paths.remove(attachment_path)
    
    # Delete the physical file
    file_path = Path("uploads") / attachment_path
    if file_path.exists():
        file_path.unlink()
    
    # Update the result
    if len(attachment_paths) == 0:
        result.attachment_path = None
    else:
        result.attachment_path = json.dumps(attachment_paths)
    
    result.updated_by = current_user.id
    result.updated_at = utcnow()
    db.commit()
    
    return {"message": "Attachment deleted successfully"}


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
    attachments: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Xray", "Xray Head", "Admin"]))
):
    """Create or update x-ray result with optional file attachment"""
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Ensure investigation_id is an integer
    try:
        investigation_id = int(investigation_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid investigation_id type: {type(investigation_id)}, value: {investigation_id}")
        raise HTTPException(status_code=400, detail=f"Invalid investigation ID: {investigation_id}")
    
    logger.info(f"Creating xray result for investigation_id: {investigation_id} (type: {type(investigation_id)})")
    
    investigation = None
    is_inpatient = False
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        logger.info(f"Found IPD investigation {investigation_id}, type: {ipd_investigation.investigation_type}")
        investigation = ipd_investigation
        is_inpatient = True
    else:
        # Not IPD, check OPD
        logger.info(f"Investigation {investigation_id} not found in IPD, checking OPD")
        investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
        if not investigation:
            logger.error(f"Investigation {investigation_id} not found in both IPD and OPD tables")
            raise HTTPException(status_code=404, detail=f"Investigation not found: {investigation_id}")
    
    if investigation.investigation_type != "xray":
        raise HTTPException(status_code=400, detail="This endpoint is only for x-ray investigations")
    
    # If investigation is completed, only Admin and Xray Head can edit
    if is_inpatient:
        from app.models.inpatient_investigation import InpatientInvestigationStatus
        if investigation.status == InpatientInvestigationStatus.COMPLETED.value:
            if current_user.role not in ["Admin", "Xray Head"]:
                raise HTTPException(
                    status_code=403,
                    detail="Only Admin and Xray Head can edit completed investigations. Please contact Xray Head to revert the status."
                )
    else:
        if investigation.status == InvestigationStatus.COMPLETED.value:
            if current_user.role not in ["Admin", "Xray Head"]:
                raise HTTPException(
                    status_code=403,
                    detail="Only Admin and Xray Head can edit completed investigations. Please contact Xray Head to revert the status."
                )
    
    # Handle multiple file uploads
    import os
    import uuid
    import json
    from pathlib import Path
    
    uploaded_paths = []
    if attachments:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/xray_results")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each uploaded file
        for attachment in attachments:
            if attachment:
                # Preserve original filename, but sanitize it and handle conflicts
                original_filename = attachment.filename or "unnamed_file.pdf"
                # Sanitize filename: remove path components and keep only safe characters
                safe_filename = Path(original_filename).name
                # Replace spaces and special chars that might cause issues
                safe_filename = safe_filename.replace(' ', '_')
                
                # Check if file already exists and add number suffix if needed
                base_name = Path(safe_filename).stem
                file_ext = Path(safe_filename).suffix or ".pdf"
                file_name = safe_filename
                counter = 1
                while (upload_dir / file_name).exists():
                    file_name = f"{base_name}_{counter}{file_ext}"
                    counter += 1
                
                file_path = upload_dir / file_name
                
                # Save file - UploadFile.read() returns bytes
                content = await attachment.read()
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                
                # Store relative path for serving (with original filename preserved)
                uploaded_paths.append(f"xray_results/{file_name}")
    
    # Determine final attachment_path (JSON array or None)
    attachment_path = json.dumps(uploaded_paths) if uploaded_paths else None
    
    # Handle IPD and OPD investigations separately due to FK constraints
    if is_inpatient:
        # Use InpatientXrayResult for IPD investigations
        existing_result = db.query(InpatientXrayResult).filter(InpatientXrayResult.investigation_id == investigation_id).first()
    else:
        # Use XrayResult for OPD investigations
        existing_result = db.query(XrayResult).filter(XrayResult.investigation_id == investigation_id).first()
    
    if existing_result:
        # Update existing result
        existing_result.results_text = results_text
        if uploaded_paths:
            # Merge with existing attachments
            existing_attachments = []
            if existing_result.attachment_path:
                try:
                    existing_attachments = json.loads(existing_result.attachment_path)
                    if not isinstance(existing_attachments, list):
                        existing_attachments = [existing_result.attachment_path]
                except:
                    # If not JSON, treat as single attachment
                    existing_attachments = [existing_result.attachment_path]
            # Combine existing and new attachments
            all_attachments = existing_attachments + uploaded_paths
            existing_result.attachment_path = json.dumps(all_attachments)
        existing_result.updated_by = current_user.id  # Track who updated
        existing_result.updated_at = utcnow()
        
        # Mark investigation as completed if results are entered
        if results_text or uploaded_paths:
            if is_inpatient:
                from app.models.inpatient_investigation import InpatientInvestigationStatus
                investigation.status = InpatientInvestigationStatus.COMPLETED.value
            else:
                investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session
            db.add(investigation)
    else:
        # Create new result
        if is_inpatient:
            xray_result = InpatientXrayResult(
                investigation_id=investigation_id,
                results_text=results_text,
                attachment_path=attachment_path,
                entered_by=current_user.id
            )
        else:
            xray_result = XrayResult(
                investigation_id=investigation_id,
                results_text=results_text,
                attachment_path=attachment_path,
                entered_by=current_user.id
            )
        db.add(xray_result)
        
        # Mark investigation as completed if results are entered
        if results_text or uploaded_paths:
            if is_inpatient:
                from app.models.inpatient_investigation import InpatientInvestigationStatus
                investigation.status = InpatientInvestigationStatus.COMPLETED.value
            else:
                investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_by = current_user.id  # Track who completed
            # Ensure investigation is in session
            db.add(investigation)
    
    db.commit()
    # Refresh investigation to ensure status and completed_by are updated
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
    """Get x-ray result for an investigation (supports both OPD and IPD investigations)"""
    # IMPORTANT: Check if this is an IPD investigation FIRST
    from app.models.inpatient_investigation import InpatientInvestigation
    import logging
    
    logger = logging.getLogger(__name__)
    
    # ALWAYS check IPD first to prevent ID collision issues
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    
    if ipd_investigation:
        logger.info(f"Found IPD investigation {investigation_id}, type: {ipd_investigation.investigation_type}")
        # This is definitely an IPD investigation - ONLY query InpatientXrayResult table
        if ipd_investigation.investigation_type != "xray":
            logger.info(f"IPD investigation {investigation_id} is not an xray investigation, returning None")
            return None
        
        result = db.query(InpatientXrayResult).filter(InpatientXrayResult.investigation_id == investigation_id).first()
        
        if not result:
            logger.info(f"No IPD xray result found for investigation {investigation_id}, returning None")
            return None
        
        logger.info(f"Found IPD xray result for investigation {investigation_id}")
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
        return XrayResultResponse(**result_dict)
    
    # Not an IPD investigation - check OPD
    logger.info(f"Investigation {investigation_id} is not IPD, checking OPD")
    opd_investigation = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not opd_investigation:
        logger.info(f"No OPD investigation found for {investigation_id}, returning None")
        return None
    
    if opd_investigation.investigation_type != "xray":
        logger.info(f"OPD investigation {investigation_id} is not an xray investigation, returning None")
        return None
    
    # Query OPD XrayResult table
    result = db.query(XrayResult).filter(XrayResult.investigation_id == investigation_id).first()
    
    if not result:
        logger.info(f"No OPD xray result found for investigation {investigation_id}, returning None")
        return None
    
    logger.info(f"Found OPD xray result for investigation {investigation_id}")
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
    return XrayResultResponse(**result_dict)


@router.get("/xray-result/{investigation_id}/download")
def download_xray_result_attachment(
    investigation_id: int,
    attachment_path: Optional[str] = Query(None),
    view: bool = Query(False, description="If true, open in browser instead of downloading"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download x-ray result attachment file"""
    import mimetypes
    import json
    from pathlib import Path
    
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        # Use InpatientXrayResult for IPD
        result = db.query(InpatientXrayResult).filter(InpatientXrayResult.investigation_id == investigation_id).first()
    else:
        # Use XrayResult for OPD
        result = db.query(XrayResult).filter(XrayResult.investigation_id == investigation_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="X-ray result not found")
    
    if not result.attachment_path:
        raise HTTPException(status_code=404, detail="No attachment found for this x-ray result")
    
    # Parse attachment_path (can be JSON array or single string)
    attachment_paths = []
    try:
        parsed = json.loads(result.attachment_path)
        attachment_paths = parsed if isinstance(parsed, list) else [result.attachment_path]
    except:
        attachment_paths = [result.attachment_path]
    
    # Use provided attachment_path or first one
    target_path = attachment_path if attachment_path and attachment_path in attachment_paths else attachment_paths[0]
    
    # Build full file path
    file_path = Path("uploads") / target_path
    
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
    
    # Use inline for PDFs and images when viewing, attachment for others or when downloading
    is_pdf_or_image = mime_type.startswith('image/') or mime_type == 'application/pdf'
    disposition = 'inline' if (view and is_pdf_or_image) else 'attachment'
    
    return Response(
        content=file_content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
            "Content-Length": str(len(file_content))
        }
    )


@router.delete("/xray-result/{investigation_id}/attachment")
def delete_xray_result_attachment(
    investigation_id: int,
    attachment_path: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Xray", "Xray Head", "Admin"]))
):
    """Delete a specific attachment from xray result"""
    import json
    from pathlib import Path
    
    # IMPORTANT: Check IPD FIRST to prevent ID collision issues
    from app.models.inpatient_investigation import InpatientInvestigation
    
    # Check IPD first
    ipd_investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if ipd_investigation:
        # Use InpatientXrayResult for IPD
        result = db.query(InpatientXrayResult).filter(InpatientXrayResult.investigation_id == investigation_id).first()
    else:
        # Use XrayResult for OPD
        result = db.query(XrayResult).filter(XrayResult.investigation_id == investigation_id).first()
    
    if not result:
        raise HTTPException(status_code=404, detail="X-ray result not found")
    
    if not result.attachment_path:
        raise HTTPException(status_code=404, detail="No attachments found")
    
    # Parse attachment_path (can be JSON array or single string)
    attachment_paths = []
    try:
        parsed = json.loads(result.attachment_path)
        attachment_paths = parsed if isinstance(parsed, list) else [result.attachment_path]
    except:
        attachment_paths = [result.attachment_path]
    
    # Remove the specified attachment
    if attachment_path not in attachment_paths:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    attachment_paths.remove(attachment_path)
    
    # Delete the physical file
    file_path = Path("uploads") / attachment_path
    if file_path.exists():
        file_path.unlink()
    
    # Update the result
    if len(attachment_paths) == 0:
        result.attachment_path = None
    else:
        result.attachment_path = json.dumps(attachment_paths)
    
    result.updated_by = current_user.id
    result.updated_at = utcnow()
    db.commit()
    
    return {"message": "Attachment deleted successfully"}


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
        existing_notes.updated_at = utcnow()
        # Initialize final_encounter_id to the current encounter_id (will be updated if new encounter is created)
        final_encounter_id = notes_data.encounter_id
        # Handle admission recommendation
        admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.encounter_id == notes_data.encounter_id).first()
        if notes_data.outcome == "recommended_for_admission" and notes_data.admission_ward:
            if admission:
                # If admission exists and is cancelled, delete it completely and create a new one
                if admission.cancelled == 1:
                    # Delete any related ward admission first (if exists)
                    from app.models.ward_admission import WardAdmission
                    from app.models.treatment_sheet_administration import TreatmentSheetAdministration
                    from app.models.bill import Bill, BillItem
                    ward_admission = db.query(WardAdmission).filter(
                        WardAdmission.admission_recommendation_id == admission.id
                    ).first()
                    if ward_admission:
                        # Delete treatment sheet administrations first
                        treatment_administrations = db.query(TreatmentSheetAdministration).filter(
                            TreatmentSheetAdministration.ward_admission_id == ward_admission.id
                        ).all()
                        for admin in treatment_administrations:
                            db.delete(admin)
                        db.delete(ward_admission)
                    
                    # Get patient_id from the old encounter before deleting
                    old_encounter = db.query(Encounter).filter(Encounter.id == notes_data.encounter_id).first()
                    patient_id = old_encounter.patient_id if old_encounter else None
                    ccc_number = old_encounter.ccc_number if old_encounter else None
                    
                    # Delete any unpaid bills from the cancelled admission's encounter
                    # This ensures a fresh bill is created for readmission
                    unpaid_bills = db.query(Bill).filter(
                        Bill.encounter_id == notes_data.encounter_id,
                        Bill.is_paid == False
                    ).all()
                    for bill in unpaid_bills:
                        # Delete bill items first
                        bill_items = db.query(BillItem).filter(BillItem.bill_id == bill.id).all()
                        for item in bill_items:
                            db.delete(item)
                        db.delete(bill)
                    
                    # Delete the cancelled admission recommendation
                    db.delete(admission)
                    db.flush()
                    
                    # Create a new encounter for this IPD admission (not reusing old OPD encounter)
                    new_encounter = Encounter(
                        patient_id=patient_id,
                        department=notes_data.admission_ward,  # Use ward as department for IPD
                        status=EncounterStatus.IN_CONSULTATION.value,
                        ccc_number=ccc_number,
                        created_by=current_user.id
                    )
                    db.add(new_encounter)
                    db.flush()  # Get the new encounter ID
                    
                    # Create new admission recommendation with new encounter
                    admission = AdmissionRecommendation(
                        encounter_id=new_encounter.id,
                        ward=notes_data.admission_ward,
                        recommended_by=current_user.id
                    )
                    db.add(admission)
                    # Update consultation notes to point to new encounter
                    existing_notes.encounter_id = new_encounter.id
                    # Store new encounter_id for response query
                    final_encounter_id = new_encounter.id
                else:
                    # Update existing non-cancelled admission
                    admission.ward = notes_data.admission_ward
                    admission.recommended_by = current_user.id
                    admission.updated_at = utcnow()
                    final_encounter_id = notes_data.encounter_id
            else:
                admission = AdmissionRecommendation(
                    encounter_id=notes_data.encounter_id,
                    ward=notes_data.admission_ward,
                    recommended_by=current_user.id
                )
                db.add(admission)
                final_encounter_id = notes_data.encounter_id
        else:
            # If outcome changed away from admission, remove admission record if exists
            if admission:
                db.delete(admission)
            final_encounter_id = notes_data.encounter_id
        db.commit()
        db.refresh(existing_notes)
        # Serialize response properly - use the final encounter_id (may be new or old)
        admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.encounter_id == final_encounter_id).first() if notes_data.outcome == "recommended_for_admission" else None
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
        # Initialize final_encounter_id to the current encounter_id (will be updated if new encounter is created)
        final_encounter_id = notes_data.encounter_id
        # Create admission recommendation if applicable
        if notes_data.outcome == "recommended_for_admission" and notes_data.admission_ward:
            # Check if there's an existing admission recommendation for this encounter
            existing_admission = db.query(AdmissionRecommendation).filter(
                AdmissionRecommendation.encounter_id == notes_data.encounter_id
            ).first()
            
            if existing_admission:
                # If cancelled, delete it completely and create a new one
                if existing_admission.cancelled == 1:
                    # Delete any related ward admission first (if exists)
                    from app.models.ward_admission import WardAdmission
                    from app.models.treatment_sheet_administration import TreatmentSheetAdministration
                    from app.models.bill import Bill, BillItem
                    ward_admission = db.query(WardAdmission).filter(
                        WardAdmission.admission_recommendation_id == existing_admission.id
                    ).first()
                    if ward_admission:
                        # Delete treatment sheet administrations first
                        treatment_administrations = db.query(TreatmentSheetAdministration).filter(
                            TreatmentSheetAdministration.ward_admission_id == ward_admission.id
                        ).all()
                        for admin in treatment_administrations:
                            db.delete(admin)
                        db.delete(ward_admission)
                    
                    # Get patient_id from the old encounter before deleting
                    old_encounter = db.query(Encounter).filter(Encounter.id == notes_data.encounter_id).first()
                    patient_id = old_encounter.patient_id if old_encounter else None
                    ccc_number = old_encounter.ccc_number if old_encounter else None
                    
                    # If old encounter doesn't have CCC, look for OPD encounter with CCC for same patient today
                    # This allows IPD encounters to inherit CCC from OPD encounters
                    if not ccc_number and patient_id:
                        from sqlalchemy import func
                        from app.models.ward_admission import WardAdmission
                        # Get all ward admission encounter IDs to exclude IPD encounters
                        ward_admission_encounter_ids = [wa[0] for wa in db.query(WardAdmission.encounter_id).filter(
                            WardAdmission.encounter_id.isnot(None)
                        ).all()]
                        
                        # Find OPD encounter with CCC for same patient today
                        opd_query = db.query(Encounter).filter(
                            Encounter.patient_id == patient_id,
                            Encounter.id != notes_data.encounter_id,  # Different encounter
                            Encounter.archived == False,
                            Encounter.ccc_number.isnot(None),
                            Encounter.ccc_number != "",
                            func.date(Encounter.created_at) == today()
                        )
                        
                        # Exclude IPD encounters (those with ward admissions)
                        if ward_admission_encounter_ids:
                            opd_query = opd_query.filter(~Encounter.id.in_(ward_admission_encounter_ids))
                        
                        opd_encounter_with_ccc = opd_query.first()
                        
                        if opd_encounter_with_ccc and opd_encounter_with_ccc.ccc_number:
                            ccc_number = opd_encounter_with_ccc.ccc_number
                    
                    # Delete any unpaid bills from the cancelled admission's encounter
                    # This ensures a fresh bill is created for readmission
                    unpaid_bills = db.query(Bill).filter(
                        Bill.encounter_id == notes_data.encounter_id,
                        Bill.is_paid == False
                    ).all()
                    for bill in unpaid_bills:
                        # Delete bill items first
                        bill_items = db.query(BillItem).filter(BillItem.bill_id == bill.id).all()
                        for item in bill_items:
                            db.delete(item)
                        db.delete(bill)
                    
                    # Delete the cancelled admission recommendation
                    db.delete(existing_admission)
                    db.flush()
                    
                    # Create a new encounter for this IPD admission (not reusing old OPD encounter)
                    new_encounter = Encounter(
                        patient_id=patient_id,
                        department=notes_data.admission_ward,  # Use ward as department for IPD
                        status=EncounterStatus.IN_CONSULTATION.value,
                        ccc_number=ccc_number,
                        created_by=current_user.id
                    )
                    db.add(new_encounter)
                    db.flush()  # Get the new encounter ID
                    
                    # Create new admission recommendation with new encounter
                    admission = AdmissionRecommendation(
                        encounter_id=new_encounter.id,
                        ward=notes_data.admission_ward,
                        recommended_by=current_user.id
                    )
                    db.add(admission)
                    # Update consultation notes to point to new encounter
                    notes.encounter_id = new_encounter.id
                    # Store new encounter_id for response query
                    final_encounter_id = new_encounter.id
                else:
                    # Update existing non-cancelled admission
                    existing_admission.ward = notes_data.admission_ward
                    existing_admission.recommended_by = current_user.id
                    existing_admission.updated_at = utcnow()
                    final_encounter_id = notes_data.encounter_id
            else:
                admission = AdmissionRecommendation(
                    encounter_id=notes_data.encounter_id,
                    ward=notes_data.admission_ward,
                    recommended_by=current_user.id
                )
                db.add(admission)
                final_encounter_id = notes_data.encounter_id
        db.commit()
        db.refresh(notes)
        # Serialize response properly - use the final encounter_id (may be new or old)
        admission = db.query(AdmissionRecommendation).filter(AdmissionRecommendation.encounter_id == final_encounter_id).first()
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


# Doctor Note Entry endpoints
class DoctorNoteEntryCreate(BaseModel):
    """Doctor note entry creation model"""
    encounter_id: int
    notes: str


class DoctorNoteEntryUpdate(BaseModel):
    """Doctor note entry update model"""
    notes: str


class DoctorNoteEntryResponse(BaseModel):
    """Doctor note entry response model"""
    id: int
    encounter_id: int
    notes: str
    created_by: int
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/encounters/{encounter_id}/doctor-notes", response_model=List[DoctorNoteEntryResponse])
def get_doctor_note_entries(
    encounter_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all doctor note entries for an encounter"""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    doctor_notes = db.query(DoctorNoteEntry).filter(
        DoctorNoteEntry.encounter_id == encounter_id
    ).order_by(DoctorNoteEntry.created_at.asc()).all()
    
    result = []
    for note in doctor_notes:
        creator = db.query(User).filter(User.id == note.created_by).first()
        result.append({
            "id": note.id,
            "encounter_id": note.encounter_id,
            "notes": note.notes,
            "created_by": note.created_by,
            "created_by_name": creator.full_name if creator else None,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
        })
    
    return result


@router.post("/encounters/{encounter_id}/doctor-notes", response_model=DoctorNoteEntryResponse, status_code=status.HTTP_201_CREATED)
def create_doctor_note_entry(
    encounter_id: int,
    note_data: DoctorNoteEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Create a new doctor note entry for an encounter"""
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Check if encounter is finalized - cannot add notes to finalized encounters
    if encounter.status == EncounterStatus.FINALIZED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot add doctor notes to a finalized consultation"
        )
    
    # Verify encounter_id matches
    if note_data.encounter_id != encounter_id:
        raise HTTPException(status_code=400, detail="Encounter ID mismatch")
    
    doctor_note = DoctorNoteEntry(
        encounter_id=encounter_id,
        notes=note_data.notes,
        created_by=current_user.id
    )
    
    db.add(doctor_note)
    db.commit()
    db.refresh(doctor_note)
    
    creator = db.query(User).filter(User.id == doctor_note.created_by).first()
    return {
        "id": doctor_note.id,
        "encounter_id": doctor_note.encounter_id,
        "notes": doctor_note.notes,
        "created_by": doctor_note.created_by,
        "created_by_name": creator.full_name if creator else None,
        "created_at": doctor_note.created_at,
        "updated_at": doctor_note.updated_at,
    }


@router.put("/doctor-notes/{note_id}", response_model=DoctorNoteEntryResponse)
def update_doctor_note_entry(
    note_id: int,
    note_data: DoctorNoteEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Records"]))
):
    """Update a doctor note entry (only by the creator)"""
    doctor_note = db.query(DoctorNoteEntry).filter(DoctorNoteEntry.id == note_id).first()
    if not doctor_note:
        raise HTTPException(status_code=404, detail="Doctor note entry not found")
    
    # Check if user is the creator (or admin)
    if doctor_note.created_by != current_user.id and current_user.role != "Admin":
        raise HTTPException(
            status_code=403,
            detail="You can only update your own doctor notes"
        )
    
    # Check if encounter is finalized
    encounter = db.query(Encounter).filter(Encounter.id == doctor_note.encounter_id).first()
    if encounter and encounter.status == EncounterStatus.FINALIZED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot update doctor notes for a finalized consultation"
        )
    
    doctor_note.notes = note_data.notes
    doctor_note.updated_at = utcnow()
    
    db.commit()
    db.refresh(doctor_note)
    
    creator = db.query(User).filter(User.id == doctor_note.created_by).first()
    return {
        "id": doctor_note.id,
        "encounter_id": doctor_note.encounter_id,
        "notes": doctor_note.notes,
        "created_by": doctor_note.created_by,
        "created_by_name": creator.full_name if creator else None,
        "created_at": doctor_note.created_at,
        "updated_at": doctor_note.updated_at,
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


def _create_ipd_admission_bill(db: Session, encounter, ccc_number: Optional[str], created_by: int):
    """
    Create automatic bill for IPD admission based on insurance status and surgery/diagnosis.
    
    Rules:
    - Insured clients: 50 cedis admission fee + surgery co-payment (if surgery exists)
    - Non-insured clients: 30 cedis admission fee + chief diagnosis (if no surgery) OR surgery base rate (if surgery exists)
    """
    from app.models.bill import Bill, BillItem
    from app.models.diagnosis import Diagnosis
    from app.services.price_list_service_v2 import get_price_from_all_tables
    import random
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Check if patient is insured (has CCC number)
        is_insured = ccc_number is not None and ccc_number.strip() != ""
        
        # Check if there's a surgery (procedure_g_drg_code exists)
        has_surgery = encounter.procedure_g_drg_code is not None and encounter.procedure_g_drg_code.strip() != ""
        
        logger.info(f"Creating IPD admission bill for encounter {encounter.id}, is_insured={is_insured}, has_surgery={has_surgery}")
        
        # Find or create an unpaid bill for this encounter
        # For readmissions (reused cancelled admissions), we want to ensure we use/create a bill
        # Check for any unpaid bill first, but if it's paid or doesn't exist, create a new one
        existing_bill = db.query(Bill).filter(
            Bill.encounter_id == encounter.id,
            Bill.is_paid == False
        ).first()
        
        if existing_bill:
            bill = existing_bill
            logger.info(f"Using existing unpaid bill {bill.id} with current total_amount={bill.total_amount}")
        else:
            # Check if there's a paid bill - if so, we'll still create a new unpaid bill for the readmission
            paid_bill = db.query(Bill).filter(
                Bill.encounter_id == encounter.id,
                Bill.is_paid == True
            ).first()
            if paid_bill:
                logger.info(f"Found paid bill {paid_bill.id} from previous admission, creating new bill for readmission")
            
            # Create new bill for this admission/readmission
            bill_number = f"BILL-{random.randint(100000, 999999)}"
            bill = Bill(
                encounter_id=encounter.id,
                bill_number=bill_number,
                is_insured=is_insured,
                total_amount=0.0,  # Explicitly initialize
                created_by=created_by
            )
            db.add(bill)
            db.flush()
            logger.info(f"Created new bill {bill.id} with bill_number={bill_number} for admission")
    
        # Add admission fee
        admission_fee = 50.0 if is_insured else 30.0
        
        # Check if admission fee item already exists
        existing_admission_fee = db.query(BillItem).filter(
            BillItem.bill_id == bill.id,
            BillItem.item_name.like("%Admission Fee%")
        ).first()
        
        if not existing_admission_fee:
            admission_fee_item = BillItem(
                bill_id=bill.id,
                item_code="IPD-ADM-FEE",
                item_name=f"IPD Admission Fee ({'Insured' if is_insured else 'Non-Insured'})",
                category="other",
                quantity=1,
                unit_price=admission_fee,
                total_price=admission_fee
            )
            db.add(admission_fee_item)
            bill.total_amount = (bill.total_amount or 0.0) + admission_fee
            logger.info(f"Added admission fee: {admission_fee}, new total_amount={bill.total_amount}")
        else:
            logger.info(f"Admission fee already exists, skipping")
    
        # Handle surgery or chief diagnosis
        if has_surgery:
            # Surgery case: Add surgery fee
            surgery_code = encounter.procedure_g_drg_code
            surgery_name = encounter.procedure_name or f"Surgery: {surgery_code}"
            
            # Check if surgery item already exists
            existing_surgery = db.query(BillItem).filter(
                BillItem.bill_id == bill.id,
                BillItem.item_code == surgery_code
            ).first()
            
            if not existing_surgery:
                # Get surgery price (co-payment for insured, base rate for non-insured)
                # Pass surgery_name as procedure_name to match exact surgery when G-DRG codes map to multiple procedures
                surgery_price = get_price_from_all_tables(
                    db, 
                    surgery_code, 
                    is_insured=is_insured,
                    service_type=encounter.department,
                    procedure_name=surgery_name
                )
                logger.info(f"Looked up surgery price for code='{surgery_code}', name='{surgery_name}', is_insured={is_insured}, service_type='{encounter.department}', price={surgery_price}")
                
                if surgery_price > 0:
                    surgery_item = BillItem(
                        bill_id=bill.id,
                        item_code=surgery_code,
                        item_name=f"Surgery: {surgery_name}",
                        category="surgery",
                        quantity=1,
                        unit_price=surgery_price,
                        total_price=surgery_price
                    )
                    db.add(surgery_item)
                    bill.total_amount = (bill.total_amount or 0.0) + surgery_price
                    logger.info(f"Added surgery fee: {surgery_price}, new total_amount={bill.total_amount}")
                else:
                    logger.warning(f"Surgery price is 0 for code='{surgery_code}', skipping")
            else:
                logger.info(f"Surgery item already exists, skipping")
        else:
            # No surgery: For non-insured, add chief diagnosis
            if not is_insured:
                # Find chief diagnosis
                chief_diagnosis = db.query(Diagnosis).filter(
                    Diagnosis.encounter_id == encounter.id,
                    Diagnosis.is_chief == True,
                    Diagnosis.gdrg_code.isnot(None),
                    Diagnosis.gdrg_code != ''
                ).first()
                
                if chief_diagnosis:
                    # Check if chief diagnosis item already exists
                    existing_diagnosis = db.query(BillItem).filter(
                        BillItem.bill_id == bill.id,
                        BillItem.item_code == chief_diagnosis.gdrg_code,
                        BillItem.category == "drg"
                    ).first()
                    
                    if not existing_diagnosis:
                        # Get diagnosis price (base rate for non-insured)
                        # Pass diagnosis name as procedure_name to match exact diagnosis when G-DRG codes map to multiple procedures
                        diagnosis_price = get_price_from_all_tables(
                            db,
                            chief_diagnosis.gdrg_code,
                            is_insured=False,
                            procedure_name=chief_diagnosis.diagnosis
                        )
                        logger.info(f"Looked up diagnosis price for code='{chief_diagnosis.gdrg_code}', name='{chief_diagnosis.diagnosis}', price={diagnosis_price}")
                        
                        if diagnosis_price > 0:
                            diagnosis_item = BillItem(
                                bill_id=bill.id,
                                item_code=chief_diagnosis.gdrg_code,
                                item_name=f"Diagnosis: {chief_diagnosis.diagnosis}",
                                category="drg",
                                quantity=1,
                                unit_price=diagnosis_price,
                                total_price=diagnosis_price
                            )
                            db.add(diagnosis_item)
                            bill.total_amount = (bill.total_amount or 0.0) + diagnosis_price
                            logger.info(f"Added diagnosis fee: {diagnosis_price}, new total_amount={bill.total_amount}")
                        else:
                            logger.warning(f"Diagnosis price is 0 for code='{chief_diagnosis.gdrg_code}', skipping")
                    else:
                        logger.info(f"Diagnosis item already exists, skipping")
                else:
                    logger.info(f"No chief diagnosis found for encounter {encounter.id}")
        
        # Ensure all items are flushed before recalculating
        db.flush()
        
        # Ensure bill total is correct by recalculating from items
        # This handles cases where bill might have been modified or items deleted
        # Query items again after flush to ensure we get all items
        bill_items = db.query(BillItem).filter(BillItem.bill_id == bill.id).all()
        calculated_total = sum(item.total_price for item in bill_items)
        bill.total_amount = calculated_total
        
        # Flush again to ensure total_amount is saved
        db.flush()
        
        # Refresh bill to ensure we have the latest state
        db.refresh(bill)
        
        logger.info(f"IPD admission bill created/updated successfully. Bill ID: {bill.id}, Total Amount: {bill.total_amount}, Items: {len(bill_items)}")
        print(f"DEBUG: IPD admission bill created/updated. Bill ID: {bill.id}, Total: {bill.total_amount}, Items: {len(bill_items)}")
        
        # Verify bill was actually created with items
        if bill.total_amount == 0 and len(bill_items) == 0:
            logger.warning(f"WARNING: Bill {bill.id} was created but has no items and total is 0!")
            print(f"WARNING: Bill {bill.id} was created but has no items and total is 0!")
        elif bill.total_amount == 0 and len(bill_items) > 0:
            logger.error(f"ERROR: Bill {bill.id} has {len(bill_items)} items but total_amount is 0! Items: {[(item.item_name, item.total_price) for item in bill_items]}")
            print(f"ERROR: Bill {bill.id} has {len(bill_items)} items but total_amount is 0! Items: {[(item.item_name, item.total_price) for item in bill_items]}")
            # Force recalculation one more time
            calculated_total = sum(item.total_price for item in bill_items)
            bill.total_amount = calculated_total
            db.flush()
            db.refresh(bill)
            logger.info(f"Force-recalculated bill {bill.id} total_amount to {bill.total_amount}")
            print(f"Force-recalculated bill {bill.id} total_amount to {bill.total_amount}")
        
    except Exception as e:
        logger.error(f"Error creating IPD admission bill for encounter {encounter.id}: {str(e)}", exc_info=True)
        print(f"ERROR in _create_ipd_admission_bill: {str(e)}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise to let caller handle it


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
    from app.models.encounter import EncounterStatus
    from sqlalchemy import func
    encounter = db.query(Encounter).filter(Encounter.id == admission.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Update encounter for IPD admission
    # Set status to IN_CONSULTATION for IPD
    if encounter.status != EncounterStatus.IN_CONSULTATION.value:
        encounter.status = EncounterStatus.IN_CONSULTATION.value
        encounter.updated_at = utcnow()
    
    # Update encounter department to match ward
    if encounter.department != admission.ward:
        encounter.department = admission.ward
        encounter.updated_at = utcnow()
    
    # Ensure encounter is not archived
    if encounter.archived:
        encounter.archived = False
        encounter.updated_at = utcnow()
    
    # For IPD confirmations from recommendations: if IPD encounter doesn't have CCC,
    # check if there's an OPD encounter with CCC for the same patient today and copy it
    # This allows the IPD encounter to be recognized as insured even though it's the second encounter
    ccc_to_use = form_data.ccc_number or encounter.ccc_number
    if not ccc_to_use and encounter.patient_id:
        # Look for an OPD encounter (not associated with a ward admission) with CCC for same patient today
        from app.models.ward_admission import WardAdmission
        # Get all ward admission encounter IDs to exclude IPD encounters
        ward_admission_encounter_ids = [wa[0] for wa in db.query(WardAdmission.encounter_id).filter(
            WardAdmission.encounter_id.isnot(None)
        ).all()]
        
        # Find OPD encounter with CCC for same patient today
        opd_query = db.query(Encounter).filter(
            Encounter.patient_id == encounter.patient_id,
            Encounter.id != encounter.id,  # Different encounter
            Encounter.archived == False,
            Encounter.ccc_number.isnot(None),
            Encounter.ccc_number != "",
            func.date(Encounter.created_at) == today()
        )
        
        # Exclude IPD encounters (those with ward admissions)
        if ward_admission_encounter_ids:
            opd_query = opd_query.filter(~Encounter.id.in_(ward_admission_encounter_ids))
        
        opd_encounter_with_ccc = opd_query.first()
        
        if opd_encounter_with_ccc and opd_encounter_with_ccc.ccc_number:
            # Copy CCC from OPD encounter to IPD encounter
            ccc_to_use = opd_encounter_with_ccc.ccc_number
            encounter.ccc_number = ccc_to_use
            encounter.updated_at = utcnow()
    
    # Update encounter CCC if provided in form
    if form_data.ccc_number and not encounter.ccc_number:
        encounter.ccc_number = form_data.ccc_number
        ccc_to_use = form_data.ccc_number
    
    # Update patient emergency contact if not already set
    patient = encounter.patient
    if patient:
        if not patient.emergency_contact_name:
            patient.emergency_contact_name = form_data.emergency_contact_name
            patient.emergency_contact_relationship = form_data.emergency_contact_relationship
            patient.emergency_contact_number = form_data.emergency_contact_number
    
    # Mark admission as confirmed
    admission.confirmed_by = current_user.id
    admission.confirmed_at = utcnow()
    admission.updated_at = utcnow()
    
    # Mark bed as occupied
    bed.is_occupied = True
    bed.updated_at = utcnow()
    
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
        admitted_at=utcnow()
    )
    db.add(ward_admission)
    db.flush()  # Flush to get ward_admission ID before committing
    
    # Auto-generate IPD admission bill
    import logging
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Attempting to create IPD admission bill for encounter {encounter.id}, CCC: {ccc_to_use}")
        print(f"DEBUG: About to call _create_ipd_admission_bill for encounter {encounter.id}")
        _create_ipd_admission_bill(db, encounter, ccc_to_use, current_user.id)
        db.flush()  # Ensure bill is saved before commit
        
        # Verify bill was created correctly after flush
        from app.models.bill import Bill
        created_bill = db.query(Bill).filter(Bill.encounter_id == encounter.id, Bill.is_paid == False).order_by(Bill.created_at.desc()).first()
        if created_bill:
            # Recalculate total one more time to ensure it's correct
            from app.models.bill import BillItem
            bill_items = db.query(BillItem).filter(BillItem.bill_id == created_bill.id).all()
            if bill_items:
                calculated_total = sum(item.total_price for item in bill_items)
                if created_bill.total_amount != calculated_total:
                    logger.warning(f"Bill {created_bill.id} total_amount mismatch: stored={created_bill.total_amount}, calculated={calculated_total}. Fixing...")
                    print(f"WARNING: Bill {created_bill.id} total_amount mismatch: stored={created_bill.total_amount}, calculated={calculated_total}. Fixing...")
                    created_bill.total_amount = calculated_total
                    db.flush()
        
        logger.info(f"Successfully created IPD admission bill for encounter {encounter.id}")
        print(f"DEBUG: Successfully created IPD admission bill for encounter {encounter.id}")
    except Exception as e:
        # Log error but don't fail admission confirmation
        logger.error(f"Failed to create IPD admission bill for encounter {encounter.id}: {str(e)}", exc_info=True)
        # Continue with admission confirmation even if bill creation fails
        # But log it so we can investigate
        # Also print to console for immediate visibility
        print(f"ERROR: Failed to create IPD admission bill for encounter {encounter.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        # Re-raise the exception so we can see what's happening
        # But only in development - in production we'll continue
        # raise  # Uncomment this to see the actual error
    
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
        # Delete all related treatment sheet administrations first (to avoid foreign key constraint)
        from app.models.treatment_sheet_administration import TreatmentSheetAdministration
        treatment_administrations = db.query(TreatmentSheetAdministration).filter(
            TreatmentSheetAdministration.ward_admission_id == ward_admission.id
        ).all()
        for admin in treatment_administrations:
            db.delete(admin)
        
        # Free up the bed
        if ward_admission.bed_id:
            from app.models.bed import Bed
            bed = db.query(Bed).filter(Bed.id == ward_admission.bed_id).first()
            if bed:
                bed.is_occupied = False
                bed.updated_at = utcnow()
        
        # Delete the ward admission record
        db.delete(ward_admission)
    
    # Revert confirmation status
    admission.confirmed_by = None
    admission.confirmed_at = None
    admission.updated_at = utcnow()
    
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
    bed_id: Optional[int] = None
    bed_number: Optional[str] = None
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = None
    doctor_username: Optional[str] = None
    admitted_by: int
    admitted_at: datetime
    discharged_at: Optional[datetime] = None
    discharged_by: Optional[int] = None
    discharge_outcome: Optional[str] = None
    discharge_condition: Optional[str] = None
    partially_discharged_at: Optional[datetime] = None
    partially_discharged_by: Optional[int] = None
    final_orders: Optional[str] = None
    
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
                if ward_admission.bed_id:
                    if ward_admission.bed:
                        bed_number = ward_admission.bed.bed_number
                        print(f"DEBUG get_ward_admissions: Ward admission {ward_admission.id} has bed_id={ward_admission.bed_id}, bed_number={bed_number}")
                    else:
                        print(f"DEBUG get_ward_admissions: Ward admission {ward_admission.id} has bed_id={ward_admission.bed_id} but bed relationship is None")
                else:
                    print(f"DEBUG get_ward_admissions: Ward admission {ward_admission.id} has no bed_id")
                
                # Get doctor information (doctor under whose care)
                doctor_id = ward_admission.doctor_id
                doctor_name = None
                doctor_username = None
                if doctor_id:
                    doctor_user = db.query(User).filter(User.id == doctor_id).first()
                    if doctor_user:
                        doctor_name = doctor_user.full_name
                        doctor_username = doctor_user.username
                
                # Debug log for emergency contact
                print(f"Ward admission {ward_admission.id} - Patient {patient.card_number}: emergency_contact_name={emergency_contact_name}, relationship={emergency_contact_relationship}, number={emergency_contact_number}")
                
                result.append({
                    "id": ward_admission.id,
                    "encounter_id": ward_admission.encounter_id,
                    "ward": ward_admission.ward,
                    "bed_id": ward_admission.bed_id,
                    "bed_number": bed_number,
                    "doctor_id": doctor_id,
                    "doctor_name": doctor_name,
                    "doctor_username": doctor_username,
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
            transferred_at=utcnow()
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
                old_bed.updated_at = utcnow()
        
        # Mark new bed as occupied
        bed.is_occupied = True
        bed.updated_at = utcnow()
        
        # Update ward admission
        ward_admission.bed_id = form_data.bed_id
        ward_admission.updated_at = utcnow()
        
        # Create transfer record (auto-accepted for same-ward transfers)
        transfer = WardTransfer(
            ward_admission_id=ward_admission.id,
            from_ward=form_data.from_ward,
            to_ward=form_data.to_ward,
            transfer_reason=form_data.transfer_reason,
            status="accepted",
            transferred_by=current_user.id,
            accepted_by=current_user.id,
            transferred_at=utcnow(),
            accepted_at=utcnow()
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
    ward: Optional[str] = Query(None),
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


@router.get("/ward-admissions/{ward_admission_id}", response_model=WardAdmissionResponse)
def get_ward_admission(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get a single ward admission by ID"""
    from app.models.ward_admission import WardAdmission
    from app.models.patient import Patient
    
    try:
        ward_admission = db.query(WardAdmission).options(
            joinedload(WardAdmission.encounter).joinedload(Encounter.patient),
            joinedload(WardAdmission.bed)
        ).filter(WardAdmission.id == ward_admission_id).first()
        
        if not ward_admission:
            raise HTTPException(status_code=404, detail="Ward admission not found")
        
        encounter = ward_admission.encounter
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found for this ward admission")
        
        patient = encounter.patient
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found for this encounter")
        
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
        emergency_contact_name = patient.emergency_contact_name
        emergency_contact_relationship = patient.emergency_contact_relationship
        emergency_contact_number = patient.emergency_contact_number
        
        # Get bed information
        bed_number = None
        if ward_admission.bed_id:
            if ward_admission.bed:
                bed_number = ward_admission.bed.bed_number
                print(f"DEBUG get_ward_admission: Ward admission {ward_admission.id} has bed_id={ward_admission.bed_id}, bed_number={bed_number}")
            else:
                print(f"DEBUG get_ward_admission: Ward admission {ward_admission.id} has bed_id={ward_admission.bed_id} but bed relationship is None")
        else:
            print(f"DEBUG get_ward_admission: Ward admission {ward_admission.id} has no bed_id")
        
        # Get doctor information (doctor under whose care)
        doctor_id = ward_admission.doctor_id
        doctor_name = None
        doctor_username = None
        if doctor_id:
            doctor_user = db.query(User).filter(User.id == doctor_id).first()
            if doctor_user:
                doctor_name = doctor_user.full_name
                doctor_username = doctor_user.username
        
        return {
            "id": ward_admission.id,
            "encounter_id": ward_admission.encounter_id,
            "ward": ward_admission.ward,
            "bed_id": ward_admission.bed_id,
            "bed_number": bed_number,
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "doctor_username": doctor_username,
            "admitted_by": ward_admission.admitted_by,
            "admitted_at": ward_admission.admitted_at,
            "discharged_at": ward_admission.discharged_at,
            "discharged_by": ward_admission.discharged_by,
            "discharge_outcome": ward_admission.discharge_outcome,
            "discharge_condition": ward_admission.discharge_condition,
            "partially_discharged_at": ward_admission.partially_discharged_at,
            "partially_discharged_by": ward_admission.partially_discharged_by,
            "final_orders": ward_admission.final_orders,
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
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_ward_admission: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching ward admission: {str(e)}")


class PartialDischargeRequest(BaseModel):
    """Request for partial discharge"""
    discharge_outcome: str  # discharged, absconded, referred, died, discharged_against_medical_advice
    discharge_condition: str  # stable, cured, died, absconded
    final_orders: Optional[str] = None  # Doctor's final orders/notes


class FinalDischargeRequest(BaseModel):
    """Request for final discharge"""
    discharge_outcome: str  # discharged, absconded, referred, died, discharged_against_medical_advice
    discharge_condition: str  # stable, cured, died, absconded
    final_orders: Optional[str] = None  # Doctor's final orders/notes


@router.post("/ward-admissions/{ward_admission_id}/partial-discharge")
def partial_discharge_patient(
    ward_admission_id: int,
    request: PartialDischargeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Initiate partial discharge - allows doctor to give final orders before final discharge"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Patient has already been discharged")
    
    if ward_admission.partially_discharged_at is not None:
        raise HTTPException(status_code=400, detail="Patient has already been partially discharged")
    
    # Validate outcome and condition
    valid_outcomes = ["discharged", "absconded", "referred", "died", "discharged_against_medical_advice"]
    valid_conditions = ["stable", "cured", "delivered", "improved", "not_improved", "died", "absconded"]
    
    if request.discharge_outcome not in valid_outcomes:
        raise HTTPException(status_code=400, detail=f"Invalid discharge outcome. Must be one of: {', '.join(valid_outcomes)}")
    
    if request.discharge_condition not in valid_conditions:
        raise HTTPException(status_code=400, detail=f"Invalid discharge condition. Must be one of: {', '.join(valid_conditions)}")
    
    # Mark as partially discharged
    ward_admission.partially_discharged_at = utcnow()
    ward_admission.partially_discharged_by = current_user.id
    ward_admission.discharge_outcome = request.discharge_outcome
    ward_admission.discharge_condition = request.discharge_condition
    ward_admission.final_orders = request.final_orders
    ward_admission.updated_at = utcnow()
    
    db.commit()
    db.refresh(ward_admission)
    
    return {
        "id": ward_admission.id,
        "encounter_id": ward_admission.encounter_id,
        "ward": ward_admission.ward,
        "partially_discharged_at": ward_admission.partially_discharged_at,
        "partially_discharged_by": ward_admission.partially_discharged_by,
        "discharge_outcome": ward_admission.discharge_outcome,
        "discharge_condition": ward_admission.discharge_condition,
        "message": "Partial discharge initiated successfully. Please ensure all bills are paid before final discharge."
    }


@router.post("/ward-admissions/{ward_admission_id}/revert-partial-discharge")
def revert_partial_discharge(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Revert partial discharge - allows staff to undo partial discharge if services were missed"""
    from app.models.ward_admission import WardAdmission
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Cannot revert partial discharge for a fully discharged patient")
    
    if ward_admission.partially_discharged_at is None:
        raise HTTPException(status_code=400, detail="Patient has not been partially discharged")
    
    # Revert partial discharge fields
    ward_admission.partially_discharged_at = None
    ward_admission.partially_discharged_by = None
    ward_admission.discharge_outcome = None
    ward_admission.discharge_condition = None
    ward_admission.final_orders = None
    ward_admission.updated_at = utcnow()
    
    db.commit()
    db.refresh(ward_admission)
    
    return {
        "id": ward_admission.id,
        "encounter_id": ward_admission.encounter_id,
        "ward": ward_admission.ward,
        "message": "Partial discharge reverted successfully. You can now add services and discharge again when ready."
    }


@router.put("/ward-admissions/{ward_admission_id}/discharge")
def final_discharge_patient(
    ward_admission_id: int,
    request: FinalDischargeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Final discharge - checks bills are paid before completing discharge"""
    from datetime import datetime
    from app.models.ward_admission import WardAdmission
    from app.models.bed import Bed
    from app.models.bill import Bill
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Patient has already been discharged")
    
    # Check if partially discharged first
    if ward_admission.partially_discharged_at is None:
        raise HTTPException(status_code=400, detail="Patient must be partially discharged first before final discharge")
    
    # Validate outcome and condition
    valid_outcomes = ["discharged", "absconded", "referred", "died", "discharged_against_medical_advice"]
    valid_conditions = ["stable", "cured", "delivered", "improved", "not_improved", "died", "absconded"]
    
    if request.discharge_outcome not in valid_outcomes:
        raise HTTPException(status_code=400, detail=f"Invalid discharge outcome. Must be one of: {', '.join(valid_outcomes)}")
    
    if request.discharge_condition not in valid_conditions:
        raise HTTPException(status_code=400, detail=f"Invalid discharge condition. Must be one of: {', '.join(valid_conditions)}")
    
    # Check if all bills are paid (skip check for died or absconded patients)
    is_died_or_absconded = (
        request.discharge_outcome in ["died", "absconded"] or 
        request.discharge_condition in ["died", "absconded"]
    )
    
    if not is_died_or_absconded:
        encounter = ward_admission.encounter
        if encounter:
            unpaid_bills = db.query(Bill).filter(
                Bill.encounter_id == encounter.id,
                Bill.is_paid == False
            ).all()
            
            if unpaid_bills:
                total_unpaid = sum(bill.total_amount - bill.paid_amount for bill in unpaid_bills)
                if total_unpaid > 0.01:  # Allow small rounding differences
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot discharge patient. Outstanding bills amount to GHC {total_unpaid:.2f}. All bills must be paid before discharge."
                    )
    
    # Free up the bed
    if ward_admission.bed_id:
        bed = db.query(Bed).filter(Bed.id == ward_admission.bed_id).first()
        if bed:
            bed.is_occupied = False
            bed.updated_at = utcnow()
    
    # Update discharge information (in case it changed from partial discharge)
    ward_admission.discharge_outcome = request.discharge_outcome
    ward_admission.discharge_condition = request.discharge_condition
    if request.final_orders:
        ward_admission.final_orders = request.final_orders
    
    # Mark as fully discharged
    ward_admission.discharged_at = utcnow()
    ward_admission.discharged_by = current_user.id
    ward_admission.updated_at = utcnow()
    
    db.commit()
    db.refresh(ward_admission)
    
    return {
        "id": ward_admission.id,
        "encounter_id": ward_admission.encounter_id,
        "ward": ward_admission.ward,
        "discharged_at": ward_admission.discharged_at,
        "discharged_by": ward_admission.discharged_by,
        "discharge_outcome": ward_admission.discharge_outcome,
        "discharge_condition": ward_admission.discharge_condition,
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
    ward_admission.updated_at = utcnow()
    
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
    
    # Check permissions: user can edit their own documentation, admin and doctor can edit any
    if current_user.role not in ["Admin"] and nurse_mid_doc.created_by != current_user.id:
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


@router.put("/ward-admissions/{ward_admission_id}/vitals/{vital_id}")
def update_inpatient_vital(
    ward_admission_id: int,
    vital_id: int,
    request: CreateInpatientVitalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Update a vital record for an inpatient"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_vital import InpatientVital
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    vital = db.query(InpatientVital).filter(
        InpatientVital.id == vital_id,
        InpatientVital.ward_admission_id == ward_admission_id
    ).first()
    
    if not vital:
        raise HTTPException(status_code=404, detail="Vital record not found")
    
    # Check permissions: user can edit their own vital, admin can edit any
    if current_user.role != "Admin" and vital.recorded_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only edit your own vital record. Admin can edit any record."
        )
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Cannot edit vital record for discharged patient")
    
    # Calculate BMI if weight and height are provided
    bmi = None
    if request.weight and request.height and request.height > 0:
        bmi = request.weight / ((request.height / 100) ** 2)
    
    # Update vital fields
    vital.temperature = request.temperature
    vital.blood_pressure_systolic = request.blood_pressure_systolic
    vital.blood_pressure_diastolic = request.blood_pressure_diastolic
    vital.pulse = request.pulse
    vital.respiratory_rate = request.respiratory_rate
    vital.oxygen_saturation = request.oxygen_saturation
    vital.weight = request.weight
    vital.height = request.height
    vital.bmi = bmi
    vital.notes = request.notes
    
    db.commit()
    db.refresh(vital)
    
    recorder = db.query(User).filter(User.id == vital.recorded_by).first()
    
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
        "recorded_by_name": recorder.full_name if recorder else None,
        "recorded_at": vital.recorded_at,
        "message": "Vital record updated successfully"
    }


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
        nurse_note.strikethrough_at = utcnow()
    else:
        nurse_note.strikethrough = 0
        nurse_note.strikethrough_by = None
        nurse_note.strikethrough_at = None
    
    nurse_note.updated_at = utcnow()
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
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin", "Pharmacy", "Pharmacy Head"]))
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


@router.put("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}")
def update_inpatient_clinical_review(
    ward_admission_id: int,
    clinical_review_id: int,
    request: CreateInpatientClinicalReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin"]))
):
    """Update a clinical review for an inpatient"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    # Check permissions: user can edit their own review, admin can edit any
    if current_user.role != "Admin" and clinical_review.reviewed_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only edit your own clinical review. Admin can edit any review."
        )
    
    if ward_admission.discharged_at is not None:
        raise HTTPException(status_code=400, detail="Cannot edit clinical review for discharged patient")
    
    # Update review notes
    clinical_review.review_notes = request.review_notes
    
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
        "message": "Clinical review updated successfully"
    }


@router.delete("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}")
def delete_inpatient_clinical_review(
    ward_admission_id: int,
    clinical_review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete a clinical review (Admin only)"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    # Only Admin can delete
    if current_user.role != "Admin":
        raise HTTPException(
            status_code=403,
            detail="Only Admin can delete clinical reviews"
        )
    
    db.delete(clinical_review)
    db.commit()
    
    return {
        "message": "Clinical review deleted successfully"
    }


# Inpatient Diagnosis endpoints
class InpatientDiagnosisCreate(BaseModel):
    clinical_review_id: int
    icd10: Optional[str] = None
    diagnosis: str
    gdrg_code: Optional[str] = None
    diagnosis_status: Optional[str] = None  # 'new', 'old', or 'recurring'
    is_provisional: bool = False
    is_chief: bool = False


@router.post("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}/diagnoses")
def create_inpatient_diagnosis(
    ward_admission_id: int,
    clinical_review_id: int,
    diagnosis_data: InpatientDiagnosisCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin"]))
):
    """Add a diagnosis to a clinical review"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_diagnosis import InpatientDiagnosis
    from app.models.icd10_drg_mapping import ICD10DRGMapping
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    # Convert None ICD-10 to empty string
    diagnosis_dict = diagnosis_data.dict()
    if diagnosis_dict.get('icd10') is None:
        diagnosis_dict['icd10'] = ''
    
    # Auto-add ICD-10 code to system if it doesn't exist
    icd10_code = diagnosis_dict.get('icd10', '').strip()
    if icd10_code:
        existing_mapping = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.icd10_code == icd10_code
        ).first()
        
        if not existing_mapping:
            new_icd10 = ICD10DRGMapping(
                drg_code='',
                drg_description='',
                icd10_code=icd10_code,
                icd10_description=diagnosis_dict.get('diagnosis', '').strip() or '',
                notes='Auto-added from inpatient diagnosis entry',
                remarks='',
                is_active=True
            )
            db.add(new_icd10)
            db.flush()
    
    # Auto-map ICD-10 to DRG code
    if icd10_code and not diagnosis_dict.get('gdrg_code'):
        mapping = db.query(ICD10DRGMapping).filter(
            ICD10DRGMapping.icd10_code == icd10_code,
            ICD10DRGMapping.is_active == True,
            ICD10DRGMapping.drg_code != '',
            ICD10DRGMapping.drg_code.isnot(None)
        ).first()
        
        if mapping:
            diagnosis_dict['gdrg_code'] = mapping.drg_code
            if not diagnosis_dict.get('diagnosis') or not diagnosis_dict['diagnosis'].strip():
                if mapping.icd10_description:
                    diagnosis_dict['diagnosis'] = mapping.icd10_description
    
    diagnosis = InpatientDiagnosis(**diagnosis_dict, created_by=current_user.id)
    db.add(diagnosis)
    db.commit()
    db.refresh(diagnosis)
    
    return {
        "id": diagnosis.id,
        "clinical_review_id": diagnosis.clinical_review_id,
        "icd10": diagnosis.icd10,
        "diagnosis": diagnosis.diagnosis,
        "gdrg_code": diagnosis.gdrg_code,
        "diagnosis_status": diagnosis.diagnosis_status,
        "is_provisional": diagnosis.is_provisional,
        "is_chief": diagnosis.is_chief,
        "created_by": diagnosis.created_by,
        "created_at": diagnosis.created_at,
    }


@router.get("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}/diagnoses")
def get_inpatient_diagnoses(
    ward_admission_id: int,
    clinical_review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all diagnoses for a clinical review"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_diagnosis import InpatientDiagnosis
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    diagnoses = db.query(InpatientDiagnosis).filter(
        InpatientDiagnosis.clinical_review_id == clinical_review_id
    ).all()
    
    return [
        {
            "id": d.id,
            "clinical_review_id": d.clinical_review_id,
            "icd10": d.icd10,
            "diagnosis": d.diagnosis,
            "gdrg_code": d.gdrg_code,
            "diagnosis_status": d.diagnosis_status,
            "is_provisional": d.is_provisional,
            "is_chief": d.is_chief,
            "created_by": d.created_by,
            "created_at": d.created_at,
        }
        for d in diagnoses
    ]


@router.delete("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}/diagnoses/{diagnosis_id}")
def delete_inpatient_diagnosis(
    ward_admission_id: int,
    clinical_review_id: int,
    diagnosis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin"]))
):
    """Delete a diagnosis from a clinical review"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_diagnosis import InpatientDiagnosis
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    diagnosis = db.query(InpatientDiagnosis).filter(
        InpatientDiagnosis.id == diagnosis_id,
        InpatientDiagnosis.clinical_review_id == clinical_review_id
    ).first()
    if not diagnosis:
        raise HTTPException(status_code=404, detail="Diagnosis not found")
    
    db.delete(diagnosis)
    db.commit()
    return None


# Inpatient Prescription endpoints
class InpatientPrescriptionCreate(BaseModel):
    # clinical_review_id is in the URL path, not needed in body
    medicine_code: str
    medicine_name: str
    dose: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    quantity: int = 0
    unparsed: Optional[str] = None
    is_external: Optional[bool] = False  # Mark prescription as external (to be filled outside)


class InpatientPrescriptionUpdate(BaseModel):
    """Inpatient prescription update model (clinical_review_id not required for updates)"""
    medicine_code: str
    medicine_name: str
    dose: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None
    quantity: int = 0
    unparsed: Optional[str] = None
    is_external: Optional[bool] = None  # Mark prescription as external (to be filled outside)


@router.post("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}/prescriptions")
def create_inpatient_prescription(
    ward_admission_id: int,
    clinical_review_id: int,
    prescription_data: InpatientPrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin", "Pharmacy", "Pharmacy Head"]))
):
    """Add a prescription to a clinical review"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_prescription import InpatientPrescription
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    # Get frequency value from mapping
    frequency_value = None
    if prescription_data.frequency:
        frequency_value = FREQUENCY_MAPPING.get(prescription_data.frequency.strip(), None)
    
    # Handle is_external flag (convert boolean to integer for SQLite)
    is_external = prescription_data.is_external if prescription_data.is_external is not None else False
    is_external_int = 1 if is_external else 0
    
    prescription = InpatientPrescription(
        clinical_review_id=clinical_review_id,
        medicine_code=prescription_data.medicine_code,
        medicine_name=prescription_data.medicine_name,
        dose=prescription_data.dose,
        unit=prescription_data.unit,
        frequency=prescription_data.frequency,
        frequency_value=frequency_value,
        duration=prescription_data.duration,
        instructions=prescription_data.instructions,
        quantity=prescription_data.quantity,
        unparsed=prescription_data.unparsed,
        prescribed_by=current_user.id,
        is_external=is_external_int
    )
    
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    
    return {
        "id": prescription.id,
        "clinical_review_id": prescription.clinical_review_id,
        "medicine_code": prescription.medicine_code,
        "medicine_name": prescription.medicine_name,
        "dose": prescription.dose,
        "unit": prescription.unit,
        "frequency": prescription.frequency,
        "frequency_value": prescription.frequency_value,
        "duration": prescription.duration,
        "instructions": prescription.instructions,
        "quantity": prescription.quantity,
        "prescribed_by": prescription.prescribed_by,
        "is_external": bool(prescription.is_external),
        "created_at": prescription.created_at,
    }


@router.get("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}/prescriptions")
def get_inpatient_prescriptions(
    ward_admission_id: int,
    clinical_review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all prescriptions for a clinical review"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_prescription import InpatientPrescription
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    prescriptions = db.query(InpatientPrescription).filter(
        InpatientPrescription.clinical_review_id == clinical_review_id
    ).all()
    
    return [
        {
            "id": p.id,
            "clinical_review_id": p.clinical_review_id,
            "medicine_code": p.medicine_code,
            "medicine_name": p.medicine_name,
            "dose": p.dose,
            "unit": p.unit,
            "frequency": p.frequency,
            "frequency_value": p.frequency_value,
            "duration": p.duration,
            "instructions": p.instructions,
            "quantity": p.quantity,
            "prescribed_by": p.prescribed_by,
            "created_at": p.created_at,
        }
        for p in prescriptions
    ]


@router.get("/ward-admissions/{ward_admission_id}/prescriptions")
def get_all_ward_admission_prescriptions(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all DISPENSED prescriptions for a ward admission (for treatment sheet)"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_prescription import InpatientPrescription
    from app.models.prescription import Prescription
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    result = []
    
    # 1. Get all DISPENSED inpatient prescriptions from clinical reviews
    clinical_reviews = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).all()
    
    if clinical_reviews:
        clinical_review_ids = [cr.id for cr in clinical_reviews]
        inpatient_prescriptions = db.query(InpatientPrescription).filter(
            InpatientPrescription.clinical_review_id.in_(clinical_review_ids),
            InpatientPrescription.dispensed_by.isnot(None)  # Only dispensed prescriptions
        ).order_by(InpatientPrescription.created_at.desc()).all()
        
        for p in inpatient_prescriptions:
            result.append({
                "id": p.id,
                "clinical_review_id": p.clinical_review_id,
                "encounter_id": None,  # Not from OPD encounter
                "medicine_code": p.medicine_code,
                "medicine_name": p.medicine_name,
                "dose": p.dose,
                "unit": p.unit,
                "frequency": p.frequency,
                "frequency_value": p.frequency_value,
                "duration": p.duration,
                "instructions": p.instructions,
                "quantity": p.quantity,
                "prescribed_by": p.prescribed_by,
                "created_at": p.created_at,
                "source": "inpatient"  # Mark as inpatient prescription
            })
    
    # 2. Get DISPENSED OPD encounter prescriptions (if encounter_id exists)
    if ward_admission.encounter_id:
        opd_prescriptions = db.query(Prescription).filter(
            Prescription.encounter_id == ward_admission.encounter_id,
            Prescription.dispensed_by.isnot(None)  # Only dispensed prescriptions
        ).order_by(Prescription.created_at.desc()).all()
        
        for p in opd_prescriptions:
            result.append({
                "id": p.id,
                "clinical_review_id": None,  # Not from clinical review
                "encounter_id": p.encounter_id,
                "medicine_code": p.medicine_code,
                "medicine_name": p.medicine_name,
                "dose": p.dose,
                "unit": p.unit,
                "frequency": p.frequency,
                "frequency_value": p.frequency_value,
                "duration": p.duration,
                "instructions": p.instructions,
                "quantity": p.quantity,
                "prescribed_by": p.prescribed_by,
                "created_at": p.created_at,
                "source": "opd"  # Mark as OPD prescription
            })
    
    # Sort by created_at descending
    result.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
    
    return result


@router.get("/ward-admissions/{ward_admission_id}/diagnoses/all")
def get_all_inpatient_diagnoses_for_ward_admission(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin", "Nurse", "Doctor", "PA"]))
):
    """Get all diagnoses for a ward admission (across all clinical reviews and from OPD encounter)"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_diagnosis import InpatientDiagnosis
    from app.models.diagnosis import Diagnosis
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    result = []
    
    # Get OPD diagnoses from the encounter (if encounter exists)
    if ward_admission.encounter_id:
        opd_diagnoses = db.query(Diagnosis).filter(
            Diagnosis.encounter_id == ward_admission.encounter_id
        ).order_by(Diagnosis.created_at.desc()).all()
        
        for d in opd_diagnoses:
            creator = db.query(User).filter(User.id == d.created_by).first()
            result.append({
                "id": d.id,
                "clinical_review_id": None,  # OPD diagnoses don't have clinical_review_id
                "icd10": d.icd10,
                "diagnosis": d.diagnosis,
                "gdrg_code": d.gdrg_code,
                "diagnosis_status": d.diagnosis_status,
                "is_provisional": d.is_provisional,
                "is_chief": d.is_chief,
                "created_by": d.created_by,
                "created_by_name": creator.full_name if creator else "Unknown",
                "created_at": d.created_at,
                "source": "opd",  # Flag to indicate this is from OPD encounter
            })
    
    # Get all clinical reviews for this ward admission
    clinical_reviews = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).all()
    
    if clinical_reviews:
        clinical_review_ids = [cr.id for cr in clinical_reviews]
        
        # Get all diagnoses from all clinical reviews
        inpatient_diagnoses = db.query(InpatientDiagnosis).filter(
            InpatientDiagnosis.clinical_review_id.in_(clinical_review_ids)
        ).order_by(InpatientDiagnosis.created_at.desc()).all()
        
        for d in inpatient_diagnoses:
            creator = db.query(User).filter(User.id == d.created_by).first()
            result.append({
                "id": d.id,
                "clinical_review_id": d.clinical_review_id,
                "icd10": d.icd10,
                "diagnosis": d.diagnosis,
                "gdrg_code": d.gdrg_code,
                "diagnosis_status": d.diagnosis_status,
                "is_provisional": d.is_provisional,
                "is_chief": d.is_chief,
                "created_by": d.created_by,
                "created_by_name": creator.full_name if creator else "Unknown",
                "created_at": d.created_at,
                "source": "inpatient",  # Flag to indicate this is from inpatient clinical review
            })
    
    # Sort all diagnoses by created_at (most recent first)
    result.sort(key=lambda x: x.get("created_at") or datetime.min, reverse=True)
    
    return result


@router.get("/ward-admissions/{ward_admission_id}/prescriptions/all")
def get_all_inpatient_prescriptions_for_pharmacy(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Get ALL inpatient prescriptions for a ward admission (for pharmacy - includes pending, confirmed, and dispensed)"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_prescription import InpatientPrescription
    from app.models.user import User as UserModel
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    result = []
    
    # Get all clinical reviews for this ward admission
    clinical_reviews = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).all()
    
    if not clinical_reviews:
        return []
    
    clinical_review_ids = [cr.id for cr in clinical_reviews]
    
    # Get ALL inpatient prescriptions (pending, confirmed, and dispensed)
    inpatient_prescriptions = db.query(InpatientPrescription).filter(
        InpatientPrescription.clinical_review_id.in_(clinical_review_ids)
    ).order_by(InpatientPrescription.created_at.desc()).all()
    
    for p in inpatient_prescriptions:
        # Get prescriber info
        prescriber = db.query(UserModel).filter(UserModel.id == p.prescribed_by).first()
        prescriber_name = prescriber.full_name if prescriber else "Unknown"
        
        # Get confirmer info if confirmed
        confirmer_name = None
        if p.confirmed_by:
            confirmer = db.query(UserModel).filter(UserModel.id == p.confirmed_by).first()
            confirmer_name = confirmer.full_name if confirmer else "Unknown"
        
        # Get dispenser info if dispensed
        dispenser_name = None
        if p.dispensed_by:
            dispenser = db.query(UserModel).filter(UserModel.id == p.dispensed_by).first()
            dispenser_name = dispenser.full_name if dispenser else "Unknown"
        
        result.append({
            "id": p.id,
            "clinical_review_id": p.clinical_review_id,
            "ward_admission_id": ward_admission.id,
            "encounter_id": ward_admission.encounter_id,
            "ward": ward_admission.ward,
            "medicine_code": p.medicine_code,
            "medicine_name": p.medicine_name,
            "dose": p.dose,
            "unit": p.unit,
            "frequency": p.frequency,
            "frequency_value": p.frequency_value,
            "duration": p.duration,
            "instructions": p.instructions,
            "quantity": p.quantity,
            "prescribed_by": p.prescribed_by,
            "prescriber_name": prescriber_name,
            "confirmed_by": p.confirmed_by,
            "confirmer_name": confirmer_name,
            "confirmed_at": p.confirmed_at,
            "dispensed_by": p.dispensed_by,
            "dispenser_name": dispenser_name,
            "service_date": p.service_date,  # Add service_date for dispensed date/time
            "is_external": bool(p.is_external) if hasattr(p, 'is_external') else False,
            "created_at": p.created_at,
            "is_confirmed": p.confirmed_by is not None,
            "is_dispensed": p.dispensed_by is not None
        })
    
    return result


# Treatment Sheet Administration endpoints
class TreatmentSheetAdministrationCreate(BaseModel):
    prescription_id: int
    administration_date: str  # ISO date string
    administration_time: str  # HH:MM format
    signature: Optional[str] = None
    notes: Optional[str] = None


@router.post("/ward-admissions/{ward_admission_id}/treatment-sheet/administrations")
def create_treatment_administration(
    ward_admission_id: int,
    administration_data: TreatmentSheetAdministrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Record medication administration on treatment sheet"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_prescription import InpatientPrescription
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.prescription import Prescription
    from app.models.treatment_sheet_administration import TreatmentSheetAdministration
    from datetime import datetime, date, time
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    # Verify prescription belongs to this ward admission
    # Check if it's an inpatient prescription
    inpatient_prescription = db.query(InpatientPrescription).filter(
        InpatientPrescription.id == administration_data.prescription_id
    ).first()
    
    # Check if it's an OPD prescription
    opd_prescription = None
    if not inpatient_prescription:
        opd_prescription = db.query(Prescription).filter(
            Prescription.id == administration_data.prescription_id
        ).first()
    
    if not inpatient_prescription and not opd_prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Validate prescription belongs to this ward admission
    if inpatient_prescription:
        # Check if prescription belongs to a clinical review for this ward admission
        clinical_review = db.query(InpatientClinicalReview).filter(
            InpatientClinicalReview.id == inpatient_prescription.clinical_review_id,
            InpatientClinicalReview.ward_admission_id == ward_admission_id
        ).first()
        
        if not clinical_review:
            raise HTTPException(status_code=400, detail="Prescription does not belong to this ward admission")
    elif opd_prescription:
        # Check if OPD prescription belongs to the encounter for this ward admission
        if opd_prescription.encounter_id != ward_admission.encounter_id:
            raise HTTPException(status_code=400, detail="Prescription does not belong to this ward admission's encounter")
    
    # Parse date and time
    try:
        admin_date = datetime.fromisoformat(administration_data.administration_date).date()
        time_parts = administration_data.administration_time.split(':')
        admin_time = time(int(time_parts[0]), int(time_parts[1]))
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid date or time format: {str(e)}")
    
    # Determine prescription type
    prescription_type = "inpatient" if inpatient_prescription else "opd"
    
    administration = TreatmentSheetAdministration(
        ward_admission_id=ward_admission_id,
        prescription_id=administration_data.prescription_id,
        prescription_type=prescription_type,
        administration_date=admin_date,
        administration_time=admin_time,
        given_by=current_user.id,
        signature=administration_data.signature,
        notes=administration_data.notes
    )
    
    db.add(administration)
    db.commit()
    db.refresh(administration)
    
    giver = db.query(User).filter(User.id == current_user.id).first()
    
    return {
        "id": administration.id,
        "ward_admission_id": administration.ward_admission_id,
        "prescription_id": administration.prescription_id,
        "administration_date": administration.administration_date.isoformat(),
        "administration_time": administration.administration_time.strftime("%H:%M"),
        "given_by": administration.given_by,
        "given_by_name": giver.full_name if giver else None,
        "signature": administration.signature,
        "notes": administration.notes,
        "created_at": administration.created_at,
        "message": "Medication administration recorded successfully"
    }


@router.get("/ward-admissions/{ward_admission_id}/treatment-sheet/administrations")
def get_treatment_administrations(
    ward_admission_id: int,
    prescription_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all medication administrations for a ward admission"""
    from app.models.ward_admission import WardAdmission
    from app.models.treatment_sheet_administration import TreatmentSheetAdministration
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    query = db.query(TreatmentSheetAdministration).filter(
        TreatmentSheetAdministration.ward_admission_id == ward_admission_id
    )
    
    if prescription_id:
        query = query.filter(TreatmentSheetAdministration.prescription_id == prescription_id)
    
    administrations = query.order_by(
        TreatmentSheetAdministration.administration_date.desc(),
        TreatmentSheetAdministration.administration_time.desc()
    ).all()
    
    result = []
    for admin in administrations:
        giver = db.query(User).filter(User.id == admin.given_by).first()
        result.append({
            "id": admin.id,
            "ward_admission_id": admin.ward_admission_id,
            "prescription_id": admin.prescription_id,
            "prescription_type": getattr(admin, 'prescription_type', 'inpatient'),  # Default for backward compatibility
            "administration_date": admin.administration_date.isoformat(),
            "administration_time": admin.administration_time.strftime("%H:%M"),
            "given_by": admin.given_by,
            "given_by_name": giver.full_name if giver else None,
            "signature": admin.signature,
            "notes": admin.notes,
            "created_at": admin.created_at,
        })
    
    return result


@router.delete("/ward-admissions/{ward_admission_id}/treatment-sheet/administrations/{administration_id}")
def delete_treatment_administration(
    ward_admission_id: int,
    administration_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Delete a medication administration record (only by creator or Admin)"""
    from app.models.ward_admission import WardAdmission
    from app.models.treatment_sheet_administration import TreatmentSheetAdministration
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    administration = db.query(TreatmentSheetAdministration).filter(
        TreatmentSheetAdministration.id == administration_id,
        TreatmentSheetAdministration.ward_admission_id == ward_admission_id
    ).first()
    
    if not administration:
        raise HTTPException(status_code=404, detail="Administration record not found")
    
    # Check permissions: user can delete their own record, admin can delete any
    if current_user.role != "Admin" and administration.given_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own administration records. Admin can delete any record."
        )
    
    db.delete(administration)
    db.commit()
    
    return {"message": "Administration record deleted successfully"}


@router.delete("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}/prescriptions/{prescription_id}")
def delete_inpatient_prescription(
    ward_admission_id: int,
    clinical_review_id: int,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin"]))
):
    """Delete a prescription from a clinical review"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_prescription import InpatientPrescription
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    prescription = db.query(InpatientPrescription).filter(
        InpatientPrescription.id == prescription_id,
        InpatientPrescription.clinical_review_id == clinical_review_id
    ).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    db.delete(prescription)
    db.commit()
    return None


@router.put("/inpatient-prescription/{prescription_id}/confirm")
def confirm_inpatient_prescription(
    prescription_id: int,
    dispense_data: Optional[PrescriptionDispense] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Confirm an inpatient prescription and add to IPD bill (no payment required)"""
    from app.models.inpatient_prescription import InpatientPrescription
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.ward_admission import WardAdmission
    from app.models.bill import Bill, BillItem
    from app.services.price_list_service_v2 import get_price_from_all_tables
    import random
    
    prescription = db.query(InpatientPrescription).filter(InpatientPrescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Inpatient prescription not found")
    
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
    
    # Get clinical review and ward admission to access encounter
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == prescription.clinical_review_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    ward_admission = db.query(WardAdmission).filter(
        WardAdmission.id == clinical_review.ward_admission_id
    ).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    encounter = ward_admission.encounter
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Update prescription details if provided
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
    
    # Mark as confirmed
    prescription.confirmed_by = current_user.id
    prescription.confirmed_at = utcnow()
    
    # Determine if insured based on encounter CCC number
    is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
    
    # Get price for the medicine
    unit_price = get_price_from_all_tables(db, prescription.medicine_code, is_insured_encounter)
    
    # Ensure quantity is set
    if not prescription.quantity or prescription.quantity <= 0:
        prescription.quantity = 1
    
    total_price = unit_price * prescription.quantity
    
    # Check if we should add to IPD bill (default is True, but skip if external)
    add_to_bill = True
    if mark_as_external:
        # External prescriptions are not billed
        add_to_bill = False
    elif dispense_data and hasattr(dispense_data, 'add_to_ipd_bill'):
        add_to_bill = dispense_data.add_to_ipd_bill if dispense_data.add_to_ipd_bill is not None else True
    
    # Add to IPD bill (no payment required - accumulates until discharge)
    # Skip billing for external prescriptions
    if total_price > 0 and add_to_bill and not mark_as_external:
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
    
    db.commit()
    db.refresh(prescription)
    
    return {
        "id": prescription.id,
        "medicine_code": prescription.medicine_code,
        "medicine_name": prescription.medicine_name,
        "confirmed_by": prescription.confirmed_by,
        "confirmed_at": prescription.confirmed_at,
        "message": "Inpatient prescription confirmed and added to IPD bill"
    }


@router.put("/inpatient-prescription/{prescription_id}/dispense")
def dispense_inpatient_prescription(
    prescription_id: int,
    dispense_data: Optional[PrescriptionDispense] = Body(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Mark an inpatient prescription as dispensed (no payment check - medications accumulate in IPD bills)"""
    from app.models.inpatient_prescription import InpatientPrescription
    
    prescription = db.query(InpatientPrescription).filter(InpatientPrescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Inpatient prescription not found")
    
    if prescription.dispensed_by is not None:
        raise HTTPException(status_code=400, detail="Prescription has already been dispensed")
    
    if prescription.confirmed_by is None:
        raise HTTPException(status_code=400, detail="Prescription must be confirmed before dispense")
    
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
    prescription.service_date = utcnow()
    
    db.commit()
    db.refresh(prescription)
    
    return {
        "id": prescription.id,
        "medicine_code": prescription.medicine_code,
        "medicine_name": prescription.medicine_name,
        "dispensed_by": prescription.dispensed_by,
        "service_date": prescription.service_date,
        "message": "Inpatient prescription dispensed successfully"
    }


@router.put("/inpatient-prescription/{prescription_id}/return")
def return_inpatient_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Return a dispensed inpatient prescription (undo dispense)"""
    from app.models.inpatient_prescription import InpatientPrescription
    
    prescription = db.query(InpatientPrescription).filter(InpatientPrescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Inpatient prescription not found")
    
    if prescription.dispensed_by is None:
        raise HTTPException(status_code=400, detail="Prescription has not been dispensed")
    
    prescription.dispensed_by = None
    # Don't set service_date to None - it has a NOT NULL constraint
    # Keep the existing service_date value or update it to current time
    prescription.service_date = utcnow()
    
    db.commit()
    db.refresh(prescription)
    
    return {
        "id": prescription.id,
        "medicine_code": prescription.medicine_code,
        "medicine_name": prescription.medicine_name,
        "dispensed_by": None,
        "service_date": prescription.service_date.isoformat() if prescription.service_date else None,
        "message": "Inpatient prescription returned successfully"
    }


@router.put("/inpatient-prescription/{prescription_id}", response_model=dict)
def update_inpatient_prescription(
    prescription_id: int,
    prescription_data: InpatientPrescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "Admin", "PA", "Pharmacy", "Pharmacy Head"]))
):
    """Update an inpatient prescription"""
    from app.models.inpatient_prescription import InpatientPrescription
    
    prescription = db.query(InpatientPrescription).filter(InpatientPrescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Inpatient prescription not found")
    
    # Prevent editing if prescription is confirmed by pharmacy staff
    # Only Admin can override this restriction
    if prescription.confirmed_by is not None and current_user.role != "Admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot edit prescription that has been confirmed by pharmacy staff. Contact admin if changes are needed."
        )
    
    # Get frequency value from mapping if frequency is provided
    frequency_value = None
    if prescription_data.frequency:
        frequency_value = FREQUENCY_MAPPING.get(prescription_data.frequency.strip(), None)
    
    # Auto-calculate quantity based on pharmacist logic
    quantity = prescription_data.quantity
    if (not quantity or quantity <= 0) and prescription_data.dose and prescription_data.frequency and prescription_data.duration:
        try:
            # Extract numeric value from dose
            dose_str = str(prescription_data.dose).strip()
            try:
                dose_num = float(dose_str) if dose_str else 0
            except (ValueError, TypeError):
                dose_num = 0
            
            # If parsing fails, try to extract first number
            if dose_num <= 0:
                import re
                first_number_match = re.search(r'\d+(\.\d+)?', dose_str)
                if first_number_match:
                    dose_num = float(first_number_match.group())
            
            frequency_value_for_calc = frequency_value or FREQUENCY_MAPPING.get(prescription_data.frequency.strip(), 1)
            
            if dose_num and dose_num > 0 and frequency_value_for_calc:
                # Extract duration number
                duration_str = str(prescription_data.duration).strip()
                duration_num = 1
                try:
                    direct_num = float(duration_str)
                    if direct_num > 0:
                        duration_num = int(direct_num)
                except (ValueError, TypeError):
                    import re
                    duration_match = re.search(r'\d+', duration_str)
                    if duration_match:
                        duration_num = int(duration_match.group())
                
                # Convert dose to units based on unit type
                units_per_dose = dose_num
                if prescription_data.unit and prescription_data.unit.upper() == 'MG':
                    units_per_dose = dose_num / 100
                elif prescription_data.unit and prescription_data.unit.upper() == 'MCG':
                    units_per_dose = dose_num / 1000
                
                # Calculate: units per dose × frequency per day × number of days
                calculated_quantity = int(units_per_dose * frequency_value_for_calc * duration_num)
                if calculated_quantity > 0:
                    quantity = calculated_quantity
        except Exception:
            pass
    
    # Ensure quantity is set
    if not quantity or quantity <= 0:
        quantity = 1
    
    # Update prescription fields
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
    # Update is_external if provided
    if prescription_data.is_external is not None:
        prescription.is_external = 1 if prescription_data.is_external else 0
    
    db.commit()
    db.refresh(prescription)
    
    return {
        "id": prescription.id,
        "medicine_code": prescription.medicine_code,
        "medicine_name": prescription.medicine_name,
        "dose": prescription.dose,
        "unit": prescription.unit,
        "frequency": prescription.frequency,
        "duration": prescription.duration,
        "quantity": prescription.quantity,
        "instructions": prescription.instructions,
        "is_external": bool(prescription.is_external),
        "message": "Inpatient prescription updated successfully"
    }


@router.put("/inpatient-prescription/{prescription_id}/unconfirm")
def unconfirm_inpatient_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Revert a confirmed inpatient prescription back to pending status (undo confirmation)"""
    from app.models.inpatient_prescription import InpatientPrescription
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.ward_admission import WardAdmission
    from app.models.bill import Bill, BillItem
    
    prescription = db.query(InpatientPrescription).filter(InpatientPrescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Inpatient prescription not found")
    
    if prescription.confirmed_by is None:
        raise HTTPException(status_code=400, detail="Prescription has not been confirmed")
    
    # Prevent unconfirming if prescription has been dispensed
    if prescription.dispensed_by is not None:
        raise HTTPException(
            status_code=400, 
            detail="Cannot revert a prescription that has already been dispensed. Please return it first."
        )
    
    # Get encounter through clinical review and ward admission
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == prescription.clinical_review_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    ward_admission = db.query(WardAdmission).filter(
        WardAdmission.id == clinical_review.ward_admission_id
    ).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    encounter = ward_admission.encounter
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Find and remove the bill item that was created during confirmation
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
            # Remove the bill item amount from the bill total
            bill.total_amount -= bill_item.total_price
            if bill.total_amount < 0:
                bill.total_amount = 0.0
            
            # Delete the bill item
            db.delete(bill_item)
            
            # If bill has no items left and total is 0, delete the bill
            remaining_items = db.query(BillItem).filter(BillItem.bill_id == bill.id).count()
            if remaining_items == 0 and bill.total_amount == 0:
                db.delete(bill)
    
    # Clear confirmation fields and external flag
    prescription.confirmed_by = None
    prescription.confirmed_at = None
    if hasattr(prescription, 'is_external'):
        prescription.is_external = 0  # Clear external flag so it can be confirmed again
    
    db.commit()
    db.refresh(prescription)
    
    return {
        "id": prescription.id,
        "medicine_code": prescription.medicine_code,
        "medicine_name": prescription.medicine_name,
        "confirmed_by": None,
        "confirmed_at": None,
        "message": "Inpatient prescription unconfirmed successfully"
    }


@router.get("/ward-admissions/patient/{card_number}")
def get_ward_admissions_by_patient_card(
    card_number: str,
    include_discharged: Optional[bool] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Billing", "Admin", "Nurse", "Doctor", "PA", "Records"]))
):
    """Get ward admissions for a patient by card number. Set include_discharged=True to include discharged admissions."""
    from app.models.ward_admission import WardAdmission
    from app.models.patient import Patient
    
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.card_number == card_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get all ward admissions for this patient
    patient_encounters = db.query(Encounter).filter(
        Encounter.patient_id == patient.id
    ).all()
    
    if not patient_encounters:
        return []
    
    encounter_ids = [e.id for e in patient_encounters]
    
    query = db.query(WardAdmission).filter(
        WardAdmission.encounter_id.in_(encounter_ids)
    )
    
    # Filter by discharged status if not including discharged
    if not include_discharged:
        query = query.filter(WardAdmission.discharged_at.is_(None))
    
    ward_admissions = query.order_by(WardAdmission.admitted_at.desc()).all()
    
    result = []
    for wa in ward_admissions:
        encounter = wa.encounter
        if not encounter:
            continue
        
        result.append({
            "id": wa.id,
            "encounter_id": wa.encounter_id,
            "ward": wa.ward,
            "bed_id": wa.bed_id,
            "bed_number": wa.bed.bed_number if wa.bed else None,
            "admitted_at": wa.admitted_at,
            "admission_notes": wa.admission_notes,
            "discharged_at": wa.discharged_at,
            "discharged_by": wa.discharged_by,
            "encounter_created_at": encounter.created_at,
            "encounter_department": encounter.department,
        })
    
    return result


@router.get("/inpatient-prescription/patient/{card_number}")
def get_inpatient_prescriptions_by_patient_card(
    card_number: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Get all inpatient prescriptions for a patient by card number"""
    from app.models.inpatient_prescription import InpatientPrescription
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.ward_admission import WardAdmission
    from app.models.patient import Patient
    from app.models.user import User as UserModel
    
    # Verify patient exists
    patient = db.query(Patient).filter(Patient.card_number == card_number).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get all ward admissions for this patient
    # First get encounters for this patient, then get ward admissions
    patient_encounters = db.query(Encounter).filter(
        Encounter.patient_id == patient.id
    ).all()
    
    if not patient_encounters:
        return []
    
    encounter_ids = [e.id for e in patient_encounters]
    
    ward_admissions = db.query(WardAdmission).filter(
        WardAdmission.encounter_id.in_(encounter_ids),
        WardAdmission.discharged_at.is_(None)  # Only active admissions
    ).all()
    
    if not ward_admissions:
        return []
    
    ward_admission_ids = [wa.id for wa in ward_admissions]
    
    # Get all clinical reviews for these ward admissions
    clinical_reviews = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.ward_admission_id.in_(ward_admission_ids)
    ).all()
    
    if not clinical_reviews:
        return []
    
    clinical_review_ids = [cr.id for cr in clinical_reviews]
    
    # Get all inpatient prescriptions for these clinical reviews
    prescriptions = db.query(InpatientPrescription).filter(
        InpatientPrescription.clinical_review_id.in_(clinical_review_ids)
    ).order_by(InpatientPrescription.created_at.desc()).all()
    
    result = []
    for p in prescriptions:
        clinical_review = next((cr for cr in clinical_reviews if cr.id == p.clinical_review_id), None)
        if not clinical_review:
            continue
        
        ward_admission = next((wa for wa in ward_admissions if wa.id == clinical_review.ward_admission_id), None)
        if not ward_admission:
            continue
        
        # Get prescriber info
        prescriber = db.query(UserModel).filter(UserModel.id == p.prescribed_by).first()
        prescriber_name = prescriber.full_name if prescriber else "Unknown"
        
        # Get confirmer info if confirmed
        confirmer_name = None
        if p.confirmed_by:
            confirmer = db.query(UserModel).filter(UserModel.id == p.confirmed_by).first()
            confirmer_name = confirmer.full_name if confirmer else "Unknown"
        
        # Get dispenser info if dispensed
        dispenser_name = None
        if p.dispensed_by:
            dispenser = db.query(UserModel).filter(UserModel.id == p.dispensed_by).first()
            dispenser_name = dispenser.full_name if dispenser else "Unknown"
        
        result.append({
            "id": p.id,
            "prescription_type": "inpatient",
            "clinical_review_id": p.clinical_review_id,
            "ward_admission_id": ward_admission.id,
            "encounter_id": ward_admission.encounter_id,
            "ward": ward_admission.ward,
            "medicine_code": p.medicine_code,
            "medicine_name": p.medicine_name,
            "dose": p.dose,
            "unit": p.unit,
            "frequency": p.frequency,
            "frequency_value": p.frequency_value,
            "duration": p.duration,
            "instructions": p.instructions,
            "quantity": p.quantity,
            "prescribed_by": p.prescribed_by,
            "prescriber_name": prescriber_name,
            "confirmed_by": p.confirmed_by,
            "confirmer_name": confirmer_name,
            "confirmed_at": p.confirmed_at,
            "dispensed_by": p.dispensed_by,
            "dispenser_name": dispenser_name,
            "is_external": bool(p.is_external) if hasattr(p, 'is_external') else False,
            "created_at": p.created_at,
            "is_confirmed": p.confirmed_by is not None,
            "is_dispensed": p.dispensed_by is not None
        })
    
    return result


# Inpatient Investigation endpoints
class InpatientInvestigationCreate(BaseModel):
    clinical_review_id: int
    service_type: Optional[str] = None
    gdrg_code: str
    procedure_name: Optional[str] = None
    investigation_type: str  # lab, scan, xray
    notes: Optional[str] = None
    price: Optional[str] = None


@router.post("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}/investigations")
def create_inpatient_investigation(
    ward_admission_id: int,
    clinical_review_id: int,
    investigation_data: InpatientInvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin"]))
):
    """Add an investigation to a clinical review"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_investigation import InpatientInvestigation
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    investigation = InpatientInvestigation(
        clinical_review_id=clinical_review_id,
        service_type=investigation_data.service_type,
        gdrg_code=investigation_data.gdrg_code,
        procedure_name=investigation_data.procedure_name,
        investigation_type=investigation_data.investigation_type,
        notes=investigation_data.notes,
        price=investigation_data.price,
        requested_by=current_user.id
    )
    
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    
    return {
        "id": investigation.id,
        "clinical_review_id": investigation.clinical_review_id,
        "service_type": investigation.service_type,
        "gdrg_code": investigation.gdrg_code,
        "procedure_name": investigation.procedure_name,
        "investigation_type": investigation.investigation_type,
        "notes": investigation.notes,
        "price": investigation.price,
        "status": investigation.status,
        "requested_by": investigation.requested_by,
        "created_at": investigation.created_at,
    }


@router.get("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}/investigations")
def get_inpatient_investigations(
    ward_admission_id: int,
    clinical_review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all investigations for a clinical review"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_investigation import InpatientInvestigation
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    investigations = db.query(InpatientInvestigation).filter(
        InpatientInvestigation.clinical_review_id == clinical_review_id
    ).all()
    
    return [
        {
            "id": i.id,
            "clinical_review_id": i.clinical_review_id,
            "service_type": i.service_type,
            "gdrg_code": i.gdrg_code,
            "procedure_name": i.procedure_name,
            "investigation_type": i.investigation_type,
            "notes": i.notes,
            "price": i.price,
            "status": i.status,
            "requested_by": i.requested_by,
            "created_at": i.created_at,
        }
        for i in investigations
    ]


@router.get("/ward-admissions/{ward_admission_id}/investigations/all")
def get_all_inpatient_investigations_for_ward_admission(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all investigations for a ward admission (across all clinical reviews)"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_investigation import InpatientInvestigation
    from app.models.inpatient_lab_result import InpatientLabResult
    from app.models.inpatient_scan_result import InpatientScanResult
    from app.models.inpatient_xray_result import InpatientXrayResult
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    # Get all clinical reviews for this ward admission
    clinical_reviews = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).all()
    
    if not clinical_reviews:
        return []
    
    clinical_review_ids = [cr.id for cr in clinical_reviews]
    
    # Get all investigations from all clinical reviews
    investigations = db.query(InpatientInvestigation).filter(
        InpatientInvestigation.clinical_review_id.in_(clinical_review_ids)
    ).order_by(InpatientInvestigation.created_at.desc()).all()
    
    result = []
    if not investigations:
        return []
    
    for inv in investigations:
        requester = db.query(User).filter(User.id == inv.requested_by).first()
        confirmed_by_user = None
        completed_by_user = None
        
        if inv.confirmed_by:
            confirmed_by_user = db.query(User).filter(User.id == inv.confirmed_by).first()
        if inv.completed_by:
            completed_by_user = db.query(User).filter(User.id == inv.completed_by).first()
        
        # Check if result exists
        has_result = False
        if inv.investigation_type == "lab":
            # Check if template_id column exists to avoid query errors
            from sqlalchemy import text, inspect
            has_template_id = False
            try:
                inspector = inspect(db.bind)
                columns_info = inspector.get_columns('inpatient_lab_results')
                if columns_info and isinstance(columns_info, list):
                    columns = [col.get('name', '') for col in columns_info if isinstance(col, dict)]
                    has_template_id = 'template_id' in columns
            except Exception as e:
                # If inspection fails, assume column doesn't exist
                import logging
                logging.getLogger(__name__).warning(f"Failed to inspect columns for has_result check: {e}")
                has_template_id = False
            
            if has_template_id:
                lab_result = db.query(InpatientLabResult).filter(
                    InpatientLabResult.investigation_id == inv.id
                ).first()
                has_result = lab_result is not None
            else:
                # Column doesn't exist, use raw SQL
                lab_result_row = db.execute(
                    text("SELECT id FROM inpatient_lab_results WHERE investigation_id = :inv_id LIMIT 1"),
                    {"inv_id": inv.id}
                ).first()
                has_result = lab_result_row is not None
        elif inv.investigation_type == "scan":
            scan_result = db.query(InpatientScanResult).filter(
                InpatientScanResult.investigation_id == inv.id
            ).first()
            has_result = scan_result is not None
        elif inv.investigation_type == "xray":
            xray_result = db.query(InpatientXrayResult).filter(
                InpatientXrayResult.investigation_id == inv.id
            ).first()
            has_result = xray_result is not None
        
        result.append({
            "id": inv.id,
            "clinical_review_id": inv.clinical_review_id,
            "service_type": inv.service_type,
            "gdrg_code": inv.gdrg_code,
            "procedure_name": inv.procedure_name,
            "investigation_type": inv.investigation_type,
            "notes": inv.notes,
            "price": inv.price,
            "status": inv.status,
            "requested_by": inv.requested_by,
            "requested_by_name": requester.full_name if requester else None,
            "confirmed_by": inv.confirmed_by,
            "confirmed_by_name": confirmed_by_user.full_name if confirmed_by_user else None,
            "completed_by": inv.completed_by,
            "completed_by_name": completed_by_user.full_name if completed_by_user else None,
            "has_result": has_result,
            "created_at": inv.created_at,
            "service_date": inv.service_date,
        })
    
    return result


@router.delete("/ward-admissions/{ward_admission_id}/clinical-reviews/{clinical_review_id}/investigations/{investigation_id}")
def delete_inpatient_investigation(
    ward_admission_id: int,
    clinical_review_id: int,
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin"]))
):
    """Delete an investigation from a clinical review"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_investigation import InpatientInvestigation
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == clinical_review_id,
        InpatientClinicalReview.ward_admission_id == ward_admission_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    investigation = db.query(InpatientInvestigation).filter(
        InpatientInvestigation.id == investigation_id,
        InpatientInvestigation.clinical_review_id == clinical_review_id
    ).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    db.delete(investigation)
    db.commit()
    return None


@router.get("/inpatient-investigations/by-type")
def get_inpatient_investigations_by_type(
    investigation_type: str,  # lab, scan, xray
    status: Optional[str] = None,  # requested, confirmed, completed, cancelled
    search: Optional[str] = None,  # Search by card number or patient name
    date: Optional[str] = None,  # Filter by date (YYYY-MM-DD), defaults to today
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Scan", "Xray", "Admin", "Lab Head", "Scan Head", "Xray Head"]))
):
    """
    Get IPD investigations by type with filters
    Used by Lab, Scan, and X-ray pages to show IPD service requests
    """
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_investigation import InpatientInvestigation
    from app.models.patient import Patient
    from app.models.encounter import Encounter
    from datetime import datetime, date as date_class
    
    # Validate investigation type
    valid_types = ["lab", "scan", "xray"]
    if investigation_type.lower() not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid investigation_type. Must be one of: {', '.join(valid_types)}")
    
    # Build base query with joins and eager loading
    from sqlalchemy.orm import joinedload
    
    query = (
        db.query(InpatientInvestigation)
        .options(
            joinedload(InpatientInvestigation.clinical_review)
            .joinedload(InpatientClinicalReview.ward_admission)
            .joinedload(WardAdmission.encounter)
            .joinedload(Encounter.patient),
            joinedload(InpatientInvestigation.clinical_review)
            .joinedload(InpatientClinicalReview.ward_admission)
            .joinedload(WardAdmission.bed)
        )
        .join(InpatientClinicalReview, InpatientInvestigation.clinical_review_id == InpatientClinicalReview.id)
        .join(WardAdmission, InpatientClinicalReview.ward_admission_id == WardAdmission.id)
        .join(Encounter, WardAdmission.encounter_id == Encounter.id)
        .join(Patient, Encounter.patient_id == Patient.id)
    )
    
    # Filter by investigation type
    query = query.filter(InpatientInvestigation.investigation_type == investigation_type.lower())
    
    # Filter by status
    if status:
        valid_statuses = ["requested", "confirmed", "completed", "cancelled"]
        if status.lower() not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        query = query.filter(InpatientInvestigation.status == status.lower())
    
    # Filter by date (optional - if not provided, show all)
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d").date()
            # Filter by date (using investigation created_at date)
            # Use date-only comparison to avoid timezone/time precision issues
            # For SQLite, use func.date() to extract date from datetime
            from sqlalchemy import func
            print(f"DEBUG: Filtering by date {date}, filter_date={filter_date}")
            # Compare only the date part, ignoring time
            query = query.filter(func.date(InpatientInvestigation.created_at) == filter_date)
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}")
    else:
        print(f"DEBUG: No date filter provided - showing all investigations")
    # If no date provided, don't filter by date (show all investigations)
    
    # Search by card number or patient name
    if search:
        search_term = f"%{search.strip()}%"
        from sqlalchemy import or_
        query = query.filter(
            or_(
                Patient.card_number.ilike(search_term),
                Patient.name.ilike(search_term),
                Patient.surname.ilike(search_term)
            )
        )
    
    # Order by created_at descending (newest first)
    query = query.order_by(InpatientInvestigation.created_at.desc())
    
    # Debug: Print the query and count before executing
    try:
        # Get count before processing
        count = query.count()
        print(f"DEBUG get_inpatient_investigations_by_type: Query will return {count} IPD investigations")
        print(f"DEBUG Filters: investigation_type='{investigation_type}', status={status}, date={date}, search={search}")
        
        # Also check total investigations of this type without filters
        total_count = db.query(InpatientInvestigation).filter(
            InpatientInvestigation.investigation_type == investigation_type.lower()
        ).count()
        print(f"DEBUG Total {investigation_type} investigations in database: {total_count}")
    except Exception as e:
        import traceback
        print(f"DEBUG get_inpatient_investigations_by_type: Error counting investigations: {str(e)}")
        print(traceback.format_exc())
    
    investigations = query.all()
    print(f"DEBUG get_inpatient_investigations_by_type: Retrieved {len(investigations)} investigations from database")
    
    # Debug: Print first few investigation details
    if len(investigations) > 0:
        for i, inv in enumerate(investigations[:3]):  # Print first 3
            from datetime import date as date_type
            inv_date = inv.created_at.date() if inv.created_at else None
            print(f"DEBUG Investigation {i+1}: id={inv.id}, type={inv.investigation_type}, status={inv.status}, created_at={inv.created_at}, date_part={inv_date}")
    else:
        # If no investigations found, check what's in the database
        all_inv = db.query(InpatientInvestigation).filter(
            InpatientInvestigation.investigation_type == investigation_type.lower()
        ).limit(5).all()
        print(f"DEBUG: No investigations matched filters. Sample investigations in DB:")
        for inv in all_inv:
            inv_date = inv.created_at.date() if inv.created_at else None
            print(f"  - id={inv.id}, type={inv.investigation_type}, status={inv.status}, created_at={inv.created_at}, date_part={inv_date}")
    
    # Build response with patient info and user names
    result = []
    for inv in investigations:
        try:
            # Get user names
            confirmed_by_name = None
            if inv.confirmed_by:
                confirmed_user = db.query(User).filter(User.id == inv.confirmed_by).first()
                confirmed_by_name = confirmed_user.full_name if confirmed_user else None
            
            completed_by_name = None
            if inv.completed_by:
                completed_user = db.query(User).filter(User.id == inv.completed_by).first()
                completed_by_name = completed_user.full_name if completed_user else None
            
            # Access relationships - they should be loaded by the joins
            clinical_review = inv.clinical_review
            ward_admission = clinical_review.ward_admission if clinical_review else None
            encounter = ward_admission.encounter if ward_admission else None
            patient = encounter.patient if encounter else None
            
            # Build patient name safely
            patient_name = "Unknown"
            patient_card_number = None
            ward = None
            bed_number = None
            encounter_id = None
            ward_admission_id = None
            
            if patient:
                patient_name = f"{patient.name or ''} {patient.surname or ''} {patient.other_names or ''}".strip() or "Unknown"
                patient_card_number = patient.card_number
            
            if ward_admission:
                ward = ward_admission.ward
                # Get bed number from bed relationship if bed exists
                bed_number = ward_admission.bed.bed_number if ward_admission.bed else None
                encounter_id = ward_admission.encounter_id
                ward_admission_id = ward_admission.id
            
            inv_dict = {
                "id": inv.id,
                "clinical_review_id": inv.clinical_review_id,
                "ward_admission_id": ward_admission_id,
                "encounter_id": encounter_id,
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
                "patient_name": patient_name,
                "patient_card_number": patient_card_number,
                "encounter_date": inv.created_at,  # Use investigation created_at (request date) instead of encounter date
                "confirmed_by_name": confirmed_by_name,
                "completed_by_name": completed_by_name,
                "ward": ward,
                "bed_number": bed_number,
                "source": "inpatient",  # Mark as IPD
                "prescription_type": "inpatient"  # For compatibility
            }
            result.append(inv_dict)
        except Exception as e:
            # Log error but continue processing other investigations
            import traceback
            inv_id = inv.id if inv and hasattr(inv, 'id') else 'unknown'
            print(f"Error processing IPD investigation {inv_id}: {str(e)}")
            print(traceback.format_exc())
            # Skip this investigation
            continue
    
    return result


@router.get("/inpatient-investigation/{investigation_id}")
def get_inpatient_investigation(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Scan", "Xray", "Admin", "Lab Head", "Scan Head", "Xray Head", "Doctor", "PA", "Nurse"]))
):
    """Get a single IPD investigation by ID"""
    from app.models.inpatient_investigation import InpatientInvestigation
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.ward_admission import WardAdmission
    from app.models.encounter import Encounter
    from app.models.patient import Patient
    from sqlalchemy.orm import joinedload
    
    investigation = (
        db.query(InpatientInvestigation)
        .options(
            joinedload(InpatientInvestigation.clinical_review)
            .joinedload(InpatientClinicalReview.ward_admission)
            .joinedload(WardAdmission.encounter)
            .joinedload(Encounter.patient),
            joinedload(InpatientInvestigation.clinical_review)
            .joinedload(InpatientClinicalReview.ward_admission)
            .joinedload(WardAdmission.bed)
        )
        .filter(InpatientInvestigation.id == investigation_id)
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
    
    # Access relationships
    clinical_review = investigation.clinical_review
    ward_admission = clinical_review.ward_admission if clinical_review else None
    encounter = ward_admission.encounter if ward_admission else None
    patient = encounter.patient if encounter else None
    
    # Build patient name safely
    patient_name = "Unknown"
    patient_card_number = None
    ward = None
    bed_number = None
    encounter_id = None
    ward_admission_id = None
    
    if patient:
        patient_name = f"{patient.name or ''} {patient.surname or ''}".strip() or "Unknown"
        patient_card_number = patient.card_number
    
    if ward_admission:
        ward = ward_admission.ward
        bed_number = ward_admission.bed.bed_number if ward_admission.bed else None
        encounter_id = ward_admission.encounter_id
        ward_admission_id = ward_admission.id
    
    return {
        "id": investigation.id,
        "clinical_review_id": investigation.clinical_review_id,
        "ward_admission_id": ward_admission_id,
        "encounter_id": encounter_id,
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
        "patient_name": patient_name,
        "patient_card_number": patient_card_number,
        "encounter_date": investigation.created_at,
        "confirmed_by_name": confirmed_by_name,
        "completed_by_name": completed_by_name,
        "ward": ward,
        "bed_number": bed_number,
        "source": "inpatient",
        "prescription_type": "inpatient"
    }


class InpatientInvestigationConfirm(BaseModel):
    add_to_ipd_bill: bool = True


@router.put("/inpatient-investigation/{investigation_id}/confirm")
def confirm_inpatient_investigation(
    investigation_id: int,
    confirm_data: InpatientInvestigationConfirm = Body(default=InpatientInvestigationConfirm()),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Scan", "Xray", "Admin", "Lab Head", "Scan Head", "Xray Head"]))
):
    """Confirm an IPD investigation and optionally add to IPD bill"""
    from app.models.inpatient_investigation import InpatientInvestigation, InpatientInvestigationStatus
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.ward_admission import WardAdmission
    from app.models.encounter import Encounter
    from app.models.bill import Bill, BillItem
    from app.services.price_list_service_v2 import get_price_from_all_tables
    import random
    
    investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    if investigation.status != InpatientInvestigationStatus.REQUESTED.value:
        raise HTTPException(status_code=400, detail=f"Investigation is already {investigation.status}")
    
    # Get clinical review and ward admission
    clinical_review = db.query(InpatientClinicalReview).filter(
        InpatientClinicalReview.id == investigation.clinical_review_id
    ).first()
    if not clinical_review:
        raise HTTPException(status_code=404, detail="Clinical review not found")
    
    ward_admission = db.query(WardAdmission).filter(
        WardAdmission.id == clinical_review.ward_admission_id
    ).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    encounter = db.query(Encounter).filter(Encounter.id == ward_admission.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Update investigation status
    investigation.status = InpatientInvestigationStatus.CONFIRMED.value
    investigation.confirmed_by = current_user.id
    
    # Generate and store sample ID for lab investigations
    if investigation.investigation_type == "lab":
        _generate_and_store_sample_id(db, investigation, current_user.id)
    
    # Get price
    is_insured_encounter = bool(encounter.ccc_number)
    unit_price = 0.0
    if investigation.gdrg_code:
        try:
            # Determine service type based on investigation type for accurate price lookup
            service_type = None
            if investigation.investigation_type == "lab":
                service_type = "Lab"
            elif investigation.investigation_type == "scan":
                service_type = "Scan"
            elif investigation.investigation_type == "xray":
                service_type = "X-ray"
            
            unit_price = get_price_from_all_tables(db, investigation.gdrg_code, is_insured_encounter, service_type, investigation.procedure_name)
            print(f"DEBUG confirm_inpatient_investigation: Looked up price for gdrg_code='{investigation.gdrg_code}', procedure_name='{investigation.procedure_name}', is_insured={is_insured_encounter}, service_type='{service_type}', price={unit_price}")
            
            # If lookup returns 0.0, it means price wasn't found
            if unit_price == 0.0:
                print(f"WARNING confirm_inpatient_investigation: Price lookup returned 0.0 for gdrg_code='{investigation.gdrg_code}', service_type='{service_type}'. Price not found in pricelist.")
                # Only use stored price if it exists and lookup returned 0
                if investigation.price:
                    try:
                        stored_price = float(investigation.price)
                        if stored_price > 0:
                            print(f"WARNING confirm_inpatient_investigation: Using stored price '{stored_price}' as fallback (price not found in pricelist)")
                            unit_price = stored_price
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            print(f"WARNING confirm_inpatient_investigation: Error getting price: {str(e)}")
            # If lookup throws exception, try using stored price as fallback
            if investigation.price:
                try:
                    unit_price = float(investigation.price)
                    print(f"DEBUG confirm_inpatient_investigation: Using stored price '{unit_price}' as fallback after exception")
                except (ValueError, TypeError):
                    pass
    
    total_price = unit_price
    
    # Add to IPD bill if requested and price > 0
    add_to_bill = confirm_data.add_to_ipd_bill if confirm_data.add_to_ipd_bill is not None else True
    if total_price > 0 and add_to_bill:
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
            
            # Create bill item
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
    
    db.commit()
    db.refresh(investigation)
    
    return {
        "investigation_id": investigation.id,
        "status": investigation.status,
        "message": "IPD investigation confirmed successfully"
    }


@router.put("/inpatient-investigation/{investigation_id}/revert-status")
def revert_inpatient_investigation_status(
    investigation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab Head", "Scan Head", "Xray Head", "Admin"]))
):
    """Revert IPD investigation status from completed to confirmed (to allow editing results) - Admin and Head roles only"""
    from app.models.inpatient_investigation import InpatientInvestigation, InpatientInvestigationStatus
    
    investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Only allow reverting from completed to confirmed
    if investigation.status != InpatientInvestigationStatus.COMPLETED.value:
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
    investigation.status = InpatientInvestigationStatus.CONFIRMED.value
    # Clear completed_by when reverting
    investigation.completed_by = None
    
    db.commit()
    db.refresh(investigation)
    
    return {"investigation_id": investigation.id, "status": investigation.status, "message": "Status reverted to confirmed"}


class InpatientInvestigationRevertToRequested(BaseModel):
    """Model for reverting IPD investigation from confirmed to requested"""
    reason: str  # Reason for reverting (required)


@router.put("/inpatient-investigation/{investigation_id}/revert-to-requested")
def revert_inpatient_investigation_to_requested(
    investigation_id: int,
    revert_data: InpatientInvestigationRevertToRequested,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Revert IPD investigation status from confirmed to requested - Admin only"""
    from app.models.inpatient_investigation import InpatientInvestigation, InpatientInvestigationStatus
    from datetime import datetime
    
    investigation = db.query(InpatientInvestigation).filter(InpatientInvestigation.id == investigation_id).first()
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    
    # Only allow reverting from confirmed to requested
    if investigation.status != InpatientInvestigationStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot revert status. Current status is '{investigation.status}'. Only confirmed investigations can be reverted to requested."
        )
    
    # Revert status to requested
    investigation.status = InpatientInvestigationStatus.REQUESTED.value
    # Clear confirmed_by when reverting
    investigation.confirmed_by = None
    # Store revert reason in cancellation_reason field (reusing existing field)
    investigation.cancellation_reason = f"Reverted to requested by Admin: {revert_data.reason}"
    investigation.cancelled_by = current_user.id
    investigation.cancelled_at = utcnow()
    
    db.commit()
    db.refresh(investigation)
    
    return {"investigation_id": investigation.id, "status": investigation.status, "message": "Status reverted to requested"}


class BulkConfirmInpatientInvestigations(BaseModel):
    """Model for bulk confirming multiple IPD investigations"""
    investigation_ids: List[int]
    add_to_ipd_bill: bool = True  # Whether to add to IPD bill


# Inpatient Surgery endpoints
class InpatientSurgeryCreate(BaseModel):
    """Request model for creating an inpatient surgery"""
    g_drg_code: Optional[str] = None
    surgery_name: str
    surgery_type: Optional[str] = None
    surgeon_name: Optional[str] = None
    assistant_surgeon: Optional[str] = None
    anesthesia_type: Optional[str] = None
    surgery_date: Optional[datetime] = None
    surgery_notes: Optional[str] = None


class InpatientSurgeryUpdate(BaseModel):
    """Request model for updating/completing an inpatient surgery"""
    surgery_name: Optional[str] = None
    surgery_type: Optional[str] = None
    surgeon_name: Optional[str] = None
    assistant_surgeon: Optional[str] = None
    anesthesia_type: Optional[str] = None
    surgery_date: Optional[datetime] = None
    surgery_notes: Optional[str] = None
    operative_notes: Optional[str] = None
    post_operative_notes: Optional[str] = None
    complications: Optional[str] = None
    is_completed: Optional[bool] = None


class InpatientSurgeryResponse(BaseModel):
    """Response model for inpatient surgery"""
    id: int
    ward_admission_id: int
    encounter_id: int
    g_drg_code: Optional[str]
    surgery_name: str
    surgery_type: Optional[str]
    surgeon_name: Optional[str]
    assistant_surgeon: Optional[str]
    anesthesia_type: Optional[str]
    surgery_date: Optional[datetime]
    surgery_notes: Optional[str]
    operative_notes: Optional[str]
    post_operative_notes: Optional[str]
    complications: Optional[str]
    is_completed: bool
    completed_at: Optional[datetime]
    completed_by: Optional[int]
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/ward-admissions/{ward_admission_id}/surgeries", response_model=InpatientSurgeryResponse, status_code=status.HTTP_201_CREATED)
def create_inpatient_surgery(
    ward_admission_id: int,
    surgery_data: InpatientSurgeryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin"]))
):
    """Create a new surgery record for an inpatient"""
    from app.models.inpatient_surgery import InpatientSurgery
    from app.models.ward_admission import WardAdmission
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    surgery = InpatientSurgery(
        ward_admission_id=ward_admission_id,
        encounter_id=ward_admission.encounter_id,
        g_drg_code=surgery_data.g_drg_code,
        surgery_name=surgery_data.surgery_name,
        surgery_type=surgery_data.surgery_type,
        surgeon_name=surgery_data.surgeon_name,
        assistant_surgeon=surgery_data.assistant_surgeon,
        anesthesia_type=surgery_data.anesthesia_type,
        surgery_date=surgery_data.surgery_date,
        surgery_notes=surgery_data.surgery_notes,
        created_by=current_user.id
    )
    db.add(surgery)
    db.commit()
    db.refresh(surgery)
    
    return surgery


@router.get("/ward-admissions/{ward_admission_id}/surgeries", response_model=List[InpatientSurgeryResponse])
def get_inpatient_surgeries(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get all surgeries for a ward admission"""
    from app.models.inpatient_surgery import InpatientSurgery
    from app.models.ward_admission import WardAdmission
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    surgeries = db.query(InpatientSurgery).filter(
        InpatientSurgery.ward_admission_id == ward_admission_id
    ).order_by(InpatientSurgery.created_at.desc()).all()
    
    return surgeries


@router.get("/ward-admissions/{ward_admission_id}/surgeries/{surgery_id}", response_model=InpatientSurgeryResponse)
def get_inpatient_surgery(
    ward_admission_id: int,
    surgery_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Get a single surgery by ID"""
    from app.models.inpatient_surgery import InpatientSurgery
    from app.models.ward_admission import WardAdmission
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    surgery = db.query(InpatientSurgery).filter(
        InpatientSurgery.id == surgery_id,
        InpatientSurgery.ward_admission_id == ward_admission_id
    ).first()
    
    if not surgery:
        raise HTTPException(status_code=404, detail="Surgery not found")
    
    return surgery


@router.put("/ward-admissions/{ward_admission_id}/surgeries/{surgery_id}", response_model=InpatientSurgeryResponse)
def update_inpatient_surgery(
    ward_admission_id: int,
    surgery_id: int,
    surgery_data: InpatientSurgeryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Doctor", "PA", "Admin"]))
):
    """Update a surgery record (including completion)"""
    from app.models.inpatient_surgery import InpatientSurgery
    from app.models.ward_admission import WardAdmission
    from app.models.encounter import Encounter
    from app.models.bill import Bill, BillItem
    from app.services.price_list_service_v2 import get_price_from_all_tables
    from datetime import datetime
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    surgery = db.query(InpatientSurgery).filter(
        InpatientSurgery.id == surgery_id,
        InpatientSurgery.ward_admission_id == ward_admission_id
    ).first()
    
    if not surgery:
        raise HTTPException(status_code=404, detail="Surgery not found")
    
    # Track if surgery is being completed (was False, now True)
    was_completed = surgery.is_completed
    is_being_completed = False
    
    # Update fields
    update_data = surgery_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(surgery, field, value)
    
    # Handle completion
    if surgery_data.is_completed is not None:
        surgery.is_completed = surgery_data.is_completed
        if surgery_data.is_completed and not surgery.completed_at:
            surgery.completed_at = utcnow()
            surgery.completed_by = current_user.id
            # Check if surgery is being completed (was not completed before)
            if not was_completed:
                is_being_completed = True
        elif not surgery_data.is_completed:
            surgery.completed_at = None
            surgery.completed_by = None
    
    surgery.updated_at = utcnow()
    
    # If surgery is being completed, create bill item
    if is_being_completed and surgery.g_drg_code:
        try:
            # Get encounter to determine insurance status
            encounter = db.query(Encounter).filter(Encounter.id == surgery.encounter_id).first()
            if encounter:
                is_insured = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
                
                # Find or create an unpaid bill for this encounter
                bill = db.query(Bill).filter(
                    Bill.encounter_id == encounter.id,
                    Bill.is_paid == False
                ).first()
                
                if not bill:
                    # Create new bill
                    bill = Bill(
                        encounter_id=encounter.id,
                        patient_id=encounter.patient_id,
                        is_insured=is_insured,
                        total_amount=0.0,
                        created_by=current_user.id
                    )
                    db.add(bill)
                    db.flush()
                
                # Check if surgery item already exists for this surgery
                existing_surgery_item = db.query(BillItem).filter(
                    BillItem.bill_id == bill.id,
                    BillItem.item_code == surgery.g_drg_code,
                    BillItem.category == "surgery"
                ).first()
                
                if not existing_surgery_item:
                    # Get surgery price from SurgeryPrice table only (exclude procedure/day surgery prices)
                    from app.services.price_list_service_v2 import get_surgery_price
                    surgery_price = get_surgery_price(
                        db,
                        surgery.g_drg_code,
                        is_insured=is_insured,
                        service_type=encounter.department if encounter.department else None
                    )
                    
                    if surgery_price > 0:
                        # Create bill item for surgery
                        surgery_item = BillItem(
                            bill_id=bill.id,
                            item_code=surgery.g_drg_code,
                            item_name=f"Surgery: {surgery.surgery_name}",
                            category="surgery",
                            quantity=1.0,
                            unit_price=surgery_price,
                            total_price=surgery_price
                        )
                        db.add(surgery_item)
                        bill.total_amount += surgery_price
        except Exception as e:
            # Log error but don't fail surgery update
            import logging
            logging.error(f"Failed to create bill item for completed surgery {surgery.id}: {str(e)}")
            # Continue with surgery update even if billing fails
    
    db.commit()
    db.refresh(surgery)
    
    return surgery


@router.delete("/ward-admissions/{ward_admission_id}/surgeries/{surgery_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inpatient_surgery(
    ward_admission_id: int,
    surgery_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete a surgery record and its corresponding bill item if billed - Admin only"""
    from app.models.inpatient_surgery import InpatientSurgery
    from app.models.ward_admission import WardAdmission
    from app.models.bill import Bill, BillItem
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    surgery = db.query(InpatientSurgery).filter(
        InpatientSurgery.id == surgery_id,
        InpatientSurgery.ward_admission_id == ward_admission_id
    ).first()
    
    if not surgery:
        raise HTTPException(status_code=404, detail="Surgery not found")
    
    # If surgery has a g_drg_code, find and delete corresponding bill item
    if surgery.g_drg_code:
        # Find bill items for this surgery (by g_drg_code and category "surgery")
        bill_items = db.query(BillItem).join(Bill).filter(
            Bill.encounter_id == surgery.encounter_id,
            BillItem.item_code == surgery.g_drg_code,
            BillItem.category == "surgery"
        ).all()
        
        for bill_item in bill_items:
            bill = db.query(Bill).filter(Bill.id == bill_item.bill_id).first()
            if bill:
                # Subtract the bill item total from bill total
                bill.total_amount -= bill_item.total_price
                # Ensure bill total doesn't go negative
                if bill.total_amount < 0:
                    bill.total_amount = 0.0
            db.delete(bill_item)
    
    # Delete the surgery record
    db.delete(surgery)
    db.commit()
    return None

# Additional Services endpoints (Admin-defined services for IPD)
class AdditionalServiceCreate(BaseModel):
    service_name: str
    description: Optional[str] = None
    price_per_unit: float
    unit_type: str = "hour"  # "hour", "day", "unit"


class AdditionalServiceUpdate(BaseModel):
    service_name: Optional[str] = None
    description: Optional[str] = None
    price_per_unit: Optional[float] = None
    unit_type: Optional[str] = None
    is_active: Optional[bool] = None


class AdditionalServiceResponse(BaseModel):
    id: int
    service_name: str
    description: Optional[str]
    price_per_unit: float
    unit_type: str
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/additional-services", response_model=AdditionalServiceResponse, status_code=status.HTTP_201_CREATED)
def create_additional_service(
    service_data: AdditionalServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Create a new additional service - Admin only"""
    from app.models.additional_service import AdditionalService
    
    # Check if service with same name already exists
    existing = db.query(AdditionalService).filter(
        AdditionalService.service_name == service_data.service_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Service '{service_data.service_name}' already exists"
        )
    
    service = AdditionalService(
        service_name=service_data.service_name,
        description=service_data.description,
        price_per_unit=service_data.price_per_unit,
        unit_type=service_data.unit_type,
        created_by=current_user.id
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    
    return service


@router.get("/additional-services", response_model=List[AdditionalServiceResponse])
def get_additional_services(
    active_only: Optional[bool] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin", "Billing"]))
):
    """Get all additional services"""
    from app.models.additional_service import AdditionalService
    
    query = db.query(AdditionalService)
    
    if active_only:
        query = query.filter(AdditionalService.is_active == True)
    
    services = query.order_by(AdditionalService.service_name).all()
    return services


@router.get("/additional-services/{service_id}", response_model=AdditionalServiceResponse)
def get_additional_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin", "Billing"]))
):
    """Get a single additional service"""
    from app.models.additional_service import AdditionalService
    
    service = db.query(AdditionalService).filter(AdditionalService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Additional service not found")
    
    return service


@router.put("/additional-services/{service_id}", response_model=AdditionalServiceResponse)
def update_additional_service(
    service_id: int,
    service_data: AdditionalServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update an additional service - Admin only"""
    from app.models.additional_service import AdditionalService
    
    service = db.query(AdditionalService).filter(AdditionalService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Additional service not found")
    
    # Check if service name is being changed and conflicts with existing
    if service_data.service_name and service_data.service_name != service.service_name:
        existing = db.query(AdditionalService).filter(
            AdditionalService.service_name == service_data.service_name,
            AdditionalService.id != service_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Service '{service_data.service_name}' already exists"
            )
    
    update_data = service_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(service, field, value)
    
    service.updated_at = utcnow()
    db.commit()
    db.refresh(service)
    
    return service


@router.delete("/additional-services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_additional_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete (soft delete) an additional service - Admin only"""
    from app.models.additional_service import AdditionalService
    
    service = db.query(AdditionalService).filter(AdditionalService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Additional service not found")
    
    # Soft delete by setting is_active to False
    service.is_active = False
    service.updated_at = utcnow()
    db.commit()
    
    return None


# Blood Transfusion Type Management endpoints (Admin only)
class BloodTransfusionTypeCreate(BaseModel):
    type_name: str
    description: Optional[str] = None
    unit_price: float
    unit_type: str = "unit"  # "unit", "pack", etc.


class BloodTransfusionTypeUpdate(BaseModel):
    type_name: Optional[str] = None
    description: Optional[str] = None
    unit_price: Optional[float] = None
    unit_type: Optional[str] = None
    is_active: Optional[bool] = None


class BloodTransfusionTypeResponse(BaseModel):
    id: int
    type_name: str
    description: Optional[str]
    unit_price: float
    unit_type: str
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/blood-transfusion-types", response_model=BloodTransfusionTypeResponse, status_code=status.HTTP_201_CREATED)
def create_blood_transfusion_type(
    type_data: BloodTransfusionTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Create a new blood transfusion type - Admin only"""
    from app.models.blood_transfusion_type import BloodTransfusionType
    
    # Check if type with same name already exists
    existing = db.query(BloodTransfusionType).filter(
        BloodTransfusionType.type_name == type_data.type_name
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Blood transfusion type '{type_data.type_name}' already exists"
        )
    
    transfusion_type = BloodTransfusionType(
        type_name=type_data.type_name,
        description=type_data.description,
        unit_price=type_data.unit_price,
        unit_type=type_data.unit_type,
        created_by=current_user.id
    )
    db.add(transfusion_type)
    db.commit()
    db.refresh(transfusion_type)
    
    return transfusion_type


@router.get("/blood-transfusion-types", response_model=List[BloodTransfusionTypeResponse])
def get_blood_transfusion_types(
    active_only: Optional[bool] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin", "Lab"]))
):
    """Get all blood transfusion types"""
    from app.models.blood_transfusion_type import BloodTransfusionType
    
    query = db.query(BloodTransfusionType)
    
    if active_only:
        query = query.filter(BloodTransfusionType.is_active == True)
    
    types = query.order_by(BloodTransfusionType.type_name).all()
    return types


@router.get("/blood-transfusion-types/{type_id}", response_model=BloodTransfusionTypeResponse)
def get_blood_transfusion_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin", "Lab"]))
):
    """Get a specific blood transfusion type"""
    from app.models.blood_transfusion_type import BloodTransfusionType
    
    transfusion_type = db.query(BloodTransfusionType).filter(BloodTransfusionType.id == type_id).first()
    if not transfusion_type:
        raise HTTPException(status_code=404, detail="Blood transfusion type not found")
    
    return transfusion_type


@router.put("/blood-transfusion-types/{type_id}", response_model=BloodTransfusionTypeResponse)
def update_blood_transfusion_type(
    type_id: int,
    type_data: BloodTransfusionTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Update a blood transfusion type - Admin only"""
    from app.models.blood_transfusion_type import BloodTransfusionType
    
    transfusion_type = db.query(BloodTransfusionType).filter(BloodTransfusionType.id == type_id).first()
    if not transfusion_type:
        raise HTTPException(status_code=404, detail="Blood transfusion type not found")
    
    # Check if type name is being changed and conflicts with existing
    if type_data.type_name and type_data.type_name != transfusion_type.type_name:
        existing = db.query(BloodTransfusionType).filter(
            BloodTransfusionType.type_name == type_data.type_name,
            BloodTransfusionType.id != type_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Blood transfusion type '{type_data.type_name}' already exists"
            )
    
    update_data = type_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transfusion_type, field, value)
    
    transfusion_type.updated_at = utcnow()
    db.commit()
    db.refresh(transfusion_type)
    
    return transfusion_type


@router.delete("/blood-transfusion-types/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blood_transfusion_type(
    type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete (soft delete) a blood transfusion type - Admin only"""
    from app.models.blood_transfusion_type import BloodTransfusionType
    
    transfusion_type = db.query(BloodTransfusionType).filter(BloodTransfusionType.id == type_id).first()
    if not transfusion_type:
        raise HTTPException(status_code=404, detail="Blood transfusion type not found")
    
    # Soft delete by setting is_active to False
    transfusion_type.is_active = False
    transfusion_type.updated_at = utcnow()
    db.commit()
    
    return None


# Blood Transfusion Request endpoints
class BloodTransfusionRequestCreate(BaseModel):
    ward_admission_id: int
    encounter_id: int
    transfusion_type_id: int
    quantity: float = 1.0
    request_reason: Optional[str] = None


class BloodTransfusionRequestResponse(BaseModel):
    id: int
    ward_admission_id: int
    encounter_id: int
    transfusion_type_id: int
    transfusion_type_name: str
    quantity: float
    request_reason: Optional[str]
    status: str
    requested_by: int
    requested_by_name: Optional[str]
    accepted_by: Optional[int]
    accepted_by_name: Optional[str]
    fulfilled_by: Optional[int]
    fulfilled_by_name: Optional[str]
    returned_by: Optional[int]
    returned_by_name: Optional[str]
    bill_item_id: Optional[int]
    return_bill_item_id: Optional[int]
    requested_at: datetime
    accepted_at: Optional[datetime]
    fulfilled_at: Optional[datetime]
    returned_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancellation_reason: Optional[str]
    patient_name: str
    patient_card_number: str
    ward: str
    unit_price: float
    total_price: float
    
    class Config:
        from_attributes = True


@router.post("/blood-transfusion-requests", response_model=BloodTransfusionRequestResponse, status_code=status.HTTP_201_CREATED)
def create_blood_transfusion_request(
    request_data: BloodTransfusionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Create a new blood transfusion request"""
    from app.models.blood_transfusion_request import BloodTransfusionRequest
    from app.models.blood_transfusion_type import BloodTransfusionType
    from app.models.ward_admission import WardAdmission
    from app.models.encounter import Encounter
    
    # Verify ward admission exists
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == request_data.ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    # Verify encounter exists and matches
    encounter = db.query(Encounter).filter(Encounter.id == request_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    if encounter.id != ward_admission.encounter_id:
        raise HTTPException(status_code=400, detail="Encounter does not match ward admission")
    
    # Verify transfusion type exists and is active
    transfusion_type = db.query(BloodTransfusionType).filter(BloodTransfusionType.id == request_data.transfusion_type_id).first()
    if not transfusion_type:
        raise HTTPException(status_code=404, detail="Blood transfusion type not found")
    
    if not transfusion_type.is_active:
        raise HTTPException(status_code=400, detail="Blood transfusion type is not active")
    
    # Create request
    blood_request = BloodTransfusionRequest(
        ward_admission_id=request_data.ward_admission_id,
        encounter_id=request_data.encounter_id,
        transfusion_type_id=request_data.transfusion_type_id,
        quantity=request_data.quantity,
        request_reason=request_data.request_reason,
        status="pending",
        requested_by=current_user.id
    )
    db.add(blood_request)
    db.commit()
    db.refresh(blood_request)
    
    # Load relationships for response
    patient = encounter.patient
    requester = db.query(User).filter(User.id == current_user.id).first()
    
    return {
        "id": blood_request.id,
        "ward_admission_id": blood_request.ward_admission_id,
        "encounter_id": blood_request.encounter_id,
        "transfusion_type_id": blood_request.transfusion_type_id,
        "transfusion_type_name": transfusion_type.type_name,
        "quantity": blood_request.quantity,
        "request_reason": blood_request.request_reason,
        "status": blood_request.status,
        "requested_by": blood_request.requested_by,
        "requested_by_name": requester.full_name if requester else None,
        "accepted_by": None,
        "accepted_by_name": None,
        "fulfilled_by": None,
        "fulfilled_by_name": None,
        "returned_by": None,
        "returned_by_name": None,
        "bill_item_id": None,
        "return_bill_item_id": None,
        "requested_at": blood_request.requested_at,
        "accepted_at": None,
        "fulfilled_at": None,
        "returned_at": None,
        "cancelled_at": None,
        "cancellation_reason": None,
        "patient_name": f"{patient.name} {patient.surname or ''}".strip(),
        "patient_card_number": patient.card_number or "",
        "ward": ward_admission.ward,
        "unit_price": transfusion_type.unit_price,
        "total_price": transfusion_type.unit_price * blood_request.quantity,
    }


@router.get("/blood-transfusion-requests", response_model=List[BloodTransfusionRequestResponse])
def get_blood_transfusion_requests(
    status: Optional[str] = Query(None),  # Filter by status: pending, accepted, fulfilled, returned, cancelled
    ward: Optional[str] = Query(None),  # Filter by ward
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin", "Lab"]))
):
    """Get blood transfusion requests"""
    from app.models.blood_transfusion_request import BloodTransfusionRequest
    from app.models.ward_admission import WardAdmission
    from sqlalchemy.orm import joinedload
    
    query = db.query(BloodTransfusionRequest).options(
        joinedload(BloodTransfusionRequest.transfusion_type),
        joinedload(BloodTransfusionRequest.ward_admission).joinedload(WardAdmission.encounter).joinedload(Encounter.patient),
        joinedload(BloodTransfusionRequest.requester),
        joinedload(BloodTransfusionRequest.accepter),
        joinedload(BloodTransfusionRequest.fulfiller),
        joinedload(BloodTransfusionRequest.returner)
    )
    
    if status:
        query = query.filter(BloodTransfusionRequest.status == status)
    
    if ward:
        query = query.join(WardAdmission).filter(WardAdmission.ward == ward)
    
    requests = query.order_by(BloodTransfusionRequest.requested_at.desc()).all()
    
    result = []
    for req in requests:
        patient = req.ward_admission.encounter.patient if req.ward_admission and req.ward_admission.encounter else None
        if not patient:
            continue
        
        result.append({
            "id": req.id,
            "ward_admission_id": req.ward_admission_id,
            "encounter_id": req.encounter_id,
            "transfusion_type_id": req.transfusion_type_id,
            "transfusion_type_name": req.transfusion_type.type_name if req.transfusion_type else "",
            "quantity": req.quantity,
            "request_reason": req.request_reason,
            "status": req.status,
            "requested_by": req.requested_by,
            "requested_by_name": req.requester.full_name if req.requester else None,
            "accepted_by": req.accepted_by,
            "accepted_by_name": req.accepter.full_name if req.accepter else None,
            "fulfilled_by": req.fulfilled_by,
            "fulfilled_by_name": req.fulfiller.full_name if req.fulfiller else None,
            "returned_by": req.returned_by,
            "returned_by_name": req.returner.full_name if req.returner else None,
            "bill_item_id": req.bill_item_id,
            "return_bill_item_id": req.return_bill_item_id,
            "requested_at": req.requested_at,
            "accepted_at": req.accepted_at,
            "fulfilled_at": req.fulfilled_at,
            "returned_at": req.returned_at,
            "cancelled_at": req.cancelled_at,
            "cancellation_reason": req.cancellation_reason,
            "patient_name": f"{patient.name} {patient.surname or ''}".strip(),
            "patient_card_number": patient.card_number or "",
            "ward": req.ward_admission.ward if req.ward_admission else "",
            "unit_price": req.transfusion_type.unit_price if req.transfusion_type else 0.0,
            "total_price": (req.transfusion_type.unit_price * req.quantity) if req.transfusion_type else 0.0,
        })
    
    return result


@router.post("/blood-transfusion-requests/{request_id}/accept", response_model=BloodTransfusionRequestResponse)
def accept_blood_transfusion_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Admin"]))
):
    """Accept a blood transfusion request - Lab only. Creates bill item. Can accept pending or returned requests."""
    from app.models.blood_transfusion_request import BloodTransfusionRequest
    from app.models.bill import Bill, BillItem
    from app.models.encounter import Encounter
    
    blood_request = db.query(BloodTransfusionRequest).filter(BloodTransfusionRequest.id == request_id).first()
    if not blood_request:
        raise HTTPException(status_code=404, detail="Blood transfusion request not found")
    
    if blood_request.status not in ["pending"]:
        raise HTTPException(status_code=400, detail=f"Cannot accept request with status '{blood_request.status}'. Only pending requests can be accepted.")
    
    # If this was previously returned, we need to create a new bill item (the old one was credited)
    # If it's a new request, create the first bill item
    create_new_bill_item = True
    if blood_request.bill_item_id:
        # Check if the original bill item still exists
        existing_bill_item = db.query(BillItem).filter(BillItem.id == blood_request.bill_item_id).first()
        if existing_bill_item and existing_bill_item.total_price > 0:
            # Original bill item exists and wasn't credited, reuse it
            create_new_bill_item = False
    
    # Get encounter to check if patient is insured
    encounter = db.query(Encounter).filter(Encounter.id == blood_request.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    is_insured = bool(encounter.ccc_number and encounter.ccc_number.strip())
    
    # Get or create bill for encounter
    bill = db.query(Bill).filter(Bill.encounter_id == blood_request.encounter_id).first()
    if not bill:
        # Create new bill
        import random
        bill_number = f"BILL-{random.randint(100000, 999999)}"
        bill = Bill(
            encounter_id=blood_request.encounter_id,
            bill_number=bill_number,
            total_amount=0.0,
            is_insured=is_insured,
            created_by=current_user.id
        )
        db.add(bill)
        db.flush()
    
    # Calculate price (use base rate for cash, co-payment for insured)
    unit_price = blood_request.transfusion_type.unit_price
    total_price = unit_price * blood_request.quantity
    
    if create_new_bill_item:
        # Create new bill item
        bill_item = BillItem(
            bill_id=bill.id,
            item_code=f"BLOOD-{blood_request.transfusion_type.type_name.upper().replace(' ', '-')}",
            item_name=f"{blood_request.transfusion_type.type_name} ({blood_request.quantity} {blood_request.transfusion_type.unit_type})",
            category="other",
            quantity=blood_request.quantity,
            unit_price=unit_price,
            total_price=total_price
        )
        db.add(bill_item)
        db.flush()
        
        # Update bill total
        bill.total_amount += total_price
        db.flush()
        
        # Update request status
        blood_request.status = "accepted"
        blood_request.accepted_by = current_user.id
        blood_request.accepted_at = utcnow()
        blood_request.bill_item_id = bill_item.id
    else:
        # Reuse existing bill item - just update status
        bill_item = db.query(BillItem).filter(BillItem.id == blood_request.bill_item_id).first()
        # Update request status
        blood_request.status = "accepted"
        blood_request.accepted_by = current_user.id
        blood_request.accepted_at = utcnow()
    
    db.commit()
    db.refresh(blood_request)
    
    # Load relationships for response
    from sqlalchemy.orm import joinedload
    from app.models.ward_admission import WardAdmission
    blood_request = db.query(BloodTransfusionRequest).options(
        joinedload(BloodTransfusionRequest.transfusion_type),
        joinedload(BloodTransfusionRequest.ward_admission).joinedload(WardAdmission.encounter).joinedload(Encounter.patient),
        joinedload(BloodTransfusionRequest.requester),
        joinedload(BloodTransfusionRequest.accepter)
    ).filter(BloodTransfusionRequest.id == request_id).first()
    
    patient = blood_request.ward_admission.encounter.patient if blood_request.ward_admission and blood_request.ward_admission.encounter else None
    
    return {
        "id": blood_request.id,
        "ward_admission_id": blood_request.ward_admission_id,
        "encounter_id": blood_request.encounter_id,
        "transfusion_type_id": blood_request.transfusion_type_id,
        "transfusion_type_name": blood_request.transfusion_type.type_name if blood_request.transfusion_type else "",
        "quantity": blood_request.quantity,
        "request_reason": blood_request.request_reason,
        "status": blood_request.status,
        "requested_by": blood_request.requested_by,
        "requested_by_name": blood_request.requester.full_name if blood_request.requester else None,
        "accepted_by": blood_request.accepted_by,
        "accepted_by_name": blood_request.accepter.full_name if blood_request.accepter else None,
        "fulfilled_by": None,
        "fulfilled_by_name": None,
        "returned_by": None,
        "returned_by_name": None,
        "bill_item_id": blood_request.bill_item_id,
        "return_bill_item_id": None,
        "requested_at": blood_request.requested_at,
        "accepted_at": blood_request.accepted_at,
        "fulfilled_at": None,
        "returned_at": None,
        "cancelled_at": None,
        "cancellation_reason": None,
        "patient_name": f"{patient.name} {patient.surname or ''}".strip() if patient else "",
        "patient_card_number": patient.card_number or "" if patient else "",
        "ward": blood_request.ward_admission.ward if blood_request.ward_admission else "",
        "unit_price": blood_request.transfusion_type.unit_price if blood_request.transfusion_type else 0.0,
        "total_price": (blood_request.transfusion_type.unit_price * blood_request.quantity) if blood_request.transfusion_type else 0.0,
    }


@router.post("/blood-transfusion-requests/{request_id}/fulfill", response_model=BloodTransfusionRequestResponse)
def fulfill_blood_transfusion_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Admin"]))
):
    """Fulfill a blood transfusion request - Lab only"""
    from app.models.blood_transfusion_request import BloodTransfusionRequest
    
    blood_request = db.query(BloodTransfusionRequest).filter(BloodTransfusionRequest.id == request_id).first()
    if not blood_request:
        raise HTTPException(status_code=404, detail="Blood transfusion request not found")
    
    if blood_request.status != "accepted":
        raise HTTPException(status_code=400, detail=f"Cannot fulfill request with status '{blood_request.status}'. Must be 'accepted'.")
    
    blood_request.status = "fulfilled"
    blood_request.fulfilled_by = current_user.id
    blood_request.fulfilled_at = utcnow()
    db.commit()
    db.refresh(blood_request)
    
    # Load relationships for response
    from sqlalchemy.orm import joinedload
    from app.models.ward_admission import WardAdmission
    blood_request = db.query(BloodTransfusionRequest).options(
        joinedload(BloodTransfusionRequest.transfusion_type),
        joinedload(BloodTransfusionRequest.ward_admission).joinedload(WardAdmission.encounter).joinedload(Encounter.patient),
        joinedload(BloodTransfusionRequest.requester),
        joinedload(BloodTransfusionRequest.accepter),
        joinedload(BloodTransfusionRequest.fulfiller)
    ).filter(BloodTransfusionRequest.id == request_id).first()
    
    patient = blood_request.ward_admission.encounter.patient if blood_request.ward_admission and blood_request.ward_admission.encounter else None
    
    return {
        "id": blood_request.id,
        "ward_admission_id": blood_request.ward_admission_id,
        "encounter_id": blood_request.encounter_id,
        "transfusion_type_id": blood_request.transfusion_type_id,
        "transfusion_type_name": blood_request.transfusion_type.type_name if blood_request.transfusion_type else "",
        "quantity": blood_request.quantity,
        "request_reason": blood_request.request_reason,
        "status": blood_request.status,
        "requested_by": blood_request.requested_by,
        "requested_by_name": blood_request.requester.full_name if blood_request.requester else None,
        "accepted_by": blood_request.accepted_by,
        "accepted_by_name": blood_request.accepter.full_name if blood_request.accepter else None,
        "fulfilled_by": blood_request.fulfilled_by,
        "fulfilled_by_name": blood_request.fulfiller.full_name if blood_request.fulfiller else None,
        "returned_by": None,
        "returned_by_name": None,
        "bill_item_id": blood_request.bill_item_id,
        "return_bill_item_id": None,
        "requested_at": blood_request.requested_at,
        "accepted_at": blood_request.accepted_at,
        "fulfilled_at": blood_request.fulfilled_at,
        "returned_at": None,
        "cancelled_at": None,
        "cancellation_reason": None,
        "patient_name": f"{patient.name} {patient.surname or ''}".strip() if patient else "",
        "patient_card_number": patient.card_number or "" if patient else "",
        "ward": blood_request.ward_admission.ward if blood_request.ward_admission else "",
        "unit_price": blood_request.transfusion_type.unit_price if blood_request.transfusion_type else 0.0,
        "total_price": (blood_request.transfusion_type.unit_price * blood_request.quantity) if blood_request.transfusion_type else 0.0,
    }


class CancelBloodRequestRequest(BaseModel):
    cancellation_reason: Optional[str] = None


@router.post("/blood-transfusion-requests/{request_id}/cancel", response_model=BloodTransfusionRequestResponse)
def cancel_blood_transfusion_request(
    request_id: int,
    cancel_data: CancelBloodRequestRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Cancel a blood transfusion request - Normal users can cancel their own requests, Admin can cancel any"""
    from app.models.blood_transfusion_request import BloodTransfusionRequest
    
    blood_request = db.query(BloodTransfusionRequest).filter(BloodTransfusionRequest.id == request_id).first()
    if not blood_request:
        raise HTTPException(status_code=404, detail="Blood transfusion request not found")
    
    # Normal users can only cancel their own pending requests
    if current_user.role != "Admin":
        if blood_request.requested_by != current_user.id:
            raise HTTPException(status_code=403, detail="You can only cancel your own requests")
        if blood_request.status != "pending":
            raise HTTPException(status_code=400, detail=f"Cannot cancel request with status '{blood_request.status}'. Only pending requests can be cancelled.")
    else:
        # Admin can cancel any request that hasn't been fulfilled or returned
        if blood_request.status in ["fulfilled", "returned"]:
            raise HTTPException(status_code=400, detail=f"Cannot cancel request with status '{blood_request.status}'")
    
    blood_request.status = "cancelled"
    blood_request.cancelled_at = utcnow()
    blood_request.cancellation_reason = cancel_data.cancellation_reason
    db.commit()
    db.refresh(blood_request)
    
    # Load relationships for response
    from sqlalchemy.orm import joinedload
    from app.models.ward_admission import WardAdmission
    blood_request = db.query(BloodTransfusionRequest).options(
        joinedload(BloodTransfusionRequest.transfusion_type),
        joinedload(BloodTransfusionRequest.ward_admission).joinedload(WardAdmission.encounter).joinedload(Encounter.patient),
        joinedload(BloodTransfusionRequest.requester),
        joinedload(BloodTransfusionRequest.accepter),
        joinedload(BloodTransfusionRequest.fulfiller),
        joinedload(BloodTransfusionRequest.returner)
    ).filter(BloodTransfusionRequest.id == request_id).first()
    
    patient = blood_request.ward_admission.encounter.patient if blood_request.ward_admission and blood_request.ward_admission.encounter else None
    
    return {
        "id": blood_request.id,
        "ward_admission_id": blood_request.ward_admission_id,
        "encounter_id": blood_request.encounter_id,
        "transfusion_type_id": blood_request.transfusion_type_id,
        "transfusion_type_name": blood_request.transfusion_type.type_name if blood_request.transfusion_type else "",
        "quantity": blood_request.quantity,
        "request_reason": blood_request.request_reason,
        "status": blood_request.status,
        "requested_by": blood_request.requested_by,
        "requested_by_name": blood_request.requester.full_name if blood_request.requester else None,
        "accepted_by": blood_request.accepted_by,
        "accepted_by_name": blood_request.accepter.full_name if blood_request.accepter else None,
        "fulfilled_by": blood_request.fulfilled_by,
        "fulfilled_by_name": blood_request.fulfiller.full_name if blood_request.fulfiller else None,
        "returned_by": blood_request.returned_by,
        "returned_by_name": blood_request.returner.full_name if blood_request.returner else None,
        "bill_item_id": blood_request.bill_item_id,
        "return_bill_item_id": blood_request.return_bill_item_id,
        "requested_at": blood_request.requested_at,
        "accepted_at": blood_request.accepted_at,
        "fulfilled_at": blood_request.fulfilled_at,
        "returned_at": blood_request.returned_at,
        "cancelled_at": blood_request.cancelled_at,
        "cancellation_reason": blood_request.cancellation_reason,
        "patient_name": f"{patient.name} {patient.surname or ''}".strip() if patient else "",
        "patient_card_number": patient.card_number or "" if patient else "",
        "ward": blood_request.ward_admission.ward if blood_request.ward_admission else "",
        "unit_price": blood_request.transfusion_type.unit_price if blood_request.transfusion_type else 0.0,
        "total_price": (blood_request.transfusion_type.unit_price * blood_request.quantity) if blood_request.transfusion_type else 0.0,
    }


@router.delete("/blood-transfusion-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_blood_transfusion_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Delete a blood transfusion request - Admin only. Permanently removes the request."""
    from app.models.blood_transfusion_request import BloodTransfusionRequest
    
    blood_request = db.query(BloodTransfusionRequest).filter(BloodTransfusionRequest.id == request_id).first()
    if not blood_request:
        raise HTTPException(status_code=404, detail="Blood transfusion request not found")
    
    # Only allow deletion if request is cancelled or pending (not accepted/fulfilled/returned)
    if blood_request.status not in ["pending", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete request with status '{blood_request.status}'. Only pending or cancelled requests can be deleted."
        )
    
    db.delete(blood_request)
    db.commit()
    
    return None


@router.post("/blood-transfusion-requests/{request_id}/return", response_model=BloodTransfusionRequestResponse)
def return_blood_transfusion_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"]))
):
    """Return blood transfusion - Admin only. Creates return bill item (credit). After return, request can be accepted again."""
    from app.models.blood_transfusion_request import BloodTransfusionRequest
    from app.models.bill import Bill, BillItem
    from app.models.encounter import Encounter
    
    blood_request = db.query(BloodTransfusionRequest).filter(BloodTransfusionRequest.id == request_id).first()
    if not blood_request:
        raise HTTPException(status_code=404, detail="Blood transfusion request not found")
    
    if blood_request.status not in ["accepted", "fulfilled"]:
        raise HTTPException(status_code=400, detail=f"Cannot return request with status '{blood_request.status}'")
    
    # Get encounter to check if patient is insured
    encounter = db.query(Encounter).filter(Encounter.id == blood_request.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    is_insured = bool(encounter.ccc_number and encounter.ccc_number.strip())
    
    # Get bill
    bill = db.query(Bill).filter(Bill.encounter_id == blood_request.encounter_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")
    
    # Calculate return price (negative amount)
    unit_price = blood_request.transfusion_type.unit_price
    return_total_price = -(unit_price * blood_request.quantity)  # Negative for credit
    
    # Create return bill item (credit)
    return_bill_item = BillItem(
        bill_id=bill.id,
        item_code=f"BLOOD-RETURN-{blood_request.transfusion_type.type_name.upper().replace(' ', '-')}",
        item_name=f"Return: {blood_request.transfusion_type.type_name} ({blood_request.quantity} {blood_request.transfusion_type.unit_type})",
        category="other",
        quantity=blood_request.quantity,
        unit_price=-unit_price,  # Negative unit price
        total_price=return_total_price  # Negative total
    )
    db.add(return_bill_item)
    db.flush()
    
    # Update bill total (subtract the return amount)
    bill.total_amount += return_total_price  # Adding negative = subtracting
    db.flush()
    
    # Update request status - set to "pending" so it can be accepted again
    blood_request.status = "pending"
    blood_request.returned_by = current_user.id
    blood_request.returned_at = utcnow()
    blood_request.return_bill_item_id = return_bill_item.id
    # Reset accepted/fulfilled fields so it can be re-accepted
    blood_request.accepted_by = None
    blood_request.accepted_at = None
    blood_request.fulfilled_by = None
    blood_request.fulfilled_at = None
    # Keep the original bill_item_id for reference, but we'll create a new one if accepted again
    db.commit()
    db.refresh(blood_request)
    
    # Load relationships for response
    from sqlalchemy.orm import joinedload
    from app.models.ward_admission import WardAdmission
    blood_request = db.query(BloodTransfusionRequest).options(
        joinedload(BloodTransfusionRequest.transfusion_type),
        joinedload(BloodTransfusionRequest.ward_admission).joinedload(WardAdmission.encounter).joinedload(Encounter.patient),
        joinedload(BloodTransfusionRequest.requester),
        joinedload(BloodTransfusionRequest.accepter),
        joinedload(BloodTransfusionRequest.fulfiller),
        joinedload(BloodTransfusionRequest.returner)
    ).filter(BloodTransfusionRequest.id == request_id).first()
    
    patient = blood_request.ward_admission.encounter.patient if blood_request.ward_admission and blood_request.ward_admission.encounter else None
    
    return {
        "id": blood_request.id,
        "ward_admission_id": blood_request.ward_admission_id,
        "encounter_id": blood_request.encounter_id,
        "transfusion_type_id": blood_request.transfusion_type_id,
        "transfusion_type_name": blood_request.transfusion_type.type_name if blood_request.transfusion_type else "",
        "quantity": blood_request.quantity,
        "request_reason": blood_request.request_reason,
        "status": blood_request.status,
        "requested_by": blood_request.requested_by,
        "requested_by_name": blood_request.requester.full_name if blood_request.requester else None,
        "accepted_by": blood_request.accepted_by,
        "accepted_by_name": blood_request.accepter.full_name if blood_request.accepter else None,
        "fulfilled_by": blood_request.fulfilled_by,
        "fulfilled_by_name": blood_request.fulfiller.full_name if blood_request.fulfiller else None,
        "returned_by": blood_request.returned_by,
        "returned_by_name": blood_request.returner.full_name if blood_request.returner else None,
        "bill_item_id": blood_request.bill_item_id,
        "return_bill_item_id": blood_request.return_bill_item_id,
        "requested_at": blood_request.requested_at,
        "accepted_at": blood_request.accepted_at,
        "fulfilled_at": blood_request.fulfilled_at,
        "returned_at": blood_request.returned_at,
        "cancelled_at": blood_request.cancelled_at,
        "cancellation_reason": blood_request.cancellation_reason,
        "patient_name": f"{patient.name} {patient.surname or ''}".strip() if patient else "",
        "patient_card_number": patient.card_number or "" if patient else "",
        "ward": blood_request.ward_admission.ward if blood_request.ward_admission else "",
        "unit_price": blood_request.transfusion_type.unit_price if blood_request.transfusion_type else 0.0,
        "total_price": (blood_request.transfusion_type.unit_price * blood_request.quantity) if blood_request.transfusion_type else 0.0,
    }


# Inpatient Additional Service Usage endpoints
class InpatientAdditionalServiceCreate(BaseModel):
    service_id: int
    start_time: Optional[datetime] = None  # Defaults to now if not provided
    notes: Optional[str] = None


class InpatientAdditionalServiceStop(BaseModel):
    end_time: Optional[datetime] = None  # Defaults to now if not provided
    notes: Optional[str] = None


class InpatientAdditionalServiceResponse(BaseModel):
    id: int
    ward_admission_id: int
    encounter_id: int
    service_id: int
    service_name: str
    service_price_per_unit: float
    service_unit_type: str
    start_time: datetime
    end_time: Optional[datetime]
    units_used: Optional[float]
    total_cost: Optional[float]
    is_billed: bool
    bill_item_id: Optional[int]
    notes: Optional[str]
    started_by: int
    started_by_name: Optional[str]
    stopped_by: Optional[int]
    stopped_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


@router.post("/ward-admissions/{ward_admission_id}/additional-services", response_model=InpatientAdditionalServiceResponse, status_code=status.HTTP_201_CREATED)
def start_additional_service(
    ward_admission_id: int,
    service_data: InpatientAdditionalServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Start an additional service for a patient"""
    from app.models.inpatient_additional_service import InpatientAdditionalService
    from app.models.additional_service import AdditionalService
    from app.models.ward_admission import WardAdmission
    from datetime import datetime
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    service = db.query(AdditionalService).filter(
        AdditionalService.id == service_data.service_id,
        AdditionalService.is_active == True
    ).first()
    if not service:
        raise HTTPException(status_code=404, detail="Additional service not found or inactive")
    
    start_time = service_data.start_time or utcnow()
    
    patient_service = InpatientAdditionalService(
        ward_admission_id=ward_admission_id,
        encounter_id=ward_admission.encounter_id,
        service_id=service_data.service_id,
        start_time=start_time,
        notes=service_data.notes,
        started_by=current_user.id
    )
    db.add(patient_service)
    db.commit()
    db.refresh(patient_service)
    
    # Load relationships for response
    starter = db.query(User).filter(User.id == patient_service.started_by).first()
    
    return {
        "id": patient_service.id,
        "ward_admission_id": patient_service.ward_admission_id,
        "encounter_id": patient_service.encounter_id,
        "service_id": patient_service.service_id,
        "service_name": service.service_name,
        "service_price_per_unit": service.price_per_unit,
        "service_unit_type": service.unit_type,
        "start_time": patient_service.start_time,
        "end_time": patient_service.end_time,
        "units_used": patient_service.units_used,
        "total_cost": patient_service.total_cost,
        "is_billed": patient_service.is_billed,
        "bill_item_id": patient_service.bill_item_id,
        "notes": patient_service.notes,
        "started_by": patient_service.started_by,
        "started_by_name": starter.full_name if starter else None,
        "stopped_by": patient_service.stopped_by,
        "stopped_by_name": None,
        "created_at": patient_service.created_at,
        "updated_at": patient_service.updated_at,
    }


@router.get("/ward-admissions/{ward_admission_id}/additional-services", response_model=List[InpatientAdditionalServiceResponse])
def get_inpatient_additional_services(
    ward_admission_id: int,
    active_only: Optional[bool] = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin", "Billing"]))
):
    """Get all additional services for a ward admission"""
    from app.models.inpatient_additional_service import InpatientAdditionalService
    from app.models.additional_service import AdditionalService
    from app.models.ward_admission import WardAdmission
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    query = db.query(InpatientAdditionalService).filter(
        InpatientAdditionalService.ward_admission_id == ward_admission_id
    )
    
    if active_only:
        query = query.filter(InpatientAdditionalService.end_time.is_(None))
    
    services = query.order_by(InpatientAdditionalService.start_time.desc()).all()
    
    result = []
    for patient_service in services:
        service = db.query(AdditionalService).filter(AdditionalService.id == patient_service.service_id).first()
        starter = db.query(User).filter(User.id == patient_service.started_by).first()
        stopper = db.query(User).filter(User.id == patient_service.stopped_by).first() if patient_service.stopped_by else None
        
        result.append({
            "id": patient_service.id,
            "ward_admission_id": patient_service.ward_admission_id,
            "encounter_id": patient_service.encounter_id,
            "service_id": patient_service.service_id,
            "service_name": service.service_name if service else "Unknown",
            "service_price_per_unit": service.price_per_unit if service else 0,
            "service_unit_type": service.unit_type if service else "hour",
            "start_time": patient_service.start_time,
            "end_time": patient_service.end_time,
            "units_used": patient_service.units_used,
            "total_cost": patient_service.total_cost,
            "is_billed": patient_service.is_billed,
            "bill_item_id": patient_service.bill_item_id,
            "notes": patient_service.notes,
            "started_by": patient_service.started_by,
            "started_by_name": starter.full_name if starter else None,
            "stopped_by": patient_service.stopped_by,
            "stopped_by_name": stopper.full_name if stopper else None,
            "created_at": patient_service.created_at,
            "updated_at": patient_service.updated_at,
        })
    
    return result


@router.put("/ward-admissions/{ward_admission_id}/additional-services/{service_usage_id}/stop", response_model=InpatientAdditionalServiceResponse)
def stop_additional_service(
    ward_admission_id: int,
    service_usage_id: int,
    stop_data: InpatientAdditionalServiceStop,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Stop an additional service and automatically bill the patient"""
    from app.models.inpatient_additional_service import InpatientAdditionalService
    from app.models.additional_service import AdditionalService
    from app.models.ward_admission import WardAdmission
    from app.models.bill import Bill, BillItem
    from datetime import datetime, timedelta, timezone
    import random
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    patient_service = db.query(InpatientAdditionalService).filter(
        InpatientAdditionalService.id == service_usage_id,
        InpatientAdditionalService.ward_admission_id == ward_admission_id
    ).first()
    
    if not patient_service:
        raise HTTPException(status_code=404, detail="Service usage not found")
    
    if patient_service.end_time is not None:
        raise HTTPException(status_code=400, detail="Service has already been stopped")
    
    service = db.query(AdditionalService).filter(AdditionalService.id == patient_service.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Additional service not found")
    
    # Calculate end time - normalize to naive UTC datetime
    if stop_data.end_time:
        # If end_time is provided, parse it and ensure it's naive
        if isinstance(stop_data.end_time, str):
            # Parse ISO format datetime string
            try:
                end_time = datetime.fromisoformat(stop_data.end_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                # Fallback to simple parsing
                end_time = datetime.strptime(stop_data.end_time.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
        else:
            end_time = stop_data.end_time
        
        # Convert to naive UTC if timezone-aware
        if end_time.tzinfo is not None:
            # Convert to UTC first, then remove timezone info
            end_time = end_time.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        end_time = utcnow()
    
    # Ensure start_time is also naive for comparison
    start_time = patient_service.start_time
    if hasattr(start_time, 'tzinfo') and start_time.tzinfo is not None:
        start_time = start_time.astimezone(timezone.utc).replace(tzinfo=None)
    
    # Calculate units used based on unit_type
    time_diff = end_time - start_time
    
    if service.unit_type == "hour":
        units_used = max(1, round(time_diff.total_seconds() / 3600, 2))  # Round to 2 decimals, minimum 1 hour
    elif service.unit_type == "day":
        units_used = max(1, round(time_diff.total_seconds() / 86400, 2))  # Round to 2 decimals, minimum 1 day
    else:  # "unit"
        units_used = 1
    
    total_cost = round(units_used * service.price_per_unit, 2)
    
    # Update patient service
    patient_service.end_time = end_time
    patient_service.units_used = units_used
    patient_service.total_cost = total_cost
    patient_service.stopped_by = current_user.id
    if stop_data.notes:
        patient_service.notes = (patient_service.notes or "") + f"\n{stop_data.notes}" if patient_service.notes else stop_data.notes
    
    # Auto-bill: Add to patient's bill
    is_insured = ward_admission.ccc_number is not None and ward_admission.ccc_number.strip() != ""
    
    # Get or create bill for this encounter
    bill = db.query(Bill).filter(
        Bill.encounter_id == ward_admission.encounter_id,
        Bill.is_paid == False
    ).first()
    
    if not bill:
        bill_number = f"BILL-{random.randint(100000, 999999)}"
        bill = Bill(
            encounter_id=ward_admission.encounter_id,
            bill_number=bill_number,
            is_insured=is_insured,
            created_by=current_user.id
        )
        db.add(bill)
        db.flush()
    
    # Create bill item
    bill_item = BillItem(
        bill_id=bill.id,
        item_code=f"ADD-SVC-{service.id}" if service.id else "MISC",
        item_name=f"{service.service_name} ({units_used} {service.unit_type}(s))",
        category="other",
        quantity=units_used,
        unit_price=service.price_per_unit,
        total_price=total_cost
    )
    db.add(bill_item)
    db.flush()
    
    # Link bill item to patient service
    patient_service.bill_item_id = bill_item.id
    patient_service.is_billed = True
    
    # Update bill total
    bill.total_amount += total_cost
    
    db.commit()
    db.refresh(patient_service)
    
    # Load relationships for response
    starter = db.query(User).filter(User.id == patient_service.started_by).first()
    stopper = db.query(User).filter(User.id == patient_service.stopped_by).first()
    
    return {
        "id": patient_service.id,
        "ward_admission_id": patient_service.ward_admission_id,
        "encounter_id": patient_service.encounter_id,
        "service_id": patient_service.service_id,
        "service_name": service.service_name,
        "service_price_per_unit": service.price_per_unit,
        "service_unit_type": service.unit_type,
        "start_time": patient_service.start_time,
        "end_time": patient_service.end_time,
        "units_used": patient_service.units_used,
        "total_cost": patient_service.total_cost,
        "is_billed": patient_service.is_billed,
        "bill_item_id": patient_service.bill_item_id,
        "notes": patient_service.notes,
        "started_by": patient_service.started_by,
        "started_by_name": starter.full_name if starter else None,
        "stopped_by": patient_service.stopped_by,
        "stopped_by_name": stopper.full_name if stopper else None,
        "created_at": patient_service.created_at,
        "updated_at": patient_service.updated_at,
    }


# Inventory Debit endpoints
class InpatientInventoryDebitCreate(BaseModel):
    product_code: str
    product_name: str
    quantity: float = 1.0
    unit_price: Optional[float] = None  # If not provided, will be looked up from price list
    notes: Optional[str] = None


class InpatientInventoryDebitResponse(BaseModel):
    id: int
    ward_admission_id: int
    encounter_id: int
    product_code: str
    product_name: str
    quantity: float
    unit_price: float
    total_price: float
    notes: Optional[str] = None
    is_billed: bool
    bill_item_id: Optional[int] = None
    is_released: Optional[bool] = False
    released_by: Optional[int] = None
    released_by_name: Optional[str] = None
    released_at: Optional[datetime] = None
    used_by: int
    used_by_name: Optional[str] = None
    used_at: datetime
    created_at: datetime
    updated_at: datetime
    # Additional fields for pharmacy view
    patient_name: Optional[str] = None
    patient_card_number: Optional[str] = None
    ward: Optional[str] = None  # Current ward (for backward compatibility)
    requesting_ward: Optional[str] = None  # Original ward that requested the inventory
    admitted_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


@router.post("/ward-admissions/{ward_admission_id}/inventory-debits", response_model=InpatientInventoryDebitResponse, status_code=status.HTTP_201_CREATED)
def create_inpatient_inventory_debit(
    ward_admission_id: int,
    debit_data: InpatientInventoryDebitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Add an inventory debit (product used) for a ward admission"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_inventory_debit import InpatientInventoryDebit
    from app.models.encounter import Encounter
    from app.models.bill import Bill, BillItem
    from app.services.price_list_service_v2 import get_price_from_all_tables
    import random
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    encounter = db.query(Encounter).filter(Encounter.id == ward_admission.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Determine if insured based on encounter CCC number
    is_insured_encounter = encounter.ccc_number is not None and encounter.ccc_number.strip() != ""
    
    # Get unit price - use provided price or look up from price list
    if debit_data.unit_price is not None:
        unit_price = debit_data.unit_price
    else:
        # Look up price from price list
        unit_price = get_price_from_all_tables(db, debit_data.product_code, is_insured_encounter)
        if unit_price == 0.0:
            raise HTTPException(
                status_code=400,
                detail=f"Product '{debit_data.product_name}' not found in price list or has no price. Please provide unit_price."
            )
    
    total_price = unit_price * debit_data.quantity
    
    # Create inventory debit record
    # Store the current ward as requesting_ward to preserve it even if patient is transferred
    inventory_debit = InpatientInventoryDebit(
        ward_admission_id=ward_admission_id,
        encounter_id=ward_admission.encounter_id,
        requesting_ward=ward_admission.ward,  # Store original ward at time of debit
        product_code=debit_data.product_code,
        product_name=debit_data.product_name,
        quantity=debit_data.quantity,
        unit_price=unit_price,
        total_price=total_price,
        notes=debit_data.notes,
        used_by=current_user.id,
        used_at=utcnow()
    )
    db.add(inventory_debit)
    db.flush()
    
    # Automatically add to bill
    # Find or create a bill for this encounter
    existing_bill = db.query(Bill).filter(
        Bill.encounter_id == ward_admission.encounter_id,
        Bill.is_paid == False  # Only use unpaid bills
    ).first()
    
    if existing_bill:
        # Check if this product is already in the bill
        existing_item = db.query(BillItem).filter(
            BillItem.bill_id == existing_bill.id,
            BillItem.item_code == debit_data.product_code,
            BillItem.item_name == debit_data.product_name
        ).first()
        
        if not existing_item:
            # Add bill item to existing bill
            bill_item = BillItem(
                bill_id=existing_bill.id,
                item_code=debit_data.product_code,
                item_name=f"Inventory: {debit_data.product_name}",
                category="product",
                quantity=debit_data.quantity,
                unit_price=unit_price,
                total_price=total_price
            )
            db.add(bill_item)
            db.flush()
            existing_bill.total_amount += total_price
            inventory_debit.bill_item_id = bill_item.id
            inventory_debit.is_billed = True
    else:
        # Create new bill
        bill_number = f"BILL-{random.randint(100000, 999999)}"
        bill = Bill(
            encounter_id=ward_admission.encounter_id,
            bill_number=bill_number,
            is_insured=is_insured_encounter,
            miscellaneous=None
        )
        db.add(bill)
        db.flush()
        
        # Add bill item
        bill_item = BillItem(
            bill_id=bill.id,
            item_code=debit_data.product_code,
            item_name=f"Inventory: {debit_data.product_name}",
            category="product",
            quantity=debit_data.quantity,
            unit_price=unit_price,
            total_price=total_price
        )
        db.add(bill_item)
        db.flush()
        bill.total_amount = total_price
        inventory_debit.bill_item_id = bill_item.id
        inventory_debit.is_billed = True
    
    db.commit()
    db.refresh(inventory_debit)
    
    # Load user for response
    user = db.query(User).filter(User.id == inventory_debit.used_by).first()
    
    return {
        "id": inventory_debit.id,
        "ward_admission_id": inventory_debit.ward_admission_id,
        "encounter_id": inventory_debit.encounter_id,
        "product_code": inventory_debit.product_code,
        "product_name": inventory_debit.product_name,
        "quantity": inventory_debit.quantity,
        "unit_price": inventory_debit.unit_price,
        "total_price": inventory_debit.total_price,
        "notes": inventory_debit.notes,
        "is_billed": inventory_debit.is_billed,
        "bill_item_id": inventory_debit.bill_item_id,
        "used_by": inventory_debit.used_by,
        "used_by_name": user.full_name if user else None,
        "used_at": inventory_debit.used_at,
        "created_at": inventory_debit.created_at,
        "updated_at": inventory_debit.updated_at,
        "requesting_ward": inventory_debit.requesting_ward,
    }


@router.get("/ward-admissions/{ward_admission_id}/inventory-debits", response_model=List[InpatientInventoryDebitResponse])
def get_inpatient_inventory_debits(
    ward_admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin", "Billing"]))
):
    """Get all inventory debits for a ward admission"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_inventory_debit import InpatientInventoryDebit
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    debits = db.query(InpatientInventoryDebit).filter(
        InpatientInventoryDebit.ward_admission_id == ward_admission_id
    ).order_by(InpatientInventoryDebit.used_at.desc()).all()
    
    result = []
    for debit in debits:
        user = db.query(User).filter(User.id == debit.used_by).first()
        
        # Get user who released (if released)
        released_by_user = None
        if debit.released_by:
            released_by_user = db.query(User).filter(User.id == debit.released_by).first()
        
        result.append({
            "id": debit.id,
            "ward_admission_id": debit.ward_admission_id,
            "encounter_id": debit.encounter_id,
            "product_code": debit.product_code,
            "product_name": debit.product_name,
            "quantity": debit.quantity,
            "unit_price": debit.unit_price,
            "total_price": debit.total_price,
            "notes": debit.notes,
            "is_billed": debit.is_billed,
            "bill_item_id": debit.bill_item_id,
            "is_released": debit.is_released,
            "released_by": debit.released_by,
            "released_by_name": released_by_user.full_name if released_by_user else None,
            "released_at": debit.released_at,
            "used_by": debit.used_by,
            "used_by_name": user.full_name if user else None,
            "used_at": debit.used_at,
            "created_at": debit.created_at,
            "updated_at": debit.updated_at,
            "requesting_ward": getattr(debit, 'requesting_ward', None) or ward_admission.ward if ward_admission else None,
        })
    
    return result


@router.delete("/ward-admissions/{ward_admission_id}/inventory-debits/{debit_id}")
def delete_inpatient_inventory_debit(
    ward_admission_id: int,
    debit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"]))
):
    """Delete an inventory debit and its corresponding bill item if billed"""
    from app.models.ward_admission import WardAdmission
    from app.models.inpatient_inventory_debit import InpatientInventoryDebit
    from app.models.bill import Bill, BillItem
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    debit = db.query(InpatientInventoryDebit).filter(
        InpatientInventoryDebit.id == debit_id,
        InpatientInventoryDebit.ward_admission_id == ward_admission_id
    ).first()
    
    if not debit:
        raise HTTPException(status_code=404, detail="Inventory debit not found")
    
    # If billed, delete the corresponding bill item and update bill total
    if debit.is_billed and debit.bill_item_id:
        bill_item = db.query(BillItem).filter(BillItem.id == debit.bill_item_id).first()
        if bill_item:
            bill = db.query(Bill).filter(Bill.id == bill_item.bill_id).first()
            if bill:
                # Subtract the bill item total from bill total
                bill.total_amount -= bill_item.total_price
                # Ensure bill total doesn't go negative
                if bill.total_amount < 0:
                    bill.total_amount = 0.0
            
            # Clear the foreign key reference first to avoid constraint violation
            debit.bill_item_id = None
            debit.is_billed = False
            db.flush()  # Flush to ensure the reference is cleared before deletion
            
            # Now safe to delete the bill item
            db.delete(bill_item)
    
    # Delete the inventory debit record
    db.delete(debit)
    db.commit()
    
    return {"message": "Inventory debit and corresponding bill item deleted successfully"}


@router.get("/inventory-debits", response_model=List[InpatientInventoryDebitResponse])
def get_all_inventory_debits(
    ward: Optional[str] = None,
    is_released: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    used_by_name: Optional[str] = None,
    product_code: Optional[str] = None,
    product_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin", "Nurse", "Doctor", "PA"]))
):
    """Get all inventory debits with optional filtering - for pharmacy staff to view and release"""
    from app.models.inpatient_inventory_debit import InpatientInventoryDebit
    from app.models.ward_admission import WardAdmission
    from app.models.encounter import Encounter
    from app.models.patient import Patient
    from datetime import datetime as dt
    
    # Build query with outer joins to handle old data that might have missing relationships
    query = db.query(InpatientInventoryDebit).outerjoin(
        WardAdmission, InpatientInventoryDebit.ward_admission_id == WardAdmission.id
    ).outerjoin(
        Encounter, InpatientInventoryDebit.encounter_id == Encounter.id
    ).outerjoin(
        Patient, Encounter.patient_id == Patient.id
    )
    
    # Filter by requesting_ward if provided (use requesting_ward field instead of current ward)
    # Handle cases where requesting_ward might be None for old records
    if ward:
        query = query.filter(
            or_(
                InpatientInventoryDebit.requesting_ward == ward,
                and_(
                    (InpatientInventoryDebit.requesting_ward.is_(None)),
                    (WardAdmission.ward == ward)
                )
            )
        )
    
    # Filter by release status if provided
    if is_released is not None:
        query = query.filter(InpatientInventoryDebit.is_released == is_released)
    
    # Filter by date range if provided
    if start_date:
        try:
            start_dt = dt.strptime(start_date, "%Y-%m-%d")
            query = query.filter(InpatientInventoryDebit.used_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = dt.strptime(end_date, "%Y-%m-%d")
            # Include the entire end date by setting time to end of day
            from datetime import timedelta
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(InpatientInventoryDebit.used_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    # Filter by user full name if provided (User model only has full_name, not name/surname)
    if used_by_name:
        query = query.join(User, InpatientInventoryDebit.used_by == User.id).filter(
            User.full_name.ilike(f"%{used_by_name}%")
        )
    
    # Filter by product code if provided
    if product_code:
        query = query.filter(InpatientInventoryDebit.product_code.ilike(f"%{product_code}%"))
    
    # Filter by product name if provided
    if product_name:
        query = query.filter(InpatientInventoryDebit.product_name.ilike(f"%{product_name}%"))
    
    # Note: Removed the filter for only active admissions to show all inventory debits
    # This allows viewing historical data even for discharged patients
    
    # Order by used_at descending (most recent first)
    debits = query.order_by(InpatientInventoryDebit.used_at.desc()).all()
    
    result = []
    for debit in debits:
        # Get user who used the product
        user = db.query(User).filter(User.id == debit.used_by).first()
        
        # Get ward admission details
        ward_admission = db.query(WardAdmission).filter(WardAdmission.id == debit.ward_admission_id).first()
        
        # Get encounter and patient details
        encounter = db.query(Encounter).filter(Encounter.id == debit.encounter_id).first()
        patient = None
        if encounter:
            patient = db.query(Patient).filter(Patient.id == encounter.patient_id).first()
        
        # Get user who released (if released)
        released_by_user = None
        if debit.released_by:
            released_by_user = db.query(User).filter(User.id == debit.released_by).first()
        
        result.append({
            "id": debit.id,
            "ward_admission_id": debit.ward_admission_id,
            "encounter_id": debit.encounter_id,
            "product_code": debit.product_code,
            "product_name": debit.product_name,
            "quantity": debit.quantity,
            "unit_price": debit.unit_price,
            "total_price": debit.total_price,
            "notes": debit.notes,
            "is_billed": debit.is_billed,
            "bill_item_id": debit.bill_item_id,
            "is_released": debit.is_released,
            "released_by": debit.released_by,
            "released_by_name": released_by_user.full_name if released_by_user else None,
            "released_at": debit.released_at,
            "used_by": debit.used_by,
            "used_by_name": user.full_name if user else None,
            "used_at": debit.used_at,
            "created_at": debit.created_at,
            "updated_at": debit.updated_at,
            # Additional patient and ward information
            "patient_name": f"{patient.surname or ''} {patient.name or ''} {patient.other_names or ''}".strip() if patient else None,
            "patient_card_number": patient.card_number if patient else None,
            "ward": ward_admission.ward if ward_admission else None,  # Current ward (for backward compatibility)
            "requesting_ward": getattr(debit, 'requesting_ward', None) or (ward_admission.ward if ward_admission else None),  # Original requesting ward
            "admitted_at": ward_admission.admitted_at if ward_admission else None,
        })
    
    return result


@router.put("/inventory-debits/{debit_id}/release")
def release_inventory_debit(
    debit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"]))
):
    """Release inventory debit - pharmacy staff marks inventory as released for ward administration"""
    from app.models.inpatient_inventory_debit import InpatientInventoryDebit
    
    debit = db.query(InpatientInventoryDebit).filter(InpatientInventoryDebit.id == debit_id).first()
    if not debit:
        raise HTTPException(status_code=404, detail="Inventory debit not found")
    
    if debit.is_released:
        raise HTTPException(status_code=400, detail="Inventory debit has already been released")
    
    # Mark as released
    debit.is_released = True
    debit.released_by = current_user.id
    debit.released_at = utcnow()
    
    db.commit()
    db.refresh(debit)
    
    # Get user who released
    released_by_user = db.query(User).filter(User.id == debit.released_by).first()
    
    return {
        "message": "Inventory debit released successfully",
        "id": debit.id,
        "is_released": debit.is_released,
        "released_by": debit.released_by,
        "released_by_name": released_by_user.full_name if released_by_user else None,
        "released_at": debit.released_at
    }


@router.put("/inpatient-investigations/bulk-confirm")
def bulk_confirm_inpatient_investigations(
    bulk_data: BulkConfirmInpatientInvestigations,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab", "Scan", "Xray", "Admin", "Lab Head", "Scan Head", "Xray Head"]))
):
    """Bulk confirm multiple IPD investigation requests"""
    from app.models.inpatient_investigation import InpatientInvestigation, InpatientInvestigationStatus
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.ward_admission import WardAdmission
    from app.models.encounter import Encounter
    from app.models.bill import Bill, BillItem
    from app.services.price_list_service_v2 import get_price_from_all_tables
    import random
    
    if not bulk_data.investigation_ids:
        raise HTTPException(status_code=400, detail="No investigation IDs provided")
    
    investigations = db.query(InpatientInvestigation).filter(
        InpatientInvestigation.id.in_(bulk_data.investigation_ids)
    ).all()
    
    if len(investigations) != len(bulk_data.investigation_ids):
        raise HTTPException(status_code=404, detail="Some investigations not found")
    
    confirmed_count = 0
    errors = []
    
    for investigation in investigations:
        try:
            # Don't allow confirming cancelled investigations
            if investigation.status == InpatientInvestigationStatus.CANCELLED.value:
                errors.append(f"Investigation {investigation.id} is cancelled")
                continue
            
            # Don't allow confirming already confirmed or completed investigations
            if investigation.status in [InpatientInvestigationStatus.CONFIRMED.value, InpatientInvestigationStatus.COMPLETED.value]:
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
            
            # Get clinical review and ward admission
            clinical_review = db.query(InpatientClinicalReview).filter(
                InpatientClinicalReview.id == investigation.clinical_review_id
            ).first()
            if not clinical_review:
                errors.append(f"Clinical review not found for investigation {investigation.id}")
                continue
            
            ward_admission = db.query(WardAdmission).filter(
                WardAdmission.id == clinical_review.ward_admission_id
            ).first()
            if not ward_admission:
                errors.append(f"Ward admission not found for investigation {investigation.id}")
                continue
            
            encounter = db.query(Encounter).filter(Encounter.id == ward_admission.encounter_id).first()
            if not encounter:
                errors.append(f"Encounter not found for investigation {investigation.id}")
                continue
            
            # Confirm the investigation
            investigation.status = InpatientInvestigationStatus.CONFIRMED.value
            investigation.confirmed_by = current_user.id
            
            # Get price
            is_insured_encounter = bool(encounter.ccc_number)
            unit_price = 0.0
            if investigation.gdrg_code:
                try:
                    # Determine service type based on investigation type for accurate price lookup
                    service_type = None
                    if investigation.investigation_type == "lab":
                        service_type = "Lab"
                    elif investigation.investigation_type == "scan":
                        service_type = "Scan"
                    elif investigation.investigation_type == "xray":
                        service_type = "X-ray"
                    
                    unit_price = get_price_from_all_tables(db, investigation.gdrg_code, is_insured_encounter, service_type, investigation.procedure_name)
                    print(f"DEBUG bulk_confirm_inpatient: Looked up price for gdrg_code='{investigation.gdrg_code}', procedure_name='{investigation.procedure_name}', is_insured={is_insured_encounter}, service_type='{service_type}', price={unit_price}")
                    
                    # If lookup returns 0.0, it means price wasn't found
                    if unit_price == 0.0:
                        print(f"WARNING bulk_confirm_inpatient: Price lookup returned 0.0 for investigation {investigation.id}, gdrg_code='{investigation.gdrg_code}', service_type='{service_type}'")
                        # Only use stored price if it exists and lookup returned 0
                        if investigation.price:
                            try:
                                stored_price = float(investigation.price)
                                if stored_price > 0:
                                    print(f"WARNING bulk_confirm_inpatient: Using stored price '{stored_price}' as fallback for investigation {investigation.id}")
                                    unit_price = stored_price
                            except (ValueError, TypeError):
                                pass
                except Exception as e:
                    print(f"ERROR bulk_confirm_inpatient: Failed to get price for investigation {investigation.id}: {e}")
                    # Fallback to stored price only if exception occurred
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
            
            # Add to IPD bill if requested and price > 0
            if total_price > 0 and bulk_data.add_to_ipd_bill:
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
                            category=investigation.investigation_type or "procedure",
                            quantity=1,
                            unit_price=unit_price,
                            total_price=total_price
                        )
                        db.add(bill_item)
                        existing_bill.total_amount += total_price
                else:
                    # Create new bill
                    bill_number = f"IPD-{encounter.id}-{random.randint(1000, 9999)}"
                    bill = Bill(
                        encounter_id=encounter.id,
                        bill_number=bill_number,
                        total_amount=total_price,
                        is_paid=False
                    )
                    db.add(bill)
                    db.flush()  # Get bill.id
                    
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
            import traceback
            print(f"ERROR bulk_confirm_inpatient: Error processing investigation {investigation.id}: {str(e)}")
            print(traceback.format_exc())
            errors.append(f"Error processing investigation {investigation.id}: {str(e)}")
            continue
    
    db.commit()
    
    return {
        "confirmed_count": confirmed_count,
        "total_requested": len(bulk_data.investigation_ids),
        "errors": errors
    }


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
    
    # Direct admissions ALWAYS create a new encounter (never reuse existing ones)
    # This ensures each direct admission has its own encounter that can be deleted on cancellation
    encounter = Encounter(
        patient_id=patient.id,
        department=form_data.ward,  # Use ward as department for inpatient
        status=EncounterStatus.IN_CONSULTATION.value,
        ccc_number=form_data.ccc_number,
        created_by=current_user.id
    )
    db.add(encounter)
    db.flush()  # Get encounter ID
    
    # Update patient emergency contact if not already set
    if not patient.emergency_contact_name:
        patient.emergency_contact_name = form_data.emergency_contact_name
        patient.emergency_contact_relationship = form_data.emergency_contact_relationship
        patient.emergency_contact_number = form_data.emergency_contact_number
    
    # Create new admission recommendation for direct admission
    # Direct admissions always create fresh records (no reuse of cancelled admissions)
    admission_recommendation = AdmissionRecommendation(
        encounter_id=encounter.id,
        ward=form_data.ward,
        recommended_by=current_user.id,
        confirmed_by=current_user.id,  # Auto-confirm for direct admission
        confirmed_at=utcnow()
    )
    db.add(admission_recommendation)
    db.flush()  # Get admission_recommendation ID
    
    # Mark bed as occupied
    bed.is_occupied = True
    bed.updated_at = utcnow()
    
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
        admitted_at=utcnow()
    )
    db.add(ward_admission)
    db.flush()  # Flush to get ward_admission ID before committing
    
    # Auto-generate IPD admission bill
    import logging
    logger = logging.getLogger(__name__)
    try:
        ccc_to_use = form_data.ccc_number or encounter.ccc_number
        logger.info(f"Attempting to create IPD admission bill for encounter {encounter.id}, CCC: {ccc_to_use}")
        print(f"DEBUG: About to call _create_ipd_admission_bill for encounter {encounter.id}")
        _create_ipd_admission_bill(db, encounter, ccc_to_use, current_user.id)
        db.flush()  # Ensure bill is saved before commit
        
        # Verify bill was created correctly after flush
        from app.models.bill import Bill
        created_bill = db.query(Bill).filter(Bill.encounter_id == encounter.id, Bill.is_paid == False).order_by(Bill.created_at.desc()).first()
        if created_bill:
            # Recalculate total one more time to ensure it's correct
            from app.models.bill import BillItem
            bill_items = db.query(BillItem).filter(BillItem.bill_id == created_bill.id).all()
            if bill_items:
                calculated_total = sum(item.total_price for item in bill_items)
                if created_bill.total_amount != calculated_total:
                    logger.warning(f"Bill {created_bill.id} total_amount mismatch: stored={created_bill.total_amount}, calculated={calculated_total}. Fixing...")
                    print(f"WARNING: Bill {created_bill.id} total_amount mismatch: stored={created_bill.total_amount}, calculated={calculated_total}. Fixing...")
                    created_bill.total_amount = calculated_total
                    db.flush()
        
        logger.info(f"Successfully created IPD admission bill for encounter {encounter.id}")
        print(f"DEBUG: Successfully created IPD admission bill for encounter {encounter.id}")
    except Exception as e:
        # Log error but don't fail admission confirmation
        logger.error(f"Failed to create IPD admission bill for encounter {encounter.id}: {str(e)}", exc_info=True)
        # Continue with admission confirmation even if bill creation fails
        # But log it so we can investigate
        print(f"ERROR: Failed to create IPD admission bill for encounter {encounter.id}: {str(e)}")
        import traceback
        traceback.print_exc()
    
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
    today_date = today()
    return today_date.year - date_of_birth.year - ((today_date.month, today_date.day) < (date_of_birth.month, date_of_birth.day))


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
            old_bed.updated_at = utcnow()
    
    # Mark new bed as occupied
    bed.is_occupied = True
    bed.updated_at = utcnow()
    
    # Update ward admission
    ward_admission.ward = transfer.to_ward
    ward_admission.bed_id = form_data.bed_id
    ward_admission.updated_at = utcnow()
    
    # Update transfer status
    transfer.status = "accepted"
    transfer.accepted_by = current_user.id
    transfer.accepted_at = utcnow()
    transfer.updated_at = utcnow()
    
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
    transfer.rejected_at = utcnow()
    transfer.updated_at = utcnow()
    
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
            # Delete all related treatment sheet administrations first (to avoid foreign key constraint)
            from app.models.treatment_sheet_administration import TreatmentSheetAdministration
            treatment_administrations = db.query(TreatmentSheetAdministration).filter(
                TreatmentSheetAdministration.ward_admission_id == ward_admission.id
            ).all()
            for admin in treatment_administrations:
                db.delete(admin)
            
            # Delete the ward admission record
            db.delete(ward_admission)
        
        # Revert confirmation status
        admission.confirmed_by = None
        admission.confirmed_at = None
    
    # Mark as cancelled
    admission.cancelled = 1
    admission.cancelled_by = current_user.id
    admission.cancelled_at = utcnow()
    admission.cancellation_reason = cancel_data.reason
    admission.updated_at = utcnow()
    
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
    bed.updated_at = utcnow()
    
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
    bed.updated_at = utcnow()
    
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
    from app.models.treatment_sheet_administration import TreatmentSheetAdministration
    
    ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
    if not ward_admission:
        raise HTTPException(status_code=404, detail="Ward admission not found")
    
    # Delete all related treatment sheet administrations first (to avoid foreign key constraint)
    treatment_administrations = db.query(TreatmentSheetAdministration).filter(
        TreatmentSheetAdministration.ward_admission_id == ward_admission_id
    ).all()
    for admin in treatment_administrations:
        db.delete(admin)
    
    # Free up the bed
    if ward_admission.bed_id:
        bed = db.query(Bed).filter(Bed.id == ward_admission.bed_id).first()
        if bed:
            bed.is_occupied = False
            bed.updated_at = utcnow()
    
    # Get admission recommendation and encounter
    admission = db.query(AdmissionRecommendation).filter(
        AdmissionRecommendation.id == ward_admission.admission_recommendation_id
    ).first()
    
    encounter = db.query(Encounter).filter(Encounter.id == ward_admission.encounter_id).first()
    
    # Check if this is a direct admission (no consultation notes = direct admission)
    # Direct admissions should have their encounter deleted on cancellation
    from app.models.consultation_notes import ConsultationNotes
    consultation_notes = None
    if encounter:
        consultation_notes = db.query(ConsultationNotes).filter(
            ConsultationNotes.encounter_id == encounter.id
        ).first()
    
    # Delete all related bills and bill items for this encounter
    from app.models.bill import Bill, BillItem
    if encounter:
        unpaid_bills = db.query(Bill).filter(
            Bill.encounter_id == encounter.id,
            Bill.is_paid == False
        ).all()
        for bill in unpaid_bills:
            # Delete bill items first
            bill_items = db.query(BillItem).filter(BillItem.bill_id == bill.id).all()
            for item in bill_items:
                db.delete(item)
            db.delete(bill)
    
    # Delete admission recommendation
    if admission:
        db.delete(admission)
    
    # Delete ward admission record
    db.delete(ward_admission)
    
    # If this is a direct admission (no consultation notes), delete the encounter
    # This ensures the encounter won't be reused on readmission
    if encounter and not consultation_notes:
        # This is a direct admission - delete the encounter
        db.delete(encounter)
    
    db.commit()
    
    return {
        "message": "Admission cancelled successfully. All records have been removed."
    }