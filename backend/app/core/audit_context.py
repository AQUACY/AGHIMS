"""
Resolve human-readable references for audit trail summaries across the platform.
Prefer card numbers, insurance IDs, bill numbers, and names over database IDs.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.audit_patient import patient_audit_identifier

# Path segments that are not numeric resource IDs
_NON_ID_SEGMENTS = frozenset(
    {
        "export",
        "finalize",
        "reopen",
        "regenerate",
        "edit-details",
        "detailed",
        "card",
        "search",
        "lookup",
        "import",
        "bulk",
        "confirm",
        "revert",
        "approve",
        "reject",
        "mark-paid",
        "refund",
        "generate-ccc",
        "nhia",
    }
)


def extract_path_resource_id(path: str) -> Optional[int]:
    """Last numeric path segment that looks like a record ID."""
    for part in reversed(path.split("/")):
        if not part or part in _NON_ID_SEGMENTS:
            continue
        try:
            return int(part)
        except ValueError:
            continue
    return None


def extract_card_from_path(path: str) -> Optional[str]:
    """Patient card number embedded in URL (e.g. /patients/card/E-0032-...)."""
    parts = [p for p in path.split("/") if p]
    for i, part in enumerate(parts):
        if part.lower() == "card" and i + 1 < len(parts):
            return parts[i + 1]
    return None


def _ctx_from_query(query_params: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not query_params:
        return {}
    ctx: Dict[str, str] = {}
    for key in ("patient_card_number", "card_number", "member_no", "hin", "insurance_id"):
        val = query_params.get(key)
        if val is not None and str(val).strip():
            if key in ("hin", "insurance_id", "member_no"):
                ctx["insurance_id"] = str(val).strip()
            else:
                ctx["patient_card"] = str(val).strip()
    return ctx


def _merge_ctx(base: Dict[str, str], extra: Dict[str, str]) -> Dict[str, str]:
    out = dict(base)
    for k, v in extra.items():
        if v and not out.get(k):
            out[k] = v
    return out


def _patient_ctx(db: Session, patient_id: int) -> Dict[str, str]:
    from app.models.patient import Patient

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {}
    ident = patient_audit_identifier(patient)
    ctx: Dict[str, str] = {"patient": ident}
    card = (patient.card_number or "").strip()
    if card:
        ctx["patient_card"] = card
    ins = (patient.insurance_id or "").strip()
    if ins:
        ctx["insurance_id"] = ins
    return ctx


def _encounter_ctx(db: Session, encounter_id: int) -> Dict[str, str]:
    from app.models.encounter import Encounter

    enc = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not enc:
        return {}
    ctx = _patient_ctx(db, enc.patient_id)
    dept = (enc.department or "").strip()
    if dept:
        ctx["encounter"] = f"{dept} encounter"
    else:
        ctx["encounter"] = "OPD encounter"
    if enc.ccc_number:
        ctx["ccc"] = enc.ccc_number.strip()
    return ctx


def _bill_ctx(db: Session, bill_id: int) -> Dict[str, str]:
    from app.models.bill import Bill

    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        return {}
    ctx = _encounter_ctx(db, bill.encounter_id)
    if bill.bill_number:
        ctx["bill"] = bill.bill_number
    return ctx


def _claim_ctx(db: Session, claim_pk: int) -> Dict[str, str]:
    from app.models.claim import Claim

    claim = db.query(Claim).filter(Claim.id == claim_pk).first()
    if not claim:
        return {}
    ctx = _encounter_ctx(db, claim.encounter_id)
    claim_ref = (claim.claim_id or "").strip()
    if claim_ref:
        ctx["claim"] = claim_ref
    else:
        ctx["claim"] = "NHIA claim"
    if claim.member_no:
        ctx["insurance_id"] = claim.member_no.strip()
    return ctx


def _companion_visit_ctx(db: Session, visit_id: int) -> Dict[str, str]:
    from app.models.companion_visit import CompanionVisit

    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        return {}
    card = (visit.external_card_number or "").strip()
    visit_no = (visit.external_visit_number or "").strip()
    ctx: Dict[str, str] = {}
    if card:
        ctx["patient_card"] = card
        ctx["companion"] = f"companion card {card}"
    if visit_no:
        ctx["companion"] = f"companion visit {visit_no}" + (f" (card {card})" if card else "")
    return ctx


def _staff_ctx(db: Session, user_id: int) -> Dict[str, str]:
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {}
    label = (user.full_name or user.username or "").strip()
    return {"staff": label or f"user {user.username}"}


def _ward_admission_ctx(db: Session, admission_id: int) -> Dict[str, str]:
    from app.models.ward_admission import WardAdmission

    adm = db.query(WardAdmission).filter(WardAdmission.id == admission_id).first()
    if not adm:
        return {}
    ctx = _encounter_ctx(db, adm.encounter_id)
    ward = (adm.ward or "").strip()
    if ward:
        ctx["ward"] = ward
        ctx["admission"] = f"{ward} admission"
    else:
        ctx["admission"] = "ward admission"
    return ctx


def _investigation_ctx(db: Session, investigation_id: int, *, inpatient: bool = False) -> Dict[str, str]:
    if inpatient:
        from app.models.inpatient_investigation import InpatientInvestigation
        from app.models.inpatient_clinical_review import InpatientClinicalReview

        inv = (
            db.query(InpatientInvestigation)
            .filter(InpatientInvestigation.id == investigation_id)
            .first()
        )
        if inv and inv.clinical_review_id:
            review = (
                db.query(InpatientClinicalReview)
                .filter(InpatientClinicalReview.id == inv.clinical_review_id)
                .first()
            )
            if review and review.ward_admission_id:
                return _ward_admission_ctx(db, review.ward_admission_id)
        return {}
    from app.models.investigation import Investigation

    inv = db.query(Investigation).filter(Investigation.id == investigation_id).first()
    if not inv:
        return {}
    return _encounter_ctx(db, inv.encounter_id)


def _pharmacy_requisition_ctx(db: Session, requisition_id: int) -> Dict[str, str]:
    from app.models.pharmacy_requisition import PharmacyRequisition

    req = db.query(PharmacyRequisition).filter(PharmacyRequisition.id == requisition_id).first()
    if not req:
        return {}
    num = (req.requisition_number or "").strip()
    return {"requisition": num or "pharmacy requisition"}


def _store_ctx(db: Session, store_id: int) -> Dict[str, str]:
    from app.models.store import Store

    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        return {}
    name = (store.name or "").strip()
    return {"store": name or "store"}


def _prescription_ctx(db: Session, prescription_id: int) -> Dict[str, str]:
    from app.models.prescription import Prescription

    rx = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not rx:
        return {}
    if rx.encounter_id:
        return _encounter_ctx(db, rx.encounter_id)
    return {}


def resolve_audit_context(
    db: Session,
    path: str,
    resource_id: Optional[int] = None,
    query_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Build context keys for summary text (patient_card, bill, claim, etc.)."""
    path_l = path.lower()
    ctx = _ctx_from_query(query_params)
    card_in_path = extract_card_from_path(path)
    if card_in_path:
        ctx["patient_card"] = card_in_path

    rid = resource_id if resource_id is not None else extract_path_resource_id(path)
    if rid is None:
        return ctx

    # Billing routes keyed by encounter id in the path
    if "/billing/encounter/" in path_l:
        m = re.search(r"/encounter/(\d+)", path_l)
        if m:
            return _merge_ctx(ctx, _encounter_ctx(db, int(m.group(1))))

    # Module-specific lookups (order matters — more specific paths first)
    if "companion-visits" in path_l or "companion_visits" in path_l:
        return _merge_ctx(ctx, _companion_visit_ctx(db, rid))

    if "/billing" in path_l:
        return _merge_ctx(ctx, _bill_ctx(db, rid))

    if "/claims" in path_l:
        return _merge_ctx(ctx, _claim_ctx(db, rid))

    if "ward-admission" in path_l or "ward_admissions" in path_l:
        return _merge_ctx(ctx, _ward_admission_ctx(db, rid))

    if "/patients/" in path_l and "/card/" not in path_l:
        return _merge_ctx(ctx, _patient_ctx(db, rid))

    if "pharmacy-requisition" in path_l or "pharmacy_requisition" in path_l:
        return _merge_ctx(ctx, _pharmacy_requisition_ctx(db, rid))

    if "/stores/" in path_l or path_l.startswith("/api/stores"):
        return _merge_ctx(ctx, _store_ctx(db, rid))

    if "prescription" in path_l:
        return _merge_ctx(ctx, _prescription_ctx(db, rid))

    if "/encounters/" in path_l or path_l.endswith(f"/encounters/{rid}"):
        return _merge_ctx(ctx, _encounter_ctx(db, rid))

    if "/staff/" in path_l:
        return _merge_ctx(ctx, _staff_ctx(db, rid))

    if "inpatient" in path_l and "investigation" in path_l:
        return _merge_ctx(ctx, _investigation_ctx(db, rid, inpatient=True))

    if "investigation" in path_l:
        return _merge_ctx(ctx, _investigation_ctx(db, rid, inpatient=False))

    if "/vitals" in path_l:
        from app.models.vital import Vital

        vital = db.query(Vital).filter(Vital.id == rid).first()
        if vital and vital.encounter_id:
            return _merge_ctx(ctx, _encounter_ctx(db, vital.encounter_id))

    if "/consultation/" in path_l or path_l.startswith("/api/consultation"):
        # Encounter-scoped consultation routes
        if re.search(r"/encounters/\d+", path_l):
            enc_id = rid
            m = re.search(r"/encounters/(\d+)", path_l)
            if m:
                enc_id = int(m.group(1))
            return _merge_ctx(ctx, _encounter_ctx(db, enc_id))

    # Generic patient id fallback when resource type is Patients
    if "/patients" in path_l:
        return _merge_ctx(ctx, _patient_ctx(db, rid))

    return ctx


def _action_verb(method: str, action: str) -> str:
    method_u = (method or "").upper()
    if method_u == "POST":
        return "Created"
    if method_u in ("PUT", "PATCH"):
        return "Updated"
    if method_u == "DELETE":
        return "Deleted"
    if method_u == "GET" or action == "VIEW":
        return "Viewed"
    return action.title() if action else "Changed"


def _subject_from_context(ctx: Dict[str, str], path: str) -> str:
    path_l = path.lower()
    if ctx.get("requisition"):
        return f"pharmacy requisition {ctx['requisition']}"
    if ctx.get("store"):
        return f"store {ctx['store']}"
    if ctx.get("companion"):
        return ctx["companion"]
    if ctx.get("claim"):
        patient = ctx.get("patient") or ctx.get("patient_card")
        if patient:
            return f"claim {ctx['claim']} for patient {patient}"
        return f"claim {ctx['claim']}"
    if ctx.get("bill"):
        patient = ctx.get("patient") or ctx.get("patient_card")
        if patient:
            return f"bill {ctx['bill']} for patient {patient}"
        return f"bill {ctx['bill']}"
    if ctx.get("ward") and (ctx.get("patient") or ctx.get("patient_card")):
        return f"{ctx['ward']} admission for patient {ctx.get('patient') or ctx.get('patient_card')}"
    if ctx.get("encounter") and (ctx.get("patient") or ctx.get("patient_card")):
        return f"{ctx['encounter']} for patient {ctx.get('patient') or ctx.get('patient_card')}"
    if ctx.get("patient"):
        return f"patient {ctx['patient']}"
    if ctx.get("patient_card"):
        return f"patient {ctx['patient_card']}"
    if ctx.get("insurance_id"):
        return f"insurance {ctx['insurance_id']}"
    if ctx.get("staff"):
        return f"staff account {ctx['staff']}"

    # Path-based labels without DB id
    if "patient" in path_l:
        return "a patient record"
    if "companion" in path_l:
        return "a companion visit"
    if "billing" in path_l or "bill" in path_l:
        return "a bill"
    if "claim" in path_l:
        return "a claim"
    if "encounter" in path_l:
        return "an encounter"
    if "staff" in path_l:
        return "a staff account"
    if "consultation" in path_l:
        return "a consultation record"
    if "inventory" in path_l or "store" in path_l or "requisition" in path_l:
        return "inventory"
    if "ward" in path_l:
        return "a ward record"
    return "a record"


def build_platform_audit_summary(
    db: Session,
    path: str,
    method: str,
    resource_type: Optional[str],
    action: str,
    resource_id: Optional[int] = None,
    query_params: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Human-readable audit sentence without raw database IDs.
    Used by middleware when an endpoint does not set request.state.audit_summary.
    """
    path_l = path.lower()
    ctx = resolve_audit_context(db, path, resource_id, query_params)
    verb = _action_verb(method, action)
    subject = _subject_from_context(ctx, path)

    # Path-specific phrasing
    if method.upper() == "POST":
        if "generate-ccc" in path_l:
            return f"{verb} NHIA CCC for {subject}."
        if "login" in path_l:
            return f"User logged in."
        if "receipt" in path_l:
            return f"{verb} a payment receipt for {subject}."
        if "patient" in path_l and "import" not in path_l and "nhia/lookup" not in path_l:
            if verb == "Created":
                return f"Registered {subject}."
        if "encounter" in path_l and verb == "Created":
            return f"{verb} {subject}."
        if "finalize" in path_l:
            return f"Finalized {subject}."
        if "close" in path_l and "companion" in path_l:
            return f"Closed {subject}."
        if "approve" in path_l:
            return f"Approved undertaking for {subject}."
        if "reject" in path_l:
            return f"Rejected undertaking for {subject}."

    if method.upper() in ("PUT", "PATCH"):
        if "patient" in path_l:
            return f"Updated {subject}."
        if "staff" in path_l:
            return f"Updated {subject}."

    if method.upper() == "DELETE":
        return f"Deleted {subject}."

    resource_label = (resource_type or "record").replace("_", " ").lower()
    return f"{verb} {subject} ({resource_label})."
