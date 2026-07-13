"""
GHIMS XML import endpoints for Suhum.
"""
import re
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.datetime_utils import utcnow
from app.core.dependencies import get_current_user
from app.models.claim_xml_import import ClaimXmlImportBatch, ClaimXmlImportItem
from app.models.product_price import ProductPrice
from app.models.user import User
from app.services.claim_amount_service import (
    PriceAmountCache,
    compute_claim_summary_from_ghims_payload,
    compute_ghims_batch_claim_totals,
)
from app.services.claim_nhia_ccc import fetch_ccc_preview_for_ghims_payload
from app.services.claim_xml_import_parser import (
    build_claims_xml_from_payloads,
    parse_claims_xml,
)
from app.services.nhia_integration import NhiaIntegrationError

from app.services.claimit_errors import get_claimit_errors_for_import_item

router = APIRouter(prefix="/ghims-import", tags=["ghims-import"])


class GhimsFetchCccRequest(BaseModel):
    member_no: Optional[str] = None
    otac: Optional[str] = None


class GhimsImportItemUpdateBody(BaseModel):
    payload: dict


class GhimsExportBatchBody(BaseModel):
    item_ids: List[int]


class GhimsBulkStatusBody(BaseModel):
    item_ids: List[int]
    action: str
    comment: Optional[str] = None


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
                detail=f"Medicine section {idx + 1}: missing dose. Please enter dose before saving.",
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


@router.post("/upload")
async def upload_ghims_claims_xml(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
        uploaded_by_id=current_user.id,
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


@router.get("/batches")
def list_ghims_import_batches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@router.get("/batches/{batch_id}")
def get_ghims_import_batch(
    batch_id: int,
    include_totals: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@router.get("/batches/{batch_id}/claim-totals")
def get_ghims_import_batch_claim_totals(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@router.get("/items/{item_id}")
def get_ghims_import_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        "claimit_errors": get_claimit_errors_for_import_item(db, item),
    }


@router.put("/items/{item_id}")
def update_ghims_import_item(
    item_id: int,
    body: GhimsImportItemUpdateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.post("/items/{item_id}/fetch-ccc")
def fetch_ghims_import_item_ccc(
    item_id: int,
    body: GhimsFetchCccRequest = GhimsFetchCccRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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


@router.patch("/items/{item_id}/finalize")
def finalize_ghims_import_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")
    payload = _validate_and_normalize_ghims_payload(db, item.payload or {})
    item.payload = payload
    item.status = "finalized"
    item.finalized_at = utcnow()
    db.commit()
    return {"id": item.id, "status": item.status}


@router.patch("/items/{item_id}/reopen")
def reopen_ghims_import_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = db.query(ClaimXmlImportItem).filter(ClaimXmlImportItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Imported claim not found.")
    item.status = "draft"
    item.finalized_at = None
    db.commit()
    return {"id": item.id, "status": item.status}


@router.patch("/items/{item_id}/flag")
def flag_ghims_import_item(
    item_id: int,
    body: dict = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.delete("/batches/{batch_id}")
def delete_ghims_import_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    batch = db.query(ClaimXmlImportBatch).filter(ClaimXmlImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")
    db.delete(batch)
    db.commit()
    return {"deleted": True}


@router.patch("/items/bulk-status")
def bulk_update_ghims_import_items_status(
    body: GhimsBulkStatusBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    if action == "flag":
        bad = [i.id for i in items if i.status == "finalized"]
        if bad:
            raise HTTPException(status_code=400, detail=f"Cannot flag finalized imported claim(s): {bad}")
        if not comment:
            raise HTTPException(status_code=400, detail="Flag comment is required for bulk flag.")
    if action == "finalize":
        bad = [i.id for i in items if i.status == "flagged"]
        if bad:
            raise HTTPException(status_code=400, detail=f"Cannot finalize flagged imported claim(s): {bad}")

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


def _not_covered_medicine_codes(db: Session, medicine_codes: List[str]) -> set[str]:
    codes = {str(c or "").strip() for c in medicine_codes if str(c or "").strip()}
    if not codes:
        return set()
    rows = (
        db.query(ProductPrice.medication_code, ProductPrice.insurance_covered)
        .filter(ProductPrice.medication_code.in_(codes))
        .all()
    )
    return {
        code
        for code, covered in rows
        if (covered or "yes").strip().lower() == "no"
    }


@router.post("/export")
def export_ghims_import_items(
    body: GhimsExportBatchBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

    all_medicine_codes: List[str] = []
    for p in payloads:
        for med in p.get("medicines") or []:
            if isinstance(med, dict):
                all_medicine_codes.append(str(med.get("medicineCode") or ""))

    not_covered_codes = _not_covered_medicine_codes(db, all_medicine_codes)
    xml_content = build_claims_xml_from_payloads(payloads, not_covered_codes)
    filename = f"NHIS_CLA_imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    return Response(
        content=xml_content,
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
