"""
ClaimIT import report upload and error batches for Suhum GHIMS workflow.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.datetime_utils import utcnow
from app.core.dependencies import get_current_user
from app.models.claimit_report import ClaimItReportBatch, ClaimItReportError
from app.models.claim_xml_import import ClaimXmlImportBatch, ClaimXmlImportItem
from app.models.user import User
from app.services.claimit_report_parser import parse_claimit_report_html

router = APIRouter(prefix="/claimit-report", tags=["claimit-report"])


def _resolve_ghims_batch_for_claimit_report(
    db: Session,
    explicit_batch_id: Optional[int],
    report_claim_ids: set,
) -> Tuple[Optional[int], str]:
    if explicit_batch_id is not None:
        batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == explicit_batch_id).first()
        if not batch:
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
    for batch in batches:
        in_batch = {
            row[0]
            for row in db.query(ClaimXmlImportItem.claim_claim_id)
            .filter(ClaimXmlImportItem.batch_id == batch.id)
            .all()
        }
        if report_claim_ids <= in_batch:
            return batch.id, "auto_subset"

    best_id = None
    best_count = 0
    for batch in batches:
        count = (
            db.query(func.count(ClaimXmlImportItem.id))
            .filter(
                ClaimXmlImportItem.batch_id == batch.id,
                ClaimXmlImportItem.claim_claim_id.in_(list(report_claim_ids)),
            )
            .scalar()
        ) or 0
        if count > best_count:
            best_count = count
            best_id = batch.id
    if best_id is not None and best_count > 0:
        return best_id, "auto_overlap"
    return None, "none"


@router.post("/upload")
async def upload_claimit_report(
    file: UploadFile = File(...),
    ghims_import_batch_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith((".html", ".htm")):
        raise HTTPException(status_code=400, detail="Please upload an HTML file (ClaimIT import report).")
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file.")

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
    report_claim_ids = {err["claim_id"] for err in errors_list if err.get("claim_id")}
    ghims_batch_id, ghims_match_reason = _resolve_ghims_batch_for_claimit_report(
        db, ghims_import_batch_id, report_claim_ids
    )
    ghims_file_name = None
    if ghims_batch_id is not None:
        ghims_batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == ghims_batch_id).first()
        ghims_file_name = ghims_batch.file_name if ghims_batch else None

    summary_out = dict(overview) if isinstance(overview, dict) else {}
    summary_out["ghims_resolution"] = ghims_match_reason

    batch = ClaimItReportBatch(
        name=None,
        file_name=file.filename or "report.html",
        uploaded_by_id=current_user.id,
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
        "claim_ids": [err["claim_id"] for err in errors_list],
        "ghims_import_batch_id": ghims_batch_id,
        "ghims_import_batch_file_name": ghims_file_name,
        "ghims_match_reason": ghims_match_reason,
    }


@router.get("/batches")
def list_claimit_report_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batches = (
        db.query(ClaimItReportBatch)
        .order_by(ClaimItReportBatch.uploaded_at.desc())
        .limit(100)
        .all()
    )
    ghims_ids = {batch.ghims_import_batch_id for batch in batches if batch.ghims_import_batch_id}
    ghims_meta = {}
    if ghims_ids:
        for ghims_batch in db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id.in_(ghims_ids)).all():
            ghims_meta[ghims_batch.id] = {
                "file_name": ghims_batch.file_name,
                "claim_count": ghims_batch.claim_count,
            }
    return [
        {
            "id": batch.id,
            "name": batch.name,
            "file_name": batch.file_name,
            "uploaded_at": batch.uploaded_at.isoformat() if batch.uploaded_at else None,
            "error_count": batch.error_count,
            "summary": batch.summary,
            "ghims_import_batch_id": batch.ghims_import_batch_id,
            "ghims_import_batch_file_name": (ghims_meta.get(batch.ghims_import_batch_id) or {}).get("file_name"),
            "ghims_import_claim_count": (ghims_meta.get(batch.ghims_import_batch_id) or {}).get("claim_count"),
        }
        for batch in batches
    ]


@router.get("/batches/{batch_id}")
def get_claimit_report_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batch = db.query(ClaimItReportBatch).filter(ClaimItReportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    errors = (
        db.query(ClaimItReportError)
        .filter(ClaimItReportError.batch_id == batch_id)
        .order_by(ClaimItReportError.row_index, ClaimItReportError.id)
        .all()
    )

    ghims_item_ids = [error.ghims_import_item_id for error in errors if error.ghims_import_item_id]
    ghims_items_by_id = {}
    if ghims_item_ids:
        for item in db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id.in_(ghims_item_ids)).all():
            ghims_items_by_id[item.id] = item

    completed_by_ids = {error.completed_by_id for error in errors if error.completed_by_id}
    users_by_id = {}
    if completed_by_ids:
        for user in db.query(User).filter(User.id.in_(completed_by_ids)).all():
            users_by_id[user.id] = user

    ghims_batch_file = None
    ghims_import_claim_count = None
    if batch.ghims_import_batch_id:
        ghims_batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch.ghims_import_batch_id).first()
        if ghims_batch:
            ghims_batch_file = ghims_batch.file_name
            ghims_import_claim_count = ghims_batch.claim_count

    error_rows = []
    for error in errors:
        ghims_item = ghims_items_by_id.get(error.ghims_import_item_id) if error.ghims_import_item_id else None
        completed_by_user = users_by_id.get(error.completed_by_id) if error.completed_by_id else None
        error_rows.append({
            "id": error.id,
            "claim_claim_id": error.claim_claim_id,
            "outcome": error.outcome,
            "error_messages": error.error_messages or [],
            "row_index": error.row_index,
            "ghims_import_item_id": error.ghims_import_item_id,
            "ghims_import_item_status": ghims_item.status if ghims_item else None,
            "completed_at": error.completed_at.isoformat() if error.completed_at else None,
            "completed_by_id": error.completed_by_id,
            "completed_by_name": (
                completed_by_user.username or completed_by_user.full_name or str(completed_by_user.id)
            ) if completed_by_user else None,
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


@router.patch("/batches/{batch_id}/errors/{error_id}/complete")
def set_claimit_error_completed(
    batch_id: int,
    error_id: int,
    body: ClaimItErrorCompleteBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    error = (
        db.query(ClaimItReportError)
        .filter(ClaimItReportError.id == error_id, ClaimItReportError.batch_id == batch_id)
        .first()
    )
    if not error:
        raise HTTPException(status_code=404, detail="Error row not found.")
    if body.completed:
        error.completed_at = utcnow()
        error.completed_by_id = current_user.id
    else:
        error.completed_at = None
        error.completed_by_id = None
    db.commit()
    return {
        "id": error.id,
        "completed": body.completed,
        "completed_at": error.completed_at.isoformat() if error.completed_at else None,
        "completed_by_id": error.completed_by_id,
    }
