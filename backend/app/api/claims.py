"""
Claims management endpoints
"""
import io
import re
import zipfile
from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from pydantic import BaseModel
from typing import Optional, List, Tuple, Dict
from datetime import datetime, date, timedelta
from app.core.database import get_db
from app.core.dependencies import require_role, require_module_permission
from app.core.audit import get_effective_creator_id
from app.models.user import User
from app.models.encounter import Encounter
from app.models.claim import Claim, ClaimStatus
from app.models.bill import Bill
from app.utils.claim_generator import generate_claim_id, generate_claim_check_code
from app.services.xml_export import export_claims_xml, export_claims_by_date_range, get_claim_ids_by_date_range, stream_claims_xml_by_ids, is_consultation_service_procedure
from app.models.diagnosis import Diagnosis
from app.models.claimit_report import ClaimItReportBatch, ClaimItReportError
from app.services.claimit_report_parser import parse_claimit_report_html
from app.models.claim_xml_import import ClaimXmlImportBatch, ClaimXmlImportItem
from app.services.claim_xml_import_parser import parse_claims_xml, build_claims_xml_from_payloads
from app.services.claim_nhia_ccc import fetch_ccc_preview_for_claim, fetch_ccc_preview_for_ghims_payload
from app.services.nhia_integration import NhiaIntegrationError
from app.models.product_price import ProductPrice
from app.services.claim_amount_service import (
    get_claim_amount_from_price_list,
    compute_claim_summary_dict,
    compute_claim_summary_from_ghims_payload,
    compute_encounter_claim_summary,
    compute_ghims_batch_claim_totals,
    PriceAmountCache,
)

router = APIRouter(prefix="/claims", tags=["claims"])

# Section keys used for ClaimIT errors on Edit Claim (must match frontend)
CLAIMIT_SECTION_ORDER = ["client", "provider", "services", "procedures", "diagnosis", "investigations", "medicines", "other"]


def _enrich_encounter_row_with_claim_amount(
    db: Session,
    row: dict,
    encounter: Encounter,
    claim: Optional[Claim] = None,
    ward_admission=None,
) -> dict:
    """Attach total_claim_amount to an eligible-encounters list row."""
    try:
        summary = compute_encounter_claim_summary(db, encounter, claim, ward_admission)
        row["total_claim_amount"] = round(float(summary.get("total_amount") or 0.0), 2)
    except Exception:
        row["total_claim_amount"] = 0.0
    return row


def _should_include_opd_prescription(presc, include_prescription_ids: Optional[List[int]] = None) -> bool:
    """Include dispensed OPD prescriptions, or undispensed ones explicitly selected at claim generation."""
    if not presc.medicine_code:
        return False
    if presc.dispensed_by:
        return True
    return bool(include_prescription_ids and presc.id in include_prescription_ids)


def _should_include_ipd_prescription(presc, include_inpatient_prescription_ids: Optional[List[int]] = None) -> bool:
    """Include dispensed IPD prescriptions, or undispensed ones explicitly selected at claim generation."""
    if not presc.medicine_code:
        return False
    if presc.dispensed_by:
        return True
    return bool(include_inpatient_prescription_ids and presc.id in include_inpatient_prescription_ids)


def _load_encounter_with_services(db: Session, encounter_id: int) -> Optional[Encounter]:
    """Load encounter with diagnoses, investigations, prescriptions, and patient eagerly."""
    from sqlalchemy.orm import joinedload
    return db.query(Encounter).options(
        joinedload(Encounter.diagnoses),
        joinedload(Encounter.investigations),
        joinedload(Encounter.prescriptions),
        joinedload(Encounter.patient),
    ).filter(Encounter.id == encounter_id).first()


def _categorize_claimit_error_pairs(pairs: List[Tuple[Optional[str], str]]) -> dict:
    """
    Map ClaimIT messages to form sections. Each pair is (outcome_or_None, message).
    When outcome is set, the stored string is prefixed [ERROR] / [WARNING] for display.
    """
    by_section = {s: [] for s in CLAIMIT_SECTION_ORDER}
    for outcome, msg in pairs:
        if not msg or not isinstance(msg, str):
            continue
        lower = msg.lower()
        labeled = f"[{(outcome or 'ERROR').strip().upper()}] {msg}" if outcome else msg

        # OPD/IPD combined procedure+diagnosis validation → show under both sections
        if (
            ("procedures/diagnoses" in lower.replace(" ", ""))
            or ("procedure" in lower and "diagnosis" in lower and ("opd" in lower or "ipd" in lower))
        ):
            by_section["procedures"].append(labeled)
            by_section["diagnosis"].append(labeled)
            continue

        if any(k in lower for k in ("member", "card serial", "hospital record", "insurance id", "patient", "surname", "other name", "date of birth", "age", "gender", "nhis number")):
            by_section["client"].append(labeled)
        elif any(k in lower for k in ("provider", "scheme code", "month of claim")):
            by_section["provider"].append(labeled)
        elif any(k in lower for k in ("type of service", "opd", "ipd", "pharmacy", "attendance", "specialty", "specialties", "outcome", "principal gdrg", "service outcome")):
            by_section["services"].append(labeled)
        elif any(k in lower for k in ("procedure", "surgery", "surgical")) and "diagnosis" not in lower:
            by_section["procedures"].append(labeled)
        elif any(k in lower for k in ("diagnosis", "icd-10", "icd10", "chief complaint", "gdrg")) and "procedure" not in lower and "surgery" not in lower:
            by_section["diagnosis"].append(labeled)
        elif any(k in lower for k in ("investigation", "lab", "x-ray", "xray", "scan")):
            by_section["investigations"].append(labeled)
        elif any(k in lower for k in ("drug", "medicine", "prescription", "frequency", "duration", "dose", "quantity", "pharmacy", "medication")):
            by_section["medicines"].append(labeled)
        else:
            by_section["other"].append(labeled)
    return by_section


def _categorize_claimit_errors(messages: list) -> dict:
    """Map ClaimIT error message strings to form sections (no outcome prefix)."""
    pairs = [(None, m) for m in messages if m and isinstance(m, str)]
    return _categorize_claimit_error_pairs(pairs)


def _get_claimit_errors_for_claim(db: Session, claim_id_str: str) -> dict:
    """Fetch ClaimIT report errors for this claim (by claim id string) and return messages + by_section."""
    rows = (
        db.query(ClaimItReportError)
        .filter(ClaimItReportError.claim_claim_id == claim_id_str)
        .order_by(ClaimItReportError.id.desc())
        .all()
    )
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for e in rows:
        oc = (e.outcome or "ERROR").strip().upper()
        for m in (e.error_messages or []):
            if not isinstance(m, str) or not m.strip():
                continue
            key = (oc, m.strip())
            if key in seen:
                continue
            seen.add(key)
            pairs.append(key)
    by_section = _categorize_claimit_error_pairs(pairs)
    messages = list(dict.fromkeys(f"[{o}] {t}" for o, t in pairs))
    return {"messages": messages, "by_section": by_section}


def _get_claimit_errors_for_import_item(db: Session, item: ClaimXmlImportItem) -> dict:
    """ClaimIT errors for a GHIMS import row — match report rows by DB claim_claim_id or payload claimID."""
    ids = {str(item.claim_claim_id or "").strip()}
    p = item.payload or {}
    cid = str(p.get("claimID") or p.get("claimId") or "").strip()
    if cid:
        ids.add(cid)
    ids.discard("")
    if not ids:
        return {"messages": [], "by_section": {s: [] for s in CLAIMIT_SECTION_ORDER}}
    rows = (
        db.query(ClaimItReportError)
        .filter(ClaimItReportError.claim_claim_id.in_(list(ids)))
        .order_by(ClaimItReportError.id.desc())
        .all()
    )
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for e in rows:
        oc = (e.outcome or "ERROR").strip().upper()
        for m in (e.error_messages or []):
            if not isinstance(m, str) or not m.strip():
                continue
            key = (oc, m.strip())
            if key in seen:
                continue
            seen.add(key)
            pairs.append(key)
    by_section = _categorize_claimit_error_pairs(pairs)
    messages = list(dict.fromkeys(f"[{o}] {t}" for o, t in pairs))
    return {"messages": messages, "by_section": by_section}


def _ensure_claim_procedures_icd10_column(db: Session) -> None:
    """Ensure claim_procedures has icd10 column (for DBs created before it was added)."""
    try:
        dialect_name = db.get_bind().dialect.name if hasattr(db.get_bind(), "dialect") else ""
        if dialect_name == "mysql":
            db.execute(text("ALTER TABLE claim_procedures ADD COLUMN icd10 VARCHAR(50) NULL"))
        elif dialect_name == "sqlite":
            db.execute(text("ALTER TABLE claim_procedures ADD COLUMN icd10 VARCHAR(50)"))
        else:
            return
        db.flush()
    except Exception as e:
        err = str(e).lower()
        if "duplicate column" in err or "already exists" in err:
            pass
        else:
            raise


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
    finalized_by_username: Optional[str] = None  # Username of user who finalized
    created_at: datetime
    claim_id: Optional[int] = None
    claim_status: Optional[str] = None
    ward_admission_id: Optional[int] = None  # For IPD claims
    total_claim_amount: Optional[float] = None
    
    class Config:
        from_attributes = True


class ClaimCreate(BaseModel):
    """Claim creation model"""
    encounter_id: Optional[int] = None  # For OPD claims
    ward_admission_id: Optional[int] = None  # For IPD claims
    physician_id: str
    type_of_service: str = "OPD"
    type_of_attendance: Optional[str] = "EAE"
    specialty_attended: Optional[str] = "OPDC"
    include_prescription_ids: Optional[List[int]] = None  # OPD: undispensed prescriptions to include
    include_inpatient_prescription_ids: Optional[List[int]] = None  # IPD: undispensed prescriptions to include


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
    icd10: Optional[str] = ""


class ClaimDetailedUpdate(BaseModel):
    """Detailed claim update model"""
    physician_id: str
    physician_name: Optional[str] = ""
    type_of_service: str = "OPD"
    includes_pharmacy: bool = False  # Pharmacy ticked under type of service -> export <includesPharmacy>1</includesPharmacy>
    type_of_attendance: Optional[str] = "EAE"
    specialty_attended: Optional[str] = "OPDC"
    service_outcome: Optional[str] = "DISC"
    is_unbundled: bool = False
    principal_gdrg: Optional[str] = ""
    claim_check_code: Optional[str] = None
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
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "create"))
):
    """Create a new claim from an encounter (OPD) or ward admission (IPD)"""
    from app.models.ward_admission import WardAdmission
    from app.models.admission import AdmissionRecommendation
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_diagnosis import InpatientDiagnosis
    from app.models.inpatient_investigation import InpatientInvestigation
    from app.models.inpatient_prescription import InpatientPrescription
    from app.models.prescription import Prescription as OPDPrescription
    from app.models.claim_detail import ClaimDiagnosis, ClaimInvestigation, ClaimPrescription, ClaimProcedure
    from app.services.price_list_service_v2 import get_price_from_all_tables
    
    # Determine if this is an IPD claim
    is_ipd = claim_data.type_of_service.upper() == "IPD" or claim_data.ward_admission_id is not None
    
    if is_ipd:
        # IPD Claim - get ward admission
        if not claim_data.ward_admission_id:
            raise HTTPException(status_code=400, detail="ward_admission_id is required for IPD claims")
        
        ward_admission = db.query(WardAdmission).filter(WardAdmission.id == claim_data.ward_admission_id).first()
        if not ward_admission:
            raise HTTPException(status_code=404, detail="Ward admission not found")
        
        if not ward_admission.discharged_at:
            raise HTTPException(status_code=400, detail="Can only create claims for discharged patients")
        
        # Get the IPD encounter
        encounter = ward_admission.encounter
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found for ward admission")
        
        # Get OPD encounter that led to admission (if exists)
        opd_encounter = None
        admission_recommendation = db.query(AdmissionRecommendation).filter(
            AdmissionRecommendation.id == ward_admission.admission_recommendation_id
        ).first()
        
        if admission_recommendation and admission_recommendation.encounter_id != ward_admission.encounter_id:
            # Different encounter means there was an OPD encounter before admission
            from sqlalchemy.orm import joinedload
            opd_encounter = db.query(Encounter)\
                .options(
                    joinedload(Encounter.diagnoses),
                    joinedload(Encounter.investigations),
                    joinedload(Encounter.prescriptions)
                )\
                .filter(Encounter.id == admission_recommendation.encounter_id)\
                .first()
        
        # Check if all bills are paid for the IPD encounter
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
        
        patient = encounter.patient
        
        # Validate member number (insurance_id) exists
        if not patient.insurance_id or patient.insurance_id.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Cannot create claim: Patient member number (insurance ID) is required but not found. Please update the patient's insurance information."
            )
        
        # Get all IPD services
        clinical_reviews = db.query(InpatientClinicalReview).filter(
            InpatientClinicalReview.ward_admission_id == ward_admission.id
        ).all()
        
        clinical_review_ids = [cr.id for cr in clinical_reviews] if clinical_reviews else []
        
        # Get IPD diagnoses
        ipd_diagnoses = []
        if clinical_review_ids:
            ipd_diagnoses = db.query(InpatientDiagnosis).filter(
                InpatientDiagnosis.clinical_review_id.in_(clinical_review_ids)
            ).order_by(InpatientDiagnosis.created_at).all()
        
        # Get IPD investigations (include all statuses except cancelled)
        ipd_investigations = []
        if clinical_review_ids:
            ipd_investigations = db.query(InpatientInvestigation).filter(
                InpatientInvestigation.clinical_review_id.in_(clinical_review_ids),
                InpatientInvestigation.status != "cancelled"
            ).order_by(InpatientInvestigation.created_at).all()
        
        # Get all IPD prescriptions (dispensed auto-included; undispensed only if selected)
        ipd_prescriptions = []
        if clinical_review_ids:
            ipd_prescriptions = db.query(InpatientPrescription).filter(
                InpatientPrescription.clinical_review_id.in_(clinical_review_ids)
            ).order_by(InpatientPrescription.created_at).all()
        
        # Check if pharmacy items exist (OPD + IPD)
        has_pharmacy = False
        if opd_encounter:
            has_pharmacy = len(opd_encounter.prescriptions) > 0
        if not has_pharmacy:
            has_pharmacy = len(ipd_prescriptions) > 0
        
        # Get principal GDRG from chief diagnosis (check OPD first, then IPD)
        principal_gdrg = None
        if opd_encounter:
            chief_diagnosis = db.query(Diagnosis).filter(
                Diagnosis.encounter_id == opd_encounter.id,
                Diagnosis.is_chief == True
            ).first()
            if chief_diagnosis:
                principal_gdrg = chief_diagnosis.gdrg_code
        
        if not principal_gdrg and ipd_diagnoses:
            chief_ipd_diag = next((d for d in ipd_diagnoses if d.is_chief), None)
            if chief_ipd_diag:
                principal_gdrg = chief_ipd_diag.gdrg_code
        
        # Set encounter finalized_at to discharge date for IPD claims (for 2nd visit date)
        if ward_admission.discharged_at:
            encounter.finalized_at = ward_admission.discharged_at
        
        # Create claim
        claim = Claim(
            encounter_id=encounter.id,  # Use IPD encounter_id
            claim_id=generate_claim_id(db),
            claim_check_code=generate_claim_check_code(),
            physician_id=claim_data.physician_id,
            member_no=patient.insurance_id,
            card_serial_no=patient.card_number or "",
            is_dependant=False,
            type_of_service="IPD",
            includes_pharmacy=has_pharmacy,
            type_of_attendance=claim_data.type_of_attendance,
            service_outcome="DISC",
            specialty_attended=claim_data.specialty_attended,
            principal_gdrg=principal_gdrg,
            status=ClaimStatus.DRAFT.value,
            created_by=get_effective_creator_id(db, current_user)
        )
        
        db.add(claim)
        db.flush()
        
        # Populate diagnoses: OPD first, then IPD (no limit for IPD claims - include all services)
        diagnosis_order = 0
        
        # Add OPD diagnoses first
        if opd_encounter:
            for diag in opd_encounter.diagnoses:
                diagnosis_exists = db.query(Diagnosis).filter(Diagnosis.id == diag.id).first() is not None
                claim_diag = ClaimDiagnosis(
                    claim_id=claim.id,
                    diagnosis_id=diag.id if diagnosis_exists else None,
                    description=diag.diagnosis,
                    icd10=diag.icd10,
                    gdrg_code=diag.gdrg_code or "",
                    is_chief=diag.is_chief,
                    display_order=diagnosis_order
                )
                db.add(claim_diag)
                diagnosis_order += 1
        
        # Add IPD diagnoses (all of them - no limit)
        for diag in ipd_diagnoses:
            claim_diag = ClaimDiagnosis(
                claim_id=claim.id,
                diagnosis_id=None,  # IPD diagnoses don't have direct diagnosis_id reference
                description=diag.diagnosis,
                icd10=diag.icd10,
                gdrg_code=diag.gdrg_code or "",
                is_chief=diag.is_chief,
                display_order=diagnosis_order
            )
            db.add(claim_diag)
            diagnosis_order += 1
        
        # Populate investigations: OPD first, then IPD (no limit for IPD claims - include all services)
        investigation_order = 0
        
        # Add OPD investigations first (include all statuses except cancelled)
        if opd_encounter:
            from app.models.investigation import Investigation
            for inv in opd_encounter.investigations:
                if inv.status != "cancelled" and inv.gdrg_code:
                    # Verify investigation still exists in database (it might have been deleted)
                    investigation_exists = db.query(Investigation).filter(Investigation.id == inv.id).first() is not None
                    investigation_id = inv.id if investigation_exists else None
                    
                    claim_inv = ClaimInvestigation(
                        claim_id=claim.id,
                        investigation_id=investigation_id,  # Set to None if investigation was deleted
                        description=inv.procedure_name or "",
                        gdrg_code=inv.gdrg_code,
                        service_date=inv.service_date or opd_encounter.created_at,
                        investigation_type=inv.investigation_type,
                        display_order=investigation_order
                    )
                    db.add(claim_inv)
                    investigation_order += 1
        
        # Add IPD investigations (all of them - no limit)
        for inv in ipd_investigations:
            if inv.gdrg_code:
                # Get clinical review for service date
                clinical_review = next((cr for cr in clinical_reviews if cr.id == inv.clinical_review_id), None)
                service_date = clinical_review.created_at if clinical_review else ward_admission.admitted_at
                
                claim_inv = ClaimInvestigation(
                    claim_id=claim.id,
                    investigation_id=None,  # IPD investigations use different model
                    description=inv.procedure_name or "",
                    gdrg_code=inv.gdrg_code,
                    service_date=service_date,
                    investigation_type=inv.investigation_type,
                    display_order=investigation_order
                )
                db.add(claim_inv)
                investigation_order += 1
        
        # Populate prescriptions: OPD first, then IPD (no limit for IPD claims - include all services)
        prescription_order = 0
        
        # Add OPD prescriptions first
        if opd_encounter:
            for presc in opd_encounter.prescriptions:
                if _should_include_opd_prescription(presc, claim_data.include_prescription_ids):
                    claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
                    prescription_exists = db.query(OPDPrescription).filter(OPDPrescription.id == presc.id).first() is not None
                    
                    claim_presc = ClaimPrescription(
                        claim_id=claim.id,
                        prescription_id=presc.id if prescription_exists else None,
                        description=presc.medicine_name,
                        code=presc.medicine_code,
                        price=float(claim_amount) if claim_amount else 0.0,
                        quantity=presc.quantity,
                        total_cost=float(claim_amount * presc.quantity) if claim_amount else 0.0,
                        service_date=presc.service_date or opd_encounter.created_at,
                        dose=presc.dose or "",
                        frequency=presc.frequency or "",
                        duration=presc.duration or "",
                        unparsed=presc.unparsed or "",
                        display_order=prescription_order
                    )
                    db.add(claim_presc)
                    prescription_order += 1
        
        # Add IPD prescriptions (all of them - no limit)
        for presc in ipd_prescriptions:
            if _should_include_ipd_prescription(presc, claim_data.include_inpatient_prescription_ids):
                claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
                
                # Get clinical review for service date
                clinical_review = next((cr for cr in clinical_reviews if cr.id == presc.clinical_review_id), None)
                service_date = clinical_review.created_at if clinical_review else ward_admission.admitted_at
                
                claim_presc = ClaimPrescription(
                    claim_id=claim.id,
                    prescription_id=None,  # IPD prescriptions use different model
                    description=presc.medicine_name,
                    code=presc.medicine_code,
                    price=float(claim_amount) if claim_amount else 0.0,
                    quantity=presc.quantity,
                    total_cost=float(claim_amount * presc.quantity) if claim_amount else 0.0,
                    service_date=service_date,
                    dose=presc.dose or "",
                    frequency=presc.frequency or "",
                    duration=presc.duration or "",
                    unparsed=presc.unparsed or "",
                    display_order=prescription_order
                )
                db.add(claim_presc)
                prescription_order += 1
        
        # Populate procedures from surgeries (IPD only - surgeries, not encounter procedure)
        from app.models.inpatient_surgery import InpatientSurgery
        surgeries = db.query(InpatientSurgery).filter(
            InpatientSurgery.ward_admission_id == ward_admission.id,
            InpatientSurgery.is_completed == True  # Only completed surgeries
        ).order_by(InpatientSurgery.surgery_date, InpatientSurgery.created_at).all()
        
        procedure_order = 0
        for surgery in surgeries:
            if procedure_order >= 3:  # Limit to 3 procedures
                break
            claim_proc = ClaimProcedure(
                claim_id=claim.id,
                description=surgery.surgery_name or "",
                gdrg_code=surgery.g_drg_code or "",
                service_date=surgery.surgery_date or encounter.created_at,
                display_order=procedure_order
            )
            db.add(claim_proc)
            procedure_order += 1
        
    else:
        # OPD Claim - original logic
        if not claim_data.encounter_id:
            raise HTTPException(status_code=400, detail="encounter_id is required for OPD claims")
        
        encounter = _load_encounter_with_services(db, claim_data.encounter_id)
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
        
        # Validate member number (insurance_id) exists
        if not patient.insurance_id or patient.insurance_id.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Cannot create claim: Patient member number (insurance ID) is required but not found. Please update the patient's insurance information."
            )
        
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
            member_no=patient.insurance_id,
            card_serial_no=patient.card_number or "",
            is_dependant=False,
            type_of_service=claim_data.type_of_service,
            includes_pharmacy=has_pharmacy,
            type_of_attendance=claim_data.type_of_attendance,
            service_outcome="DISC",
            specialty_attended=claim_data.specialty_attended,
            principal_gdrg=principal_gdrg,
            status=ClaimStatus.DRAFT.value,
            created_by=get_effective_creator_id(db, current_user)
        )
        
        db.add(claim)
        db.flush()  # Flush to get claim.id
        
        # Populate diagnoses (up to 4)
        diagnosis_order = 0
        for diag in encounter.diagnoses:
            if diagnosis_order >= 4:
                break
            # Verify diagnosis still exists in database before referencing it
            diagnosis_exists = db.query(Diagnosis).filter(Diagnosis.id == diag.id).first() is not None
            claim_diag = ClaimDiagnosis(
                claim_id=claim.id,
                diagnosis_id=diag.id if diagnosis_exists else None,
                description=diag.diagnosis,
                icd10=diag.icd10,
                gdrg_code=diag.gdrg_code or "",
                is_chief=diag.is_chief,
                display_order=diagnosis_order
            )
            db.add(claim_diag)
            diagnosis_order += 1
        
        # Populate investigations (up to 5, include all except cancelled)
        investigation_order = 0
        from app.models.investigation import Investigation
        for inv in encounter.investigations:
            if investigation_order >= 5:
                break
            if inv.status != "cancelled" and inv.gdrg_code:
                # Verify investigation still exists in database (it might have been deleted)
                investigation_exists = db.query(Investigation).filter(Investigation.id == inv.id).first() is not None
                investigation_id = inv.id if investigation_exists else None
                
                claim_inv = ClaimInvestigation(
                    claim_id=claim.id,
                    investigation_id=investigation_id,  # Set to None if investigation was deleted
                    description=inv.procedure_name or "",
                    gdrg_code=inv.gdrg_code,
                    service_date=inv.service_date or encounter.created_at,
                    investigation_type=inv.investigation_type,
                    display_order=investigation_order
                )
                db.add(claim_inv)
                investigation_order += 1
        
        # Populate prescriptions (up to 5; dispensed auto-included, undispensed only if selected)
        prescription_order = 0
        for presc in encounter.prescriptions:
            if prescription_order >= 5:
                break
            if _should_include_opd_prescription(presc, claim_data.include_prescription_ids):
                # Get claim amount from price list
                claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
                
                # Verify prescription still exists in database before referencing it
                prescription_exists = db.query(OPDPrescription).filter(OPDPrescription.id == presc.id).first() is not None
                
                claim_presc = ClaimPrescription(
                    claim_id=claim.id,
                    prescription_id=presc.id if prescription_exists else None,
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
        
        # Populate procedures from surgeries for OPD (if any surgeries exist, e.g., catheter changing)
        from app.models.inpatient_surgery import InpatientSurgery
        opd_surgeries = db.query(InpatientSurgery).filter(
            InpatientSurgery.encounter_id == encounter.id,
            InpatientSurgery.is_completed == True  # Only completed surgeries
        ).order_by(InpatientSurgery.surgery_date, InpatientSurgery.created_at).all()
        
        procedure_order = 0
        for surgery in opd_surgeries:
            if procedure_order >= 3:  # Limit to 3 procedures
                break
            claim_proc = ClaimProcedure(
                claim_id=claim.id,
                description=surgery.surgery_name or "",
                gdrg_code=surgery.g_drg_code or "",
                service_date=surgery.surgery_date or encounter.created_at,
                display_order=procedure_order
            )
            db.add(claim_proc)
            procedure_order += 1
        # If no surgeries found, no procedures are added (only diagnoses, medications, and investigations)
    
    db.commit()
    db.refresh(claim)
    
    return claim


@router.put("/{claim_id}/finalize")
def finalize_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update"))
):
    """Finalize a claim"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # For IPD admissions, require discharge before finalization
    if claim.type_of_service == "IPD":
        from app.models.ward_admission import WardAdmission
        ward_admission = db.query(WardAdmission).filter(
            WardAdmission.encounter_id == claim.encounter_id
        ).first()
        
        if ward_admission:
            # Check if patient has been discharged
            if ward_admission.discharged_at is None:
                raise HTTPException(
                    status_code=400, 
                    detail="Cannot finalize IPD claim before patient is discharged. Please discharge the patient from the ward first."
                )
    
    claim.status = ClaimStatus.FINALIZED.value
    claim.finalized_at = datetime.utcnow()
    db.commit()
    
    return {"claim_id": claim.id, "status": claim.status}


@router.put("/{claim_id}/reopen")
def reopen_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update"))
):
    """Reopen a finalized claim for corrections"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    claim.status = ClaimStatus.REOPENED.value
    db.commit()
    
    return {"claim_id": claim.id, "status": claim.status}


@router.put("/{claim_id}/regenerate")
def regenerate_claim(
    claim_id: int,
    claim_data: ClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update"))
):
    """Regenerate a claim by deleting existing details and recreating from encounter (OPD) or ward admission (IPD)"""
    from app.models.ward_admission import WardAdmission
    from app.models.admission import AdmissionRecommendation
    from app.models.inpatient_clinical_review import InpatientClinicalReview
    from app.models.inpatient_diagnosis import InpatientDiagnosis
    from app.models.inpatient_investigation import InpatientInvestigation
    from app.models.inpatient_prescription import InpatientPrescription
    from app.models.prescription import Prescription as OPDPrescription
    from app.models.claim_detail import ClaimDiagnosis, ClaimInvestigation, ClaimPrescription, ClaimProcedure
    from app.services.price_list_service_v2 import get_price_from_all_tables
    
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # Only allow regenerating draft or reopened claims
    if claim.status not in ["draft", "reopened"]:
        raise HTTPException(
            status_code=400,
            detail="Can only regenerate claims in draft or reopened mode. Current status: " + claim.status
        )
    
    # Determine if this is an IPD claim
    is_ipd = claim.type_of_service.upper() == "IPD" or claim_data.ward_admission_id is not None
    
    if is_ipd:
        # IPD Claim regeneration
        # Get ward admission - use claim_data.ward_admission_id if provided, otherwise try to find from claim
        ward_admission_id = claim_data.ward_admission_id
        if not ward_admission_id:
            # Try to find ward admission from encounter
            if claim.encounter_id:
                ward_admission = db.query(WardAdmission).filter(
                    WardAdmission.encounter_id == claim.encounter_id
                ).first()
                if ward_admission:
                    ward_admission_id = ward_admission.id
        
        if not ward_admission_id:
            raise HTTPException(status_code=400, detail="ward_admission_id is required for IPD claim regeneration")
        
        ward_admission = db.query(WardAdmission).filter(WardAdmission.id == ward_admission_id).first()
        if not ward_admission:
            raise HTTPException(status_code=404, detail="Ward admission not found")
        
        if not ward_admission.discharged_at:
            raise HTTPException(status_code=400, detail="Can only regenerate claims for discharged patients")
        
        # Get the IPD encounter
        encounter = ward_admission.encounter
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found for ward admission")
        
        # Set encounter finalized_at to discharge date for IPD claims (for 2nd visit date)
        if ward_admission.discharged_at:
            encounter.finalized_at = ward_admission.discharged_at
        
        # Get OPD encounter that led to admission (if exists)
        opd_encounter = None
        admission_recommendation = db.query(AdmissionRecommendation).filter(
            AdmissionRecommendation.id == ward_admission.admission_recommendation_id
        ).first()
        
        if admission_recommendation and admission_recommendation.encounter_id != ward_admission.encounter_id:
            # Different encounter means there was an OPD encounter before admission
            from sqlalchemy.orm import joinedload
            opd_encounter = db.query(Encounter)\
                .options(
                    joinedload(Encounter.diagnoses),
                    joinedload(Encounter.investigations),
                    joinedload(Encounter.prescriptions)
                )\
                .filter(Encounter.id == admission_recommendation.encounter_id)\
                .first()
        
        # Get all IPD services
        clinical_reviews = db.query(InpatientClinicalReview).filter(
            InpatientClinicalReview.ward_admission_id == ward_admission.id
        ).all()
        
        clinical_review_ids = [cr.id for cr in clinical_reviews] if clinical_reviews else []
        
        # Get IPD diagnoses
        ipd_diagnoses = []
        if clinical_review_ids:
            ipd_diagnoses = db.query(InpatientDiagnosis).filter(
                InpatientDiagnosis.clinical_review_id.in_(clinical_review_ids)
            ).order_by(InpatientDiagnosis.created_at).all()
        
        # Get IPD investigations (include all statuses except cancelled)
        ipd_investigations = []
        if clinical_review_ids:
            ipd_investigations = db.query(InpatientInvestigation).filter(
                InpatientInvestigation.clinical_review_id.in_(clinical_review_ids),
                InpatientInvestigation.status != "cancelled"
            ).order_by(InpatientInvestigation.created_at).all()
        
        # Get all IPD prescriptions (dispensed auto-included; undispensed only if selected)
        ipd_prescriptions = []
        if clinical_review_ids:
            ipd_prescriptions = db.query(InpatientPrescription).filter(
                InpatientPrescription.clinical_review_id.in_(clinical_review_ids)
            ).order_by(InpatientPrescription.created_at).all()
        
        # Check if pharmacy items exist (OPD + IPD)
        has_pharmacy = False
        if opd_encounter:
            has_pharmacy = len(opd_encounter.prescriptions) > 0
        if not has_pharmacy:
            has_pharmacy = len(ipd_prescriptions) > 0
        
        # Get principal GDRG from chief diagnosis (check OPD first, then IPD)
        principal_gdrg = None
        if opd_encounter:
            chief_diagnosis = db.query(Diagnosis).filter(
                Diagnosis.encounter_id == opd_encounter.id,
                Diagnosis.is_chief == True
            ).first()
            if chief_diagnosis:
                principal_gdrg = chief_diagnosis.gdrg_code
        
        if not principal_gdrg and ipd_diagnoses:
            chief_ipd_diag = next((d for d in ipd_diagnoses if d.is_chief), None)
            if chief_ipd_diag:
                principal_gdrg = chief_ipd_diag.gdrg_code
        
        patient = encounter.patient
        
        # Validate member number (insurance_id) exists for IPD
        if not patient.insurance_id or patient.insurance_id.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Cannot regenerate claim: Patient member number (insurance ID) is required but not found. Please update the patient's insurance information."
            )
        
    else:
        # OPD Claim regeneration
        # Get encounter - use claim_data.encounter_id if provided, otherwise use claim's encounter_id
        encounter_id = claim_data.encounter_id or claim.encounter_id
        if not encounter_id:
            raise HTTPException(status_code=400, detail="encounter_id is required for OPD claim regeneration")
        
        encounter = _load_encounter_with_services(db, encounter_id)
        if not encounter:
            raise HTTPException(status_code=404, detail="Encounter not found")
        
        if encounter.status != "finalized":
            raise HTTPException(
                status_code=400,
                detail="Can only regenerate claims from finalized encounters"
            )
        
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
        
        # Validate member number (insurance_id) exists for OPD
        if not patient.insurance_id or patient.insurance_id.strip() == "":
            raise HTTPException(
                status_code=400,
                detail="Cannot regenerate claim: Patient member number (insurance ID) is required but not found. Please update the patient's insurance information."
            )
    
    # Delete existing claim details
    db.query(ClaimDiagnosis).filter(ClaimDiagnosis.claim_id == claim_id).delete()
    db.query(ClaimInvestigation).filter(ClaimInvestigation.claim_id == claim_id).delete()
    db.query(ClaimPrescription).filter(ClaimPrescription.claim_id == claim_id).delete()
    db.query(ClaimProcedure).filter(ClaimProcedure.claim_id == claim_id).delete()
    
    # Update claim basic info
    claim.physician_id = claim_data.physician_id
    claim.type_of_service = claim_data.type_of_service
    claim.type_of_attendance = claim_data.type_of_attendance
    claim.specialty_attended = claim_data.specialty_attended
    claim.includes_pharmacy = has_pharmacy
    claim.principal_gdrg = principal_gdrg
    claim.member_no = patient.insurance_id  # Update member number
    claim.card_serial_no = patient.card_number or ""  # Update card number
    
    db.flush()
    
    if is_ipd:
        # IPD: Repopulate claim detail tables from OPD + IPD services
        diagnosis_order = 0
        
        # Add OPD diagnoses first
        if opd_encounter:
            for diag in opd_encounter.diagnoses:
                diagnosis_exists = db.query(Diagnosis).filter(Diagnosis.id == diag.id).first() is not None
                claim_diag = ClaimDiagnosis(
                    claim_id=claim.id,
                    diagnosis_id=diag.id if diagnosis_exists else None,
                    description=diag.diagnosis,
                    icd10=diag.icd10,
                    gdrg_code=diag.gdrg_code or "",
                    is_chief=diag.is_chief,
                    display_order=diagnosis_order
                )
                db.add(claim_diag)
                diagnosis_order += 1
        
        # Add IPD diagnoses (all of them - no limit)
        for diag in ipd_diagnoses:
            claim_diag = ClaimDiagnosis(
                claim_id=claim.id,
                diagnosis_id=None,  # IPD diagnoses don't have direct diagnosis_id reference
                description=diag.diagnosis,
                icd10=diag.icd10,
                gdrg_code=diag.gdrg_code or "",
                is_chief=diag.is_chief,
                display_order=diagnosis_order
            )
            db.add(claim_diag)
            diagnosis_order += 1
        
        # Populate investigations: OPD first, then IPD (no limit)
        investigation_order = 0
        
        # Add OPD investigations first (include all statuses except cancelled)
        if opd_encounter:
            from app.models.investigation import Investigation
            for inv in opd_encounter.investigations:
                if inv.status != "cancelled" and inv.gdrg_code:
                    # Verify investigation still exists in database (it might have been deleted)
                    investigation_exists = db.query(Investigation).filter(Investigation.id == inv.id).first() is not None
                    investigation_id = inv.id if investigation_exists else None
                    
                    claim_amount = get_claim_amount_from_price_list(db, inv.gdrg_code, is_insured=True)
                    claim_inv = ClaimInvestigation(
                        claim_id=claim.id,
                        investigation_id=investigation_id,  # Set to None if investigation was deleted
                        description=inv.procedure_name or "",
                        gdrg_code=inv.gdrg_code,
                        service_date=inv.service_date or opd_encounter.created_at,
                        investigation_type=inv.investigation_type or "",
                        display_order=investigation_order
                    )
                    db.add(claim_inv)
                    investigation_order += 1
        
        # Add IPD investigations (all of them - no limit)
        for inv in ipd_investigations:
            if inv.gdrg_code:
                # Get clinical review for service date
                clinical_review = next((cr for cr in clinical_reviews if cr.id == inv.clinical_review_id), None)
                service_date = clinical_review.created_at if clinical_review else ward_admission.admitted_at
                
                claim_inv = ClaimInvestigation(
                    claim_id=claim.id,
                    investigation_id=None,  # IPD investigations don't have direct investigation_id reference
                    description=inv.procedure_name or "",
                    gdrg_code=inv.gdrg_code,
                    service_date=service_date,
                    investigation_type=inv.investigation_type or "",
                    display_order=investigation_order
                )
                db.add(claim_inv)
                investigation_order += 1
        
        # Populate prescriptions: OPD first, then IPD (no limit)
        prescription_order = 0
        
        # Add OPD prescriptions first
        if opd_encounter:
            for presc in opd_encounter.prescriptions:
                if _should_include_opd_prescription(presc, claim_data.include_prescription_ids):
                    claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
                    claim_presc = ClaimPrescription(
                        claim_id=claim.id,
                        prescription_id=presc.id,
                        description=presc.medicine_name,
                        code=presc.medicine_code,
                        price=float(claim_amount) if claim_amount else 0.0,
                        quantity=presc.quantity,
                        total_cost=float(claim_amount * presc.quantity) if claim_amount else 0.0,
                        service_date=presc.service_date or opd_encounter.created_at,
                        dose=presc.dose or "",
                        frequency=presc.frequency or "",
                        duration=presc.duration or "",
                        unparsed=presc.unparsed or "",
                        display_order=prescription_order
                    )
                    db.add(claim_presc)
                    prescription_order += 1
        
        # Add IPD prescriptions (all of them - no limit)
        for presc in ipd_prescriptions:
            if _should_include_ipd_prescription(presc, claim_data.include_inpatient_prescription_ids):
                claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
                
                # Get clinical review for service date
                clinical_review = next((cr for cr in clinical_reviews if cr.id == presc.clinical_review_id), None)
                service_date = clinical_review.created_at if clinical_review else ward_admission.admitted_at
                
                claim_presc = ClaimPrescription(
                    claim_id=claim.id,
                    prescription_id=None,  # IPD prescriptions use different model
                    description=presc.medicine_name,
                    code=presc.medicine_code,
                    price=float(claim_amount) if claim_amount else 0.0,
                    quantity=presc.quantity,
                    total_cost=float(claim_amount * presc.quantity) if claim_amount else 0.0,
                    service_date=service_date,
                    dose=presc.dose or "",
                    frequency=presc.frequency or "",
                    duration=presc.duration or "",
                    unparsed=presc.unparsed or "",
                    display_order=prescription_order
                )
                db.add(claim_presc)
                prescription_order += 1
        
        # Populate procedures from surgeries (IPD only - surgeries, not encounter procedure)
        from app.models.inpatient_surgery import InpatientSurgery
        surgeries = db.query(InpatientSurgery).filter(
            InpatientSurgery.ward_admission_id == ward_admission.id,
            InpatientSurgery.is_completed == True  # Only completed surgeries
        ).order_by(InpatientSurgery.surgery_date, InpatientSurgery.created_at).all()
        
        procedure_order = 0
        for surgery in surgeries:
            if procedure_order >= 3:  # Limit to 3 procedures
                break
            claim_proc = ClaimProcedure(
                claim_id=claim.id,
                description=surgery.surgery_name or "",
                gdrg_code=surgery.g_drg_code or "",
                service_date=surgery.surgery_date or encounter.created_at,
                display_order=procedure_order
            )
            db.add(claim_proc)
            procedure_order += 1
    
    else:
        # OPD: Repopulate claim detail tables from encounter services
        # Populate diagnoses (up to 4)
        diagnosis_order = 0
        for diag in encounter.diagnoses:
            if diagnosis_order >= 4:
                break
            # Verify diagnosis still exists in database before referencing it
            diagnosis_exists = db.query(Diagnosis).filter(Diagnosis.id == diag.id).first() is not None
            claim_diag = ClaimDiagnosis(
                claim_id=claim.id,
                diagnosis_id=diag.id if diagnosis_exists else None,
                description=diag.diagnosis,
                icd10=diag.icd10,
                gdrg_code=diag.gdrg_code or "",
                is_chief=diag.is_chief,
                display_order=diagnosis_order
            )
            db.add(claim_diag)
            diagnosis_order += 1
        
        # Populate investigations (up to 5, include all except cancelled)
        investigation_order = 0
        from app.models.investigation import Investigation
        for inv in encounter.investigations:
            if investigation_order >= 5:
                break
            if inv.status != "cancelled" and inv.gdrg_code:
                # Verify investigation still exists in database (it might have been deleted)
                investigation_exists = db.query(Investigation).filter(Investigation.id == inv.id).first() is not None
                investigation_id = inv.id if investigation_exists else None
                
                claim_inv = ClaimInvestigation(
                    claim_id=claim.id,
                    investigation_id=investigation_id,  # Set to None if investigation was deleted
                    description=inv.procedure_name or "",
                    gdrg_code=inv.gdrg_code,
                    service_date=inv.service_date or encounter.created_at,
                    investigation_type=inv.investigation_type,
                    display_order=investigation_order
                )
                db.add(claim_inv)
                investigation_order += 1
        
        # Populate prescriptions (up to 5; dispensed auto-included, undispensed only if selected)
        prescription_order = 0
        for presc in encounter.prescriptions:
            if prescription_order >= 5:
                break
            if _should_include_opd_prescription(presc, claim_data.include_prescription_ids):
                # Get claim amount from price list
                claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
                
                # Verify prescription still exists in database before referencing it
                from app.models.prescription import Prescription
                prescription_exists = db.query(Prescription).filter(Prescription.id == presc.id).first() is not None
                
                claim_presc = ClaimPrescription(
                    claim_id=claim.id,
                    prescription_id=presc.id if prescription_exists else None,
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
        
        # Populate procedures from surgeries for OPD (if any surgeries exist, e.g., catheter changing)
        from app.models.inpatient_surgery import InpatientSurgery
        opd_surgeries = db.query(InpatientSurgery).filter(
            InpatientSurgery.encounter_id == encounter.id,
            InpatientSurgery.is_completed == True  # Only completed surgeries
        ).order_by(InpatientSurgery.surgery_date, InpatientSurgery.created_at).all()
        
        procedure_order = 0
        for surgery in opd_surgeries:
            if procedure_order >= 3:  # Limit to 3 procedures
                break
            claim_proc = ClaimProcedure(
                claim_id=claim.id,
                description=surgery.surgery_name or "",
                gdrg_code=surgery.g_drg_code or "",
                service_date=surgery.surgery_date or encounter.created_at,
                display_order=procedure_order
            )
            db.add(claim_proc)
            procedure_order += 1
        # If no surgeries found, no procedures are added (only diagnoses, medications, and investigations)
    
    db.commit()
    db.refresh(claim)
    
    return claim


@router.get("/export-by-date-range")
def export_claims_by_date(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read"))
):
    """Export claims within a date range as a ZIP containing one XML file (max 5000 claims)."""
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be on or after start date")
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    try:
        claim_ids = get_claim_ids_by_date_range(start_dt, end_dt, db)
        stream = stream_claims_xml_by_ids(claim_ids)
        xml_bytes = b"".join(stream)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
    xml_name = f"NHIS_CLA{start_date.strftime('%Y%m%d')}{end_date.strftime('%Y%m%d')}.xml"
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(xml_name, xml_bytes)
    zip_buffer.seek(0)
    zip_filename = f"NHIS_CLA{start_date.strftime('%Y%m%d')}{end_date.strftime('%Y%m%d')}.zip"
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )


class ExportBatchRequest(BaseModel):
    """Request body for batch export of claims"""
    claim_ids: List[int]


@router.post("/export/batch")
def export_claims_batch(
    body: ExportBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read"))
):
    """Export multiple finalized claims as a single XML file. Uses selectinload for speed."""
    import time
    if not body.claim_ids:
        raise HTTPException(status_code=400, detail="No claim IDs provided")
    from app.services.xml_export import generate_claim_xml, _claim_export_load_options
    t0 = time.perf_counter()
    claims = (
        db.query(Claim)
        .options(*_claim_export_load_options())
        .filter(Claim.id.in_(body.claim_ids))
        .all()
    )
    t1 = time.perf_counter()
    found_ids = {c.id for c in claims}
    missing = [i for i in body.claim_ids if i not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Claims not found: {missing}")
    not_finalized = [c for c in claims if c.status != "finalized"]
    if not_finalized:
        raise HTTPException(
            status_code=400,
            detail="Can only export finalized claims"
        )
    xml_content = generate_claim_xml(claims, db)
    t2 = time.perf_counter()
    filename = f"NHIS_CLA_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Export-Query-Sec": f"{t1 - t0:.2f}",
            "X-Export-Xml-Sec": f"{t2 - t1:.2f}",
        }
    )


@router.get("/export/{claim_id}")
def export_claim_xml(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read"))
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


class EligibleEncountersResponse(BaseModel):
    """Response model for eligible encounters with pagination"""
    items: List[EncounterWithClaimInfo]
    total: int
    skip: int
    limit: int
    total_revenue: float = 0.0


class SpecialtiesResponse(BaseModel):
    """List of specialty names for filtering (OPD = departments, IPD = wards)"""
    specialties: List[str]

class ClaimsDashboardTrendPoint(BaseModel):
    month: str  # YYYY-MM
    volume: int
    cost: float


class ClaimsDashboardTopItem(BaseModel):
    name: str
    count: int


class ClaimsDashboardMultipleAttendanceItem(BaseModel):
    member_no: str
    patient_card_number: Optional[str] = None
    patient_name: Optional[str] = None
    attendance_count: int
    claim_ids: List[str] = []
    suggested_specialty_attended: str = "OPDC"


class ClaimsDashboardDuplicateGroup(BaseModel):
    key: str
    member_no: str
    patient_card_number: Optional[str] = None
    patient_name: Optional[str] = None
    count: int
    claim_ids: List[str] = []


class ClaimsDashboardAdvice(BaseModel):
    multiple_attendance: List[ClaimsDashboardMultipleAttendanceItem]
    potential_duplicates: List[ClaimsDashboardDuplicateGroup]


class ClaimsDashboardKPIs(BaseModel):
    total_volume: int
    total_cost: float
    avg_cost_per_claim: float


class ClaimsDashboardResponse(BaseModel):
    source: str  # main | import
    month: str  # YYYY-MM
    kpis: ClaimsDashboardKPIs
    trend: List[ClaimsDashboardTrendPoint]
    top_diagnoses: List[ClaimsDashboardTopItem]
    top_medicines: List[ClaimsDashboardTopItem]
    advice: ClaimsDashboardAdvice


def _month_range(month_yyyy_mm: str) -> tuple[datetime, datetime]:
    """
    Return [start, end) datetimes for month in local time.
    month_yyyy_mm: "YYYY-MM"
    """
    try:
        y, m = month_yyyy_mm.split("-")
        year = int(y)
        month = int(m)
        start = datetime(year, month, 1)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM.")
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


def _prev_month_yyyy_mm(now: Optional[datetime] = None) -> str:
    d = (now or datetime.now()).date().replace(day=1)
    prev_end = datetime.combine(d, datetime.min.time()) - timedelta(days=1)
    return f"{prev_end.year:04d}-{prev_end.month:02d}"

def _month_add(yyyy_mm: str, delta_months: int) -> str:
    y, m = yyyy_mm.split("-")
    year = int(y)
    month = int(m)
    idx = (year * 12 + (month - 1)) + int(delta_months)
    ny = idx // 12
    nm = (idx % 12) + 1
    return f"{ny:04d}-{nm:02d}"


def _months_between_inclusive(start_yyyy_mm: str, end_yyyy_mm: str) -> List[str]:
    """Inclusive month list from start to end. Both YYYY-MM."""
    # Compare by year*12+month index
    sy, sm = start_yyyy_mm.split("-")
    ey, em = end_yyyy_mm.split("-")
    s_idx = int(sy) * 12 + (int(sm) - 1)
    e_idx = int(ey) * 12 + (int(em) - 1)
    if e_idx < s_idx:
        s_idx, e_idx = e_idx, s_idx
        start_yyyy_mm, end_yyyy_mm = end_yyyy_mm, start_yyyy_mm
    months = []
    cur = start_yyyy_mm
    while True:
        months.append(cur)
        if cur == end_yyyy_mm:
            break
        cur = _month_add(cur, 1)
        if len(months) > 120:
            break
    return months


def _parse_month_yyyy_mm(raw: Optional[str]) -> Optional[str]:
    """
    Parse month-of-claim strings into YYYY-MM.
    Supports: YYYY-MM, YYYY/MM, MM/YYYY, MM-YYYY, YYYYMM, YYYY MM.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.replace("\\", "/").replace("-", "/").replace(" ", "/")
    parts = [p for p in s.split("/") if p]
    try:
        if len(parts) == 2:
            a, b = parts[0], parts[1]
            # YYYY/MM
            if len(a) == 4:
                y = int(a)
                m = int(b)
            # MM/YYYY
            elif len(b) == 4:
                y = int(b)
                m = int(a)
            else:
                return None
            if 1 <= m <= 12:
                return f"{y:04d}-{m:02d}"
            return None
        # YYYYMM
        digits = re.sub(r"[^0-9]", "", s)
        if len(digits) == 6:
            y = int(digits[:4])
            m = int(digits[4:])
            if 1 <= m <= 12:
                return f"{y:04d}-{m:02d}"
    except Exception:
        return None
    return None


def _month_range_for_column(db: Session, col, month_yyyy_mm: str):
    """
    Return (start_dt, end_dt) bounds for the given SQLAlchemy datetime column.
    Use local naive datetimes; callers decide which column to filter.
    """
    return _month_range(month_yyyy_mm)


@router.get("/dashboard", response_model=ClaimsDashboardResponse)
def get_claims_dashboard(
    month: Optional[str] = None,  # YYYY-MM
    source: str = "main",  # main | import
    trend_start: Optional[str] = None,  # YYYY-MM (optional; controls trend only)
    trend_end: Optional[str] = None,  # YYYY-MM (optional; controls trend only)
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read"))
):
    """
    Claims dashboard aggregates for a given month.

    - month defaults to previous month (YYYY-MM).
    - source:
      - main: uses finalized claims in `claims` table
      - import: uses finalized imported claims in `claim_xml_import_items`
    """
    from sqlalchemy import and_, or_
    from sqlalchemy.orm import aliased
    from app.models.patient import Patient
    from app.models.claim_detail import ClaimDiagnosis, ClaimPrescription
    from app.models.claim_xml_import import ClaimXmlImportItem

    # Month selection controls ONLY month-specific panels (KPIs + top lists + advice).
    if month is None or not str(month).strip():
        month = _prev_month_yyyy_mm()
    month = str(month).strip()
    source = (source or "main").strip().lower()
    if source not in ("main", "import"):
        raise HTTPException(status_code=400, detail="Invalid source. Use main or import.")

    # HMS "main claims" month should represent when the claim was generated in HMS (created_at),
    # not when it was finalized for export.
    # Imported claims month should come from the payload's provider.monthOfClaim when available.
    start_dt, end_dt = _month_range(month)

    # Trend defaults to a rolling 6 months ending at previous month,
    # and can be overridden by an explicit month range (trend_start/trend_end).
    if trend_start and str(trend_start).strip():
        trend_start = str(trend_start).strip()
    else:
        trend_start = None
    if trend_end and str(trend_end).strip():
        trend_end = str(trend_end).strip()
    else:
        trend_end = None

    if trend_start or trend_end:
        # If only one side is provided, infer the other to preserve a usable range.
        if trend_start and not trend_end:
            trend_end = trend_start
        if trend_end and not trend_start:
            trend_start = _month_add(trend_end, -5)
        trend_months = _months_between_inclusive(trend_start, trend_end)
        # Cap for safety
        trend_months = trend_months[:24]
    else:
        anchor = _prev_month_yyyy_mm()
        trend_months = [_month_add(anchor, -5 + i) for i in range(6)]

    trend: List[ClaimsDashboardTrendPoint] = []
    top_diagnoses: List[ClaimsDashboardTopItem] = []
    top_medicines: List[ClaimsDashboardTopItem] = []
    multiple_attendance: List[ClaimsDashboardMultipleAttendanceItem] = []
    potential_duplicates: List[ClaimsDashboardDuplicateGroup] = []

    total_volume = 0
    total_cost = 0.0

    if source == "main":
        # Base query: finalized claims within month.
        base = (
            db.query(Claim)
            .join(Encounter, Claim.encounter_id == Encounter.id)
            .join(Patient, Encounter.patient_id == Patient.id)
            .filter(
                Claim.status == ClaimStatus.FINALIZED.value,
                Claim.created_at.isnot(None),
                Claim.created_at >= start_dt,
                Claim.created_at < end_dt,
            )
        )

        total_volume = int(base.count())

        # Total cost from prescriptions (pharmacy cost is usually the largest signal).
        # Some claims may have no prescriptions.
        cost_rows = (
            db.query(func.coalesce(func.sum(ClaimPrescription.total_cost), 0.0))
            .select_from(Claim)
            .join(ClaimPrescription, ClaimPrescription.claim_id == Claim.id, isouter=True)
            .filter(
                Claim.status == ClaimStatus.FINALIZED.value,
                Claim.created_at.isnot(None),
                Claim.created_at >= start_dt,
                Claim.created_at < end_dt,
            )
            .one()
        )
        total_cost = float(cost_rows[0] or 0.0)

        # Trend months are independent of selected `month`.
        for m_yyyy_mm in trend_months:
            m_start, m_end = _month_range(m_yyyy_mm)
            vol = (
                db.query(func.count(Claim.id))
                .filter(
                    Claim.status == ClaimStatus.FINALIZED.value,
                    Claim.created_at.isnot(None),
                    Claim.created_at >= m_start,
                    Claim.created_at < m_end,
                )
                .scalar()
            ) or 0
            c = (
                db.query(func.coalesce(func.sum(ClaimPrescription.total_cost), 0.0))
                .select_from(Claim)
                .join(ClaimPrescription, ClaimPrescription.claim_id == Claim.id, isouter=True)
                .filter(
                    Claim.status == ClaimStatus.FINALIZED.value,
                    Claim.created_at.isnot(None),
                    Claim.created_at >= m_start,
                    Claim.created_at < m_end,
                )
                .scalar()
            ) or 0.0
            trend.append(ClaimsDashboardTrendPoint(month=m_yyyy_mm, volume=int(vol), cost=float(c)))

        # Top diagnoses by count.
        dx_rows = (
            db.query(ClaimDiagnosis.description, func.count(ClaimDiagnosis.id))
            .join(Claim, ClaimDiagnosis.claim_id == Claim.id)
            .filter(
                Claim.status == ClaimStatus.FINALIZED.value,
                Claim.created_at.isnot(None),
                Claim.created_at >= start_dt,
                Claim.created_at < end_dt,
                ClaimDiagnosis.description.isnot(None),
                ClaimDiagnosis.description != "",
            )
            .group_by(ClaimDiagnosis.description)
            .order_by(func.count(ClaimDiagnosis.id).desc())
            .limit(10)
            .all()
        )
        top_diagnoses = [ClaimsDashboardTopItem(name=str(name), count=int(cnt)) for name, cnt in dx_rows]

        # Top medicines by count (frequency of prescription lines).
        med_rows = (
            db.query(ClaimPrescription.description, func.count(ClaimPrescription.id))
            .join(Claim, ClaimPrescription.claim_id == Claim.id)
            .filter(
                Claim.status == ClaimStatus.FINALIZED.value,
                Claim.created_at.isnot(None),
                Claim.created_at >= start_dt,
                Claim.created_at < end_dt,
                ClaimPrescription.description.isnot(None),
                ClaimPrescription.description != "",
            )
            .group_by(ClaimPrescription.description)
            .order_by(func.count(ClaimPrescription.id).desc())
            .limit(10)
            .all()
        )
        top_medicines = [ClaimsDashboardTopItem(name=str(name), count=int(cnt)) for name, cnt in med_rows]

        # Multiple attendance advice: same member_no with ANC/PNC attendance multiple times in month.
        # Patient name columns: stored as (name, surname, other_names) in this codebase.
        patient_name_expr = func.trim(
            func.concat(
                func.coalesce(Patient.surname, ""),
                " ",
                func.coalesce(Patient.other_names, ""),
                " ",
                func.coalesce(Patient.name, ""),
            )
        )

        ma_rows = (
            db.query(
                Claim.member_no,
                func.max(Patient.card_number),
                func.max(patient_name_expr),
                func.count(Claim.id),
                func.group_concat(Claim.claim_id) if db.get_bind().dialect.name == "mysql" else func.max(Claim.claim_id),
            )
            .select_from(Claim)
            .join(Encounter, Claim.encounter_id == Encounter.id)
            .join(Patient, Encounter.patient_id == Patient.id)
            .filter(
                Claim.status == ClaimStatus.FINALIZED.value,
                Claim.created_at.isnot(None),
                Claim.created_at >= start_dt,
                Claim.created_at < end_dt,
                Claim.type_of_attendance.isnot(None),
                func.upper(func.trim(Claim.type_of_attendance)).in_(["ANC", "PNC"]),
            )
            .group_by(Claim.member_no)
            .having(func.count(Claim.id) > 1)
            .order_by(func.count(Claim.id).desc())
            .limit(50)
            .all()
        )
        for member_no, card_no, full_name, cnt, ids in ma_rows:
            if db.get_bind().dialect.name == "mysql":
                claim_ids = [x for x in str(ids or "").split(",") if x]
            else:
                claim_ids = [str(ids)] if ids else []
            multiple_attendance.append(
                ClaimsDashboardMultipleAttendanceItem(
                    member_no=str(member_no),
                    patient_card_number=str(card_no) if card_no else None,
                    patient_name=str(full_name) if full_name else None,
                    attendance_count=int(cnt),
                    claim_ids=claim_ids,
                    suggested_specialty_attended="OPDC",
                )
            )

        # Potential duplicates: same member_no + same date (finalized day) + same principal_gdrg (if set).
        # This is only a heuristic; officer reviews and decides.
        finalized_date = func.date(Claim.created_at)
        dup_rows = (
            db.query(
                Claim.member_no,
                func.max(Patient.card_number),
                func.max(patient_name_expr),
                finalized_date,
                func.coalesce(func.nullif(func.trim(Claim.principal_gdrg), ""), "_"),
                func.count(Claim.id),
                func.group_concat(Claim.claim_id) if db.get_bind().dialect.name == "mysql" else func.max(Claim.claim_id),
            )
            .select_from(Claim)
            .join(Encounter, Claim.encounter_id == Encounter.id)
            .join(Patient, Encounter.patient_id == Patient.id)
            .filter(
                Claim.status == ClaimStatus.FINALIZED.value,
                Claim.created_at.isnot(None),
                Claim.created_at >= start_dt,
                Claim.created_at < end_dt,
            )
            .group_by(
                Claim.member_no,
                finalized_date,
                func.coalesce(func.nullif(func.trim(Claim.principal_gdrg), ""), "_"),
            )
            .having(func.count(Claim.id) > 1)
            .order_by(func.count(Claim.id).desc())
            .limit(50)
            .all()
        )
        for member_no, card_no, full_name, fdate, pgdrg, cnt, ids in dup_rows:
            if db.get_bind().dialect.name == "mysql":
                claim_ids = [x for x in str(ids or "").split(",") if x]
            else:
                claim_ids = [str(ids)] if ids else []
            key = f"{member_no}|{fdate}|{pgdrg}"
            potential_duplicates.append(
                ClaimsDashboardDuplicateGroup(
                    key=key,
                    member_no=str(member_no),
                    patient_card_number=str(card_no) if card_no else None,
                    patient_name=str(full_name) if full_name else None,
                    count=int(cnt),
                    claim_ids=claim_ids,
                )
            )

    else:
        # Imported claims: treat finalized import items as "claims". Costs and top items
        # depend on payload structure; for now provide volumes and advice based on payload fields if present.
        # Month selection for imported claims should respect payload provider.monthOfClaim when possible.
        # Fallback: finalized_at month.
        items = (
            db.query(ClaimXmlImportItem)
            .filter(ClaimXmlImportItem.status == "finalized")
            .all()
        )
        filtered_items: List[ClaimXmlImportItem] = []
        for it in items:
            p = it.payload or {}
            provider = p.get("provider") or {}
            moc = _parse_month_yyyy_mm(provider.get("monthOfClaim") or provider.get("month_of_claim"))
            if moc is None and it.finalized_at:
                moc = f"{it.finalized_at.year:04d}-{it.finalized_at.month:02d}"
            if moc == month:
                filtered_items.append(it)
        items = filtered_items
        total_volume = len(items)
        total_cost = 0.0

        # Trend months are independent of selected `month`.
        for m_yyyy_mm in trend_months:
            # Count imported items by monthOfClaim where possible (fallback to finalized_at month).
            vol = 0
            rows = (
                db.query(ClaimXmlImportItem)
                .filter(ClaimXmlImportItem.status == "finalized")
                .all()
            )
            for it in rows:
                p = it.payload or {}
                provider = p.get("provider") or {}
                moc = _parse_month_yyyy_mm(provider.get("monthOfClaim") or provider.get("month_of_claim"))
                if moc is None and it.finalized_at:
                    moc = f"{it.finalized_at.year:04d}-{it.finalized_at.month:02d}"
                if moc == m_yyyy_mm:
                    vol += 1
            trend.append(ClaimsDashboardTrendPoint(month=m_yyyy_mm, volume=int(vol), cost=0.0))

        # Advice from payload keys if present.
        # Multiple attendance: payload.client.memberNumber + payload.services.typeOfAttendance (heuristic)
        by_member = {}
        for it in items:
            p = it.payload or {}
            client = p.get("client") or {}
            services = p.get("services") or {}
            member_no = str(client.get("memberNumber") or client.get("member_no") or "").strip()
            if not member_no:
                continue
            toa = str(services.get("typeOfAttendance") or services.get("type_of_attendance") or "").strip().upper()
            if toa not in ("ANC", "PNC"):
                continue
            by_member.setdefault(member_no, []).append(str(p.get("claimID") or p.get("claimId") or it.claim_claim_id))
        for member_no, ids in sorted(by_member.items(), key=lambda kv: len(kv[1]), reverse=True):
            if len(ids) <= 1:
                continue
            multiple_attendance.append(
                ClaimsDashboardMultipleAttendanceItem(
                    member_no=member_no,
                    attendance_count=len(ids),
                    claim_ids=ids[:50],
                    suggested_specialty_attended="OPDC",
                )
            )
            if len(multiple_attendance) >= 50:
                break

        # Potential duplicates: payload.client.memberNumber + payload.provider.monthOfClaim + payload.services.principalGdrg
        groups = {}
        for it in items:
            p = it.payload or {}
            client = p.get("client") or {}
            provider = p.get("provider") or {}
            services = p.get("services") or {}
            member_no = str(client.get("memberNumber") or client.get("member_no") or "").strip()
            if not member_no:
                continue
            moc = str(provider.get("monthOfClaim") or provider.get("month_of_claim") or "").strip()
            pg = str(services.get("principalGdrg") or services.get("principal_gdrg") or "").strip() or "_"
            key = f"{member_no}|{moc}|{pg}"
            groups.setdefault(key, {"member_no": member_no, "ids": []})
            groups[key]["ids"].append(str(p.get("claimID") or p.get("claimId") or it.claim_claim_id))
        for key, info in sorted(groups.items(), key=lambda kv: len(kv[1]["ids"]), reverse=True):
            ids = info["ids"]
            if len(ids) <= 1:
                continue
            potential_duplicates.append(
                ClaimsDashboardDuplicateGroup(
                    key=key,
                    member_no=info["member_no"],
                    count=len(ids),
                    claim_ids=ids[:50],
                )
            )
            if len(potential_duplicates) >= 50:
                break

        top_diagnoses = []
        top_medicines = []

    avg_cost = float(total_cost / total_volume) if total_volume else 0.0
    return ClaimsDashboardResponse(
        source=source,
        month=month,
        kpis=ClaimsDashboardKPIs(
            total_volume=int(total_volume),
            total_cost=float(total_cost),
            avg_cost_per_claim=float(avg_cost),
        ),
        trend=trend,
        top_diagnoses=top_diagnoses,
        top_medicines=top_medicines,
        advice=ClaimsDashboardAdvice(
            multiple_attendance=multiple_attendance,
            potential_duplicates=potential_duplicates,
        ),
    )



@router.get("/specialties", response_model=SpecialtiesResponse)
def get_claims_specialties(
    claim_type: Optional[str] = None,  # 'opd', 'ipd', or None for both (combined)
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read"))
):
    """
    Get distinct specialties for filtering finalized encounters.
    - OPD: distinct encounter.department (clinics/departments)
    - IPD: distinct ward names (all wards; vetters can filter by ward/specialty)
    - All: combined list from both
    """
    from sqlalchemy import distinct, func
    from app.models.ward_admission import WardAdmission
    from app.models.consultation_notes import ConsultationNotes
    from sqlalchemy import or_, and_

    specialties = []
    if claim_type in (None, "opd", "other"):
        # OPD/Other: distinct departments from finalized encounters with CCC
        opd_query = db.query(Encounter.department).filter(
            Encounter.status == "finalized",
            Encounter.ccc_number.isnot(None),
            Encounter.ccc_number != "",
            Encounter.archived == False,
            Encounter.department.isnot(None),
            Encounter.department != ""
        ).distinct().order_by(Encounter.department)
        opd_rows = opd_query.all()
        for row in opd_rows:
            if row[0] and row[0].strip() and row[0].strip() not in specialties:
                specialties.append(row[0].strip())
    if claim_type in (None, "ipd"):
        # IPD: distinct wards from discharged ward admissions with CCC
        ipd_query = db.query(WardAdmission.ward).join(Encounter).filter(
            WardAdmission.discharged_at.isnot(None),
            WardAdmission.ward.isnot(None),
            WardAdmission.ward != "",
            or_(
                and_(WardAdmission.ccc_number.isnot(None), WardAdmission.ccc_number != ""),
                and_(Encounter.ccc_number.isnot(None), Encounter.ccc_number != "")
            )
        ).distinct().order_by(WardAdmission.ward)
        ipd_rows = ipd_query.all()
        for row in ipd_rows:
            if row[0] and row[0].strip() and row[0].strip() not in specialties:
                specialties.append(row[0].strip())
    # Sort for consistent display when combined
    specialties.sort(key=lambda s: (s or "").lower())
    return SpecialtiesResponse(specialties=specialties)


@router.get("/eligible-encounters", response_model=EligibleEncountersResponse)
def get_eligible_encounters_for_claims(
    claim_type: Optional[str] = None,  # 'opd' or 'ipd'
    start_date: Optional[str] = None,  # Filter by start date (YYYY-MM-DD)
    end_date: Optional[str] = None,  # Filter by end date (YYYY-MM-DD)
    claim_status: Optional[str] = None,  # Filter by claim status: 'draft', 'finalized', 'reopened', or None for all
    card_number: Optional[str] = None,  # Filter by patient card number
    claim_id: Optional[str] = None,  # Filter by claim ID (e.g., "CLA-XXXXX")
    ccc: Optional[str] = None,  # Filter by claim check code / CCC (partial match)
    specialty: Optional[str] = None,  # Filter by specialty: OPD = encounter.department, IPD = ward (all wards if not set)
    skip: int = 0,  # Pagination offset
    limit: int = 50,  # Pagination limit
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read"))
):
    """
    Get finalized encounters with CCC numbers that are eligible for claim generation.
    Only encounters with active insurance (CCC number) and finalized status are returned.
    
    For IPD claims, returns discharged ward admissions (all wards); use specialty to filter by ward.
    
    Filters:
    - claim_type: 'opd', 'ipd', 'other', or None for all
    - start_date: Filter encounters finalized on or after this date (YYYY-MM-DD)
    - end_date: Filter encounters finalized on or before this date (YYYY-MM-DD)
    - claim_status: Filter by claim status: 'draft', 'finalized', 'reopened', or None for all
    - card_number: Filter by patient card number (partial match supported)
    - claim_id: Filter by claim ID (e.g., "CLA-XXXXX")
    - specialty: Filter by specialty (OPD = department/clinic, IPD = ward name)
    """
    from sqlalchemy.orm import joinedload
    from datetime import datetime
    
    # Handle IPD claims separately - return discharged ward admissions (all wards; specialty filters by ward)
    if claim_type == 'ipd':
        return get_eligible_ipd_ward_admissions_for_claims(
            start_date=start_date,
            end_date=end_date,
            claim_status=claim_status,
            card_number=card_number,
            claim_id=claim_id,
            ccc=ccc,
            specialty=specialty,
            skip=skip,
            limit=limit,
            db=db,
            current_user=current_user
        )
    
    # Build base query for OPD encounters
    query = db.query(Encounter)\
        .options(
            joinedload(Encounter.patient),
            joinedload(Encounter.investigations),
            joinedload(Encounter.prescriptions),
        )\
        .filter(
            Encounter.status == "finalized",
            Encounter.ccc_number.isnot(None),
            Encounter.ccc_number != "",
            Encounter.archived == False
        )
    
    # Apply card number filter (partial match)
    if card_number:
        card_number_clean = card_number.strip()
        if card_number_clean:
            from app.models.patient import Patient
            query = query.join(Patient).filter(
                Patient.card_number.like(f'%{card_number_clean}%')
            )
    
    # Apply claim_id filter
    if claim_id:
        claim_id_clean = claim_id.strip()
        if claim_id_clean:
            # Filter by claim_id - find encounters that have a claim with matching claim_id
            query = query.join(Claim).filter(
                Claim.claim_id == claim_id_clean
            )
    
    # Apply date filters
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Encounter.finalized_at >= start_dt)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            # Add one day to include the entire end date
            from datetime import timedelta
            end_dt = end_dt + timedelta(days=1)
            query = query.filter(Encounter.finalized_at < end_dt)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    # Optimize: Use LEFT JOINs to filter at database level instead of loading all records
    from app.models.consultation_notes import ConsultationNotes
    from sqlalchemy import func, case, or_, and_
    
    # Add LEFT JOIN for consultation notes (to filter by outcome/type)
    query = query.outerjoin(ConsultationNotes, ConsultationNotes.encounter_id == Encounter.id)
    
    # Add LEFT JOIN for claims (to filter by claim status)
    query = query.outerjoin(Claim, Claim.encounter_id == Encounter.id)
    
    # Apply specialty filter (OPD: by encounter.department)
    if specialty and specialty.strip():
        query = query.filter(Encounter.department == specialty.strip())
    
    # Apply claim_type filter at database level using consultation notes outcome
    if claim_type == 'opd':
        # OPD: outcome should NOT be 'discharged' or 'recommended_for_admission'
        query = query.filter(
            or_(
                ConsultationNotes.outcome.is_(None),
                func.lower(ConsultationNotes.outcome) != 'discharged',
                func.lower(ConsultationNotes.outcome) != 'recommended_for_admission'
            )
        )
    elif claim_type == 'other':
        # Other: outcome should NOT be 'discharged' or 'recommended_for_admission'
        query = query.filter(
            or_(
                ConsultationNotes.outcome.is_(None),
                and_(
                    func.lower(ConsultationNotes.outcome) != 'discharged',
                    func.lower(ConsultationNotes.outcome) != 'recommended_for_admission'
                )
            )
        )
    # If claim_type is None, include all (no additional filter)
    
    # Apply claim_status filter at database level
    if claim_status:
        if claim_status == 'no_claim':
            # No claim: claim should not exist
            query = query.filter(Claim.id.is_(None))
        else:
            # Specific status: claim must exist and have matching status
            query = query.filter(Claim.status == claim_status)

    # Apply CCC / claim check code filter (partial match)
    if ccc:
        ccc_clean = str(ccc).strip()
        if ccc_clean:
            query = query.filter(func.lower(Claim.claim_check_code).like(f"%{ccc_clean.lower()}%"))
    
    # Get total count efficiently using COUNT query
    total_count = query.count()
    
    # If claim_type is None, we need to combine OPD and IPD, so load enough records from both
    # For specific claim types, we can paginate at database level
    if claim_type is None:
        # Import WardAdmission for IPD count query
        from app.models.ward_admission import WardAdmission
        
        # Get IPD total count first (without loading all records)
        ipd_count_query = db.query(WardAdmission)\
            .join(Encounter)\
            .outerjoin(Claim, Claim.encounter_id == WardAdmission.encounter_id)\
            .filter(
                WardAdmission.discharged_at.isnot(None),
                or_(
                    and_(WardAdmission.ccc_number.isnot(None), WardAdmission.ccc_number != ""),
                    and_(Encounter.ccc_number.isnot(None), Encounter.ccc_number != "")
                )
            )
        
        # Apply same filters to IPD count query
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                ipd_count_query = ipd_count_query.filter(WardAdmission.discharged_at >= start_dt)
            except ValueError:
                pass
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                end_dt = end_dt + timedelta(days=1)
                ipd_count_query = ipd_count_query.filter(WardAdmission.discharged_at < end_dt)
            except ValueError:
                pass
        if claim_status:
            if claim_status == 'no_claim':
                ipd_count_query = ipd_count_query.filter(Claim.id.is_(None))
            else:
                ipd_count_query = ipd_count_query.filter(Claim.status == claim_status)
        if card_number:
            card_number_clean = card_number.strip()
            if card_number_clean:
                from app.models.patient import Patient
                patient_ids_subquery = db.query(Patient.id).filter(
                    Patient.card_number.like(f'%{card_number_clean}%')
                )
                ipd_count_query = ipd_count_query.filter(Encounter.patient_id.in_(patient_ids_subquery))
        if claim_id:
            claim_id_clean = claim_id.strip()
            if claim_id_clean:
                ipd_count_query = ipd_count_query.filter(Claim.claim_id == claim_id_clean)
        if specialty and specialty.strip():
            ipd_count_query = ipd_count_query.filter(WardAdmission.ward == specialty.strip())
        
        ipd_total = ipd_count_query.count()
        
        # For "All" type: Load enough OPD and IPD records to cover the requested page range
        # We need to load more than the page size because after combining and sorting,
        # the distribution might be different
        # Load enough to ensure we have records for the requested page
        buffer_size = 200  # Load extra records to account for sorting distribution
        opd_load_limit = min(skip + limit + buffer_size, total_count)
        ipd_load_limit = min(skip + limit + buffer_size, ipd_total)
        
        # Load OPD records (without pagination, but limited to what we need)
        opd_encounters = query.order_by(Encounter.finalized_at.desc()).limit(opd_load_limit).all()
        
        # Process OPD results
        result = []
        for encounter in opd_encounters:
            # Get claim - query directly since LEFT JOIN doesn't populate relationship
            claim = db.query(Claim).filter(Claim.encounter_id == encounter.id).first()
            
            # Get finalized_by username
            finalized_by_username = None
            if encounter.finalized_by:
                finalized_user = db.query(User).filter(User.id == encounter.finalized_by).first()
                if finalized_user:
                    finalized_by_username = finalized_user.username
            
            encounter_data = {
                "id": encounter.id,
                "patient_id": encounter.patient_id,
                "patient_name": f"{encounter.patient.name or ''} {encounter.patient.surname or ''} {encounter.patient.other_names or ''}".strip() or "Unknown",
                "patient_card_number": encounter.patient.card_number or "",
                "ccc_number": encounter.ccc_number or "",
                "status": encounter.status or "finalized",
                "department": encounter.department or "",
                "finalized_at": encounter.finalized_at,
                "finalized_by_username": finalized_by_username,
                "created_at": encounter.created_at,
                "claim_id": claim.id if claim else None,
                "claim_status": claim.status if claim else None,
                "ward_admission_id": None,  # OPD encounters don't have ward_admission_id
            }
            result.append(_enrich_encounter_row_with_claim_amount(db, encounter_data, encounter, claim))
        
        # Get IPD results (load enough to cover the page range); IPD includes all wards, specialty filters by ward
        ipd_response = get_eligible_ipd_ward_admissions_for_claims(
            start_date=start_date,
            end_date=end_date,
            claim_status=claim_status,
            card_number=card_number,
            claim_id=claim_id,
            specialty=specialty,
            skip=0,
            limit=ipd_load_limit,
            db=db,
            current_user=current_user
        )
        ipd_results = ipd_response["items"]
        
        # Combine and sort by finalized_at (most recent first)
        result.extend(ipd_results)
        result.sort(key=lambda x: x.get("finalized_at") or datetime.min, reverse=True)
        
        # Update total count to include IPD (use actual counts, not loaded items)
        total_count = total_count + ipd_total
        
        # Apply pagination to combined results
        result = result[skip:skip + limit]
    else:
        # For specific claim types (OPD, Other), paginate at database level
        encounters = query.order_by(Encounter.finalized_at.desc()).offset(skip).limit(limit).all()
        
        # Process results
        result = []
        for encounter in encounters:
            # Get claim - query directly since LEFT JOIN doesn't populate relationship
            claim = db.query(Claim).filter(Claim.encounter_id == encounter.id).first()
            
            # Get finalized_by username
            finalized_by_username = None
            if encounter.finalized_by:
                finalized_user = db.query(User).filter(User.id == encounter.finalized_by).first()
                if finalized_user:
                    finalized_by_username = finalized_user.username
            
            encounter_data = {
                "id": encounter.id,
                "patient_id": encounter.patient_id,
                "patient_name": f"{encounter.patient.name or ''} {encounter.patient.surname or ''} {encounter.patient.other_names or ''}".strip() or "Unknown",
                "patient_card_number": encounter.patient.card_number or "",
                "ccc_number": encounter.ccc_number or "",
                "status": encounter.status or "finalized",
                "department": encounter.department or "",
                "finalized_at": encounter.finalized_at,
                "finalized_by_username": finalized_by_username,
                "created_at": encounter.created_at,
                "claim_id": claim.id if claim else None,
                "claim_status": claim.status if claim else None,
                "ward_admission_id": None,  # OPD encounters don't have ward_admission_id
            }
            result.append(_enrich_encounter_row_with_claim_amount(db, encounter_data, encounter, claim))
    
    page_revenue = sum(float(r.get("total_claim_amount") or 0.0) for r in result)
    
    return {
        "items": result,
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "total_revenue": round(page_revenue, 2),
    }


def get_eligible_ipd_ward_admissions_for_claims(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    claim_status: Optional[str] = None,
    card_number: Optional[str] = None,
    claim_id: Optional[str] = None,
    ccc: Optional[str] = None,  # Filter by claim check code / CCC (partial match)
    specialty: Optional[str] = None,  # Filter by ward (IPD covers all wards; this narrows by ward/specialty)
    skip: int = 0,
    limit: int = 50,
    db: Session = None,
    current_user: User = None
):
    """Get discharged ward admissions eligible for IPD claim generation. IPD includes all wards; optional specialty filters by ward."""
    from app.models.ward_admission import WardAdmission
    from app.models.admission import AdmissionRecommendation
    from app.models.patient import Patient
    from sqlalchemy.orm import joinedload
    from sqlalchemy import or_, and_
    from datetime import datetime, timedelta
    
    # Build base query for discharged ward admissions
    # Check CCC number on both ward_admission and encounter (use OR condition)
    query = db.query(WardAdmission)\
        .options(joinedload(WardAdmission.encounter).joinedload(Encounter.patient))\
        .join(Encounter)\
        .filter(
            WardAdmission.discharged_at.isnot(None),  # Only discharged patients
            or_(
                # CCC number on ward admission
                and_(
                    WardAdmission.ccc_number.isnot(None),
                    WardAdmission.ccc_number != ""
                ),
                # OR CCC number on encounter
                and_(
                    Encounter.ccc_number.isnot(None),
                    Encounter.ccc_number != ""
                )
            )
        )
    
    # Apply card number filter (partial match)
    if card_number:
        card_number_clean = card_number.strip()
        if card_number_clean:
            # Use subquery to filter by patient card number (partial match) to avoid duplicate join issues
            patient_ids_subquery = db.query(Patient.id).filter(
                Patient.card_number.like(f'%{card_number_clean}%')
            )
            # Filter encounters where patient_id matches the subquery
            query = query.filter(
                Encounter.patient_id.in_(patient_ids_subquery)
            )
    
    # Apply claim_id filter
    if claim_id:
        claim_id_clean = claim_id.strip()
        if claim_id_clean:
            # Filter by claim_id - find ward admissions that have a claim with matching claim_id
            query = query.join(Claim, Claim.encounter_id == WardAdmission.encounter_id).filter(
                Claim.claim_id == claim_id_clean
            )

    # Apply CCC / claim check code filter (partial match)
    if ccc:
        ccc_clean = str(ccc).strip()
        if ccc_clean:
            # Outer join claims so we can search claim_check_code while still allowing ward admissions with no claim yet
            query = query.outerjoin(Claim, Claim.encounter_id == WardAdmission.encounter_id).filter(
                Claim.claim_check_code.isnot(None),
                func.lower(Claim.claim_check_code).like(f"%{ccc_clean.lower()}%")
            )
    
    # Apply date filters (filter by discharge date)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(WardAdmission.discharged_at >= start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = end_dt + timedelta(days=1)
            query = query.filter(WardAdmission.discharged_at < end_dt)
        except ValueError:
            pass
    
    # Optimize: Apply claim_status filter at database level using LEFT JOIN
    query = query.outerjoin(Claim, Claim.encounter_id == WardAdmission.encounter_id)
    
    # Apply claim_status filter at database level
    if claim_status:
        if claim_status == 'no_claim':
            # No claim: claim should not exist
            query = query.filter(Claim.id.is_(None))
        else:
            # Specific status: claim must exist and have matching status
            query = query.filter(Claim.status == claim_status)
    
    # Apply specialty filter (IPD: by ward name; when not set, all wards are included)
    if specialty and specialty.strip():
        query = query.filter(WardAdmission.ward == specialty.strip())
    
    # Get total count efficiently using COUNT query
    total_count = query.count()
    
    # Apply pagination at database level using LIMIT and OFFSET
    ward_admissions = query.order_by(WardAdmission.discharged_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for ward_admission in ward_admissions:
        # Get claim - query directly since LEFT JOIN doesn't populate relationship
        claim = db.query(Claim).filter(Claim.encounter_id == ward_admission.encounter_id).first()
        
        # Get patient info
        patient = ward_admission.encounter.patient
        encounter = ward_admission.encounter
        
        # Get CCC number from ward admission or encounter (prefer ward admission)
        ccc_number = ward_admission.ccc_number or encounter.ccc_number
        
        # Get discharged_by username
        discharged_by_username = None
        if ward_admission.discharged_by:
            discharged_user = db.query(User).filter(User.id == ward_admission.discharged_by).first()
            if discharged_user:
                discharged_by_username = discharged_user.username
        
        ward_admission_data = {
            "id": ward_admission.encounter_id,  # Use encounter_id for compatibility
            "ward_admission_id": ward_admission.id,  # Add ward_admission_id
            "patient_id": patient.id,
            "patient_name": f"{patient.name or ''} {patient.surname or ''} {patient.other_names or ''}".strip(),
            "patient_card_number": patient.card_number or "",
            "ccc_number": ccc_number,
            "status": "finalized",  # Discharged ward admissions are considered finalized
            "department": ward_admission.ward,
            "finalized_at": ward_admission.discharged_at,  # Use discharge date
            "finalized_by_username": discharged_by_username,
            "created_at": ward_admission.admitted_at,
            "claim_id": claim.id if claim else None,
            "claim_status": claim.status if claim else None,
        }
        result.append(
            _enrich_encounter_row_with_claim_amount(
                db, ward_admission_data, encounter, claim, ward_admission
            )
        )
    
    page_revenue = sum(float(r.get("total_claim_amount") or 0.0) for r in result)
    
    return {
        "items": result,
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "total_revenue": round(page_revenue, 2),
    }


@router.get("/", response_model=List[ClaimResponse])
def get_all_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read"))
):
    """Get all claims"""
    claims = db.query(Claim).order_by(Claim.created_at.desc()).all()
    return claims


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(
    claim_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read"))
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
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read"))
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
    
    # Determine if this is an IPD claim and get OPD encounter if exists
    is_ipd = claim.type_of_service.upper() == "IPD"
    opd_encounter = None
    ward_admission = None
    
    if is_ipd:
        # Get OPD encounter that led to admission (if exists)
        # Use the same logic as create_claim to ensure consistency
        from app.models.ward_admission import WardAdmission
        from app.models.admission import AdmissionRecommendation
        from sqlalchemy.orm import joinedload
        
        ward_admission = db.query(WardAdmission).filter(
            WardAdmission.encounter_id == encounter.id
        ).first()
        
        # First, try to get OPD encounter from admission recommendation (same as create_claim)
        if ward_admission and ward_admission.admission_recommendation_id:
            admission_recommendation = db.query(AdmissionRecommendation).filter(
                AdmissionRecommendation.id == ward_admission.admission_recommendation_id
            ).first()
            
            if admission_recommendation and admission_recommendation.encounter_id:
                # If admission recommendation points to a different encounter, that's the OPD encounter
                if admission_recommendation.encounter_id != ward_admission.encounter_id:
                    # Different encounter means there was an OPD encounter before admission
                    opd_encounter = db.query(Encounter)\
                        .options(
                            joinedload(Encounter.diagnoses),
                            joinedload(Encounter.prescriptions),
                            joinedload(Encounter.investigations)
                        )\
                        .filter(Encounter.id == admission_recommendation.encounter_id)\
                        .first()
                else:
                    # Same encounter - this means the OPD encounter IS the same as the IPD encounter
                    # The encounter was created as OPD and then the patient was admitted
                    # In this case, we should use the same encounter but only get OPD-related data
                    # However, since we can't distinguish OPD vs IPD data in the same encounter,
                    # we'll use the encounter itself as the OPD encounter
                    # This will include all diagnoses, prescriptions, and investigations from that encounter
                    opd_encounter = db.query(Encounter)\
                        .options(
                            joinedload(Encounter.diagnoses),
                            joinedload(Encounter.prescriptions),
                            joinedload(Encounter.investigations)
                        )\
                        .filter(Encounter.id == admission_recommendation.encounter_id)\
                        .first()
        
        # If OPD encounter not found via admission recommendation, 
        # look for the most recent finalized OPD encounter before this IPD encounter
        # This is a fallback to ensure we find OPD data even if admission recommendation link is missing
        if not opd_encounter:
            # Try multiple strategies to find OPD encounter
            # Strategy 1: Most recent finalized encounter before or on IPD encounter created_at date
            # Use date comparison (not datetime) to handle same-day scenarios
            from sqlalchemy import func
            ipd_created_date = encounter.created_at.date() if encounter.created_at else None
            
            if ipd_created_date:
                # Try with finalized_at date <= IPD created_at date
                opd_encounter = db.query(Encounter)\
                    .options(
                        joinedload(Encounter.diagnoses),
                        joinedload(Encounter.prescriptions),
                        joinedload(Encounter.investigations)
                    )\
                    .filter(
                        Encounter.patient_id == encounter.patient_id,
                        Encounter.id != encounter.id,
                        Encounter.finalized_at.isnot(None),
                        func.date(Encounter.finalized_at) <= ipd_created_date
                    )\
                    .order_by(Encounter.finalized_at.desc())\
                    .first()
            
            # Strategy 2: If still not found, try with strict datetime comparison
            if not opd_encounter:
                opd_encounter = db.query(Encounter)\
                    .options(
                        joinedload(Encounter.diagnoses),
                        joinedload(Encounter.prescriptions),
                        joinedload(Encounter.investigations)
                    )\
                    .filter(
                        Encounter.patient_id == encounter.patient_id,
                        Encounter.id != encounter.id,
                        Encounter.finalized_at.isnot(None),
                        Encounter.finalized_at <= encounter.created_at
                    )\
                    .order_by(Encounter.finalized_at.desc())\
                    .first()
            
            # Strategy 3: If still not found, try without finalized_at requirement (just before created_at)
            if not opd_encounter:
                opd_encounter = db.query(Encounter)\
                    .options(
                        joinedload(Encounter.diagnoses),
                        joinedload(Encounter.prescriptions),
                        joinedload(Encounter.investigations)
                    )\
                    .filter(
                        Encounter.patient_id == encounter.patient_id,
                        Encounter.id != encounter.id,
                        Encounter.created_at < encounter.created_at
                    )\
                    .order_by(Encounter.created_at.desc())\
                    .first()
            
            # Strategy 4: Last resort - find any encounter for this patient before IPD (most recent)
            # This will find the most recent encounter regardless of finalized status
            if not opd_encounter:
                opd_encounter = db.query(Encounter)\
                    .options(
                        joinedload(Encounter.diagnoses),
                        joinedload(Encounter.prescriptions),
                        joinedload(Encounter.investigations)
                    )\
                    .filter(
                        Encounter.patient_id == encounter.patient_id,
                        Encounter.id != encounter.id
                    )\
                    .order_by(Encounter.created_at.desc())\
                    .first()
        
        # Ensure relationships are loaded by accessing them
        if opd_encounter:
            # Force load relationships by accessing them (this triggers the joinedload)
            _ = list(opd_encounter.diagnoses)
            _ = list(opd_encounter.prescriptions)
            _ = list(opd_encounter.investigations)
    
    # Get diagnoses from claim detail table (or fallback to encounter diagnoses)
    from app.models.claim_detail import ClaimDiagnosis, ClaimInvestigation, ClaimPrescription, ClaimProcedure
    
    # Check if claim has been edited before (any claim detail table has rows)
    claim_has_been_edited = (
        db.query(ClaimDiagnosis).filter(ClaimDiagnosis.claim_id == claim.id).first() is not None
        or db.query(ClaimProcedure).filter(ClaimProcedure.claim_id == claim.id).first() is not None
        or db.query(ClaimInvestigation).filter(ClaimInvestigation.claim_id == claim.id).first() is not None
        or db.query(ClaimPrescription).filter(ClaimPrescription.claim_id == claim.id).first() is not None
    )
    
    claim_diagnoses = db.query(ClaimDiagnosis)\
        .filter(ClaimDiagnosis.claim_id == claim.id)\
        .order_by(ClaimDiagnosis.display_order)\
        .all()
    
    diagnoses_list = []
    if claim_diagnoses:
        # Use claim detail diagnoses when present (preserves user edits)
        for claim_diag in claim_diagnoses:
            diagnoses_list.append({
                "id": claim_diag.diagnosis_id if claim_diag.diagnosis_id else claim_diag.id,
                "description": claim_diag.description,
                "icd10": claim_diag.icd10,
                "gdrg": claim_diag.gdrg_code or "",
                "is_chief": claim_diag.is_chief,
            })
    else:
        # First time loading - fallback to encounter diagnoses
        # For IPD claims, include OPD diagnoses first, then IPD
        if is_ipd:
            # Add OPD diagnoses first (if exists)
            if opd_encounter:
                try:
                    # Convert to list to force evaluation of the relationship
                    opd_diagnoses = list(opd_encounter.diagnoses) if hasattr(opd_encounter, 'diagnoses') else []
                    for diag in opd_diagnoses:
                        diagnoses_list.append({
                            "id": diag.id,
                            "description": diag.diagnosis,
                            "icd10": diag.icd10,
                            "gdrg": diag.gdrg_code or "",
                            "is_chief": diag.is_chief,
                        })
                except Exception:
                    pass
            
            # Add IPD diagnoses from clinical reviews
            if ward_admission:
                from app.models.inpatient_clinical_review import InpatientClinicalReview
                from app.models.inpatient_diagnosis import InpatientDiagnosis
                
                clinical_reviews = db.query(InpatientClinicalReview).filter(
                    InpatientClinicalReview.ward_admission_id == ward_admission.id
                ).all()
                
                clinical_review_ids = [cr.id for cr in clinical_reviews] if clinical_reviews else []
                
                if clinical_review_ids:
                    ipd_diagnoses = db.query(InpatientDiagnosis).filter(
                        InpatientDiagnosis.clinical_review_id.in_(clinical_review_ids)
                    ).order_by(InpatientDiagnosis.created_at).all()
                    
                    for diag in ipd_diagnoses:
                        diagnoses_list.append({
                            "id": None,  # IPD diagnoses don't have direct diagnosis_id
                            "description": diag.diagnosis,
                            "icd10": diag.icd10,
                            "gdrg": diag.gdrg_code or "",
                            "is_chief": diag.is_chief,
                        })
        else:
            # OPD claim - use encounter diagnoses
            for diag in encounter.diagnoses:
                diagnoses_list.append({
                    "id": diag.id,
                    "description": diag.diagnosis,
                    "icd10": diag.icd10,
                    "gdrg": diag.gdrg_code or "",
                    "is_chief": diag.is_chief,
                })
    
    # Pad to 4 diagnoses (only for OPD claims, IPD can have more)
    if not is_ipd:
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
    if claim_investigations:
        # Use claim detail investigations when present (preserves user edits)
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
        # For IPD claims, include OPD investigations first, then IPD
        if is_ipd:
            # Add OPD investigations first (if exists)
            if opd_encounter:
                try:
                    # Convert to list to force evaluation of the relationship
                    opd_investigations = list(opd_encounter.investigations) if hasattr(opd_encounter, 'investigations') else []
                    for inv in opd_investigations:
                        if inv.status != "cancelled" and inv.gdrg_code:
                            investigations_list.append({
                                "id": inv.id,
                                "description": inv.procedure_name or "",
                                "date": inv.service_date.isoformat() if inv.service_date else opd_encounter.created_at.isoformat(),
                                "gdrg": inv.gdrg_code or "",
                                "investigation_type": inv.investigation_type or "",
                            })
                except Exception:
                    pass
            
            # Add IPD investigations from clinical reviews
            if ward_admission:
                from app.models.inpatient_clinical_review import InpatientClinicalReview
                from app.models.inpatient_investigation import InpatientInvestigation
                
                clinical_reviews = db.query(InpatientClinicalReview).filter(
                    InpatientClinicalReview.ward_admission_id == ward_admission.id
                ).all()
                
                clinical_review_ids = [cr.id for cr in clinical_reviews] if clinical_reviews else []
                
                if clinical_review_ids:
                    ipd_investigations = db.query(InpatientInvestigation).filter(
                        InpatientInvestigation.clinical_review_id.in_(clinical_review_ids),
                        InpatientInvestigation.status != "cancelled"
                    ).order_by(InpatientInvestigation.created_at).all()
                    
                    for inv in ipd_investigations:
                        if inv.gdrg_code:
                            clinical_review = next((cr for cr in clinical_reviews if cr.id == inv.clinical_review_id), None)
                            service_date = clinical_review.created_at if clinical_review else ward_admission.admitted_at
                            
                            investigations_list.append({
                                "id": None,  # IPD investigations don't have direct investigation_id
                                "description": inv.procedure_name or "",
                                "date": service_date.isoformat() if service_date else encounter.created_at.isoformat(),
                                "gdrg": inv.gdrg_code or "",
                                "investigation_type": inv.investigation_type or "",
                            })
        else:
            # OPD claim - use encounter investigations (include all except cancelled)
            for inv in encounter.investigations:
                if inv.status != "cancelled" and inv.gdrg_code:
                    investigations_list.append({
                        "id": inv.id,
                        "description": inv.procedure_name or "",
                        "date": inv.service_date.isoformat() if inv.service_date else encounter.created_at.isoformat(),
                        "gdrg": inv.gdrg_code or "",
                        "investigation_type": inv.investigation_type,
                    })
    
    # Pad to 5 investigations (only for OPD claims, IPD can have more)
    if not is_ipd:
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
    if claim_prescriptions:
        # Use claim detail prescriptions when present (preserves user edits)
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
        # For IPD claims, include OPD prescriptions first, then IPD
        if is_ipd:
            # Add OPD prescriptions first (if exists)
            if opd_encounter:
                try:
                    # Convert to list to force evaluation of the relationship
                    opd_prescriptions = list(opd_encounter.prescriptions) if hasattr(opd_encounter, 'prescriptions') else []
                    for presc in opd_prescriptions:
                        if presc.dispensed_by and presc.medicine_code:
                            claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
                            prescriptions_list.append({
                                "id": presc.id,
                                "description": presc.medicine_name,
                                "code": presc.medicine_code,
                                "price": float(claim_amount) if claim_amount else 0.0,
                                "quantity": presc.quantity,
                                "total_cost": float(claim_amount * presc.quantity) if claim_amount else 0.0,
                                "date": presc.service_date.isoformat() if presc.service_date else opd_encounter.created_at.isoformat(),
                                "dose": presc.dose or "",
                                "frequency": presc.frequency or "",
                                "duration": presc.duration or "",
                                "unparsed": presc.unparsed or "",
                            })
                except Exception:
                    pass
            
            # Add IPD prescriptions from clinical reviews
            if ward_admission:
                from app.models.inpatient_clinical_review import InpatientClinicalReview
                from app.models.inpatient_prescription import InpatientPrescription
                
                clinical_reviews = db.query(InpatientClinicalReview).filter(
                    InpatientClinicalReview.ward_admission_id == ward_admission.id
                ).all()
                
                clinical_review_ids = [cr.id for cr in clinical_reviews] if clinical_reviews else []
                
                if clinical_review_ids:
                    ipd_prescriptions = db.query(InpatientPrescription).filter(
                        InpatientPrescription.clinical_review_id.in_(clinical_review_ids),
                        InpatientPrescription.dispensed_by.isnot(None)
                    ).order_by(InpatientPrescription.created_at).all()
                    
                    for presc in ipd_prescriptions:
                        if presc.medicine_code:
                            claim_amount = get_claim_amount_from_price_list(db, presc.medicine_code, is_insured=True)
                            
                            clinical_review = next((cr for cr in clinical_reviews if cr.id == presc.clinical_review_id), None)
                            service_date = clinical_review.created_at if clinical_review else ward_admission.admitted_at
                            
                            prescriptions_list.append({
                                "id": None,  # IPD prescriptions don't have direct prescription_id
                                "description": presc.medicine_name,
                                "code": presc.medicine_code,
                                "price": float(claim_amount) if claim_amount else 0.0,
                                "quantity": presc.quantity,
                                "total_cost": float(claim_amount * presc.quantity) if claim_amount else 0.0,
                                "date": service_date.isoformat() if service_date else encounter.created_at.isoformat(),
                                "dose": presc.dose or "",
                                "frequency": presc.frequency or "",
                                "duration": presc.duration or "",
                                "unparsed": presc.unparsed or "",
                            })
        else:
            # OPD claim - use encounter prescriptions (include undispensed so claim edit matches generate page)
            for presc in encounter.prescriptions:
                if presc.medicine_code:
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
    
    # Pad to 5 prescriptions (only for OPD claims, IPD can have more)
    if not is_ipd:
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
    
    # Get procedures (surgeries for IPD) from claim detail table or fallback to surgeries/encounter procedure
    claim_procedures = db.query(ClaimProcedure)\
        .filter(ClaimProcedure.claim_id == claim.id)\
        .order_by(ClaimProcedure.display_order)\
        .all()
    
    # Determine if this is an IPD claim
    is_ipd = claim.type_of_service.upper() == "IPD"
    
    procedures_list = []
    
    # IMPORTANT: If claim has been edited (claim detail tables exist), ALWAYS use claim_procedures
    # even if it's empty - this respects user's deletion. Never fallback after edits.
    if claim_has_been_edited:
        # Fetch procedures via raw SQL so icd10 is always read from DB (ORM sometimes omits it)
        try:
            raw_rows = db.execute(
                text("""
                    SELECT description, service_date, gdrg_code, icd10
                    FROM claim_procedures
                    WHERE claim_id = :claim_id
                    ORDER BY display_order
                """),
                {"claim_id": claim.id},
            ).fetchall()
            for row in raw_rows:
                _desc = (row[0] or "") if row[0] else ""
                if is_consultation_service_procedure(_desc):
                    continue
                _svc_date = row[1]
                _icd10_val = row[3]
                procedures_list.append({
                    "description": _desc,
                    "date": _svc_date.isoformat() if _svc_date else (encounter.created_at.isoformat() if encounter.created_at else ""),
                    "gdrg": (row[2] or "") if row[2] else "",
                    "icd10": (str(_icd10_val).strip() if _icd10_val else "") or "",
                })
        except Exception:
            # Fallback to ORM if raw query fails (e.g. icd10 column missing in DB)
            for claim_proc in claim_procedures:
                if is_consultation_service_procedure(claim_proc.description or ""):
                    continue
                _icd10 = getattr(claim_proc, "icd10", None) or claim_proc.__dict__.get("icd10")
                _icd10_str = (str(_icd10).strip() if _icd10 else "") or ""
                procedures_list.append({
                    "description": claim_proc.description or "",
                    "date": claim_proc.service_date.isoformat() if claim_proc.service_date else encounter.created_at.isoformat(),
                    "gdrg": claim_proc.gdrg_code or "",
                    "icd10": _icd10_str,
                })
        # Note: If claim_procedures is empty (user deleted them), procedures_list stays empty
    else:
        # First time loading - for both IPD and OPD, load surgeries if they exist
        from app.models.inpatient_surgery import InpatientSurgery
        
        if is_ipd:
            # IPD: Load surgeries from ward admission
            from app.models.ward_admission import WardAdmission
            
            ward_admission = db.query(WardAdmission).filter(
                WardAdmission.encounter_id == encounter.id
            ).first()
            
            if ward_admission:
                surgeries = db.query(InpatientSurgery).filter(
                    InpatientSurgery.ward_admission_id == ward_admission.id,
                    InpatientSurgery.is_completed == True  # Only completed surgeries
                ).order_by(InpatientSurgery.surgery_date, InpatientSurgery.created_at).all()
                
                for surgery in surgeries:
                    procedures_list.append({
                        "description": surgery.surgery_name or "",
                        "date": surgery.surgery_date.isoformat() if surgery.surgery_date else encounter.created_at.isoformat(),
                        "gdrg": surgery.g_drg_code or "",
                        "icd10": "",
                    })
        else:
            # OPD: Check if there are surgeries linked to this encounter (e.g., catheter changing)
            # Surgeries can be linked to OPD encounters via encounter_id
            surgeries = db.query(InpatientSurgery).filter(
                InpatientSurgery.encounter_id == encounter.id,
                InpatientSurgery.is_completed == True  # Only completed surgeries
            ).order_by(InpatientSurgery.surgery_date, InpatientSurgery.created_at).all()
            
            for surgery in surgeries:
                procedures_list.append({
                    "description": surgery.surgery_name or "",
                    "date": surgery.surgery_date.isoformat() if surgery.surgery_date else encounter.created_at.isoformat(),
                    "gdrg": surgery.g_drg_code or "",
                    "icd10": "",
                })
            # If no surgeries found, procedures_list stays empty (don't use encounter procedure)
    
    # Pad to 3 procedures
    while len(procedures_list) < 3:
        procedures_list.append({
            "description": "",
            "date": "",
            "gdrg": "",
            "icd10": "",
        })
    
    # Build response with debug info for OPD encounter
    debug_info = {}
    if not is_ipd:
        debug_info = {
            "encounter_id": encounter.id,
            "claim_has_been_edited": claim_has_been_edited,
            "claim_diagnoses_count": len(claim_diagnoses),
            "claim_investigations_count": len(claim_investigations),
            "claim_prescriptions_count": len(claim_prescriptions),
            "encounter_diagnoses_count": len(list(encounter.diagnoses)) if hasattr(encounter, "diagnoses") else 0,
            "encounter_investigations_count": len(list(encounter.investigations)) if hasattr(encounter, "investigations") else 0,
            "encounter_prescriptions_count": len(list(encounter.prescriptions)) if hasattr(encounter, "prescriptions") else 0,
            "final_diagnoses_count": len(diagnoses_list),
            "final_prescriptions_count": len(prescriptions_list),
            "final_investigations_count": len(investigations_list),
        }
    elif is_ipd:
        opd_diag_count = 0
        opd_presc_count = 0
        opd_inv_count = 0
        if opd_encounter:
            opd_diag_count = len(list(opd_encounter.diagnoses)) if hasattr(opd_encounter, 'diagnoses') else 0
            opd_presc_count = len(list(opd_encounter.prescriptions)) if hasattr(opd_encounter, 'prescriptions') else 0
            opd_inv_count = len(list(opd_encounter.investigations)) if hasattr(opd_encounter, 'investigations') else 0
        
        # Get admission recommendation info for debugging
        admission_recommendation_id = None
        admission_recommendation_encounter_id = None
        if ward_admission and ward_admission.admission_recommendation_id:
            from app.models.admission import AdmissionRecommendation
            admission_rec = db.query(AdmissionRecommendation).filter(
                AdmissionRecommendation.id == ward_admission.admission_recommendation_id
            ).first()
            if admission_rec:
                admission_recommendation_id = admission_rec.id
                admission_recommendation_encounter_id = admission_rec.encounter_id
        
        # Count all encounters for this patient before IPD encounter
        all_previous_encounters_count = db.query(Encounter).filter(
            Encounter.patient_id == encounter.patient_id,
            Encounter.id != encounter.id,
            Encounter.created_at < encounter.created_at
        ).count()
        
        finalized_previous_encounters_count = db.query(Encounter).filter(
            Encounter.patient_id == encounter.patient_id,
            Encounter.id != encounter.id,
            Encounter.finalized_at.isnot(None),
            Encounter.finalized_at < encounter.created_at
        ).count()
        
        # Check if encounter 1125 exists and is linked to this patient (for debugging)
        encounter_1125 = db.query(Encounter).filter(Encounter.id == 1125).first()
        encounter_1125_info = None
        if encounter_1125:
            encounter_1125_info = {
                "exists": True,
                "patient_id": encounter_1125.patient_id,
                "matches_patient": encounter_1125.patient_id == encounter.patient_id,
                "created_at": encounter_1125.created_at.isoformat() if encounter_1125.created_at else None,
                "finalized_at": encounter_1125.finalized_at.isoformat() if encounter_1125.finalized_at else None,
                "is_before_ipd": encounter_1125.created_at < encounter.created_at if encounter_1125.created_at and encounter.created_at else None,
            }
        else:
            encounter_1125_info = {"exists": False}
        
        debug_info = {
            "opd_encounter_found": opd_encounter is not None,
            "opd_encounter_id": opd_encounter.id if opd_encounter else None,
            "opd_diagnoses_count": opd_diag_count,
            "opd_prescriptions_count": opd_presc_count,
            "opd_investigations_count": opd_inv_count,
            "ward_admission_found": ward_admission is not None,
            "ward_admission_id": ward_admission.id if ward_admission else None,
            "ward_admission_encounter_id": ward_admission.encounter_id if ward_admission else None,
            "admission_recommendation_id": admission_recommendation_id,
            "admission_recommendation_encounter_id": admission_recommendation_encounter_id,
            "ipd_encounter_id": encounter.id,
            "ipd_encounter_created_at": encounter.created_at.isoformat() if encounter.created_at else None,
            "all_previous_encounters_count": all_previous_encounters_count,
            "finalized_previous_encounters_count": finalized_previous_encounters_count,
            "encounter_1125_info": encounter_1125_info,
            "claim_has_been_edited": claim_has_been_edited,
            "final_diagnoses_count": len(diagnoses_list),
            "final_prescriptions_count": len(prescriptions_list),
            "final_investigations_count": len(investigations_list),
        }
    
    return {
        "claim": {
            "id": claim.id,
            "claim_id": claim.claim_id,
            "claim_check_code": claim.claim_check_code or "",
            "physician_id": claim.physician_id,
            "type_of_service": claim.type_of_service,
            "includes_pharmacy": claim.includes_pharmacy,
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
            "insured": bool(encounter.patient.insured),
            "nhis_active": bool(encounter.patient.nhis_active),
        },
        "diagnoses": diagnoses_list,
        "investigations": investigations_list,
        "prescriptions": prescriptions_list,
        "procedures": procedures_list,
        "claim_summary": compute_claim_summary_dict(
            db,
            type_of_service=claim.type_of_service,
            procedures=[{"gdrg": p.get("gdrg")} for p in procedures_list if p.get("gdrg")],
            investigations=[{"gdrg": i.get("gdrg")} for i in investigations_list if i.get("gdrg")],
            prescriptions=[
                {
                    "code": p.get("code"),
                    "quantity": p.get("quantity"),
                    "total_cost": p.get("total_cost"),
                    "price": p.get("price"),
                }
                for p in prescriptions_list
                if p.get("code")
            ],
            principal_gdrg=claim.principal_gdrg,
            encounter_procedure_gdrg=encounter.procedure_g_drg_code,
        ),
        "claimit_errors": _get_claimit_errors_for_claim(db, claim.claim_id),
        "debug": debug_info,  # Temporary debug info to diagnose OPD data issue
    }


class ClaimFetchCccRequest(BaseModel):
    member_no: Optional[str] = None
    otac: Optional[str] = None


class GhimsFetchCccRequest(BaseModel):
    member_no: Optional[str] = None
    otac: Optional[str] = None


@router.post("/{claim_id}/fetch-ccc")
def fetch_claim_ccc(
    claim_id: int,
    body: ClaimFetchCccRequest = ClaimFetchCccRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    """Fetch NHIA CCC preview for this claim (not saved until save/finalize)."""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    if claim.status == ClaimStatus.FINALIZED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot fetch CCC on a finalized claim. Reopen the claim first.",
        )
    try:
        return fetch_ccc_preview_for_claim(claim, member_no=body.member_no, otac=body.otac)
    except NhiaIntegrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ghims-import/items/{item_id}/fetch-ccc")
def fetch_ghims_import_item_ccc(
    item_id: int,
    body: GhimsFetchCccRequest = GhimsFetchCccRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    """Fetch NHIA CCC preview for an imported GHIMS claim (not saved until save/finalize)."""
    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")
    if item.status == "finalized":
        raise HTTPException(
            status_code=400,
            detail="Cannot fetch CCC on a finalized imported claim. Reopen it first.",
        )
    try:
        return fetch_ccc_preview_for_ghims_payload(
            item.payload or {},
            member_no=body.member_no,
            otac=body.otac,
        )
    except NhiaIntegrationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{claim_id}", response_model=ClaimResponse)
def update_claim(
    claim_id: int,
    claim_data: ClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update"))
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
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update"))
):
    """Update a draft, reopened, or finalized claim with detailed information"""
    claim = db.query(Claim).filter(Claim.id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    
    # If claim is finalized, automatically reopen it to allow editing
    if claim.status == "finalized":
        claim.status = ClaimStatus.REOPENED.value
    
    # Update claim fields
    claim.physician_id = claim_data.physician_id
    claim.type_of_service = claim_data.type_of_service
    claim.type_of_attendance = claim_data.type_of_attendance
    claim.specialty_attended = claim_data.specialty_attended
    claim.service_outcome = claim_data.service_outcome or "DISC"
    claim.is_unbundled = claim_data.is_unbundled
    claim.principal_gdrg = claim_data.principal_gdrg or None
    if claim_data.claim_check_code is not None and str(claim_data.claim_check_code).strip():
        claim.claim_check_code = str(claim_data.claim_check_code).strip()

    # Block non-covered medicines (insurance_covered == "no").
    uncovered_sections = []
    for idx, presc_update in enumerate(claim_data.prescriptions or []):
        code = str(getattr(presc_update, "code", "") or "").strip()
        desc = str(getattr(presc_update, "description", "") or "").strip()
        if not (code or desc):
            continue
        if not code:
            # Free-text medicine without a code can't be validated here.
            continue
        product = db.query(ProductPrice).filter(ProductPrice.medication_code == code).first()
        covered = (getattr(product, "insurance_covered", None) or "yes").strip().lower() if product else "yes"
        if covered == "no":
            uncovered_sections.append(idx + 1)
    if uncovered_sections:
        raise HTTPException(
            status_code=400,
            detail=(
                "Medicine not covered by insurance. "
                f"Change or remove medicine section(s): {', '.join(map(str, uncovered_sections))}."
            ),
        )
    # If claim has any prescriptions (drugs), ensure includes_pharmacy is true so export records it.
    # Only count lines with code/description and quantity > 0 (exclude empty placeholder rows).
    has_prescriptions = claim_data.prescriptions and len([p for p in claim_data.prescriptions if ((p.code and p.code.strip()) or (p.description and p.description.strip())) and (p.quantity or 0) > 0]) > 0
    # Coerce to bool so we never store list/dict (e.g. frontend sending [] when unchecked)
    claim.includes_pharmacy = has_prescriptions or bool(claim_data.includes_pharmacy)

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
        
        # IMPORTANT: Do NOT update encounter procedure from claim procedures
        # Encounter procedures (procedure_g_drg_code) are for general OPD procedures, not surgeries
        # Surgeries are stored in inpatient_surgeries table and should not be synced back to encounter
        # For IPD claims, surgeries are separate from encounter procedures
        # For OPD claims, we don't want to store procedures in encounter.procedure_g_drg_code
        # So we leave encounter.procedure_g_drg_code unchanged to avoid polluting it with surgery data
        
        # Principal GDRG is now set directly from the form field, not from procedure
        # (This was already set above in claim.principal_gdrg = claim_data.principal_gdrg or None)
    
    # Update claim detail tables (this is where claim-specific edits are stored)
    from app.models.claim_detail import ClaimDiagnosis, ClaimInvestigation, ClaimPrescription, ClaimProcedure
    
    # Ensure claim_procedures has icd10 column (for DBs created before it was added)
    _ensure_claim_procedures_icd10_column(db)
    
    # Delete existing claim details
    db.query(ClaimDiagnosis).filter(ClaimDiagnosis.claim_id == claim.id).delete()
    db.query(ClaimInvestigation).filter(ClaimInvestigation.claim_id == claim.id).delete()
    db.query(ClaimPrescription).filter(ClaimPrescription.claim_id == claim.id).delete()
    db.query(ClaimProcedure).filter(ClaimProcedure.claim_id == claim.id).delete()
    
    # Recreate diagnoses from updated data
    for idx, diag_update in enumerate(claim_data.diagnoses):
        if diag_update.description and diag_update.description.strip():
            # Verify diagnosis still exists in database before referencing it
            diagnosis_id = None
            if diag_update.id:
                diagnosis_exists = db.query(Diagnosis).filter(Diagnosis.id == diag_update.id).first() is not None
                diagnosis_id = diag_update.id if diagnosis_exists else None
            
            claim_diag = ClaimDiagnosis(
                claim_id=claim.id,
                diagnosis_id=diagnosis_id,
                description=diag_update.description,
                icd10=diag_update.icd10 or "",
                gdrg_code=diag_update.gdrg or "",
                is_chief=diag_update.is_chief,
                display_order=idx
            )
            db.add(claim_diag)
    
    # Recreate investigations from updated data
    from app.models.investigation import Investigation
    for idx, inv_update in enumerate(claim_data.investigations):
        if inv_update.description and inv_update.description.strip() and inv_update.gdrg:
            service_date = encounter.created_at
            if inv_update.date:
                try:
                    from datetime import datetime
                    service_date = datetime.fromisoformat(inv_update.date.replace('Z', '+00:00'))
                except:
                    pass
            
            # Verify investigation still exists in database before referencing it
            investigation_id = None
            if inv_update.id:
                investigation_exists = db.query(Investigation).filter(Investigation.id == inv_update.id).first() is not None
                investigation_id = inv_update.id if investigation_exists else None
            
            claim_inv = ClaimInvestigation(
                claim_id=claim.id,
                investigation_id=investigation_id,  # Set to None if investigation was deleted
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
            
            # Verify prescription still exists in database before referencing it
            prescription_id = None
            if presc_update.id:
                from app.models.prescription import Prescription
                prescription_exists = db.query(Prescription).filter(Prescription.id == presc_update.id).first() is not None
                prescription_id = presc_update.id if prescription_exists else None
            
            claim_presc = ClaimPrescription(
                claim_id=claim.id,
                prescription_id=prescription_id,
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
            
            _icd10_val = (proc_update.icd10 or "").strip() or None
            claim_proc = ClaimProcedure(
                claim_id=claim.id,
                description=proc_update.description,
                gdrg_code=proc_update.gdrg,
                icd10=_icd10_val,
                service_date=service_date,
                display_order=idx
            )
            db.add(claim_proc)
    
    db.commit()
    db.refresh(claim)
    
    return claim


# ---------- ClaimIT report upload & error batches ----------


def _resolve_ghims_batch_for_claimit_report(
    db: Session,
    explicit_batch_id: Optional[int],
    report_claim_ids: set,
) -> Tuple[Optional[int], str]:
    """
    Pick the GHIMS import batch this ClaimIT report belongs to.
    Returns (batch_id or None, reason: explicit | auto_subset | auto_overlap | none).
    """
    if explicit_batch_id is not None:
        b = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == explicit_batch_id).first()
        if not b:
            raise HTTPException(status_code=400, detail="Invalid GHIMS import batch id.")
        return explicit_batch_id, "explicit"

    if not report_claim_ids:
        return None, "none"

    batches = (
        db.query(ClaimXmlImportBatch)
        .order_by(ClaimXmlImportBatch.uploaded_at.desc())
        .limit(50)
        .all()
    )
    for b in batches:
        in_batch = {
            row[0]
            for row in db.query(ClaimXmlImportItem.claim_claim_id)
            .filter(ClaimXmlImportItem.batch_id == b.id)
            .all()
        }
        if report_claim_ids <= in_batch:
            return b.id, "auto_subset"

    best_id = None
    best_n = 0
    for b in batches:
        n = (
            db.query(func.count(ClaimXmlImportItem.id))
            .filter(
                ClaimXmlImportItem.batch_id == b.id,
                ClaimXmlImportItem.claim_claim_id.in_(list(report_claim_ids)),
            )
            .scalar()
        ) or 0
        if n > best_n:
            best_n = n
            best_id = b.id
    if best_id is not None and best_n > 0:
        return best_id, "auto_overlap"
    return None, "none"


@router.post("/claimit-report/upload")
async def upload_claimit_report(
    file: UploadFile = File(...),
    ghims_import_batch_id: Optional[int] = Form(None),
    main_hms_only: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "create")),
):
    """Upload a ClaimIT import report (HTML). Creates a batch and extracts claims with errors/warnings."""
    def _truthy_form(v: Optional[str]) -> bool:
        if v is None:
            return False
        return str(v).strip().lower() in ("1", "true", "yes", "on")

    skip_ghims = _truthy_form(main_hms_only)
    if not file.filename or not file.filename.lower().endswith((".html", ".htm")):
        raise HTTPException(status_code=400, detail="Please upload an HTML file (ClaimIT import report).")
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file.")
    # Try common encodings (ClaimIT reports may be UTF-8 or Windows CP1252)
    html_str = None
    for encoding in ("utf-8", "cp1252", "iso-8859-1", "latin-1"):
        try:
            html_str = content.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if html_str is None:
        html_str = content.decode("latin-1", errors="replace")
    parsed = parse_claimit_report_html(html_str)
    errors_list = parsed.get("errors") or []
    overview = parsed.get("overview") or {}
    report_claim_ids = {e["claim_id"] for e in errors_list if e.get("claim_id")}
    if skip_ghims:
        ghims_batch_id, ghims_match_reason = None, "skipped_main_hms"
    else:
        ghims_batch_id, ghims_match_reason = _resolve_ghims_batch_for_claimit_report(
            db, ghims_import_batch_id, report_claim_ids
        )
    ghims_file_name = None
    if ghims_batch_id is not None:
        gb = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == ghims_batch_id).first()
        ghims_file_name = gb.file_name if gb else None

    summary_out = dict(overview) if isinstance(overview, dict) else {}
    summary_out["ghims_resolution"] = ghims_match_reason

    batch = ClaimItReportBatch(
        name=None,
        file_name=file.filename or "report.html",
        uploaded_by_id=get_effective_creator_id(db, current_user),
        summary=summary_out,
        error_count=len(errors_list),
        ghims_import_batch_id=ghims_batch_id,
    )
    db.add(batch)
    db.flush()
    for err in errors_list:
        item_id = None
        if ghims_batch_id is not None:
            item = (
                db.query(ClaimXmlImportItem)
                .filter(
                    ClaimXmlImportItem.batch_id == ghims_batch_id,
                    ClaimXmlImportItem.claim_claim_id == err["claim_id"],
                )
                .first()
            )
            if item:
                item_id = item.id
        db.add(ClaimItReportError(
            batch_id=batch.id,
            claim_claim_id=err["claim_id"],
            outcome=err["outcome"],
            error_messages=err["error_messages"],
            row_index=err.get("row_index"),
            ghims_import_item_id=item_id,
        ))
    db.commit()
    db.refresh(batch)
    return {
        "batch_id": batch.id,
        "file_name": batch.file_name,
        "error_count": batch.error_count,
        "summary": batch.summary,
        "claim_ids": [e["claim_id"] for e in errors_list],
        "ghims_import_batch_id": ghims_batch_id,
        "ghims_import_batch_file_name": ghims_file_name,
        "ghims_match_reason": ghims_match_reason,
    }


@router.get("/claimit-report/batches")
def list_claimit_report_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    """List all ClaimIT report batches (newest first)."""
    batches = (
        db.query(ClaimItReportBatch)
        .order_by(ClaimItReportBatch.uploaded_at.desc())
        .limit(100)
        .all()
    )
    ghims_ids = {b.ghims_import_batch_id for b in batches if b.ghims_import_batch_id}
    ghims_meta = {}
    if ghims_ids:
        for gb in db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id.in_(ghims_ids)).all():
            ghims_meta[gb.id] = {"file_name": gb.file_name, "claim_count": gb.claim_count}
    return [
        {
            "id": b.id,
            "name": b.name,
            "file_name": b.file_name,
            "uploaded_at": b.uploaded_at.isoformat() if b.uploaded_at else None,
            "error_count": b.error_count,
            "summary": b.summary,
            "ghims_import_batch_id": b.ghims_import_batch_id,
            "ghims_import_batch_file_name": (ghims_meta.get(b.ghims_import_batch_id) or {}).get("file_name"),
            "ghims_import_claim_count": (ghims_meta.get(b.ghims_import_batch_id) or {}).get("claim_count"),
        }
        for b in batches
    ]


@router.get("/claimit-report/batches/{batch_id}")
def get_claimit_report_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    """Get one batch with its error rows and matched claims (by claim_id CLA-XXXXX)."""
    batch = db.query(ClaimItReportBatch).filter(ClaimItReportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    errors = (
        db.query(ClaimItReportError)
        .filter(ClaimItReportError.batch_id == batch_id)
        .order_by(ClaimItReportError.row_index, ClaimItReportError.id)
        .all()
    )
    claim_ids_from_report = [e.claim_claim_id for e in errors]
    claims_by_claim_id = {}
    if claim_ids_from_report:
        claims_in_db = db.query(Claim).filter(Claim.claim_id.in_(claim_ids_from_report)).all()
        claims_by_claim_id = {c.claim_id: c for c in claims_in_db}
    completed_by_ids = {e.completed_by_id for e in errors if e.completed_by_id}
    users_by_id = {}
    if completed_by_ids:
        users = db.query(User).filter(User.id.in_(completed_by_ids)).all()
        users_by_id = {u.id: u for u in users}
    ghims_batch_file = None
    ghims_import_claim_count = None
    if batch.ghims_import_batch_id:
        gb = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch.ghims_import_batch_id).first()
        if gb:
            ghims_batch_file = gb.file_name
            ghims_import_claim_count = gb.claim_count
    error_rows = []
    for e in errors:
        claim_in_db = claims_by_claim_id.get(e.claim_claim_id)
        completed_by_user = users_by_id.get(e.completed_by_id) if e.completed_by_id else None
        error_rows.append({
            "id": e.id,
            "claim_claim_id": e.claim_claim_id,
            "outcome": e.outcome,
            "error_messages": e.error_messages or [],
            "row_index": e.row_index,
            "claim_id": claim_in_db.id if claim_in_db else None,
            "claim_status": claim_in_db.status if claim_in_db else None,
            "ghims_import_item_id": e.ghims_import_item_id,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "completed_by_id": e.completed_by_id,
            "completed_by_name": (completed_by_user.username or completed_by_user.email or str(completed_by_user.id)) if completed_by_user else None,
        })
    return {
        "id": batch.id,
        "name": batch.name,
        "file_name": batch.file_name,
        "uploaded_at": batch.uploaded_at.isoformat() if batch.uploaded_at else None,
        "error_count": batch.error_count,
        "summary": batch.summary,
        "ghims_import_batch_id": batch.ghims_import_batch_id,
        "ghims_import_batch_file_name": ghims_batch_file,
        "ghims_import_claim_count": ghims_import_claim_count,
        "errors": error_rows,
    }


class ClaimItErrorCompleteBody(BaseModel):
    completed: bool = True


@router.patch("/claimit-report/batches/{batch_id}/errors/{error_id}/complete")
def set_claimit_error_completed(
    batch_id: int,
    error_id: int,
    body: ClaimItErrorCompleteBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "create")),
):
    """Mark a batch error row as completed (or uncomplete) so other officers know not to rework it."""
    err = (
        db.query(ClaimItReportError)
        .filter(ClaimItReportError.id == error_id, ClaimItReportError.batch_id == batch_id)
        .first()
    )
    if not err:
        raise HTTPException(status_code=404, detail="Error row not found.")
    if body.completed:
        from app.core.datetime_utils import utcnow
        err.completed_at = utcnow()
        err.completed_by_id = get_effective_creator_id(db, current_user)
    else:
        err.completed_at = None
        err.completed_by_id = None
    db.commit()
    return {"id": err.id, "completed": body.completed, "completed_at": err.completed_at.isoformat() if err.completed_at else None, "completed_by_id": err.completed_by_id}


# ---------- GHIMS XML import batches ----------

@router.post("/ghims-import/upload")
async def upload_ghims_claims_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "create")),
):
    """Upload GHIMS exported XML and create an import batch linked to existing claims."""
    if not file.filename or not file.filename.lower().endswith(".xml"):
        raise HTTPException(status_code=400, detail="Please upload an XML file.")
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file.")

    xml_str = None
    for encoding in ("utf-8", "cp1252", "iso-8859-1", "latin-1"):
        try:
            xml_str = content.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if xml_str is None:
        xml_str = content.decode("latin-1", errors="replace")

    parsed = parse_claims_xml(xml_str)
    claims = parsed.get("claims") or []

    batch = ClaimXmlImportBatch(
        file_name=file.filename or "claims.xml",
        uploaded_by_id=get_effective_creator_id(db, current_user),
        claim_count=len(claims),
    )
    db.add(batch)
    db.flush()

    for row in claims:
        db.add(ClaimXmlImportItem(
            batch_id=batch.id,
            claim_claim_id=row["claim_id"],
            row_index=row.get("row_index"),
            status="draft",
            payload=row.get("payload") or {},
        ))

    db.commit()
    db.refresh(batch)
    return {
        "batch_id": batch.id,
        "file_name": batch.file_name,
        "claim_count": batch.claim_count,
        "claim_ids": [r["claim_id"] for r in claims],
    }


@router.get("/ghims-import/batches")
def list_ghims_import_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    """List GHIMS XML import batches (newest first)."""
    batches = (
        db.query(ClaimXmlImportBatch)
        .order_by(ClaimXmlImportBatch.uploaded_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": b.id,
            "file_name": b.file_name,
            "uploaded_at": b.uploaded_at.isoformat() if b.uploaded_at else None,
            "claim_count": b.claim_count,
            "finalized_count": sum(1 for i in (b.items or []) if i.status == "finalized"),
            "flagged_count": sum(1 for i in (b.items or []) if i.status == "flagged"),
        }
        for b in batches
    ]


@router.get("/ghims-import/batches/{batch_id}")
def get_ghims_import_batch(
    batch_id: int,
    include_totals: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    """Get one imported XML batch with mapped claim records (fast by default)."""
    batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    items = (
        db.query(ClaimXmlImportItem)
        .filter(ClaimXmlImportItem.batch_id == batch_id)
        .order_by(ClaimXmlImportItem.row_index, ClaimXmlImportItem.id)
        .all()
    )

    totals_by_id: Dict[int, float] = {}
    batch_revenue = None
    if include_totals:
        totals_payload = compute_ghims_batch_claim_totals(db, items)
        totals_by_id = totals_payload["totals"]
        batch_revenue = totals_payload["total_revenue"]

    rows = []
    for i in items:
        p = i.payload or {}
        surname = str(p.get("surname") or "").strip()
        other_names = str(p.get("otherNames") or "").strip()
        missing_sections = _ghims_missing_sections(p)
        row = {
            "id": i.id,
            "row_index": i.row_index,
            "claim_claim_id": i.claim_claim_id,
            "claim_check_code": p.get("claimCheckCode"),
            "hospital_rec_no": p.get("hospitalRecNo"),
            "date_of_birth": p.get("dateOfBirth"),
            "client_name": " ".join([x for x in [surname, other_names] if x]).strip() or None,
            "type_of_service": p.get("typeOfService") or p.get("type_of_service"),
            "type_of_attendance": p.get("typeOfAttendance"),
            "specialty_attended": p.get("specialtyAttended"),
            "status": i.status,
            "flag_comment": i.flag_comment,
            "missing_sections": missing_sections,
            "has_missing_sections": len(missing_sections) > 0,
            "no_clinical_sections": len(missing_sections) == 4,
        }
        if include_totals:
            row["total_claim_amount"] = totals_by_id.get(i.id, 0.0)
        rows.append(row)

    response = {
        "id": batch.id,
        "file_name": batch.file_name,
        "uploaded_at": batch.uploaded_at.isoformat() if batch.uploaded_at else None,
        "claim_count": batch.claim_count,
        "claims": rows,
    }
    if include_totals:
        response["total_revenue"] = batch_revenue
    return response


@router.get("/ghims-import/batches/{batch_id}/claim-totals")
def get_ghims_import_batch_claim_totals(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    """Compute claim revenue totals for a batch using a shared in-memory price cache."""
    batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    items = (
        db.query(ClaimXmlImportItem)
        .filter(ClaimXmlImportItem.batch_id == batch_id)
        .order_by(ClaimXmlImportItem.row_index, ClaimXmlImportItem.id)
        .all()
    )
    totals_payload = compute_ghims_batch_claim_totals(db, items)
    return {
        "batch_id": batch_id,
        "total_revenue": totals_payload["total_revenue"],
        "totals": [
            {"id": item_id, "total_claim_amount": amount}
            for item_id, amount in totals_payload["totals"].items()
        ],
    }


class GhimsImportItemUpdateBody(BaseModel):
    payload: dict


def _normalize_medicine_dose(raw_dose: str) -> str:
    dose = str(raw_dose or "").strip()
    if not dose:
        return ""
    compact = re.sub(r"\s+", " ", dose)
    split_match = re.match(r"^(\d+(?:\.\d+)?)\s*([A-Za-z][A-Za-z0-9/%.\-]*)$", compact)
    if split_match:
        return f"{split_match.group(1)} {split_match.group(2).upper()}"
    return compact.upper()


def _normalize_medicine_duration(raw_duration: str) -> str:
    duration = str(raw_duration or "").strip()
    if not duration:
        return ""
    compact = re.sub(r"\s+", " ", duration)
    number_only = re.match(r"^(\d+(?:\.\d+)?)$", compact)
    if number_only:
        return f"{number_only.group(1)} days"
    day_based = re.match(r"^(\d+(?:\.\d+)?)\s*day(?:s)?$", compact, flags=re.IGNORECASE)
    if day_based:
        return f"{day_based.group(1)} days"
    return compact


def _reorder_ghims_diagnoses_principal_first(payload: dict) -> None:
    """Put the diagnosis matching principalGDRG first (export and UI section order)."""
    diagnoses = payload.get("diagnoses")
    if not isinstance(diagnoses, list) or len(diagnoses) <= 1:
        return
    principal_gdrg = str(payload.get("principalGDRG") or "").strip()
    if not principal_gdrg:
        return
    idx = next(
        (
            i
            for i, diag in enumerate(diagnoses)
            if isinstance(diag, dict) and str(diag.get("gdrgCode") or "").strip() == principal_gdrg
        ),
        -1,
    )
    if idx > 0:
        diagnoses.insert(0, diagnoses.pop(idx))


def _validate_and_normalize_ghims_payload(db: Session, payload: dict) -> dict:
    normalized_payload = dict(payload or {})
    diagnoses = normalized_payload.get("diagnoses")
    if isinstance(diagnoses, list):
        for idx, diag in enumerate(diagnoses):
            if not isinstance(diag, dict):
                raise HTTPException(status_code=400, detail=f"Invalid diagnosis entry at section {idx + 1}.")
            gdrg_code = str(diag.get("gdrgCode") or "").strip()
            icd10 = str(diag.get("icd10") or "").strip()
            diagnosis_text = str(diag.get("diagnosis") or "").strip()
            has_any_diagnosis_data = bool(gdrg_code or icd10 or diagnosis_text)
            if has_any_diagnosis_data and not gdrg_code:
                raise HTTPException(
                    status_code=400,
                    detail=f"Diagnosis section {idx + 1}: missing GDRG. Please enter GDRG before saving.",
                )
        _reorder_ghims_diagnoses_principal_first(normalized_payload)

    investigations = normalized_payload.get("investigations")
    if isinstance(investigations, list):
        for idx, inv in enumerate(investigations):
            if not isinstance(inv, dict):
                raise HTTPException(status_code=400, detail=f"Invalid investigation entry at section {idx + 1}.")
            gdrg_code = str(inv.get("gdrgCode") or "").strip()
            service_date = str(inv.get("serviceDate") or "").strip()
            if gdrg_code and not service_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"Investigation section {idx + 1}: missing service date. Please enter date before saving.",
                )

    procedures = normalized_payload.get("procedures")
    if isinstance(procedures, list):
        for idx, proc in enumerate(procedures):
            if not isinstance(proc, dict):
                raise HTTPException(status_code=400, detail=f"Invalid procedure entry at section {idx + 1}.")
            service_date = str(proc.get("serviceDate") or "").strip()
            has_any_procedure_data = bool(
                str(proc.get("gdrgCode") or "").strip()
                or str(proc.get("description") or "").strip()
                or str(proc.get("icd10") or "").strip()
                or str(proc.get("diagnosis") or "").strip()
            )
            if has_any_procedure_data and not service_date:
                raise HTTPException(
                    status_code=400,
                    detail=f"Procedure section {idx + 1}: missing service date. Please enter date before saving.",
                )

    medicines = normalized_payload.get("medicines")
    if not isinstance(medicines, list):
        return normalized_payload

    for idx, med in enumerate(medicines):
        if not isinstance(med, dict):
            raise HTTPException(status_code=400, detail=f"Invalid medicine entry at section {idx + 1}.")

        medicine_code = str(med.get("medicineCode") or "").strip()
        if medicine_code:
            product = (
                db.query(ProductPrice)
                .filter(ProductPrice.medication_code == medicine_code)
                .first()
            )
            covered = (getattr(product, "insurance_covered", None) or "yes").strip().lower() if product else "yes"
            if covered == "no":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Medicine not covered by insurance. "
                        f"Change or remove medicine section {idx + 1}."
                    ),
                )

        prescription = med.get("prescription")
        if prescription is None:
            prescription = {}
            med["prescription"] = prescription
        if not isinstance(prescription, dict):
            raise HTTPException(status_code=400, detail=f"Invalid prescription at medicine section {idx + 1}.")

        normalized_dose = _normalize_medicine_dose(prescription.get("dose", ""))
        if not normalized_dose:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Medicine section {idx + 1}: missing dose. Please enter dose before saving."
                ),
            )
        prescription["dose"] = normalized_dose
        prescription["duration"] = _normalize_medicine_duration(prescription.get("duration", ""))
        service_date = str(med.get("serviceDate") or "").strip()
        has_any_medicine_data = bool(
            str(med.get("medicineCode") or "").strip()
            or str(med.get("dispensedQty") or "").strip()
            or str(prescription.get("dose") or "").strip()
            or str(prescription.get("frequency") or "").strip()
            or str(prescription.get("duration") or "").strip()
            or str(prescription.get("unparsed") or "").strip()
        )
        if has_any_medicine_data and not service_date:
            raise HTTPException(
                status_code=400,
                detail=f"Medicine section {idx + 1}: missing service date. Please enter date before saving.",
            )

    return normalized_payload


def _ghims_missing_sections(payload: dict) -> List[str]:
    p = payload or {}
    missing = []
    for key in ["diagnoses", "investigations", "medicines", "procedures"]:
        value = p.get(key)
        if not isinstance(value, list) or len(value) == 0:
            missing.append(key)
    return missing


@router.get("/ghims-import/items/{item_id}")
def get_ghims_import_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")
    payload = item.payload or {}
    claim_summary = compute_claim_summary_from_ghims_payload(
        db, payload, price_cache=PriceAmountCache.build(db)
    )
    return {
        "id": item.id,
        "batch_id": item.batch_id,
        "claim_claim_id": item.claim_claim_id,
        "row_index": item.row_index,
        "status": item.status,
        "flag_comment": item.flag_comment,
        "payload": payload,
        "claim_summary": claim_summary,
        "claimit_errors": _get_claimit_errors_for_import_item(db, item),
    }


@router.put("/ghims-import/items/{item_id}")
def update_ghims_import_item(
    item_id: int,
    body: GhimsImportItemUpdateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")
    payload = body.payload or {}
    payload = _validate_and_normalize_ghims_payload(db, payload)
    claim_id = str(payload.get("claimID") or "").strip()
    if not claim_id:
        raise HTTPException(status_code=400, detail="claimID is required.")
    item.claim_claim_id = claim_id
    item.payload = payload
    db.commit()
    return {"id": item.id, "updated": True}


@router.patch("/ghims-import/items/{item_id}/finalize")
def finalize_ghims_import_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")
    payload = _validate_and_normalize_ghims_payload(db, item.payload or {})
    item.payload = payload
    from app.core.datetime_utils import utcnow
    item.status = "finalized"
    item.finalized_at = utcnow()
    db.commit()
    return {"id": item.id, "status": item.status}


@router.patch("/ghims-import/items/{item_id}/reopen")
def reopen_ghims_import_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")
    item.status = "draft"
    item.finalized_at = None
    db.commit()
    return {"id": item.id, "status": item.status}


@router.patch("/ghims-import/items/{item_id}/flag")
def flag_ghims_import_item(
    item_id: int,
    body: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")
    if item.status == "finalized":
        raise HTTPException(status_code=400, detail="Cannot flag a finalized imported claim.")
    comment = ""
    if isinstance(body, dict):
        comment = str(body.get("comment") or "").strip()
    if not comment:
        raise HTTPException(status_code=400, detail="Flag comment is required.")
    item.status = "flagged"
    item.finalized_at = None
    item.flag_comment = comment
    db.commit()
    return {"id": item.id, "status": item.status, "flag_comment": item.flag_comment}


@router.delete("/ghims-import/batches/{batch_id}")
def delete_ghims_import_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "delete")),
):
    batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    db.delete(batch)
    db.commit()
    return {"deleted": True}


class GhimsExportBatchBody(BaseModel):
    item_ids: List[int]


class GhimsBulkStatusBody(BaseModel):
    item_ids: List[int]
    action: str  # 'flag' | 'reopen' | 'finalize'
    comment: Optional[str] = None


@router.patch("/ghims-import/items/bulk-status")
def bulk_update_ghims_import_items_status(
    body: GhimsBulkStatusBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "update")),
):
    if not body.item_ids:
        raise HTTPException(status_code=400, detail="No imported claim IDs selected.")
    action = str(body.action or "").strip().lower()
    if action not in ("flag", "reopen", "finalize"):
        raise HTTPException(status_code=400, detail="Invalid action. Use flag, reopen, or finalize.")
    comment = str(body.comment or "").strip()

    items = (
        db.query(ClaimXmlImportItem)
        .filter(ClaimXmlImportItem.id.in_(body.item_ids))
        .all()
    )
    missing = sorted(set(body.item_ids) - set([i.id for i in items]))
    if missing:
        raise HTTPException(status_code=404, detail=f"Some imported claims were not found: {missing}")

    # Validate first to avoid partial updates
    if action == "flag":
        bad = [i.id for i in items if i.status == "finalized"]
        if bad:
            raise HTTPException(status_code=400, detail=f"Cannot flag finalized imported claim(s): {bad}")
        if not comment:
            raise HTTPException(status_code=400, detail="Flag comment is required for bulk flag.")
    if action == "finalize":
        # allow finalizing draft; block flagged (must be marked draft/reopened first)
        bad = [i.id for i in items if i.status == "flagged"]
        if bad:
            raise HTTPException(status_code=400, detail=f"Cannot finalize flagged imported claim(s): {bad}")

    from app.core.datetime_utils import utcnow

    for item in items:
        if action == "reopen":
            item.status = "draft"
            item.finalized_at = None
            item.flag_comment = None
        elif action == "flag":
            item.status = "flagged"
            item.finalized_at = None
            item.flag_comment = comment
        elif action == "finalize":
            payload = _validate_and_normalize_ghims_payload(db, item.payload or {})
            item.payload = payload
            item.status = "finalized"
            item.finalized_at = utcnow()
            item.flag_comment = None

    db.commit()
    return {"updated": len(items), "action": action, "item_ids": sorted([i.id for i in items])}


@router.post("/ghims-import/export")
def export_ghims_import_items(
    body: GhimsExportBatchBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Claims", "Admin", "Doctor", "PA"])),
    _module_check: User = Depends(require_module_permission("claims", "read")),
):
    if not body.item_ids:
        raise HTTPException(status_code=400, detail="No imported claim IDs selected.")
    items = (
        db.query(ClaimXmlImportItem)
        .filter(ClaimXmlImportItem.id.in_(body.item_ids))
        .all()
    )
    if len(items) != len(set(body.item_ids)):
        raise HTTPException(status_code=404, detail="Some imported claims were not found.")
    not_finalized = [i.id for i in items if i.status != "finalized"]
    if not_finalized:
        raise HTTPException(status_code=400, detail="Only finalized imported claims can be exported.")
    payloads = []
    for i in sorted(items, key=lambda x: x.row_index or 0):
        p = dict(i.payload or {})
        _reorder_ghims_diagnoses_principal_first(p)
        payloads.append(p)
    xml_content = build_claims_xml_from_payloads(payloads)
    filename = f"NHIS_CLA_imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

