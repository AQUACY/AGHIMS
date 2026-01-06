"""
NHIA ClaimIT XML export service
"""
from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, case
from app.models.encounter import Encounter
from app.models.claim import Claim
from typing import List


def format_date(date_obj) -> str:
    """Format date to YYYY-MM-DD - optimized"""
    if date_obj is None:
        return ""
    if isinstance(date_obj, str):
        return date_obj
    # Use faster formatting
    return date_obj.strftime("%Y-%m-%d")


def format_datetime(dt_obj) -> str:
    """Format datetime to YYYY-MM-DD - optimized"""
    if dt_obj is None:
        return ""
    if isinstance(dt_obj, str):
        return dt_obj
    # Use faster formatting
    return dt_obj.strftime("%Y-%m-%d")


def map_type_of_attendance(attendance_type: str) -> str:
    """Map type of attendance to XML format"""
    if not attendance_type:
        return "EAE"
    
    attendance_type = attendance_type.strip()
    
    # Map Antenatal to ANC and Postnatal to PNC
    if attendance_type.lower() == "antenatal":
        return "ANC"
    elif attendance_type.lower() == "postnatal":
        return "PNC"
    
    # Return original value for other types (EAE, Referral, CFU, etc.)
    return attendance_type


def generate_claim_xml(claims: List[Claim], db: Session) -> str:
    """
    Generate NHIA ClaimIT compatible XML from claims
    Uses claim detail tables if available, otherwise falls back to encounter services
    
    Note: Claims should already have relationships eager-loaded when passed to this function
    If not, this function will reload them with eager loading (for backward compatibility)
    """
    # Eager load relationships if not already loaded
    # Check if relationships are loaded by inspecting the first claim
    if claims:
        from sqlalchemy import inspect
        from sqlalchemy.orm import joinedload
        
        # Check if encounter relationship is already loaded
        first_claim = claims[0]
        inspector = inspect(first_claim)
        # unloaded contains relationships that are NOT loaded
        encounter_not_loaded = 'encounter' in inspector.unloaded
        
        # Only reload if relationships aren't loaded
        if encounter_not_loaded:
            claim_ids = [c.id for c in claims]
            claims = db.query(Claim)\
                .options(
                    joinedload(Claim.encounter).joinedload(Encounter.patient),
                    joinedload(Claim.claim_diagnoses),
                    joinedload(Claim.claim_investigations),
                    joinedload(Claim.claim_prescriptions),
                    joinedload(Claim.claim_procedures),
                    joinedload(Claim.encounter).joinedload(Encounter.diagnoses),
                    joinedload(Claim.encounter).joinedload(Encounter.investigations),
                    joinedload(Claim.encounter).joinedload(Encounter.prescriptions)
                )\
                .filter(Claim.id.in_(claim_ids))\
                .all()
    
    # Create root element
    root = Element("claims")
    
    for claim in claims:
        encounter = claim.encounter
        patient = encounter.patient
        
        # Create claim element
        claim_elem = SubElement(root, "claim")
        
        # Basic claim information
        SubElement(claim_elem, "claimID").text = claim.claim_id
        SubElement(claim_elem, "claimCheckCode").text = claim.claim_check_code or ""
        SubElement(claim_elem, "preAuthorizationCodes").text = claim.pre_authorization_codes or " ,"
        SubElement(claim_elem, "physicianID").text = claim.physician_id
        
        # Patient information
        SubElement(claim_elem, "memberNo").text = patient.insurance_id or ""
        SubElement(claim_elem, "cardSerialNo").text = ""  # Leave empty as requested
        
        # Optimize name parsing - compute once and reuse
        patient_name = patient.name or ""
        patient_surname = patient.surname or ""
        patient_other_names = (patient.other_names or "").strip()
        
        # Handle surname: use patient.surname if available, otherwise extract from name
        if patient_surname:
            surname_text = patient_surname
        elif patient_name:
            # If no surname, use first word of name as surname
            first_space = patient_name.find(' ')
            surname_text = patient_name[:first_space] if first_space > 0 else patient_name
        else:
            surname_text = ""
        SubElement(claim_elem, "surname").text = surname_text
        
        # Handle otherNames: prioritize patient.other_names, then construct from name
        if patient_other_names:
            other_names_text = patient_other_names
        elif patient_name:
            # Construct from patient.name
            if patient_surname:
                # If surname exists separately, remove it from name
                name_without_surname = patient_name.replace(patient_surname, "", 1).strip()
                if name_without_surname:
                    other_names_text = name_without_surname
                else:
                    # If surname removal left nothing, use everything except first word
                    first_space = patient_name.find(' ')
                    if first_space > 0:
                        other_names_text = patient_name[first_space+1:].strip()
                    else:
                        other_names_text = ""
            else:
                # No separate surname, use everything after first word
                first_space = patient_name.find(' ')
                if first_space > 0:
                    other_names_text = patient_name[first_space+1:].strip()
                else:
                    other_names_text = ""
        else:
            other_names_text = ""
        
        SubElement(claim_elem, "otherNames").text = other_names_text
        SubElement(claim_elem, "dateOfBirth").text = format_date(patient.date_of_birth)
        SubElement(claim_elem, "gender").text = patient.gender
        
        # Hospital record number (using card number or encounter ID)
        hospital_rec_no = patient.card_number or f"ENC-{encounter.id}"
        SubElement(claim_elem, "hospitalRecNo").text = hospital_rec_no
        
        SubElement(claim_elem, "isDependant").text = "1" if claim.is_dependant else "0"
        SubElement(claim_elem, "typeOfService").text = claim.type_of_service
        SubElement(claim_elem, "isUnbundled").text = "1" if claim.is_unbundled else "0"
        SubElement(claim_elem, "includesPharmacy").text = "1" if claim.includes_pharmacy else "0"
        SubElement(claim_elem, "typeOfAttendance").text = map_type_of_attendance(claim.type_of_attendance)
        SubElement(claim_elem, "serviceOutcome").text = claim.service_outcome or "DISC"
        
        # Service dates
        # First date: admission/visit date
        first_service_date = format_datetime(encounter.created_at)
        SubElement(claim_elem, "dateOfService").text = first_service_date
        
        # Second date: discharge date for IPD, same as first for OPD
        if claim.type_of_service == "IPD" and encounter.finalized_at:
            second_service_date = format_datetime(encounter.finalized_at)
        else:
            second_service_date = first_service_date
        SubElement(claim_elem, "dateOfService").text = second_service_date
        
        # Third date field (optional)
        SubElement(claim_elem, "dateOfService").text = ""
        
        SubElement(claim_elem, "specialtyAttended").text = claim.specialty_attended or "OPDC"
        
        # ALWAYS use claim detail tables - these contain the edited claim data
        # Never fallback to encounter services as those are the original, unedited data
        from app.models.claim_detail import ClaimDiagnosis, ClaimInvestigation, ClaimPrescription, ClaimProcedure
        
        # Pre-compute: Check if claim has been edited (any claim detail table entry exists)
        claim_has_been_edited = bool(claim.claim_diagnoses or claim.claim_investigations or 
                                     claim.claim_prescriptions or claim.claim_procedures)
        
        # Pre-sort and cache lists to avoid repeated sorting
        claim_investigations = sorted(claim.claim_investigations, key=lambda x: x.display_order) if claim.claim_investigations else []
        claim_diagnoses = sorted(claim.claim_diagnoses, key=lambda x: x.display_order) if claim.claim_diagnoses else []
        claim_prescriptions = sorted(claim.claim_prescriptions, key=lambda x: x.display_order) if claim.claim_prescriptions else []
        claim_procedures = sorted(claim.claim_procedures, key=lambda x: x.display_order) if claim.claim_procedures else []
        
        # Pre-compute investigation GDRG codes set (used for procedures)
        investigation_gdrg_codes = {inv.gdrg_code for inv in claim_investigations if inv.gdrg_code}
        
        # Pre-compute chief diagnosis (used for procedures)
        chief_diag = next((d for d in claim_diagnoses if d.is_chief), claim_diagnoses[0] if claim_diagnoses else None)
        
        # Investigations - ALWAYS use claim detail table (never fallback)
        for claim_inv in claim_investigations:
            if claim_inv.gdrg_code:
                inv_elem = SubElement(claim_elem, "investigation")
                SubElement(inv_elem, "serviceDate").text = format_datetime(claim_inv.service_date)
                SubElement(inv_elem, "gdrgCode").text = claim_inv.gdrg_code
        
        # If claim hasn't been edited yet, fallback to encounter investigations for backward compatibility
        if not claim_has_been_edited and encounter.investigations:
            for investigation in encounter.investigations:
                if investigation.status == "completed" and investigation.gdrg_code:
                    inv_elem = SubElement(claim_elem, "investigation")
                    SubElement(inv_elem, "serviceDate").text = format_datetime(investigation.service_date)
                    SubElement(inv_elem, "gdrgCode").text = investigation.gdrg_code
        
        # Diagnoses - ALWAYS use claim detail table (never fallback after edits)
        for claim_diag in claim_diagnoses:
            diag_elem = SubElement(claim_elem, "diagnosis")
            SubElement(diag_elem, "gdrgCode").text = claim_diag.gdrg_code or ""
            SubElement(diag_elem, "icd10").text = claim_diag.icd10
            SubElement(diag_elem, "diagnosis").text = claim_diag.description
        
        # If claim hasn't been edited yet, fallback to encounter diagnoses for backward compatibility
        if not claim_has_been_edited and encounter.diagnoses:
            for diagnosis in encounter.diagnoses:
                diag_elem = SubElement(claim_elem, "diagnosis")
                SubElement(diag_elem, "gdrgCode").text = diagnosis.gdrg_code or ""
                SubElement(diag_elem, "icd10").text = diagnosis.icd10
                SubElement(diag_elem, "diagnosis").text = diagnosis.diagnosis
        
        # Medicines (Prescriptions) - ALWAYS use claim detail table (never fallback after edits)
        for claim_presc in claim_prescriptions:
            med_elem = SubElement(claim_elem, "medicine")
            SubElement(med_elem, "medicineCode").text = claim_presc.code
            SubElement(med_elem, "dispensedQty").text = str(claim_presc.quantity)
            SubElement(med_elem, "serviceDate").text = format_datetime(claim_presc.service_date)
            
            presc_elem = SubElement(med_elem, "prescription")
            SubElement(presc_elem, "dose").text = claim_presc.dose or ""
            SubElement(presc_elem, "frequency").text = claim_presc.frequency or ""
            SubElement(presc_elem, "duration").text = claim_presc.duration or ""
            SubElement(presc_elem, "unparsed").text = claim_presc.unparsed or ""
        
        # If claim hasn't been edited yet, fallback to encounter prescriptions for backward compatibility
        if not claim_has_been_edited and encounter.prescriptions:
            for prescription in encounter.prescriptions:
                if prescription.dispensed_by:
                    med_elem = SubElement(claim_elem, "medicine")
                    SubElement(med_elem, "medicineCode").text = prescription.medicine_code
                    SubElement(med_elem, "dispensedQty").text = str(prescription.quantity)
                    SubElement(med_elem, "serviceDate").text = format_datetime(prescription.service_date)
                    
                    presc_elem = SubElement(med_elem, "prescription")
                    SubElement(presc_elem, "dose").text = prescription.dose or ""
                    SubElement(presc_elem, "frequency").text = prescription.frequency or ""
                    SubElement(presc_elem, "duration").text = prescription.duration or ""
                    SubElement(presc_elem, "unparsed").text = prescription.unparsed or ""
        
        # Procedures - ALWAYS use claim detail table (exclude investigations, never fallback after edits)
        for claim_proc in claim_procedures:
            if claim_proc.gdrg_code and claim_proc.gdrg_code not in investigation_gdrg_codes:
                proc_elem = SubElement(claim_elem, "procedure")
                SubElement(proc_elem, "serviceDate").text = format_datetime(claim_proc.service_date)
                SubElement(proc_elem, "gdrgCode").text = claim_proc.gdrg_code
                if claim_proc.description:
                    SubElement(proc_elem, "description").text = claim_proc.description
                # Use pre-computed chief diagnosis
                if chief_diag:
                    SubElement(proc_elem, "icd10").text = chief_diag.icd10
                    SubElement(proc_elem, "diagnosis").text = chief_diag.description
        
        # If claim hasn't been edited yet, fallback to encounter procedure for backward compatibility
        if not claim_has_been_edited:
            if encounter.procedure_g_drg_code and encounter.procedure_g_drg_code not in investigation_gdrg_codes:
                proc_elem = SubElement(claim_elem, "procedure")
                SubElement(proc_elem, "serviceDate").text = format_datetime(encounter.created_at)
                SubElement(proc_elem, "gdrgCode").text = encounter.procedure_g_drg_code
                if encounter.procedure_name:
                    SubElement(proc_elem, "description").text = encounter.procedure_name
                # Get diagnosis for procedure if available
                if encounter.diagnoses:
                    chief_diag_enc = next((d for d in encounter.diagnoses if d.is_chief), None)
                    if chief_diag_enc:
                        SubElement(proc_elem, "icd10").text = chief_diag_enc.icd10
                        SubElement(proc_elem, "diagnosis").text = chief_diag_enc.diagnosis
        
        # Principal GDRG
        SubElement(claim_elem, "principalGDRG").text = claim.principal_gdrg or ""
        
        # Referral info
        ref_elem = SubElement(claim_elem, "referralInfo")
        SubElement(ref_elem, "claimCheckCode").text = ""
        SubElement(ref_elem, "facilityID").text = ""
        SubElement(ref_elem, "facilityName").text = ""
    
    # Convert to XML string - skip minidom.toprettyxml() for performance
    # It's very slow for large XML files. Use tostring() directly
    xml_string = tostring(root, encoding='unicode')
    
    # Add XML declaration if not present
    if not xml_string.startswith('<?xml'):
        xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_string
    
    return xml_string


def export_claims_xml(claim_ids: List[int], db: Session) -> str:
    """
    Export multiple claims as XML
    """
    claims = db.query(Claim).filter(Claim.id.in_(claim_ids)).all()
    return generate_claim_xml(claims, db)


def export_claims_by_date_range(start_date: datetime, end_date: datetime, db: Session) -> str:
    """
    Export claims within a date range as XML
    Optimized to use eager loading from the start and filter by finalized_at
    """
    from sqlalchemy.orm import joinedload
    
    # Optimize: Use eager loading from the start and filter by finalized_at (more accurate)
    # Filter by claim finalized_at or encounter finalized_at for better performance
    claims = (
        db.query(Claim)
        .options(
            joinedload(Claim.encounter).joinedload(Encounter.patient),
            joinedload(Claim.claim_diagnoses),
            joinedload(Claim.claim_investigations),
            joinedload(Claim.claim_prescriptions),
            joinedload(Claim.claim_procedures),
            joinedload(Claim.encounter).joinedload(Encounter.diagnoses),
            joinedload(Claim.encounter).joinedload(Encounter.investigations),
            joinedload(Claim.encounter).joinedload(Encounter.prescriptions)
        )
        .join(Encounter)
        .filter(Claim.status == "finalized")
        .filter(
            # Include all finalized claims where the encounter date is within range
            # Check multiple date fields to be inclusive
            or_(
                # Claim finalized within range
                and_(
                    Claim.finalized_at.isnot(None),
                    Claim.finalized_at >= start_date,
                    Claim.finalized_at <= end_date
                ),
                # Encounter finalized within range
                and_(
                    Encounter.finalized_at.isnot(None),
                    Encounter.finalized_at >= start_date,
                    Encounter.finalized_at <= end_date
                ),
                # Encounter created within range (fallback for cases where finalized_at is not set)
                and_(
                    Encounter.created_at.isnot(None),
                    Encounter.created_at >= start_date,
                    Encounter.created_at <= end_date
                )
            )
        )
        .order_by(
            # Order by claim finalized_at if available, otherwise encounter finalized_at, otherwise created_at
            case(
                (Claim.finalized_at.isnot(None), Claim.finalized_at),
                (Encounter.finalized_at.isnot(None), Encounter.finalized_at),
                else_=Encounter.created_at
            ).desc()
        )
        .all()
    )
    return generate_claim_xml(claims, db)


