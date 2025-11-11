"""
NHIA ClaimIT XML export service
"""
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.encounter import Encounter
from app.models.claim import Claim
from typing import List


def format_date(date_obj) -> str:
    """Format date to YYYY-MM-DD"""
    if isinstance(date_obj, str):
        return date_obj
    if date_obj is None:
        return ""
    return date_obj.strftime("%Y-%m-%d")


def format_datetime(dt_obj) -> str:
    """Format datetime to YYYY-MM-DD"""
    if isinstance(dt_obj, str):
        return dt_obj
    if dt_obj is None:
        return ""
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
    """
    from sqlalchemy.orm import joinedload
    
    # Get claim IDs for eager loading
    claim_ids = [c.id for c in claims]
    
    # Eager load claim detail relationships
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
        
        # Handle surname: use patient.surname if available, otherwise extract from name
        if patient.surname:
            surname_text = patient.surname
        elif patient.name:
            # If no surname, use first word of name as surname
            name_parts = patient.name.split()
            surname_text = name_parts[0] if name_parts else ""
        else:
            surname_text = ""
        SubElement(claim_elem, "surname").text = surname_text
        
        # Handle otherNames: prioritize patient.other_names, then construct from name
        other_names_text = ""
        if patient.other_names and patient.other_names.strip():
            # Use other_names field if available
            other_names_text = patient.other_names.strip()
        elif patient.name:
            # Construct from patient.name
            name_parts = patient.name.split()
            if patient.surname:
                # If surname exists separately, use everything from name after first word
                # Or use the full name if surname is not in name
                name_without_surname = patient.name.replace(patient.surname, "").strip()
                if name_without_surname:
                    other_names_text = name_without_surname
                else:
                    # If surname removal left nothing, use everything except first word
                    if len(name_parts) > 1:
                        other_names_text = " ".join(name_parts[1:])
            else:
                # No separate surname, use everything after first word
                if len(name_parts) > 1:
                    other_names_text = " ".join(name_parts[1:])
        
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
        service_date = format_datetime(encounter.created_at)
        SubElement(claim_elem, "dateOfService").text = service_date
        SubElement(claim_elem, "dateOfService").text = service_date
        SubElement(claim_elem, "dateOfService").text = ""  # Third date field (optional)
        
        SubElement(claim_elem, "specialtyAttended").text = claim.specialty_attended or "OPDC"
        
        # ALWAYS use claim detail tables - these contain the edited claim data
        # Never fallback to encounter services as those are the original, unedited data
        from app.models.claim_detail import ClaimDiagnosis, ClaimInvestigation, ClaimPrescription, ClaimProcedure
        
        # Check if claim has been edited (any claim detail table entry exists)
        claim_has_been_edited = len(claim.claim_diagnoses) > 0 or \
                                 len(claim.claim_investigations) > 0 or \
                                 len(claim.claim_prescriptions) > 0 or \
                                 len(claim.claim_procedures) > 0
        
        # Investigations - ALWAYS use claim detail table (never fallback)
        claim_investigations = sorted(claim.claim_investigations, key=lambda x: x.display_order) if claim.claim_investigations else []
        for claim_inv in claim_investigations:
            if claim_inv.gdrg_code:
                inv_elem = SubElement(claim_elem, "investigation")
                SubElement(inv_elem, "serviceDate").text = format_datetime(claim_inv.service_date)
                SubElement(inv_elem, "gdrgCode").text = claim_inv.gdrg_code
        
        # If claim hasn't been edited yet, fallback to encounter investigations for backward compatibility
        if not claim_has_been_edited:
            for investigation in encounter.investigations:
                if investigation.status == "completed" and investigation.gdrg_code:
                    inv_elem = SubElement(claim_elem, "investigation")
                    SubElement(inv_elem, "serviceDate").text = format_datetime(investigation.service_date)
                    SubElement(inv_elem, "gdrgCode").text = investigation.gdrg_code
        
        # Diagnoses - ALWAYS use claim detail table (never fallback after edits)
        claim_diagnoses = sorted(claim.claim_diagnoses, key=lambda x: x.display_order) if claim.claim_diagnoses else []
        for claim_diag in claim_diagnoses:
            diag_elem = SubElement(claim_elem, "diagnosis")
            SubElement(diag_elem, "gdrgCode").text = claim_diag.gdrg_code or ""
            SubElement(diag_elem, "icd10").text = claim_diag.icd10
            SubElement(diag_elem, "diagnosis").text = claim_diag.description
        
        # If claim hasn't been edited yet, fallback to encounter diagnoses for backward compatibility
        if not claim_has_been_edited:
            for diagnosis in encounter.diagnoses:
                diag_elem = SubElement(claim_elem, "diagnosis")
                SubElement(diag_elem, "gdrgCode").text = diagnosis.gdrg_code or ""
                SubElement(diag_elem, "icd10").text = diagnosis.icd10
                SubElement(diag_elem, "diagnosis").text = diagnosis.diagnosis
        
        # Medicines (Prescriptions) - ALWAYS use claim detail table (never fallback after edits)
        claim_prescriptions = sorted(claim.claim_prescriptions, key=lambda x: x.display_order) if claim.claim_prescriptions else []
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
        if not claim_has_been_edited:
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
        investigation_gdrg_codes = set()
        for claim_inv in claim_investigations:
            if claim_inv.gdrg_code:
                investigation_gdrg_codes.add(claim_inv.gdrg_code)
        
        claim_procedures = sorted(claim.claim_procedures, key=lambda x: x.display_order) if claim.claim_procedures else []
        for claim_proc in claim_procedures:
            if claim_proc.gdrg_code and claim_proc.gdrg_code not in investigation_gdrg_codes:
                proc_elem = SubElement(claim_elem, "procedure")
                SubElement(proc_elem, "serviceDate").text = format_datetime(claim_proc.service_date)
                SubElement(proc_elem, "gdrgCode").text = claim_proc.gdrg_code
                if claim_proc.description:
                    SubElement(proc_elem, "description").text = claim_proc.description
                # Get diagnosis for procedure from claim diagnoses
                chief_diag = None
                if claim_diagnoses:
                    chief_diag = next((d for d in claim_diagnoses if d.is_chief), claim_diagnoses[0] if claim_diagnoses else None)
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
                chief_diag = next((d for d in encounter.diagnoses if d.is_chief), None)
                if chief_diag:
                    SubElement(proc_elem, "icd10").text = chief_diag.icd10
                    SubElement(proc_elem, "diagnosis").text = chief_diag.diagnosis
        
        # Principal GDRG
        SubElement(claim_elem, "principalGDRG").text = claim.principal_gdrg or ""
        
        # Referral info
        ref_elem = SubElement(claim_elem, "referralInfo")
        SubElement(ref_elem, "claimCheckCode").text = ""
        SubElement(ref_elem, "facilityID").text = ""
        SubElement(ref_elem, "facilityName").text = ""
    
    # Convert to pretty XML string
    rough_string = tostring(root, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def export_claims_xml(claim_ids: List[int], db: Session) -> str:
    """
    Export multiple claims as XML
    """
    claims = db.query(Claim).filter(Claim.id.in_(claim_ids)).all()
    return generate_claim_xml(claims, db)


def export_claims_by_date_range(start_date: datetime, end_date: datetime, db: Session) -> str:
    """
    Export claims within a date range as XML
    """
    claims = (
        db.query(Claim)
        .join(Encounter)
        .filter(Encounter.created_at >= start_date)
        .filter(Encounter.created_at <= end_date)
        .filter(Claim.status == "finalized")
        .all()
    )
    return generate_claim_xml(claims, db)

