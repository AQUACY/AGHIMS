"""
Vetting guide CSV upload and lookup for recovered facility visit data.
"""
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.claim_xml_import import ClaimXmlImportItem
from app.models.user import User
from app.models.vetting_guide import VettingGuideRecord, VettingGuideUpload
from app.services.vetting_guide_parser import normalize_claim_id, parse_vetting_guide_csv

router = APIRouter(prefix="/vetting-guide", tags=["vetting-guide"])


def _claim_id_variants(claim_id: str) -> Set[str]:
    base = normalize_claim_id(claim_id)
    variants = {base}
    if base.startswith("CLA-"):
        variants.add(base[4:])
    return {v for v in variants if v}


def _find_record(db: Session, claim_id: str) -> Optional[VettingGuideRecord]:
    variants = _claim_id_variants(claim_id)
    if not variants:
        return None
    return (
        db.query(VettingGuideRecord)
        .filter(VettingGuideRecord.claim_id.in_(list(variants)))
        .order_by(VettingGuideRecord.id.desc())
        .first()
    )


@router.get("/uploads")
def list_vetting_guide_uploads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uploads = (
        db.query(VettingGuideUpload)
        .order_by(VettingGuideUpload.uploaded_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": u.id,
            "file_name": u.file_name,
            "uploaded_at": u.uploaded_at.isoformat() if u.uploaded_at else None,
            "row_count": u.row_count,
            "matched_claim_ids": u.matched_claim_ids,
        }
        for u in uploads
    ]


@router.post("/upload")
async def upload_vetting_guide(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV vetting guide file.")

    try:
        raw = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file.")

    text = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode("latin-1", errors="replace")

    parsed_rows = parse_vetting_guide_csv(text)
    if not parsed_rows:
        raise HTTPException(status_code=400, detail="No claim rows found in vetting guide CSV.")

    upload = VettingGuideUpload(
        file_name=file.filename or "vetting_guide.csv",
        uploaded_by_id=current_user.id,
        row_count=len(parsed_rows),
    )
    db.add(upload)
    db.flush()

    claim_ids = [r["claim_id"] for r in parsed_rows]
    imported = (
        db.query(ClaimXmlImportItem.claim_claim_id)
        .filter(ClaimXmlImportItem.claim_claim_id.in_(claim_ids))
        .all()
    )
    imported_set: Set[str] = set()
    for row in imported:
        if row and row[0]:
            imported_set.update(_claim_id_variants(row[0]))
    matched = sum(1 for cid in claim_ids if cid in imported_set)
    upload.matched_claim_ids = matched

    for row in parsed_rows:
        db.add(VettingGuideRecord(
            upload_id=upload.id,
            claim_id=row["claim_id"],
            entity_id=row["parsed"].get("entity_id"),
            visit_type=row["parsed"].get("visit_type"),
            service_date=row["parsed"].get("service_date"),
            patient_no=row["parsed"].get("patient_no"),
            patient_name=row["parsed"].get("patient_name"),
            member_no=row["parsed"].get("member_no"),
            raw_row=row["raw_row"],
            parsed=row["parsed"],
        ))

    db.commit()
    db.refresh(upload)
    return {
        "upload_id": upload.id,
        "file_name": upload.file_name,
        "row_count": upload.row_count,
        "matched_claim_ids": upload.matched_claim_ids,
        "claim_ids": claim_ids[:50],
    }


@router.get("/for-claim/{claim_id}")
def get_vetting_guide_for_claim(
    claim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = _find_record(db, claim_id)
    if not record:
        raise HTTPException(status_code=404, detail="No recovered vetting data for this claim.")
    return {
        "claim_id": record.claim_id,
        "upload_id": record.upload_id,
        "file_name": record.upload.file_name if record.upload else None,
        "service_date": record.service_date,
        "patient_name": record.patient_name,
        "member_no": record.member_no,
        "visit_type": record.visit_type,
        "parsed": record.parsed,
        "raw_row": record.raw_row,
    }


@router.get("/coverage")
def get_vetting_guide_coverage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return claim_ids that have vetting guide records (for batch list badges)."""
    rows = db.query(VettingGuideRecord.claim_id).distinct().all()
    ids = sorted({normalize_claim_id(r[0]) for r in rows if r and r[0]})
    return {"claim_ids": ids, "count": len(ids)}


@router.get("/batch/{batch_id}/matches")
def get_vetting_matches_for_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = (
        db.query(ClaimXmlImportItem)
        .filter(ClaimXmlImportItem.batch_id == batch_id)
        .all()
    )
    out: Dict[str, bool] = {}
    for item in items:
        cid = normalize_claim_id(item.claim_claim_id)
        out[str(item.id)] = _find_record(db, cid) is not None
        out[cid] = _find_record(db, cid) is not None
    return {"matches_by_item_id": {str(i.id): _find_record(db, i.claim_claim_id) is not None for i in items}}
