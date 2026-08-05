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
from app.models.ai_claim_vetting import AiClaimVettingFinding, AiClaimVettingJob
from app.models.claim_xml_import import ClaimXmlImportBatch, ClaimXmlImportItem
from app.models.module_settings import ModuleSettings
from app.models.user import User
from app.services.ai_claim_vetting import analyze_claim_payload
from app.services.nhia_exceptions import NhiaIntegrationError
from app.services.nhia_integration import lookup_member_by_hin
from app.utils.ghims_card import is_ghana_card, normalize_ghana_card

router = APIRouter(prefix="/ai-claim-vetting", tags=["ai-claim-vetting"])

MODULE_KEY = "ai_claims_vetting"
CLAIMS_ROLES = ["Claims", "Admin", "Doctor", "PA"]

RULE_LABELS = {
    "specialty_zoom": "ZOOM specialty → OPDC",
    "ghana_card_member_no": "Ghana Card Member No → HIN",
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
    """
    item_ids: Optional[List[int]] = None
    include_finalized: bool = False


class BulkDecideRequest(BaseModel):
    finding_ids: List[int]
    decision: str  # accept | reject | edited
    note: Optional[str] = None
    otac: Optional[str] = None


class JobResponse(BaseModel):
    id: int
    batch_id: int
    status: str
    total_items: int
    processed_items: int
    findings_count: int
    item_ids: Optional[List[int]] = None
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


def _client_name_from_payload(payload: Optional[Dict[str, Any]]) -> str:
    p = payload or {}
    parts = [str(p.get("otherNames") or "").strip(), str(p.get("surname") or "").strip()]
    return " ".join(x for x in parts if x) or ""


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
) -> List[AiClaimVettingFinding]:
    """Save new findings; optionally supersede open pending ones for same source+rule."""
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
        for row in existing:
            if row.rule_code in new_codes:
                db.delete(row)
            elif row.rule_code not in new_codes:
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


def _apply_suggested_action(
    db: Session,
    item: ClaimXmlImportItem,
    finding: AiClaimVettingFinding,
    *,
    otac: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Apply an accepted suggestion to the GHIMS import payload and persist.
    Returns the updated payload dict.
    """
    if item.status == "finalized":
        raise HTTPException(
            status_code=400,
            detail="Cannot apply AI suggestion on a finalized imported claim. Reopen it first.",
        )

    payload = dict(item.payload or {})
    action = finding.suggested_action or {}
    action_type = (action.get("type") or "").strip()

    if action_type == "set_specialty":
        value = (action.get("value") or "OPDC").strip().upper()
        payload["specialtyAttended"] = value
        item.payload = payload
        flag_modified(item, "payload")
        db.add(item)
        db.commit()
        db.refresh(item)
        return payload

    if action_type == "apply_existing_hin":
        hin = (action.get("value") or payload.get("hin") or "").strip()
        if not hin or is_ghana_card(hin):
            raise HTTPException(status_code=400, detail="No usable HIN available to apply.")
        ghana = normalize_ghana_card(payload.get("ghanaCard") or payload.get("memberNo") or "")
        if ghana and is_ghana_card(ghana):
            payload["ghanaCard"] = ghana
        payload["hin"] = hin
        payload["memberNo"] = hin
        item.payload = payload
        flag_modified(item, "payload")
        db.add(item)
        db.commit()
        db.refresh(item)
        return payload

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
        item.payload = payload
        flag_modified(item, "payload")
        db.add(item)
        db.commit()
        db.refresh(item)
        return payload

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

    result = analyze_claim_payload(payload)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """Analyze a GHIMS imported claim payload and persist pending findings."""
    _ensure_module_active(db)

    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")

    result = analyze_claim_payload(item.payload or {})
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
    if decision == "accept":
        if finding.source_type == "ghims_import" and finding.source_id:
            item = (
                db.query(ClaimXmlImportItem)
                .filter(ClaimXmlImportItem.id == finding.source_id)
                .first()
            )
            if not item:
                raise HTTPException(status_code=404, detail="Imported claim not found.")
            updated_payload = _apply_suggested_action(
                db, item, finding, otac=body.otac
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Accept is only supported for GHIMS imported claims in Phase 1.",
            )

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
        },
        summary=f"AI vetting finding #{finding.id} {finding.status} ({finding.rule_code})",
    )

    return {
        "success": True,
        "finding": FindingResponse.model_validate(finding).model_dump(),
        "payload": updated_payload,
        "message": (
            "Recommendation accepted and applied."
            if decision == "accept"
            else f"Recommendation marked as {finding.status}."
        ),
    }


def _try_apply_suggested_action(
    db: Session,
    item: ClaimXmlImportItem,
    finding: AiClaimVettingFinding,
    *,
    otac: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Like _apply_suggested_action but returns (ok, error, payload) instead of raising."""
    try:
        payload = _apply_suggested_action(db, item, finding, otac=otac)
        return True, None, payload
    except HTTPException as exc:
        detail = exc.detail
        if isinstance(detail, list):
            detail = "; ".join(str(x) for x in detail)
        return False, str(detail), None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc), None


def _run_batch_analyze_job(job_id: int, creator_id: int) -> None:
    """Background worker: analyze selected GHIMS items and persist findings."""
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
        summary: Dict[str, int] = {}
        findings_total = 0

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

            result = analyze_claim_payload(item.payload or {})
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

    creator_id = get_effective_creator_id(db, current_user)
    item_ids = [i.id for i in items]
    job = AiClaimVettingJob(
        batch_id=batch_id,
        status="queued",
        total_items=len(item_ids),
        processed_items=0,
        findings_count=0,
        item_ids=item_ids,
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
        details={"job_id": job.id, "item_count": len(item_ids)},
        summary=f"Started AI vetting job #{job.id} on {len(item_ids)} claim(s)",
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
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    _ensure_module_active(db)
    job = (
        db.query(AiClaimVettingJob)
        .filter(AiClaimVettingJob.batch_id == batch_id)
        .order_by(AiClaimVettingJob.id.desc())
        .first()
    )
    return _job_response(job) if job else None


@router.get("/batches/{batch_id}/report", response_model=BatchReportResponse)
def get_batch_report(
    batch_id: int,
    status_filter: str = "pending",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(CLAIMS_ROLES)),
    _claims_mod: User = Depends(require_module_permission("claims", "read")),
):
    """Grouped AI findings for a GHIMS import batch (claim-list style report)."""
    _ensure_module_active(db)

    batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found.")

    item_ids = [
        r[0]
        for r in db.query(ClaimXmlImportItem.id)
        .filter(ClaimXmlImportItem.batch_id == batch_id)
        .all()
    ]
    if not item_ids:
        latest = (
            db.query(AiClaimVettingJob)
            .filter(AiClaimVettingJob.batch_id == batch_id)
            .order_by(AiClaimVettingJob.id.desc())
            .first()
        )
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

    items_by_id = {
        i.id: i
        for i in db.query(ClaimXmlImportItem)
        .filter(ClaimXmlImportItem.id.in_({f.source_id for f in findings if f.source_id}))
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

    groups = [
        ReportGroup(
            rule_code=code,
            label=RULE_LABELS.get(code, code),
            pending_count=len(rows),
            findings=rows,
        )
        for code, rows in grouped.items()
    ]
    groups.sort(key=lambda g: (-g.pending_count, g.label))

    latest = (
        db.query(AiClaimVettingJob)
        .filter(AiClaimVettingJob.batch_id == batch_id)
        .order_by(AiClaimVettingJob.id.desc())
        .first()
    )

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
            applied, err, _payload = _try_apply_suggested_action(
                db, item, finding, otac=body.otac
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
