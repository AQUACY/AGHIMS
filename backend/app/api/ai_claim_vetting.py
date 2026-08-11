"""
AI Claim Vetting API (Phase 1).

Optional module: ai_claims_vetting (default inactive).
Recommendations only — never silent overwrite of claim data.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.audit import create_audit_log, get_effective_creator_id
from app.core.database import SessionLocal, get_db
from app.core.datetime_utils import utcnow
from app.core.dependencies import require_module_permission, require_role
from app.models.ai_claim_vetting import AiClaimVettingFinding, AiClaimVettingJob, AiClaimVettingRule
from app.models.claim_xml_import import ClaimXmlImportBatch, ClaimXmlImportItem
from app.models.module_settings import ModuleSettings
from app.models.user import User
from app.services.ai_claim_vetting import analyze_claim_payload
from app.services.ai_claim_vetting.configurable_rules import (
    ALLOWED_OPS,
    ALLOWED_RULE_FIELDS,
    ensure_seed_rules,
)
from app.services.ai_claim_vetting.engine import normalize_analysis_mode
from app.services.nhia_exceptions import NhiaIntegrationError
from app.services.nhia_integration import lookup_member_by_hin
from app.utils.ghims_card import is_ghana_card, normalize_ghana_card

router = APIRouter(prefix="/ai-claim-vetting", tags=["ai-claim-vetting"])

MODULE_KEY = "ai_claims_vetting"
CLAIMS_ROLES = ["Claims", "Admin", "Doctor", "PA"]

RULE_LABELS = {
    "specialty_zoom": "ZOOM specialty → OPDC",
    "ghana_card_member_no": "Ghana Card Member No → HIN",
    "diagnosis_drg_mismatch": "Diagnosis GDRG mismatch",
    "diagnosis_icd_unmapped": "Diagnosis ICD unmapped",
    "procedure_drg_mismatch": "Procedure GDRG mismatch",
    "procedure_gdrg_unknown": "Procedure GDRG unknown",
    "medicine_code_unknown": "Medicine code unknown",
    "investigation_gdrg_unknown": "Investigation GDRG unknown",
    "member_no_leading_hyphen": "Member No leading hyphen",
    "member_no_length_not_8": "Member No length not 8",
    "hin_format_check": "HIN format check",
}


def _ensure_module_active(db: Session) -> ModuleSettings:
    module = (
        db.query(ModuleSettings)
        .filter(ModuleSettings.module_key == MODULE_KEY)
        .first()
    )
    if not module:
        raise HTTPException(
            status_code=403,
            detail="AI Claims Vetting module is not configured. Enable it under Module Management.",
        )
    if not module.is_active:
        raise HTTPException(
            status_code=403,
            detail="AI Claims Vetting is disabled for this facility. Enable it under Module Management.",
        )
    try:
        ensure_seed_rules(db)
    except Exception:
        db.rollback()
    return module


class SampleAnalyzeRequest(BaseModel):
    patient_id: Optional[str] = None
    diagnosis: Optional[str] = None
    medications: List[Any] = Field(default_factory=list)
    procedures: List[Any] = Field(default_factory=list)
    investigations: List[Any] = Field(default_factory=list)
    # Claim-shaped fields used by Phase-1 rules
    memberNo: Optional[str] = None
    member_no: Optional[str] = None
    hin: Optional[str] = None
    ghanaCard: Optional[str] = None
    specialtyAttended: Optional[str] = None
    specialty_attended: Optional[str] = None
    principalGDRG: Optional[str] = None
    claimID: Optional[str] = None
    diagnoses: Optional[List[Any]] = None
    medicines: Optional[List[Any]] = None
    persist: bool = False


class FindingDecisionRequest(BaseModel):
    decision: str  # accept | reject | edited
    note: Optional[str] = None
    otac: Optional[str] = None  # optional for Ghana Card → HIN NHIA lookup
    chosen_value: Optional[str] = None  # selected DRG/code when multiple options


class FindingResponse(BaseModel):
    id: int
    source_type: str
    source_id: Optional[int] = None
    claim_claim_id: Optional[str] = None
    job_id: Optional[int] = None
    rule_code: str
    finding: str
    severity: str
    explanation: Optional[str] = None
    recommendation: Optional[str] = None
    suggested_action: Optional[Dict[str, Any]] = None
    requires_human_review: bool
    provider: str
    status: str
    human_decision_note: Optional[str] = None
    decided_by_id: Optional[int] = None
    decided_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BatchAnalyzeRequest(BaseModel):
    """
    Empty item_ids:
    - include_finalized=False → all non-finalized in the batch (default)
    - include_finalized=True → every claim in the batch
    mode: phase1 | coding | thorough (standard accepted as coding alias)
    """
    item_ids: Optional[List[int]] = None
    include_finalized: bool = False
    mode: str = "phase1"


class LlmAssistRequest(BaseModel):
    """Selected claims only — local Ollama review (max 10)."""
    item_ids: List[int]
    note: Optional[str] = None


class BulkDecideRequest(BaseModel):
    finding_ids: List[int]
    decision: str  # accept | reject | edited
    note: Optional[str] = None
    otac: Optional[str] = None
    chosen_value: Optional[str] = None


class JobResponse(BaseModel):
    id: int
    batch_id: int
    status: str
    total_items: int
    processed_items: int
    findings_count: int
    item_ids: Optional[List[int]] = None
    analysis_mode: str = "phase1"
    error_message: Optional[str] = None
    summary_by_rule: Optional[Dict[str, int]] = None
    started_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_pct: float = 0.0

    class Config:
        from_attributes = True


class ReportFindingRow(BaseModel):
    id: int
    source_id: Optional[int] = None
    claim_claim_id: Optional[str] = None
    client_name: str = ""
    member_no: str = ""
    specialty_attended: str = ""
    hospital_rec_no: str = ""
    rule_code: str
    finding: str
    severity: str
    explanation: Optional[str] = None
    recommendation: Optional[str] = None
    suggested_action: Optional[Dict[str, Any]] = None
    status: str
    item_status: Optional[str] = None


class ReportGroup(BaseModel):
    rule_code: str
    label: str
    pending_count: int
    findings: List[ReportFindingRow] = Field(default_factory=list)


class BatchReportResponse(BaseModel):
    batch_id: int
    pending_total: int
    groups: List[ReportGroup] = Field(default_factory=list)
    latest_job: Optional[JobResponse] = None


class AnalyzeResponse(BaseModel):
    provider: str
    summary: str
    claim_claim_id: Optional[str] = None
    findings: List[FindingResponse] = Field(default_factory=list)
    preview_findings: List[Dict[str, Any]] = Field(default_factory=list)


class VettingStatusResponse(BaseModel):
    module_active: bool
    provider: str
    model: Optional[str] = None
    ollama_base_url: Optional[str] = None
    ollama_online: bool = False
    human_approval_required: bool = True
    screen_path: str = "/claims/ai-vetting"


def _client_name_from_payload(payload: Optional[Dict[str, Any]]) -> str:
    p = payload or {}
    parts = [str(p.get("otherNames") or "").strip(), str(p.get("surname") or "").strip()]
    return " ".join(x for x in parts if x) or ""


def _ollama_reachable(base_url: str, timeout: float = 2.0) -> bool:
    try:
        import urllib.request

        req = urllib.request.Request(f"{(base_url or '').rstrip('/')}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


@router.get("/status", response_model=VettingStatusResponse)
def get_vetting_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """
    Facility AI vetting posture for the Intelligence workspace.
    Safe to call when the optional module is off — returns module_active=false.
    """
    from app.core.config import settings

    module = (
        db.query(ModuleSettings)
        .filter(ModuleSettings.module_key == MODULE_KEY)
        .first()
    )
    module_active = bool(module and module.is_active)
    provider = (getattr(settings, "AI_CLAIM_VETTING_PROVIDER", "rules") or "rules").lower()
    model = getattr(settings, "OLLAMA_MODEL", None) if provider == "ollama" else None
    base_url = getattr(settings, "OLLAMA_BASE_URL", None) if provider == "ollama" else None
    online = _ollama_reachable(base_url) if provider == "ollama" and base_url else False

    return VettingStatusResponse(
        module_active=module_active,
        provider=provider,
        model=model,
        ollama_base_url=base_url,
        ollama_online=online,
        human_approval_required=True,
        screen_path="/claims/ai-local-assist" if provider == "ollama" else "/claims/ai-vetting",
    )


def _job_response(job: AiClaimVettingJob) -> JobResponse:
    total = int(job.total_items or 0)
    processed = int(job.processed_items or 0)
    pct = round((processed / total) * 100, 1) if total else (100.0 if job.status == "completed" else 0.0)
    return JobResponse(
        id=job.id,
        batch_id=job.batch_id,
        status=job.status,
        total_items=total,
        processed_items=processed,
        findings_count=int(job.findings_count or 0),
        item_ids=job.item_ids,
        analysis_mode=getattr(job, "analysis_mode", None) or "phase1",
        error_message=job.error_message,
        summary_by_rule=job.summary_by_rule,
        started_by_id=job.started_by_id,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        progress_pct=pct,
    )


def _finding_to_dict(f: AiClaimVettingFinding) -> Dict[str, Any]:
    return FindingResponse.model_validate(f).model_dump()


def _persist_findings(
    db: Session,
    *,
    result,
    source_type: str,
    source_id: Optional[int],
    user: Optional[User] = None,
    creator_id: Optional[int] = None,
    job_id: Optional[int] = None,
    replace_pending: bool = True,
    commit: bool = True,
    replace_scope: Optional[str] = None,
) -> List[AiClaimVettingFinding]:
    """Save new findings; optionally supersede open pending ones for same source+rule.

    replace_scope:
      - "llm" → only clear/replace pending llm_* findings (local AI assist)
      - "rules" → only clear/replace non-llm pending findings (phase scans)
      - None → legacy behaviour (all pending for source)
    """
    if creator_id is None:
        if user is None:
            raise ValueError("user or creator_id required")
        creator_id = get_effective_creator_id(db, user)
    saved: List[AiClaimVettingFinding] = []

    if replace_pending and source_id is not None:
        existing = (
            db.query(AiClaimVettingFinding)
            .filter(
                AiClaimVettingFinding.source_type == source_type,
                AiClaimVettingFinding.source_id == source_id,
                AiClaimVettingFinding.status == "pending",
            )
            .all()
        )
        new_codes = {f.rule_code for f in result.findings}

        def _in_scope(code: str) -> bool:
            is_llm = str(code or "").startswith("llm_")
            if replace_scope == "llm":
                return is_llm
            if replace_scope == "rules":
                return not is_llm
            return True

        for row in existing:
            if not _in_scope(row.rule_code):
                continue
            if row.rule_code in new_codes:
                db.delete(row)
            else:
                row.status = "rejected"
                row.human_decision_note = "Cleared on re-analysis (issue no longer present)."
                row.decided_by_id = creator_id
                row.decided_at = utcnow()

    for f in result.findings:
        row = AiClaimVettingFinding(
            source_type=source_type,
            source_id=source_id,
            claim_claim_id=result.claim_claim_id,
            job_id=job_id,
            rule_code=f.rule_code,
            finding=f.finding,
            severity=f.severity,
            explanation=f.explanation,
            recommendation=f.recommendation,
            suggested_action=f.suggested_action.model_dump() if f.suggested_action else None,
            requires_human_review=f.requires_human_review,
            provider=result.provider,
            status="pending",
            created_by_id=creator_id,
        )
        db.add(row)
        saved.append(row)

    if commit:
        db.commit()
        for row in saved:
            db.refresh(row)
    return saved


def _reopen_ghims_item_if_finalized(item: ClaimXmlImportItem) -> bool:
    """
    Reopen a finalized GHIMS import item so AI corrections can apply.
    Lands on ai_vetted (exportable) — not draft — so claims stay in the export pipeline.
    Returns True if reopened from finalized.
    """
    if (item.status or "").strip().lower() != "finalized":
        return False
    item.status = "ai_vetted"
    item.finalized_at = None
    return True


def _mark_item_ai_vetted(item: ClaimXmlImportItem) -> None:
    """After AI correction / reopen, keep claim exportable (not draft)."""
    status = (item.status or "").strip().lower()
    if status == "finalized":
        return
    if status == "draft" or status in ("", "flagged"):
        item.status = "ai_vetted"
    elif status not in (
        "ai_vetted",
        "pharmacy_vetted",
        "doctor_vetted",
        "vetted",
    ):
        item.status = "ai_vetted"


def _save_item_payload(db: Session, item: ClaimXmlImportItem, payload: Dict[str, Any]) -> Dict[str, Any]:
    item.payload = payload
    flag_modified(item, "payload")
    db.add(item)
    db.commit()
    db.refresh(item)
    return payload


def _apply_suggested_action(
    db: Session,
    item: ClaimXmlImportItem,
    finding: AiClaimVettingFinding,
    *,
    otac: Optional[str] = None,
    chosen_value: Optional[str] = None,
) -> tuple[Dict[str, Any], bool]:
    """
    Apply an accepted suggestion to the GHIMS import payload and persist.
    Auto-reopens finalized items first. Returns (payload, reopened).
    """
    reopened = _reopen_ghims_item_if_finalized(item)
    if reopened:
        db.add(item)
        db.commit()
        db.refresh(item)

    payload = dict(item.payload or {})
    action = finding.suggested_action or {}
    action_type = (action.get("type") or "").strip()
    details = action.get("details") or {}
    field = (action.get("field") or details.get("field") or "").strip()

    if action_type == "set_specialty":
        value = (chosen_value or action.get("value") or "OPDC").strip().upper()
        payload["specialtyAttended"] = value
        _mark_item_ai_vetted(item)
        return _save_item_payload(db, item, payload), reopened

    if action_type == "set_field":
        if not field:
            raise HTTPException(status_code=400, detail="Missing field on set_field suggestion.")
        if field not in ALLOWED_RULE_FIELDS:
            raise HTTPException(status_code=400, detail=f"Field '{field}' is not allowed.")
        value = chosen_value if chosen_value is not None else action.get("value")
        if value is None:
            value = details.get("value")
        payload[field] = "" if value is None else str(value)
        _mark_item_ai_vetted(item)
        return _save_item_payload(db, item, payload), reopened

    if action_type == "strip_prefix":
        if not field:
            raise HTTPException(status_code=400, detail="Missing field on strip_prefix suggestion.")
        if field not in ALLOWED_RULE_FIELDS:
            raise HTTPException(status_code=400, detail=f"Field '{field}' is not allowed.")
        prefix = str(action.get("value") or details.get("prefix") or "-")
        current = str(payload.get(field) or "")
        while current.startswith(prefix):
            current = current[len(prefix) :]
        payload[field] = current.strip()
        _mark_item_ai_vetted(item)
        return _save_item_payload(db, item, payload), reopened

    if action_type == "trim_field":
        if not field:
            raise HTTPException(status_code=400, detail="Missing field on trim_field suggestion.")
        if field not in ALLOWED_RULE_FIELDS:
            raise HTTPException(status_code=400, detail=f"Field '{field}' is not allowed.")
        payload[field] = str(payload.get(field) or "").strip()
        _mark_item_ai_vetted(item)
        return _save_item_payload(db, item, payload), reopened

    if action_type == "set_diagnosis_gdrg":
        idx = details.get("index")
        if idx is None:
            raise HTTPException(status_code=400, detail="Missing diagnosis index on suggestion.")
        value = (chosen_value or action.get("value") or details.get("preferred") or "").strip()
        if not value:
            raise HTTPException(
                status_code=400,
                detail="Choose a GDRG from the suggested list before accepting.",
            )
        allowed = details.get("allowed_drgs") or []
        allowed_codes = {
            str(a.get("drg_code") or "").strip().upper()
            for a in allowed
            if isinstance(a, dict)
        }
        if allowed_codes and value.upper() not in allowed_codes:
            raise HTTPException(
                status_code=400,
                detail=f"GDRG '{value}' is not in the allowed mapped list for this ICD-10.",
            )
        diagnoses = list(payload.get("diagnoses") or [])
        if not (0 <= int(idx) < len(diagnoses)) or not isinstance(diagnoses[int(idx)], dict):
            raise HTTPException(status_code=400, detail="Diagnosis row not found on claim.")
        diagnoses[int(idx)] = dict(diagnoses[int(idx)])
        diagnoses[int(idx)]["gdrgCode"] = value
        payload["diagnoses"] = diagnoses
        if details.get("sync_principal"):
            principal = (payload.get("principalGDRG") or "").strip().upper()
            current = (details.get("current_gdrg") or "").strip().upper()
            if not principal or principal == current:
                payload["principalGDRG"] = value
        _mark_item_ai_vetted(item)
        return _save_item_payload(db, item, payload), reopened

    if action_type == "set_procedure_gdrg":
        idx = details.get("index")
        if idx is None:
            raise HTTPException(status_code=400, detail="Missing procedure index on suggestion.")
        value = (chosen_value or action.get("value") or details.get("preferred") or "").strip()
        if not value:
            raise HTTPException(
                status_code=400,
                detail="Choose a GDRG from the suggested list before accepting.",
            )
        allowed = details.get("allowed_drgs") or []
        allowed_codes = {
            str(a.get("drg_code") or "").strip().upper()
            for a in allowed
            if isinstance(a, dict)
        }
        if allowed_codes and value.upper() not in allowed_codes:
            raise HTTPException(
                status_code=400,
                detail=f"GDRG '{value}' is not in the allowed mapped list for this ICD-10.",
            )
        procedures = list(payload.get("procedures") or [])
        if not (0 <= int(idx) < len(procedures)) or not isinstance(procedures[int(idx)], dict):
            raise HTTPException(status_code=400, detail="Procedure row not found on claim.")
        procedures[int(idx)] = dict(procedures[int(idx)])
        procedures[int(idx)]["gdrgCode"] = value
        payload["procedures"] = procedures
        _mark_item_ai_vetted(item)
        return _save_item_payload(db, item, payload), reopened

    if action_type in (
        "review_diagnosis_codes",
        "review_procedure_gdrg",
        "review_medicine_code",
        "review_investigation_gdrg",
        "review_only",
        "review_member",
        "review_diagnosis",
        "review_procedure",
        "review_medicine",
        "review_investigation",
        "review_claim",
    ) or str(finding.rule_code or "").startswith("llm_"):
        # Human supplied a corrected value → apply it (e.g. Member No length fix).
        if chosen_value is not None and str(chosen_value).strip() != "":
            target_field = field or "memberNo"
            if target_field not in ALLOWED_RULE_FIELDS:
                raise HTTPException(status_code=400, detail=f"Field '{target_field}' is not allowed.")
            payload[target_field] = str(chosen_value).strip()
            _mark_item_ai_vetted(item)
            return _save_item_payload(db, item, payload), reopened
        raise HTTPException(
            status_code=400,
            detail=(
                "This finding needs a corrected value (or use Mark edited). "
                "Enter the correct Member No / field value, then Accept — "
                "finalized claims reopen as ai_vetted and stay exportable."
            ),
        )

    if action_type == "apply_existing_hin":
        hin = (action.get("value") or payload.get("hin") or "").strip()
        if not hin or is_ghana_card(hin):
            raise HTTPException(status_code=400, detail="No usable HIN available to apply.")
        ghana = normalize_ghana_card(payload.get("ghanaCard") or payload.get("memberNo") or "")
        if ghana and is_ghana_card(ghana):
            payload["ghanaCard"] = ghana
        payload["hin"] = hin
        payload["memberNo"] = hin
        _mark_item_ai_vetted(item)
        return _save_item_payload(db, item, payload), reopened

    if action_type == "convert_ghana_card_to_hin":
        ghana_card = normalize_ghana_card(
            (action.get("details") or {}).get("ghana_card")
            or payload.get("ghanaCard")
            or payload.get("memberNo")
            or ""
        )
        if not ghana_card or not is_ghana_card(ghana_card):
            raise HTTPException(
                status_code=400,
                detail="Member number is not a Ghana Card (expected format GHA-xxxxxxxx-x).",
            )
        try:
            data = lookup_member_by_hin(ghana_card, otac=otac)
        except NhiaIntegrationError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        hin = (data.hin or "").strip()
        if not hin or is_ghana_card(hin):
            raise HTTPException(
                status_code=400,
                detail="NHIA did not return a usable HIN for this Ghana Card.",
            )
        payload["ghanaCard"] = ghana_card
        payload["hin"] = hin
        payload["memberNo"] = hin
        _mark_item_ai_vetted(item)
        return _save_item_payload(db, item, payload), reopened

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported suggested action type: {action_type or '(none)'}",
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_sample(
    body: SampleAnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """
    Sample/prototype endpoint: analyze arbitrary claim-like JSON.
    Does not modify any patient or claim records.
    """
    _ensure_module_active(db)

    payload = body.model_dump(exclude_none=True)
    payload.pop("persist", None)
    # Map sample clinical fields into a shape rules can ignore safely
    if body.diagnosis and not payload.get("diagnoses"):
        payload["diagnoses"] = [{"diagnosis": body.diagnosis}]
    if body.medications and not payload.get("medicines"):
        payload["medicines"] = body.medications

    result = analyze_claim_payload(payload, db=db, mode="phase1")
    preview = [f.model_dump() for f in result.findings]

    saved: List[AiClaimVettingFinding] = []
    if body.persist and result.findings:
        saved = _persist_findings(
            db,
            result=result,
            source_type="sample",
            source_id=None,
            user=current_user,
            replace_pending=False,
        )
        create_audit_log(
            db,
            current_user,
            action="AI_VET_ANALYZE",
            resource_type="AiClaimVetting",
            details={"source_type": "sample", "finding_count": len(saved)},
            summary=f"AI claim vetting sample analyze: {len(saved)} finding(s)",
        )

    return AnalyzeResponse(
        provider=result.provider,
        summary=result.summary,
        claim_claim_id=result.claim_claim_id,
        findings=[FindingResponse.model_validate(r) for r in saved],
        preview_findings=preview,
    )


@router.post("/ghims-items/{item_id}/analyze", response_model=AnalyzeResponse)
def analyze_ghims_item(
    item_id: int,
    mode: str = "phase1",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """Analyze a GHIMS imported claim payload and persist pending findings."""
    _ensure_module_active(db)

    analysis_mode = normalize_analysis_mode(mode)
    if (mode or "").strip().lower() not in ("", "phase1", "coding", "standard", "thorough"):
        raise HTTPException(
            status_code=400,
            detail="mode must be phase1, coding, or thorough.",
        )

    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")

    result = analyze_claim_payload(item.payload or {}, db=db, mode=analysis_mode)
    if not result.claim_claim_id:
        result.claim_claim_id = item.claim_claim_id

    saved = _persist_findings(
        db,
        result=result,
        source_type="ghims_import",
        source_id=item.id,
        user=current_user,
        replace_pending=True,
    )
    create_audit_log(
        db,
        current_user,
        action="AI_VET_ANALYZE",
        resource_type="ClaimXmlImportItem",
        resource_id=item.id,
        details={"finding_count": len(saved), "provider": result.provider},
        summary=f"AI vetted GHIMS claim {item.claim_claim_id}: {len(saved)} finding(s)",
    )

    return AnalyzeResponse(
        provider=result.provider,
        summary=result.summary,
        claim_claim_id=result.claim_claim_id or item.claim_claim_id,
        findings=[FindingResponse.model_validate(r) for r in saved],
        preview_findings=[f.model_dump() for f in result.findings],
    )


@router.get("/ghims-items/{item_id}/findings", response_model=List[FindingResponse])
def list_ghims_item_findings(
    item_id: int,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """List AI findings for a GHIMS import item."""
    _ensure_module_active(db)

    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")

    q = db.query(AiClaimVettingFinding).filter(
        AiClaimVettingFinding.source_type == "ghims_import",
        AiClaimVettingFinding.source_id == item_id,
    )
    if status_filter:
        q = q.filter(AiClaimVettingFinding.status == status_filter)
    rows = q.order_by(AiClaimVettingFinding.created_at.desc()).all()
    return [FindingResponse.model_validate(r) for r in rows]


@router.post("/findings/{finding_id}/decide")
def decide_finding(
    finding_id: int,
    body: FindingDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "update")),
):
    """
    Human reviewer decision on an AI recommendation.
    accept → apply suggested correction (when applicable) then mark accepted.
    reject / edited → record decision only (edited = human fixed manually).
    """
    _ensure_module_active(db)

    decision = (body.decision or "").strip().lower()
    if decision not in ("accept", "reject", "edited"):
        raise HTTPException(status_code=400, detail="decision must be accept, reject, or edited.")

    finding = (
        db.query(AiClaimVettingFinding)
        .filter(AiClaimVettingFinding.id == finding_id)
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")
    if finding.status != "pending":
        raise HTTPException(status_code=400, detail=f"Finding already decided ({finding.status}).")

    updated_payload = None
    reopened = False
    item_status = None
    if decision == "accept":
        if finding.source_type == "ghims_import" and finding.source_id:
            item = (
                db.query(ClaimXmlImportItem)
                .filter(ClaimXmlImportItem.id == finding.source_id)
                .first()
            )
            if not item:
                raise HTTPException(status_code=404, detail="Imported claim not found.")
            updated_payload, reopened = _apply_suggested_action(
                db,
                item,
                finding,
                otac=body.otac,
                chosen_value=body.chosen_value,
            )
            item_status = item.status
        else:
            raise HTTPException(
                status_code=400,
                detail="Accept is only supported for GHIMS imported claims in Phase 1.",
            )
    elif decision == "edited" and finding.source_type == "ghims_import" and finding.source_id:
        # Reopen finalized claims so officers can fix review-only issues; keep exportable.
        item = (
            db.query(ClaimXmlImportItem)
            .filter(ClaimXmlImportItem.id == finding.source_id)
            .first()
        )
        if item:
            reopened = _reopen_ghims_item_if_finalized(item)
            _mark_item_ai_vetted(item)
            db.add(item)
            db.commit()
            db.refresh(item)
            item_status = item.status
            updated_payload = dict(item.payload or {})

    creator_id = get_effective_creator_id(db, current_user)
    finding.status = "accepted" if decision == "accept" else decision
    finding.human_decision_note = (body.note or "").strip() or None
    finding.decided_by_id = creator_id
    finding.decided_at = utcnow()
    db.add(finding)
    db.commit()
    db.refresh(finding)

    create_audit_log(
        db,
        current_user,
        action="AI_VET_DECIDE",
        resource_type="AiClaimVettingFinding",
        resource_id=finding.id,
        details={
            "decision": finding.status,
            "rule_code": finding.rule_code,
            "source_type": finding.source_type,
            "source_id": finding.source_id,
            "reopened": reopened,
            "item_status": item_status,
        },
        summary=f"AI vetting finding #{finding.id} {finding.status} ({finding.rule_code})",
    )

    if decision == "accept":
        message = (
            "Correction applied. Claim reopened as ai_vetted (exportable)."
            if reopened
            else "Recommendation accepted and applied (status: ai_vetted)."
        )
    elif decision == "edited":
        message = (
            "Marked edited. Claim reopened as ai_vetted so you can fix and export."
            if reopened
            else "Recommendation marked as edited."
        )
    else:
        message = f"Recommendation marked as {finding.status}."

    return {
        "success": True,
        "finding": FindingResponse.model_validate(finding).model_dump(),
        "payload": updated_payload,
        "reopened": reopened,
        "item_status": item_status,
        "message": message,
    }


def _try_apply_suggested_action(
    db: Session,
    item: ClaimXmlImportItem,
    finding: AiClaimVettingFinding,
    *,
    otac: Optional[str] = None,
    chosen_value: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[Dict[str, Any]], bool]:
    """Like _apply_suggested_action but returns (ok, error, payload, reopened)."""
    try:
        payload, reopened = _apply_suggested_action(
            db, item, finding, otac=otac, chosen_value=chosen_value
        )
        return True, None, payload, reopened
    except HTTPException as exc:
        detail = exc.detail
        if isinstance(detail, list):
            detail = "; ".join(str(x) for x in detail)
        return False, str(detail), None, False
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), None, False


def _run_batch_analyze_job(job_id: int, creator_id: int) -> None:
    """Background worker: analyze selected GHIMS items and persist findings."""
    from app.core.config import settings

    db = SessionLocal()
    try:
        job = db.query(AiClaimVettingJob).filter(AiClaimVettingJob.id == job_id).first()
        if not job:
            return
        job.status = "running"
        job.started_at = utcnow()
        job.processed_items = 0
        job.findings_count = 0
        db.commit()

        item_ids = list(job.item_ids or [])
        analysis_mode = (getattr(job, "analysis_mode", None) or "standard").strip().lower()
        summary: Dict[str, int] = {}
        findings_total = 0

        # Batch phase jobs stay on rules. Dedicated llm jobs use ollama_assist.
        if analysis_mode == "llm":
            provider_name = "ollama_assist"
        else:
            use_llm = bool(getattr(settings, "AI_CLAIM_VETTING_BATCH_USE_LLM", False))
            provider_name = None if use_llm else "rules"

        for item_id in item_ids:
            item = (
                db.query(ClaimXmlImportItem)
                .filter(ClaimXmlImportItem.id == item_id)
                .first()
            )
            if not item:
                job.processed_items = int(job.processed_items or 0) + 1
                db.commit()
                continue

            try:
                result = analyze_claim_payload(
                    item.payload or {},
                    db=db,
                    mode=analysis_mode,
                    provider_name=provider_name,
                )
            except Exception as item_exc:  # noqa: BLE001
                # Never stall the whole batch on one claim / LLM hang.
                job.processed_items = int(job.processed_items or 0) + 1
                job.error_message = (
                    f"Skipped item {item_id}: {str(item_exc)[:500]}"
                )[:2000]
                db.add(job)
                db.commit()
                continue

            if not result.claim_claim_id:
                result.claim_claim_id = item.claim_claim_id

            saved = _persist_findings(
                db,
                result=result,
                source_type="ghims_import",
                source_id=item.id,
                creator_id=creator_id,
                job_id=job.id,
                replace_pending=True,
                commit=True,
                replace_scope="llm" if analysis_mode == "llm" else "rules",
            )
            findings_total += len(saved)
            for row in saved:
                summary[row.rule_code] = summary.get(row.rule_code, 0) + 1

            job.processed_items = int(job.processed_items or 0) + 1
            job.findings_count = findings_total
            job.summary_by_rule = dict(summary)
            db.add(job)
            db.commit()

        job.status = "completed"
        job.completed_at = utcnow()
        job.findings_count = findings_total
        job.summary_by_rule = summary
        db.add(job)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        try:
            job = db.query(AiClaimVettingJob).filter(AiClaimVettingJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:2000]
                job.completed_at = utcnow()
                db.add(job)
                db.commit()
        except Exception:
            db.rollback()
    finally:
        db.close()


@router.post("/batches/{batch_id}/analyze", response_model=JobResponse)
def start_batch_analyze(
    batch_id: int,
    body: BatchAnalyzeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """
    Start a background AI vetting job for selected claims (or all / all non-finalized in the batch).
    Poll GET /jobs/{job_id} until completed, then use GET /batches/{batch_id}/report.
    """
    _ensure_module_active(db)

    batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found.")

    running = (
        db.query(AiClaimVettingJob)
        .filter(
            AiClaimVettingJob.batch_id == batch_id,
            AiClaimVettingJob.status.in_(("queued", "running")),
        )
        .first()
    )
    if running:
        raise HTTPException(
            status_code=409,
            detail=f"A vetting job is already {running.status} for this batch (job #{running.id}).",
        )

    q = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.batch_id == batch_id)
    requested = [int(x) for x in (body.item_ids or []) if x is not None]
    if requested:
        q = q.filter(ClaimXmlImportItem.id.in_(requested))
    elif not body.include_finalized:
        q = q.filter(ClaimXmlImportItem.status != "finalized")

    items = q.order_by(ClaimXmlImportItem.row_index.asc(), ClaimXmlImportItem.id.asc()).all()
    if requested:
        found = {i.id for i in items}
        missing = [i for i in requested if i not in found]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Item id(s) not in this batch: {missing[:10]}",
            )
    if not items:
        raise HTTPException(status_code=400, detail="No claims to analyze in this selection.")

    raw_mode = (body.mode or "phase1").strip().lower()
    if raw_mode not in ("phase1", "coding", "standard", "thorough"):
        raise HTTPException(
            status_code=400,
            detail="mode must be phase1, coding, or thorough.",
        )
    analysis_mode = normalize_analysis_mode(raw_mode)
    if analysis_mode == "thorough":
        if not requested:
            raise HTTPException(
                status_code=400,
                detail="Thorough mode requires selecting specific claim(s) (e.g. 1–2) to validate AI carefully.",
            )
        if len(items) > 10:
            raise HTTPException(
                status_code=400,
                detail="Thorough mode is limited to 10 claims at a time. Select fewer claims to assign.",
            )

    creator_id = get_effective_creator_id(db, current_user)
    item_ids = [i.id for i in items]
    job = AiClaimVettingJob(
        batch_id=batch_id,
        status="queued",
        total_items=len(item_ids),
        processed_items=0,
        findings_count=0,
        item_ids=item_ids,
        analysis_mode=analysis_mode,
        started_by_id=creator_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    create_audit_log(
        db,
        current_user,
        action="AI_VET_BATCH_START",
        resource_type="ClaimXmlImportBatch",
        resource_id=batch_id,
        details={
            "job_id": job.id,
            "item_count": len(item_ids),
            "analysis_mode": analysis_mode,
        },
        summary=(
            f"Started AI vetting job #{job.id} ({analysis_mode}) on {len(item_ids)} claim(s)"
        ),
    )

    background_tasks.add_task(_run_batch_analyze_job, job.id, creator_id)
    return _job_response(job)


@router.post("/batches/{batch_id}/llm-assist", response_model=JobResponse)
def start_llm_assist(
    batch_id: int,
    body: LlmAssistRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """
    Run local Ollama review on selected claims only (max 10).
    Separate from Phase 1 / Coding / Thorough rules scans.
    """
    from app.core.config import settings

    _ensure_module_active(db)

    batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found.")

    provider = (getattr(settings, "AI_CLAIM_VETTING_PROVIDER", "rules") or "rules").lower()
    if provider != "ollama":
        raise HTTPException(
            status_code=400,
            detail="Local AI assist requires AI_CLAIM_VETTING_PROVIDER=ollama in the backend .env.",
        )
    base_url = getattr(settings, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    if not _ollama_reachable(base_url):
        raise HTTPException(
            status_code=503,
            detail="Local AI (Ollama) is offline. Start Ollama, then try again.",
        )

    requested = [int(x) for x in (body.item_ids or []) if x is not None]
    if not requested:
        raise HTTPException(status_code=400, detail="Select at least one claim for local AI review.")
    if len(requested) > 10:
        raise HTTPException(
            status_code=400,
            detail="Local AI assist is limited to 10 claims at a time (each takes ~30–90s).",
        )

    running = (
        db.query(AiClaimVettingJob)
        .filter(
            AiClaimVettingJob.batch_id == batch_id,
            AiClaimVettingJob.status.in_(("queued", "running")),
        )
        .first()
    )
    if running:
        raise HTTPException(
            status_code=409,
            detail=f"A vetting job is already {running.status} for this batch (job #{running.id}).",
        )

    items = (
        db.query(ClaimXmlImportItem)
        .filter(
            ClaimXmlImportItem.batch_id == batch_id,
            ClaimXmlImportItem.id.in_(requested),
        )
        .order_by(ClaimXmlImportItem.row_index.asc(), ClaimXmlImportItem.id.asc())
        .all()
    )
    found = {i.id for i in items}
    missing = [i for i in requested if i not in found]
    if missing:
        raise HTTPException(status_code=400, detail=f"Item id(s) not in this batch: {missing[:10]}")
    if not items:
        raise HTTPException(status_code=400, detail="No claims to review.")

    creator_id = get_effective_creator_id(db, current_user)
    item_ids = [i.id for i in items]
    job = AiClaimVettingJob(
        batch_id=batch_id,
        status="queued",
        total_items=len(item_ids),
        processed_items=0,
        findings_count=0,
        item_ids=item_ids,
        analysis_mode="llm",
        started_by_id=creator_id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    create_audit_log(
        db=db,
        user=current_user,
        action="ai_claim_vetting_llm_assist",
        resource_type="claim_xml_import_batch",
        resource_id=batch_id,
        details={
            "job_id": job.id,
            "item_ids": item_ids,
            "model": getattr(settings, "OLLAMA_MODEL", None),
            "note": (body.note or "")[:200] or None,
        },
        summary=f"Started local AI assist job #{job.id} on {len(item_ids)} claim(s)",
    )

    background_tasks.add_task(_run_batch_analyze_job, job.id, creator_id)
    return _job_response(job)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    _ensure_module_active(db)
    job = db.query(AiClaimVettingJob).filter(AiClaimVettingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Vetting job not found.")
    return _job_response(job)


@router.get("/batches/{batch_id}/jobs/latest", response_model=Optional[JobResponse])
def get_latest_batch_job(
    batch_id: int,
    mode: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    _ensure_module_active(db)
    q = db.query(AiClaimVettingJob).filter(AiClaimVettingJob.batch_id == batch_id)
    if mode:
        mode_n = normalize_analysis_mode(mode)
        q = q.filter(AiClaimVettingJob.analysis_mode == mode_n)
    job = q.order_by(AiClaimVettingJob.id.desc()).first()
    return _job_response(job) if job else None


@router.get("/batches/{batch_id}/report", response_model=BatchReportResponse)
def get_batch_report(
    batch_id: int,
    status_filter: str = "pending",
    scope: str = "rules",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """Grouped AI findings for a GHIMS import batch (claim-list style report).

    scope: rules (default, phase lanes) | llm (local AI assist) | all
    """
    _ensure_module_active(db)

    batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found.")

    scope_n = (scope or "rules").strip().lower()
    if scope_n not in ("rules", "llm", "all"):
        raise HTTPException(status_code=400, detail="scope must be rules, llm, or all.")

    item_ids = [
        r[0]
        for r in db.query(ClaimXmlImportItem.id)
        .filter(ClaimXmlImportItem.batch_id == batch_id)
        .all()
    ]
    if not item_ids:
        latest_q = db.query(AiClaimVettingJob).filter(AiClaimVettingJob.batch_id == batch_id)
        if scope_n == "llm":
            latest_q = latest_q.filter(AiClaimVettingJob.analysis_mode == "llm")
        elif scope_n == "rules":
            latest_q = latest_q.filter(AiClaimVettingJob.analysis_mode != "llm")
        latest = latest_q.order_by(AiClaimVettingJob.id.desc()).first()
        return BatchReportResponse(
            batch_id=batch_id,
            pending_total=0,
            groups=[],
            latest_job=_job_response(latest) if latest else None,
        )

    q = db.query(AiClaimVettingFinding).filter(
        AiClaimVettingFinding.source_type == "ghims_import",
        AiClaimVettingFinding.source_id.in_(item_ids),
    )
    if status_filter:
        q = q.filter(AiClaimVettingFinding.status == status_filter)
    findings = q.order_by(
        AiClaimVettingFinding.rule_code.asc(),
        AiClaimVettingFinding.claim_claim_id.asc(),
        AiClaimVettingFinding.id.asc(),
    ).all()

    if scope_n == "llm":
        findings = [f for f in findings if str(f.rule_code or "").startswith("llm_")]
    elif scope_n == "rules":
        findings = [f for f in findings if not str(f.rule_code or "").startswith("llm_")]

    items_by_id = {}
    source_ids = {f.source_id for f in findings if f.source_id}
    if source_ids:
        items_by_id = {
            i.id: i
            for i in db.query(ClaimXmlImportItem)
            .filter(ClaimXmlImportItem.id.in_(source_ids))
            .all()
        }

    grouped: Dict[str, List[ReportFindingRow]] = {}
    for f in findings:
        item = items_by_id.get(f.source_id) if f.source_id else None
        payload = (item.payload if item else None) or {}
        row = ReportFindingRow(
            id=f.id,
            source_id=f.source_id,
            claim_claim_id=f.claim_claim_id or (item.claim_claim_id if item else None),
            client_name=_client_name_from_payload(payload),
            member_no=str(payload.get("memberNo") or ""),
            specialty_attended=str(payload.get("specialtyAttended") or ""),
            hospital_rec_no=str(payload.get("hospitalRecNo") or ""),
            rule_code=f.rule_code,
            finding=f.finding,
            severity=f.severity,
            explanation=f.explanation,
            recommendation=f.recommendation,
            suggested_action=f.suggested_action,
            status=f.status,
            item_status=item.status if item else None,
        )
        grouped.setdefault(f.rule_code, []).append(row)

    custom_labels = {
        r.rule_code: r.name
        for r in db.query(AiClaimVettingRule.rule_code, AiClaimVettingRule.name).all()
    }

    def _label_for(code: str) -> str:
        if RULE_LABELS.get(code):
            return RULE_LABELS[code]
        if custom_labels.get(code):
            return custom_labels[code]
        if str(code).startswith("llm_"):
            pretty = (
                str(code)
                .replace("llm_review_", "")
                .replace("llm_", "")
                .replace("_", " ")
                .strip()
            )
            return pretty.title() if pretty else "Local AI review"
        return code

    groups = [
        ReportGroup(
            rule_code=code,
            label=_label_for(code),
            pending_count=len(rows),
            findings=rows,
        )
        for code, rows in grouped.items()
    ]
    groups.sort(key=lambda g: (-g.pending_count, g.label))

    latest_q = db.query(AiClaimVettingJob).filter(AiClaimVettingJob.batch_id == batch_id)
    if scope_n == "llm":
        latest_q = latest_q.filter(AiClaimVettingJob.analysis_mode == "llm")
    elif scope_n == "rules":
        latest_q = latest_q.filter(AiClaimVettingJob.analysis_mode != "llm")
    latest = latest_q.order_by(AiClaimVettingJob.id.desc()).first()

    return BatchReportResponse(
        batch_id=batch_id,
        pending_total=sum(g.pending_count for g in groups),
        groups=groups,
        latest_job=_job_response(latest) if latest else None,
    )


@router.post("/findings/bulk-decide")
def bulk_decide_findings(
    body: BulkDecideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "update")),
):
    """
    Accept / reject / mark-edited for many findings at once.
    Accept applies each suggestion (NHIA HIN lookup per Ghana Card row).
    Continues on per-row failures and returns a results list.
    """
    _ensure_module_active(db)

    decision = (body.decision or "").strip().lower()
    if decision not in ("accept", "reject", "edited"):
        raise HTTPException(status_code=400, detail="decision must be accept, reject, or edited.")
    if not body.finding_ids:
        raise HTTPException(status_code=400, detail="finding_ids is required.")

    creator_id = get_effective_creator_id(db, current_user)
    findings = (
        db.query(AiClaimVettingFinding)
        .filter(AiClaimVettingFinding.id.in_(body.finding_ids))
        .all()
    )
    by_id = {f.id: f for f in findings}

    results = []
    ok_count = 0
    fail_count = 0

    for fid in body.finding_ids:
        finding = by_id.get(fid)
        reopened = False
        if not finding:
            results.append({"finding_id": fid, "success": False, "error": "Finding not found"})
            fail_count += 1
            continue
        if finding.status != "pending":
            results.append({
                "finding_id": fid,
                "success": False,
                "error": f"Already decided ({finding.status})",
                "claim_claim_id": finding.claim_claim_id,
            })
            fail_count += 1
            continue

        if decision == "accept":
            if finding.source_type != "ghims_import" or not finding.source_id:
                results.append({
                    "finding_id": fid,
                    "success": False,
                    "error": "Accept only supported for GHIMS imports",
                    "claim_claim_id": finding.claim_claim_id,
                })
                fail_count += 1
                continue
            item = (
                db.query(ClaimXmlImportItem)
                .filter(ClaimXmlImportItem.id == finding.source_id)
                .first()
            )
            if not item:
                results.append({
                    "finding_id": fid,
                    "success": False,
                    "error": "Imported claim not found",
                    "claim_claim_id": finding.claim_claim_id,
                })
                fail_count += 1
                continue
            applied, err, _payload, reopened = _try_apply_suggested_action(
                db,
                item,
                finding,
                otac=body.otac,
                chosen_value=body.chosen_value,
            )
            if not applied:
                results.append({
                    "finding_id": fid,
                    "success": False,
                    "error": err or "Failed to apply",
                    "claim_claim_id": finding.claim_claim_id,
                    "rule_code": finding.rule_code,
                })
                fail_count += 1
                continue
        elif decision == "edited" and finding.source_type == "ghims_import" and finding.source_id:
            item = (
                db.query(ClaimXmlImportItem)
                .filter(ClaimXmlImportItem.id == finding.source_id)
                .first()
            )
            if item:
                reopened = _reopen_ghims_item_if_finalized(item)
                _mark_item_ai_vetted(item)
                db.add(item)
                db.commit()

        finding.status = "accepted" if decision == "accept" else decision
        finding.human_decision_note = (body.note or "").strip() or None
        finding.decided_by_id = creator_id
        finding.decided_at = utcnow()
        db.add(finding)
        db.commit()

        results.append({
            "finding_id": fid,
            "success": True,
            "status": finding.status,
            "claim_claim_id": finding.claim_claim_id,
            "rule_code": finding.rule_code,
            "reopened": reopened,
        })
        ok_count += 1

    create_audit_log(
        db,
        current_user,
        action="AI_VET_BULK_DECIDE",
        resource_type="AiClaimVettingFinding",
        details={
            "decision": decision,
            "requested": len(body.finding_ids),
            "ok": ok_count,
            "failed": fail_count,
        },
        summary=f"Bulk AI vetting {decision}: {ok_count} ok, {fail_count} failed",
    )

    return {
        "success": fail_count == 0,
        "decision": decision,
        "ok_count": ok_count,
        "fail_count": fail_count,
        "results": results,
        "message": f"{ok_count} applied, {fail_count} failed.",
    }


# ── Facility rules CRUD ──────────────────────────────────────────────


class RuleCreateRequest(BaseModel):
    rule_code: Optional[str] = None
    name: str
    description: Optional[str] = None
    enabled: bool = True
    severity: str = "warning"
    priority: int = 100
    analysis_modes: List[str] = Field(default_factory=lambda: ["phase1"])
    applies_to: str = "ghims_import"
    condition: Dict[str, Any]
    suggested_action: Optional[Dict[str, Any]] = None
    finding_template: Optional[str] = None
    recommendation_template: Optional[str] = None
    requires_human_review: bool = True


class RuleUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    priority: Optional[int] = None
    analysis_modes: Optional[List[str]] = None
    applies_to: Optional[str] = None
    condition: Optional[Dict[str, Any]] = None
    suggested_action: Optional[Dict[str, Any]] = None
    finding_template: Optional[str] = None
    recommendation_template: Optional[str] = None
    requires_human_review: Optional[bool] = None


class RuleResponse(BaseModel):
    id: int
    rule_code: str
    name: str
    description: Optional[str] = None
    enabled: bool
    severity: str
    priority: int
    analysis_modes: Optional[List[str]] = None
    applies_to: str
    is_system: bool
    condition: Dict[str, Any]
    suggested_action: Optional[Dict[str, Any]] = None
    finding_template: Optional[str] = None
    recommendation_template: Optional[str] = None
    requires_human_review: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


def _slug_rule_code(name: str) -> str:
    import re as _re

    base = _re.sub(r"[^a-z0-9]+", "_", (name or "rule").strip().lower()).strip("_")
    return (base or "rule")[:60]


def _validate_condition(condition: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(condition, dict):
        raise HTTPException(status_code=400, detail="condition must be an object.")
    field = (condition.get("field") or "").strip()
    op = (condition.get("op") or "").strip().lower()
    if field not in ALLOWED_RULE_FIELDS:
        raise HTTPException(
            status_code=400,
            detail=f"condition.field must be one of: {sorted(ALLOWED_RULE_FIELDS)}",
        )
    if op not in ALLOWED_OPS:
        raise HTTPException(
            status_code=400,
            detail=f"condition.op must be one of: {sorted(ALLOWED_OPS)}",
        )
    return {
        **condition,
        "field": field,
        "op": op,
    }


def _rule_response(row: AiClaimVettingRule) -> RuleResponse:
    return RuleResponse.model_validate(row)


@router.get("/rules/meta")
def rules_meta(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """Field/operator catalogs for the rules form."""
    _ensure_module_active(db)
    return {
        "fields": sorted(ALLOWED_RULE_FIELDS),
        "ops": sorted(ALLOWED_OPS),
        "severities": ["critical", "warning", "review_needed"],
        "action_types": [
            "strip_prefix",
            "trim_field",
            "set_field",
            "set_specialty",
            "review_only",
        ],
        "analysis_modes": ["phase1", "coding", "thorough"],
    }


class RuleDraftRequest(BaseModel):
    instruction: str


class RuleDraftResponse(BaseModel):
    draft: Dict[str, Any]
    explanation: str = ""
    provider: str = "ollama"
    model: Optional[str] = None


def _draft_rule_with_ollama(instruction: str) -> Dict[str, Any]:
    """Ask local Ollama to turn plain English into a structured facility rule draft."""
    from app.core.config import settings
    import json as _json
    import urllib.request

    base_url = (getattr(settings, "OLLAMA_BASE_URL", None) or "http://127.0.0.1:11434").rstrip("/")
    model = getattr(settings, "OLLAMA_MODEL", None) or "llama3.2"
    timeout = float(getattr(settings, "OLLAMA_TIMEOUT_SECONDS", 90.0) or 90.0)

    if not _ollama_reachable(base_url):
        raise HTTPException(status_code=503, detail="Local AI (Ollama) is offline. Start Ollama and retry.")

    system = (
        "You draft Ghana ClaimIT / NHIA facility vetting rules for a hospital scanner.\n"
        "Return ONLY JSON (no markdown) with this shape:\n"
        "{"
        '"name":"short name",'
        '"description":"why this rule exists",'
        '"severity":"critical|warning|review_needed",'
        '"condition":{"field":"memberNo","op":"starts_with","value":"-","skip_if_ghana_card":false,"skip_if_hin_shaped":false},'
        '"action_type":"strip_prefix|trim_field|set_field|set_specialty|review_only",'
        '"action_value":"optional value for strip/set",'
        '"finding_template":"Member No begins with hyphen ({value}).",'
        '"recommendation_template":"Remove the leading hyphen.",'
        '"explanation":"plain English summary of the drafted rule"'
        "}\n"
        f"Allowed fields: {sorted(ALLOWED_RULE_FIELDS)}\n"
        f"Allowed ops: {sorted(ALLOWED_OPS)}\n"
        "Prefer review_only when a safe automatic fix is unclear.\n"
        "Do not invent unsupported fields or operators."
    )
    body = _json.dumps(
        {
            "model": model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1, "num_predict": 700},
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        "Officer instruction:\n"
                        f"{instruction.strip()}\n\n"
                        "Draft one facility rule JSON."
                    ),
                },
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Ollama draft failed: {exc}") from exc

    content = ((data.get("message") or {}).get("content") or "").strip()
    try:
        parsed = _json.loads(content)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Ollama returned invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=502, detail="Ollama draft was not an object.")
    return parsed


@router.post("/rules/draft-from-text", response_model=RuleDraftResponse)
def draft_rule_from_text(
    body: RuleDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "update")),
):
    """
    Officer writes plain English → local AI drafts a structured rule.
    Does NOT save. Human reviews, then POST /rules to approve.
    """
    from app.core.config import settings

    _ensure_module_active(db)
    instruction = (body.instruction or "").strip()
    if len(instruction) < 8:
        raise HTTPException(status_code=400, detail="Describe the rule in a short sentence.")

    raw = _draft_rule_with_ollama(instruction)
    field = str((raw.get("condition") or {}).get("field") or "memberNo").strip()
    op = str((raw.get("condition") or {}).get("op") or "equals").strip().lower()
    if field not in ALLOWED_RULE_FIELDS:
        field = "memberNo"
    if op not in ALLOWED_OPS:
        op = "equals"
    action_type = str(raw.get("action_type") or "review_only").strip()
    if action_type not in ("strip_prefix", "trim_field", "set_field", "set_specialty", "review_only"):
        action_type = "review_only"
    severity = str(raw.get("severity") or "warning").strip().lower()
    if severity not in ("critical", "warning", "review_needed"):
        severity = "warning"

    cond = raw.get("condition") if isinstance(raw.get("condition"), dict) else {}
    draft = {
        "name": (str(raw.get("name") or "").strip() or "Facility rule")[:200],
        "description": (str(raw.get("description") or instruction).strip())[:2000],
        "severity": severity,
        "enabled": True,
        "condition": {
            "field": field,
            "op": op,
            "value": cond.get("value", ""),
            "skip_if_ghana_card": bool(cond.get("skip_if_ghana_card")),
            "skip_if_hin_shaped": bool(cond.get("skip_if_hin_shaped")),
        },
        "action_type": action_type,
        "action_value": raw.get("action_value"),
        "finding_template": (str(raw.get("finding_template") or "").strip() or None),
        "recommendation_template": (str(raw.get("recommendation_template") or "").strip() or None),
        "analysis_modes": ["phase1", "coding", "thorough"],
        "suggested_action": {
            "type": action_type,
            "field": field,
            "value": raw.get("action_value"),
            "details": {"prefix": raw.get("action_value")} if action_type == "strip_prefix" else {},
        },
    }
    explanation = str(raw.get("explanation") or draft["description"]).strip()
    return RuleDraftResponse(
        draft=draft,
        explanation=explanation,
        provider="ollama",
        model=getattr(settings, "OLLAMA_MODEL", None),
    )


@router.get("/rules", response_model=List[RuleResponse])
def list_rules(
    enabled_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    _ensure_module_active(db)
    q = db.query(AiClaimVettingRule)
    if enabled_only:
        q = q.filter(AiClaimVettingRule.enabled == True)  # noqa: E712
    rows = q.order_by(AiClaimVettingRule.priority.asc(), AiClaimVettingRule.id.asc()).all()
    return [_rule_response(r) for r in rows]


@router.post("/rules", response_model=RuleResponse)
def create_rule(
    body: RuleCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "update")),
):
    _ensure_module_active(db)
    condition = _validate_condition(body.condition)
    code = (body.rule_code or _slug_rule_code(body.name)).strip().lower()
    if not code:
        raise HTTPException(status_code=400, detail="rule_code is required.")
    exists = db.query(AiClaimVettingRule).filter(AiClaimVettingRule.rule_code == code).first()
    if exists:
        raise HTTPException(status_code=400, detail=f"Rule code '{code}' already exists.")

    creator_id = get_effective_creator_id(db, current_user)
    row = AiClaimVettingRule(
        rule_code=code,
        name=(body.name or "").strip() or code,
        description=(body.description or "").strip() or None,
        enabled=bool(body.enabled),
        severity=(body.severity or "warning").strip() or "warning",
        priority=int(body.priority or 100),
        analysis_modes=body.analysis_modes or ["phase1"],
        applies_to=(body.applies_to or "ghims_import").strip() or "ghims_import",
        is_system=False,
        condition=condition,
        suggested_action=body.suggested_action
        or {"type": "review_only", "field": condition["field"]},
        finding_template=(body.finding_template or "").strip() or None,
        recommendation_template=(body.recommendation_template or "").strip() or None,
        requires_human_review=bool(body.requires_human_review),
        created_by_id=creator_id,
        updated_by_id=creator_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    create_audit_log(
        db,
        current_user,
        action="AI_VET_RULE_CREATE",
        resource_type="AiClaimVettingRule",
        resource_id=row.id,
        details={"rule_code": row.rule_code},
        summary=f"Created AI vetting rule {row.rule_code}",
    )
    return _rule_response(row)


@router.patch("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: int,
    body: RuleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "update")),
):
    _ensure_module_active(db)
    row = db.query(AiClaimVettingRule).filter(AiClaimVettingRule.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found.")

    data = body.model_dump(exclude_unset=True)
    if "condition" in data and data["condition"] is not None:
        data["condition"] = _validate_condition(data["condition"])
    for key, val in data.items():
        setattr(row, key, val)
    row.updated_by_id = get_effective_creator_id(db, current_user)
    row.updated_at = utcnow()
    db.add(row)
    db.commit()
    db.refresh(row)
    create_audit_log(
        db,
        current_user,
        action="AI_VET_RULE_UPDATE",
        resource_type="AiClaimVettingRule",
        resource_id=row.id,
        details={"rule_code": row.rule_code, "fields": list(data.keys())},
        summary=f"Updated AI vetting rule {row.rule_code}",
    )
    return _rule_response(row)


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "update")),
):
    _ensure_module_active(db)
    row = db.query(AiClaimVettingRule).filter(AiClaimVettingRule.id == rule_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Rule not found.")
    if row.is_system:
        # Soft-disable system seeds instead of hard delete
        row.enabled = False
        row.updated_by_id = get_effective_creator_id(db, current_user)
        row.updated_at = utcnow()
        db.add(row)
        db.commit()
        return {"success": True, "disabled": True, "message": "System rule disabled (not deleted)."}
    code = row.rule_code
    db.delete(row)
    db.commit()
    create_audit_log(
        db,
        current_user,
        action="AI_VET_RULE_DELETE",
        resource_type="AiClaimVettingRule",
        resource_id=rule_id,
        details={"rule_code": code},
        summary=f"Deleted AI vetting rule {code}",
    )
    return {"success": True, "deleted": True}
