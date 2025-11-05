"""
Claims management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.core.database import get_db
from app.core.dependencies import require_role
from app.models.user import User
from app.models.encounter import Encounter
from app.models.claim import Claim, ClaimStatus
from app.models.bill import Bill
from app.utils.claim_generator import generate_claim_id, generate_claim_check_code
from app.services.xml_export import export_claims_xml, export_claims_by_date_range
from app.models.diagnosis import Diagnosis

router = APIRouter(prefix="/claims", tags=["claims"])


def get_claim_amount_from_price_list(db: Session, item_code: str, is_insured: bool = True) -> float:
    """
    Get claim amount for an item code from price list
    For insured patients: returns NHIA Approved price (nhia_app) or claim_amount for products
    For investigations/procedures: returns nhia_app if available, else base_rate
    """
    from app.models.procedure_price import ProcedurePrice
    from app.models.surgery_price import SurgeryPrice
    from app.models.product_price import ProductPrice
    from app.models.unmapped_drg_price import UnmappedDRGPrice
    
    if not is_insured:
        return 0.0
    
    if not item_code:
        return 0.0
    
    # Search in procedure, surgery, and unmapped_drg tables (use g_drg_code)
    tables = [
        db.query(ProcedurePrice).filter(ProcedurePrice.g_drg_code == item_code, ProcedurePrice.is_active == True),
        db.query(SurgeryPrice).filter(SurgeryPrice.g_drg_code == item_code, SurgeryPrice.is_active == True),
        db.query(UnmappedDRGPrice).filter(UnmappedDRGPrice.g_drg_code == item_code, UnmappedDRGPrice.is_active == True),
    ]
    
    for query in tables:
        item = query.first()
        if item:
            # For insured: use NHIA Approved price (nhia_app) if available, else base_rate
            if hasattr(item, 'nhia_app') and item.nhia_app is not None:
                return float(item.nhia_app)
            else:
                return float(item.base_rate) if item.base_rate else 0.0
    
    # Search in product table (use medication_code or product_id)
    product = db.query(ProductPrice).filter(
        ((ProductPrice.medication_code == item_code) |
         (ProductPrice.product_id == item_code)),
        ProductPrice.is_active == True
    ).first()
    
    if product:
        # For products: use claim_amount if available, else nhia_app
        if hasattr(product, 'claim_amount') and product.claim_amount is not None:
            return float(product.claim_amount)
        elif hasattr(product, 'nhia_app') and product.nhia_app is not None:
            return float(product.nhia_app)
        else:
            return float(product.base_rate) if product.base_rate else 0.0
    
    return 0.0


class EncounterWithClaimInfo(BaseModel):
    """Encounter with claim information"""
    id: int
    patient_id: int
    patient_name: str
    patient_card_number: str
    ccc_number: Optional[str]
    status: str
    department: str
    finalized_at: Optional[datetime]
    created_at: datetime
    claim_id: Optional[int] = None
    claim_status: Optional[str] = None
    
    class Config:
        from_attributes = True


class ClaimCreate(BaseModel):
    """Claim creation model"""
    encounter_id: int
    physician_id: str
    type_of_service: str = "OPD"
    type_of_attendance: Optional[str] = "EAE"
    specialty_attended: Optional[str] = "OPDC"


class DiagnosisUpdate(BaseModel):
    """Diagnosis update model"""
    id: Optional[int] = None
    description: str
    icd10: str
    gdrg: str
    is_chief: bool = False


class InvestigationUpdate(BaseModel):
    """Investigation update model"""
    id: Optional[int] = None
    description: str
    date: str
    gdrg: str


class PrescriptionUpdate(BaseModel):
    """Prescription update model"""
    id: Optional[int] = None
    description: str
    code: str
    price: float
    quantity: int
    total_cost: float
    date: str
    dose: Optional[str] = ""
    frequency: Optional[str] = ""
    duration: Optional[str] = ""
    unparsed: Optional[str] = ""


class ProcedureUpdate(BaseModel):
    """Procedure update model"""
    description: str
    date: str
    gdrg: str


class ClaimDetailedUpdate(BaseModel):
    """Detailed claim update model"""
    physician_id: str
    physician_name: Optional[str] = ""
    type_of_service: str = "OPD"
    type_of_attendance: Optional[str] = "EAE"
    specialty_attended: Optional[str] = "OPDC"
    service_outcome: Optional[str] = "DISC"
    is_unbundled: bool = False
    principal_gdrg: Optional[str] = ""
    first_visit: Optional[str] = None
    second_visit: Optional[str] = None
    third_visit: Optional[str] = None
    fourth_visit: Optional[str] = None
    duration_of_spell: Optional[int] = None
    diagnoses: List[DiagnosisUpdate] = []
    investigations: List[InvestigationUpdate] = []
    prescriptions: List[PrescriptionUpdate] = []
    procedures: List[ProcedureUpdate] = []


class ClaimResponse(BaseModel):
    """Claim response model"""
    id: int
    encounter_id: int
    claim_id: str
    status: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def create_claim(
    claim_data: ClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Create a new claim from an encounter"""
    encounter = db.query(Encounter).filter(Encounter.id == claim_data.encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    if encounter.status != "finalized":
        raise HTTPException(
            status_code=400,
            detail="Can only create claims from finalized encounters"
        )
    
    # Check if all bills are paid (ignore zero-amount unpaid bills)
    unpaid_bills_gt_zero = db.query(Bill).filter(
        Bill.encounter_id == encounter.id,
        Bill.is_paid == False,
        Bill.total_amount > 0
    ).count()
    
    if unpaid_bills_gt_zero > 0:
        raise HTTPException(
            status_code=400,
            detail="All bills must be paid before creating a claim"
        )
    
    # Get patient info
    patient = encounter.patient
    
    # Check if pharmacy items exist
    has_pharmacy = len(encounter.prescriptions) > 0
    
    # Get principal GDRG from chief diagnosis
    principal_gdrg = None
    chief_diagnosis = db.query(Diagnosis).filter(
        Diagnosis.encounter_id == encounter.id,
        Diagnosis.is_chief == True
    ).first()
    
    if chief_diagnosis:
        principal_gdrg = chief_diagnosis.gdrg_code
    
    # Create claim
    claim = Claim(
        encounter_id=encounter.id,
        claim_id=generate_claim_id(db),
        claim_check_code=generate_claim_check_code(),
        physician_id=claim_data.physician_id,
        member_no=patient.insurance_id or "",
        card_serial_no=patient.card_number or "",
        is_dependant=False,
        type_of_service=claim_data.type_of_service,
        includes_pharmacy=has_pharmacy,
        type_of_attendance=claim_data.type_of_attendance,
        service_outcome="DISC",
        specialty_attended=claim_data.specialty_attended,
        principal_gdrg=principal_gdrg,
        status=ClaimStatus.DRAFT.value,
        created_by=current_user.id
    )
    
    db.add(claim)
    db.flush()  # Flush to get claim.id
    
    # Populate claim detail tables from encounter services
    from app.models.claim_detail import ClaimDiagnosis, ClaimInvestigation, ClaimPrescription, ClaimProcedure
    from app.services.price_list_service_v2 import get_price_from_all_tables
    
    # Populate diagnoses (up to 4)
    diagnosis_order = 0
    for diag in encounter.diagnoses:
        if diagnosis_order >= 4:
            break
        claim_diag = ClaimDiagnosis(
            claim_id=claim.id,
            diagnosis_id=diag.id,
            description=diag.diagnosis,
            icd10=diag.icd10,
            gdrg_code=diag.gdrg_code or "",
            is_chief=diag.is_chief,
            display_order=diagnosis_order
        )
        db.add(claim_diag)
        diagnosis_order += 1
    
    # Populate investigations (up to 5, only completed)
    investigation_order = 0
    for inv in encounter.investigations:
        if investigation_order >= 5:
            break
        if inv.status == "completed" and inv.gdrg_code:
            claim_inv = ClaimInvestigation(
                claim_id=claim.id,
                investigation_id=inv.id,
                description=inv.procedure_name or "",
                gdrg_code=inv.gdrg_code,
                service_date=inv.service_date or encounter.created_at,
                investigation_type=inv.investigation_type,
                display_order=investigation_order
            )
            db.add(claim_inv)
            investigation_order += 1
    
    # Populate prescriptions (up to 5, only dispensed)
    prescription_order = 0
    for presc in encounter.prescriptions:
        if prescription_order >= 5:
            break
        if presc.dispensed_by and presc.medicine_code:
            # Get claim amount from price list
            claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
            
            claim_presc = ClaimPrescription(
                claim_id=claim.id,
                prescription_id=presc.id,
                description=presc.medicine_name,
                code=presc.medicine_code,
                price=float(claim_amount) if claim_amount else 0.0,
                quantity=presc.quantity,
                total_cost=float(claim_amount * presc.quantity) if claim_amount else 0.0,
                service_date=presc.service_date or encounter.created_at,
                dose=presc.dose or "",
                frequency=presc.frequency or "",
                duration=presc.duration or "",
                unparsed=presc.unparsed or "",
                display_order=prescription_order
            )
            db.add(claim_presc)
            prescription_order += 1
    
    # Populate procedures (from encounter procedure, up to 3)
    if encounter.procedure_g_drg_code:
        claim_proc = ClaimProcedure(
            claim_id=claim.id,
            description=encounter.procedure_name or "",
            gdrg_code=encounter.procedure_g_drg_code,
            service_date=encounter.created_at,
            display_order=0
        )
        db.add(claim_proc)
    
    db.commit()
    db.refresh(claim)
    
    return claim


@router.put("/{claim_id}/finalize")
def finalize_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Finalize a claim"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    # For IPD admissions, require discharge before finalization
    encounter = db.query(Encounter).filter(Encounter.id == claim.encounter_id).first()
    if encounter:
        from app.models.consultation_notes import ConsultationNotes
        notes = db.query(ConsultationNotes).filter(ConsultationNotes.encounter_id == encounter.id).first()
        outcome = (notes.outcome if notes and notes.outcome else "").lower()
        if outcome == 'recommended_for_admission':
            raise HTTPException(status_code=400, detail="Cannot finalize IPD claim before patient is discharged.")
    
    claim.status = ClaimStatus.FINALIZED.value
    claim.finalized_at = datetime.utcnow()
    db.commit()
    
    return {"claim_id": claim.id, "status": claim.status}


@router.put("/{claim_id}/reopen")
def reopen_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Reopen a finalized claim for corrections"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    claim.status = ClaimStatus.REOPENED.value
    db.commit()
    
    return {"claim_id": claim.id, "status": claim.status}


@router.get("/export/date-range")
def export_claims_by_date(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Export claims within a date range as XML"""
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    
    xml_content = export_claims_by_date_range(start_dt, end_dt, db)
    
    filename = f"NHIS_CLA{start_date.strftime('%Y%m%d')}{end_date.strftime('%Y%m%d')}.xml"
    
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/export/{claim_id}")
def export_claim_xml(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Export a single claim as XML"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    if claim.status != "finalized":
        raise HTTPException(
            status_code=400,
            detail="Can only export finalized claims"
        )
    
    xml_content = export_claims_xml([claim_id], db)
    
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename=NHIS_CLA{claim.claim_id.replace('-', '')}.xml"
        }
    )


@router.get("/eligible-encounters", response_model=List[EncounterWithClaimInfo])
def get_eligible_encounters_for_claims(
    claim_type: Optional[str] = None,  # 'opd' or 'ipd'
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """
    Get finalized encounters with CCC numbers that are eligible for claim generation.
    Only encounters with active insurance (CCC number) and finalized status are returned.
    """
    from sqlalchemy.orm import joinedload
    
    # Get finalized encounters with CCC numbers (active insurance)
    encounters = db.query(Encounter)\
        .options(joinedload(Encounter.patient))\
        .filter(
            Encounter.status == "finalized",
            Encounter.ccc_number.isnot(None),
            Encounter.ccc_number != "",
            Encounter.archived == False
        )\
        .order_by(Encounter.finalized_at.desc())\
        .all()
    
    result = []
    from app.models.consultation_notes import ConsultationNotes
    for encounter in encounters:
        # Determine outcome from consultation notes
        notes = db.query(ConsultationNotes).filter(ConsultationNotes.encounter_id == encounter.id).first()
        outcome = (notes.outcome if notes and notes.outcome else "").lower()
        # Apply type filter if provided
        if claim_type == 'opd' and outcome != 'discharged':
            continue
        if claim_type == 'ipd' and outcome != 'recommended_for_admission':
            continue
        if claim_type == 'other' and outcome in ('discharged', 'recommended_for_admission'):
            continue
        # Check if claim already exists
        claim = db.query(Claim).filter(Claim.encounter_id == encounter.id).first()
        
        encounter_data = {
            "id": encounter.id,
            "patient_id": encounter.patient_id,
            "patient_name": f"{encounter.patient.name} {encounter.patient.surname or ''}".strip(),
            "patient_card_number": encounter.patient.card_number or "",
            "ccc_number": encounter.ccc_number,
            "status": encounter.status,
            "department": encounter.department,
            "finalized_at": encounter.finalized_at,
            "created_at": encounter.created_at,
            "claim_id": claim.id if claim else None,
            "claim_status": claim.status if claim else None,
        }
        result.append(encounter_data)
    
    return result


@router.get("/", response_model=List[ClaimResponse])
def get_all_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Get all claims"""
    claims = db.query(Claim).order_by(Claim.created_at.desc()).all()
    return claims


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Get a single claim by ID"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.get("/{claim_id}/edit-details")
def get_claim_edit_details(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Get full encounter details for claim editing"""
    from sqlalchemy.orm import joinedload
    from app.models.prescription import Prescription
    from app.models.investigation import Investigation
    
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Load encounter with all relationships
    encounter = db.query(Encounter)\
        .options(
            joinedload(Encounter.patient),
            joinedload(Encounter.diagnoses),
            joinedload(Encounter.prescriptions),
            joinedload(Encounter.investigations),
            joinedload(Encounter.vitals)
        )\
        .filter(Encounter.id == claim.encounter_id)\
        .first()
    
    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")
    
    # Get diagnoses from claim detail table (or fallback to encounter diagnoses)
    from app.models.claim_detail import ClaimDiagnosis, ClaimInvestigation, ClaimPrescription, ClaimProcedure
    
    # Check if claim has been edited before (any claim detail table entry exists)
    claim_has_been_edited = db.query(ClaimDiagnosis)\
        .filter(ClaimDiagnosis.claim_id == claim.id)\
        .first() is not None
    
    claim_diagnoses = db.query(ClaimDiagnosis)\
        .filter(ClaimDiagnosis.claim_id == claim.id)\
        .order_by(ClaimDiagnosis.display_order)\
        .all()
    
    diagnoses_list = []
    if claim_has_been_edited:
        # Use claim detail table data (respects deletions)
        for claim_diag in claim_diagnoses:
            diagnoses_list.append({
                "id": claim_diag.id,
                "description": claim_diag.description,
                "icd10": claim_diag.icd10,
                "gdrg": claim_diag.gdrg_code or "",
                "is_chief": claim_diag.is_chief,
            })
    else:
        # First time loading - fallback to encounter diagnoses
        for diag in encounter.diagnoses:
            diagnoses_list.append({
                "id": diag.id,
                "description": diag.diagnosis,
                "icd10": diag.icd10,
                "gdrg": diag.gdrg_code or "",
                "is_chief": diag.is_chief,
            })
    
    # Pad to 4 diagnoses
    while len(diagnoses_list) < 4:
        diagnoses_list.append({
            "id": None,
            "description": "",
            "icd10": "",
            "gdrg": "",
            "is_chief": False,
        })
    
    # Get investigations from claim detail table (or fallback to encounter investigations)
    claim_investigations = db.query(ClaimInvestigation)\
        .filter(ClaimInvestigation.claim_id == claim.id)\
        .order_by(ClaimInvestigation.display_order)\
        .all()
    
    investigations_list = []
    if claim_has_been_edited:
        # Use claim detail table data (respects deletions)
        for claim_inv in claim_investigations:
            investigations_list.append({
                "id": claim_inv.id,
                "description": claim_inv.description or "",
                "date": claim_inv.service_date.isoformat() if claim_inv.service_date else encounter.created_at.isoformat(),
                "gdrg": claim_inv.gdrg_code or "",
                "investigation_type": claim_inv.investigation_type or "",
            })
    else:
        # First time loading - fallback to encounter investigations
        for inv in encounter.investigations:
            if inv.status == "completed":
                investigations_list.append({
                    "id": inv.id,
                    "description": inv.procedure_name or "",
                    "date": inv.service_date.isoformat() if inv.service_date else encounter.created_at.isoformat(),
                    "gdrg": inv.gdrg_code or "",
                    "investigation_type": inv.investigation_type,
                })
    
    # Pad to 5 investigations
    while len(investigations_list) < 5:
        investigations_list.append({
            "id": None,
            "description": "",
            "date": "",
            "gdrg": "",
            "investigation_type": "",
        })
    
    # Get prescriptions from claim detail table (or fallback to encounter prescriptions)
    claim_prescriptions = db.query(ClaimPrescription)\
        .filter(ClaimPrescription.claim_id == claim.id)\
        .order_by(ClaimPrescription.display_order)\
        .all()
    
    prescriptions_list = []
    if claim_has_been_edited:
        # Use claim detail table data (respects deletions)
        for claim_presc in claim_prescriptions:
            prescriptions_list.append({
                "id": claim_presc.id,
                "description": claim_presc.description,
                "code": claim_presc.code,
                "price": claim_presc.price,
                "quantity": claim_presc.quantity,
                "total_cost": claim_presc.total_cost,
                "date": claim_presc.service_date.isoformat() if claim_presc.service_date else encounter.created_at.isoformat(),
                "dose": claim_presc.dose or "",
                "frequency": claim_presc.frequency or "",
                "duration": claim_presc.duration or "",
                "unparsed": claim_presc.unparsed or "",
            })
    else:
        # First time loading - fallback to encounter prescriptions
        for presc in encounter.prescriptions:
            if presc.dispensed_by:
                claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
                prescriptions_list.append({
                    "id": presc.id,
                    "description": presc.medicine_name,
                    "code": presc.medicine_code,
                    "price": float(claim_amount) if claim_amount else 0.0,
                    "quantity": presc.quantity,
                    "total_cost": float(claim_amount * presc.quantity) if claim_amount else 0.0,
                    "date": presc.service_date.isoformat() if presc.service_date else encounter.created_at.isoformat(),
                    "dose": presc.dose or "",
                    "frequency": presc.frequency or "",
                    "duration": presc.duration or "",
                    "unparsed": presc.unparsed or "",
                })
    
    # Pad to 5 prescriptions
    while len(prescriptions_list) < 5:
        prescriptions_list.append({
            "id": None,
            "description": "",
            "code": "",
            "price": 0.0,
            "quantity": 0,
            "total_cost": 0.0,
            "date": "",
            "dose": "",
            "frequency": "",
            "duration": "",
            "unparsed": "",
        })
    
    # Get procedures from claim detail table (or fallback to encounter procedure ONLY on first load)
    # Check if claim detail tables have ever been populated for this claim
    claim_has_been_edited = db.query(ClaimDiagnosis)\
        .filter(ClaimDiagnosis.claim_id == claim.id)\
        .first() is not None
    
    # Query claim_procedures
    claim_procedures = db.query(ClaimProcedure)\
        .filter(ClaimProcedure.claim_id == claim.id)\
        .order_by(ClaimProcedure.display_order)\
        .all()
    
    procedures_list = []
    
    # IMPORTANT: If claim has been edited (claim detail tables exist), ALWAYS use claim_procedures
    # even if it's empty - this respects user's deletion. Never fallback to encounter after edits.
    if claim_has_been_edited:
        # Claim has been edited - use what's in claim_procedures (even if empty = user deleted them)
        for claim_proc in claim_procedures:
            procedures_list.append({
                "description": claim_proc.description or "",
                "date": claim_proc.service_date.isoformat() if claim_proc.service_date else encounter.created_at.isoformat(),
                "gdrg": claim_proc.gdrg_code or "",
            })
        # Note: If claim_procedures is empty (user deleted them), procedures_list stays empty
    else:
        # First time loading - fallback to encounter procedure (for backward compatibility)
        # Only happens if claim has NEVER been edited
        if encounter.procedure_g_drg_code:
            procedures_list.append({
                "description": encounter.procedure_name or "",
                "date": encounter.created_at.isoformat(),
                "gdrg": encounter.procedure_g_drg_code,
            })
    
    # Pad to 3 procedures
    while len(procedures_list) < 3:
        procedures_list.append({
            "description": "",
            "date": "",
            "gdrg": "",
        })
    
    # Build response
    return {
        "claim": {
            "id": claim.id,
            "claim_id": claim.claim_id,
            "physician_id": claim.physician_id,
            "type_of_service": claim.type_of_service,
            "type_of_attendance": claim.type_of_attendance,
            "specialty_attended": claim.specialty_attended,
            "service_outcome": claim.service_outcome,
            "is_unbundled": claim.is_unbundled,
            "principal_gdrg": claim.principal_gdrg or "",
            "status": claim.status,
        },
        "encounter": {
            "id": encounter.id,
            "created_at": encounter.created_at.isoformat(),
            "finalized_at": encounter.finalized_at.isoformat() if encounter.finalized_at else None,
            "department": encounter.department,
            "procedure_g_drg_code": encounter.procedure_g_drg_code,
            "procedure_name": encounter.procedure_name,
            "ccc_number": encounter.ccc_number,
        },
        "patient": {
            "id": encounter.patient.id,
            "name": encounter.patient.name,
            "surname": encounter.patient.surname or "",
            "other_names": encounter.patient.other_names or "",
            "date_of_birth": encounter.patient.date_of_birth.isoformat() if encounter.patient.date_of_birth else None,
            "age": encounter.patient.age,
            "gender": encounter.patient.gender,
            "card_number": encounter.patient.card_number,
            "insurance_id": encounter.patient.insurance_id or "",
        },
        "diagnoses": diagnoses_list,
        "investigations": investigations_list,
        "prescriptions": prescriptions_list,
        "procedures": procedures_list,
        "claim_summary": {
            "inpatient_amount": get_claim_amount_from_price_list(db, encounter.procedure_g_drg_code or "", is_insured=True) if claim.type_of_service == "IPD" else 0.0,
            "outpatient_amount": get_claim_amount_from_price_list(db, encounter.procedure_g_drg_code or "", is_insured=True) if claim.type_of_service == "OPD" else 0.0,
            "investigations_amount": sum([get_claim_amount_from_price_list(db, inv.gdrg_code or "", is_insured=True) for inv in encounter.investigations if inv.status == "completed" and inv.gdrg_code and inv.status != "cancelled"]),
            "pharmacy_amount": sum([get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True) * presc.quantity for presc in encounter.prescriptions if presc.dispensed_by]),
        },
    }


@router.put("/{claim_id}", response_model=ClaimResponse)
def update_claim(
    claim_id: int,
    claim_data: ClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Update a draft or reopened claim (simple update)"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Only allow editing of draft or reopened claims
    if claim.status == "finalized":
        raise HTTPException(
            status_code=400,
            detail="Cannot edit finalized claims. Please reopen the claim first."
        )
    
    # Update claim fields
    claim.physician_id = claim_data.physician_id
    claim.type_of_service = claim_data.type_of_service
    claim.type_of_attendance = claim_data.type_of_attendance
    claim.specialty_attended = claim_data.specialty_attended
    
    db.commit()
    db.refresh(claim)
    
    return claim


@router.put("/{claim_id}/detailed", response_model=ClaimResponse)
def update_claim_detailed(
    claim_id: int,
    claim_data: ClaimDetailedUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin"]))
):
    """Update a draft or reopened claim with detailed information"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Only allow editing of draft or reopened claims
    if claim.status == "finalized":
        raise HTTPException(
            status_code=400,
            detail="Cannot edit finalized claims. Please reopen the claim first."
        )
    
    # Update claim fields
    claim.physician_id = claim_data.physician_id
    claim.type_of_service = claim_data.type_of_service
    claim.type_of_attendance = claim_data.type_of_attendance
    claim.specialty_attended = claim_data.specialty_attended
    claim.service_outcome = claim_data.service_outcome or "DISC"
    claim.is_unbundled = claim_data.is_unbundled
    claim.principal_gdrg = claim_data.principal_gdrg or None
    
    # Update encounter with procedure and date information
    encounter = db.query(Encounter).filter(Encounter.id == claim.encounter_id).first()
    if encounter:
        # Update encounter dates if provided
        if claim_data.first_visit:
            try:
                from datetime import datetime
                encounter.created_at = datetime.fromisoformat(claim_data.first_visit.replace('Z', '+00:00'))
            except:
                pass
        
        if claim_data.second_visit:
            try:
                from datetime import datetime
                encounter.finalized_at = datetime.fromisoformat(claim_data.second_visit.replace('Z', '+00:00'))
            except:
                pass
        
        # Update encounter procedure from first procedure in list (only if procedures were provided)
        # If procedures array is empty, it means user intentionally removed all procedures
        if claim_data.procedures and len(claim_data.procedures) > 0:
            first_proc = claim_data.procedures[0]
            if first_proc.description and first_proc.gdrg:
                encounter.procedure_g_drg_code = first_proc.gdrg
                encounter.procedure_name = first_proc.description
        # If procedures array is empty, we should clear the encounter procedure fields to respect user's deletion
        elif claim_data.procedures is not None:  # Explicitly empty array (not undefined)
            encounter.procedure_g_drg_code = None
            encounter.procedure_name = None
        
        # Principal GDRG is now set directly from the form field, not from procedure
        # (This was already set above in claim.principal_gdrg = claim_data.principal_gdrg or None)
    
    # Update claim detail tables (this is where claim-specific edits are stored)
    from app.models.claim_detail import ClaimDiagnosis, ClaimInvestigation, ClaimPrescription, ClaimProcedure
    
    # Delete existing claim details
    db.query(ClaimDiagnosis).filter(ClaimDiagnosis.claim_id == claim.id).delete()
    db.query(ClaimInvestigation).filter(ClaimInvestigation.claim_id == claim.id).delete()
    db.query(ClaimPrescription).filter(ClaimPrescription.claim_id == claim.id).delete()
    db.query(ClaimProcedure).filter(ClaimProcedure.claim_id == claim.id).delete()
    
    # Recreate diagnoses from updated data
    for idx, diag_update in enumerate(claim_data.diagnoses):
        if diag_update.description and diag_update.description.strip():
            claim_diag = ClaimDiagnosis(
                claim_id=claim.id,
                diagnosis_id=diag_update.id if diag_update.id else None,
                description=diag_update.description,
                icd10=diag_update.icd10 or "",
                gdrg_code=diag_update.gdrg or "",
                is_chief=diag_update.is_chief,
                display_order=idx
            )
            db.add(claim_diag)
    
    # Recreate investigations from updated data
    for idx, inv_update in enumerate(claim_data.investigations):
        if inv_update.description and inv_update.description.strip() and inv_update.gdrg:
            service_date = encounter.created_at
            if inv_update.date:
                try:
                    from datetime import datetime
                    service_date = datetime.fromisoformat(inv_update.date.replace('Z', '+00:00'))
                except:
                    pass
            
            claim_inv = ClaimInvestigation(
                claim_id=claim.id,
                investigation_id=inv_update.id if inv_update.id else None,
                description=inv_update.description,
                gdrg_code=inv_update.gdrg,
                service_date=service_date,
                investigation_type="",  # Can be derived from original if needed
                display_order=idx
            )
            db.add(claim_inv)
    
    # Recreate prescriptions from updated data
    for idx, presc_update in enumerate(claim_data.prescriptions):
        if presc_update.description and presc_update.description.strip():
            service_date = encounter.created_at
            if presc_update.date:
                try:
                    from datetime import datetime
                    service_date = datetime.fromisoformat(presc_update.date.replace('Z', '+00:00'))
                except:
                    pass
            
            claim_presc = ClaimPrescription(
                claim_id=claim.id,
                prescription_id=presc_update.id if presc_update.id else None,
                description=presc_update.description,
                code=presc_update.code,
                price=presc_update.price,
                quantity=presc_update.quantity,
                total_cost=presc_update.total_cost,
                service_date=service_date,
                dose=presc_update.dose or "",
                frequency=presc_update.frequency or "",
                duration=presc_update.duration or "",
                unparsed=presc_update.unparsed or "",
                display_order=idx
            )
            db.add(claim_presc)
    
    # Recreate procedures from updated data
    for idx, proc_update in enumerate(claim_data.procedures):
        if proc_update.description and proc_update.description.strip() and proc_update.gdrg:
            service_date = encounter.created_at
            if proc_update.date:
                try:
                    from datetime import datetime
                    service_date = datetime.fromisoformat(proc_update.date.replace('Z', '+00:00'))
                except:
                    pass
            
            claim_proc = ClaimProcedure(
                claim_id=claim.id,
                description=proc_update.description,
                gdrg_code=proc_update.gdrg,
                service_date=service_date,
                display_order=idx
            )
            db.add(claim_proc)
    
    db.commit()
    db.refresh(claim)
    
    return claim

