"""
Confidential modality.

Codes are prepared by Records, handed to the client, and used at every
service point. Admin, Doctor, PA, and Claims can open the register, where
the code is mapped to the client. Claims for these visits are unchanged.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.datetime_utils import utcnow
from app.core.dependencies import get_current_user, require_role
from app.models.confidential import ConfidentialCode
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.user import User
from app.services.confidential import (
    CODE_POOL_ROLES,
    ISSUE_ROLES,
    REGISTER_ROLES,
    ensure_confidential_schema,
    user_has_role,
)

router = APIRouter(prefix="/confidential", tags=["confidential"])


class CodeGenerateRequest(BaseModel):
    prefix: str = "SCRN"
    start: int = Field(1, ge=1)
    count: int = Field(50, ge=1, le=500)
    pad: int = Field(4, ge=1, le=8)


class IssueVisitRequest(BaseModel):
    patient_id: int
    service_type: str
    code_id: Optional[int] = None
    ccc_number: Optional[str] = None
    procedure_g_drg_code: Optional[str] = None
    procedure_name: Optional[str] = None


class FollowUpRequest(BaseModel):
    code: str
    service_type: Optional[str] = None
    ccc_number: Optional[str] = None
    procedure_g_drg_code: Optional[str] = None
    procedure_name: Optional[str] = None


def _ready(db: Session) -> None:
    ensure_confidential_schema(db)


def _patient_name(patient: Patient) -> str:
    parts = [patient.name or "", patient.surname or "", patient.other_names or ""]
    return " ".join(p for p in parts if p).strip()


def _encounter_brief(encounter: Encounter) -> dict:
    return {
        "id": encounter.id,
        "status": encounter.status,
        "department": encounter.department,
        "procedure_name": encounter.procedure_name,
        "procedure_g_drg_code": encounter.procedure_g_drg_code,
        "created_at": encounter.created_at,
        "finalized_at": encounter.finalized_at,
        "is_confidential": True,
        "confidential_code": encounter.code_link.code if encounter.code_link else None,
    }


def _load_code(db: Session, code_id: int) -> ConfidentialCode:
    row = db.query(ConfidentialCode).filter(ConfidentialCode.id == code_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Code not found")
    return row


def _next_available(db: Session) -> ConfidentialCode:
    row = (
        db.query(ConfidentialCode)
        .filter(ConfidentialCode.status == "available")
        .order_by(ConfidentialCode.code.asc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=400, detail="No confidential codes are available. Generate a list first.")
    return row


def _stamp_visit(db: Session, encounter_id: int, code: ConfidentialCode, user: User, patient_id: int) -> Encounter:
    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter:
        raise HTTPException(status_code=500, detail="Encounter was not created")
    if code.patient_id and code.patient_id != patient_id:
        raise HTTPException(status_code=400, detail="This code is already assigned to another client")
    encounter.is_confidential = True
    encounter.confidential_code_id = code.id
    if code.status != "assigned":
        code.status = "assigned"
        code.patient_id = patient_id
        code.assigned_by = user.id
        code.assigned_at = utcnow()
    db.commit()
    db.refresh(encounter)
    return encounter


def _create_underlying_encounter(
    request: Request,
    db: Session,
    user: User,
    patient_id: int,
    service_type: str,
    ccc_number: Optional[str],
    procedure_g_drg_code: Optional[str],
    procedure_name: Optional[str],
) -> dict:
    from app.api.patients import create_encounter

    return create_encounter(
        request=request,
        patient_id=patient_id,
        service_type=service_type,
        ccc_number=ccc_number,
        procedure_g_drg_code=procedure_g_drg_code,
        procedure_name=procedure_name,
        db=db,
        current_user=user,
        _module_check=user,
    )


@router.post("/codes/generate")
def generate_codes(
    payload: CodeGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(list(CODE_POOL_ROLES))),
):
    """Prepare a block of codes, for example SCRN0001 onward."""
    from app.services.confidential import format_code
    from app.core.audit import set_audit_summary

    _ready(db)
    try:
        values = [format_code(payload.prefix, payload.start + offset, payload.pad) for offset in range(payload.count)]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = {
        row.code
        for row in db.query(ConfidentialCode).filter(ConfidentialCode.code.in_(values)).all()
    }
    if existing:
        sample = ", ".join(sorted(existing)[:5])
        raise HTTPException(status_code=400, detail=f"These codes already exist: {sample}")

    created = []
    for value in values:
        row = ConfidentialCode(
            code=value,
            status="available",
            created_by=current_user.id,
            created_at=utcnow(),
        )
        db.add(row)
        created.append(value)
    db.commit()
    set_audit_summary(request, f"Prepared {len(created)} confidential codes ({created[0]} to {created[-1]}).")
    return {"created": len(created), "first": created[0], "last": created[-1], "codes": created}


@router.get("/codes")
def list_codes(
    status_filter: Optional[str] = "available",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(list(ISSUE_ROLES))),
):
    """Available codes for issuing a visit. Assigned codes with names are on the register."""
    _ready(db)
    query = db.query(ConfidentialCode)
    if status_filter:
        query = query.filter(ConfidentialCode.status == status_filter)
    rows = query.order_by(ConfidentialCode.code.asc()).limit(500).all()
    available = db.query(ConfidentialCode).filter(ConfidentialCode.status == "available").count()
    assigned = db.query(ConfidentialCode).filter(ConfidentialCode.status == "assigned").count()
    return {
        "available": available,
        "assigned": assigned,
        "codes": [
            {
                "id": row.id,
                "code": row.code,
                "status": row.status,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }


@router.post("/visits", status_code=status.HTTP_201_CREATED)
def issue_visit(
    payload: IssueVisitRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(list(ISSUE_ROLES))),
):
    """Give the next prepared code, or a chosen one, to this client for this visit."""
    from app.core.audit import set_audit_summary

    _ready(db)
    service_type = (payload.service_type or "").strip()
    if not service_type:
        raise HTTPException(status_code=400, detail="Service type is required")
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    code = _load_code(db, payload.code_id) if payload.code_id else _next_available(db)
    if code.status != "available" or code.patient_id:
        raise HTTPException(status_code=400, detail=f"{code.code} is already assigned")

    created = _create_underlying_encounter(
        request,
        db,
        current_user,
        patient.id,
        service_type,
        payload.ccc_number,
        payload.procedure_g_drg_code,
        payload.procedure_name,
    )
    encounter = _stamp_visit(db, created["encounter_id"], code, current_user, patient.id)
    set_audit_summary(request, f"Issued confidential code {code.code} for encounter {encounter.id}.")
    return {
        "code": code.code,
        "encounter_id": encounter.id,
        "patient_name": _patient_name(patient),
        "patient_card_number": patient.card_number,
        "service_type": encounter.department,
        "procedure_name": encounter.procedure_name,
        "procedure_g_drg_code": encounter.procedure_g_drg_code,
        "status": encounter.status,
        "forced_cash": created.get("forced_cash", False),
        "message": created.get("message") or f"Give {code.code} to the client for this visit.",
    }


@router.post("/follow-up", status_code=status.HTTP_201_CREATED)
def start_follow_up(
    payload: FollowUpRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(list(ISSUE_ROLES))),
):
    """Open another consultation on the same code."""
    from app.core.audit import set_audit_summary

    _ready(db)
    token = (payload.code or "").strip().upper()
    code = db.query(ConfidentialCode).filter(ConfidentialCode.code == token).first()
    if not code or code.status != "assigned" or not code.patient_id:
        raise HTTPException(status_code=404, detail="No client is assigned to that code")

    previous = (
        db.query(Encounter)
        .filter(Encounter.confidential_code_id == code.id, Encounter.archived == False)
        .order_by(Encounter.created_at.desc())
        .first()
    )
    service_type = (payload.service_type or (previous.department if previous else "") or "General").strip()
    created = _create_underlying_encounter(
        request,
        db,
        current_user,
        code.patient_id,
        service_type,
        payload.ccc_number,
        payload.procedure_g_drg_code,
        payload.procedure_name,
    )
    encounter = _stamp_visit(db, created["encounter_id"], code, current_user, code.patient_id)
    set_audit_summary(request, f"Opened confidential follow-up {encounter.id} on code {code.code}.")
    return {
        "code": code.code,
        "encounter_id": encounter.id,
        "service_type": encounter.department,
        "procedure_name": encounter.procedure_name,
        "procedure_g_drg_code": encounter.procedure_g_drg_code,
        "status": encounter.status,
        "forced_cash": created.get("forced_cash", False),
        "message": created.get("message") or f"Follow-up opened on {code.code}.",
    }


@router.get("/lookup")
def lookup_code(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Service-point lookup. Returns the code and its visits, not the client."""
    _ready(db)
    token = (code or "").strip().upper()
    if not token:
        raise HTTPException(status_code=400, detail="Enter a code")
    row = (
        db.query(ConfidentialCode)
        .filter(ConfidentialCode.code == token)
        .first()
    )
    if not row or row.status != "assigned":
        raise HTTPException(status_code=404, detail="No visit is assigned to that code")
    encounters = (
        db.query(Encounter)
        .options(joinedload(Encounter.code_link))
        .filter(Encounter.confidential_code_id == row.id, Encounter.archived == False)
        .order_by(Encounter.created_at.desc())
        .all()
    )
    return {
        "code": row.code,
        "encounters": [_encounter_brief(encounter) for encounter in encounters],
    }


@router.get("/register")
def confidential_register(
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(list(REGISTER_ROLES))),
):
    """Codes mapped to clients. Admin, Doctor, PA, and Claims only."""
    if not user_has_role(current_user, REGISTER_ROLES, db):
        raise HTTPException(status_code=403, detail="The confidential register is limited to Admin, Doctor, PA, and Claims")
    _ready(db)
    query = (
        db.query(ConfidentialCode)
        .options(joinedload(ConfidentialCode.patient))
        .filter(ConfidentialCode.status == "assigned", ConfidentialCode.patient_id.isnot(None))
    )
    rows = query.order_by(ConfidentialCode.assigned_at.desc()).all()
    needle = (search or "").strip().lower()
    result = []
    for row in rows:
        patient = row.patient
        if not patient:
            continue
        name = _patient_name(patient)
        if needle and needle not in row.code.lower() and needle not in name.lower() and needle not in (patient.card_number or "").lower():
            continue
        encounters = (
            db.query(Encounter)
            .options(joinedload(Encounter.code_link))
            .filter(Encounter.confidential_code_id == row.id, Encounter.archived == False)
            .order_by(Encounter.created_at.desc())
            .all()
        )
        result.append(
            {
                "code": row.code,
                "code_id": row.id,
                "assigned_at": row.assigned_at,
                "patient_id": patient.id,
                "patient_name": name,
                "patient_card_number": patient.card_number,
                "patient_insurance_id": patient.insurance_id,
                "patient_insured": bool(patient.insured),
                "patient_nhis_active": bool(patient.nhis_active),
                "encounters": [_encounter_brief(encounter) for encounter in encounters],
            }
        )
    return result
