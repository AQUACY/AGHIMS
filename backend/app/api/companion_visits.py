"""
Companion (copayment) visits API.

Service creation and listing for Companion mode. All identifiers (card number, visit number)
come from the external government system; no internal patient/encounter IDs are used.
"""
import io
import json
import math
import re
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Request, Response
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Optional, List, Tuple, Dict, Set
from collections import defaultdict
from datetime import date, datetime
from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.core.audit import get_effective_creator_id
from app.core.datetime_utils import utcnow
from app.core.audit import is_super_admin
from app.models.user import User
from app.models.companion_visit import CompanionVisit
from app.models.companion_visit_item import CompanionVisitItem
from app.models.companion_active_investigation import CompanionActiveInvestigation
from app.models.companion_active_scan import CompanionActiveScan
from app.models.companion_active_xray import CompanionActiveXray
from app.models.companion_active_day_surgery import CompanionActiveDaySurgery
from app.models.companion_active_major_surgery import CompanionActiveMajorSurgery
from app.models.companion_active_dressing import CompanionActiveDressing
from app.models.companion_active_oxygen import CompanionActiveOxygen
from app.services.opd_government_export import (
    parse_government_opd_export,
    parse_government_ipd_export,
    parse_government_export_auto,
    normalize_service_name,
)
from app.services.price_list_service_v2 import search_price_items_all_tables, get_price_from_all_tables
from app.models.companion_government_opd_export import CompanionGovernmentOpdExport
from app.models.companion_government_ipd_export import CompanionGovernmentIpdExport
from app.models.companion_inventory_debit import CompanionInventoryDebit
from app.models.ward_stock import WardStock

router = APIRouter(prefix="/companion-visits", tags=["companion-visits"])


def _json_finite_qty(value: Any) -> float:
    """JSON/API-safe quantity (NaN/Inf from Excel or DB → 0)."""
    try:
        x = float(value if value is not None else 0)
    except (TypeError, ValueError):
        return 0.0
    return x if math.isfinite(x) else 0.0


def _json_finite_optional_float(value: Any) -> Optional[float]:
    """Optional monetary/total field: NaN/Inf → None for valid JSON."""
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _snapshot_line_dict_from_parsed(ln: Any) -> dict:
    """One government export line for lines_json and reconcile payloads (strict JSON floats)."""
    return {
        "description": getattr(ln, "description", None) or "",
        "quantity": _json_finite_qty(getattr(ln, "quantity", None)),
        "unit": getattr(ln, "unit", None),
        "total": _json_finite_optional_float(getattr(ln, "total", None)),
    }


class CompanionVisitCreate(BaseModel):
    """Payload for creating a companion visit (Records)."""
    external_card_number: str
    external_visit_number: str
    client_name: Optional[str] = None


class CompanionVisitUpdate(BaseModel):
    """Payload for updating a companion visit."""
    external_card_number: Optional[str] = None
    external_visit_number: Optional[str] = None
    client_name: Optional[str] = None
    status: Optional[str] = None  # open | closed
    admission_deposit_amount: Optional[float] = None
    admission_deposit_receipt_number: Optional[str] = None


class CompanionVisitResponse(BaseModel):
    """Single companion visit for API response."""
    id: int
    external_card_number: str
    external_visit_number: str
    client_name: Optional[str]
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    closed_at: Optional[datetime] = None
    closed_by_id: Optional[int] = None
    reopened_at: Optional[datetime] = None
    reopened_by_id: Optional[int] = None
    reopen_reason: Optional[str] = None
    undertaking_status: Optional[str] = None
    undertaking_deposit_amount: Optional[float] = None
    undertaking_deposit_receipt_number: Optional[str] = None
    undertaking_requested_at: Optional[datetime] = None
    undertaking_requested_by_id: Optional[int] = None
    undertaking_requested_by_name: Optional[str] = None  # set by API from User
    undertaking_approved_at: Optional[datetime] = None
    undertaking_approved_by_id: Optional[int] = None
    undertaking_approved_by_name: Optional[str] = None
    undertaking_unapproved_at: Optional[datetime] = None
    undertaking_unapproved_by_id: Optional[int] = None
    undertaking_unapproved_by_name: Optional[str] = None
    undertaking_unapprove_reason: Optional[str] = None
    admission_deposit_amount: Optional[float] = None
    admission_deposit_receipt_number: Optional[str] = None
    admission_deposit_remaining: float = 0.0
    # Billing snapshot (computed from line items + undertaking deposit; for list/detail without extra round-trips)
    bill_total: float = 0.0
    paid_amount: float = 0.0
    balance_due: float = 0.0

    class Config:
        from_attributes = True


class UndertakingRequestBody(BaseModel):
    """Optional deposit amount when requesting an undertaking."""
    deposit_amount: Optional[float] = None
    deposit_receipt_number: Optional[str] = None


class UndertakingUpdateBody(BaseModel):
    """Update deposit amount on a pending undertaking."""
    deposit_amount: Optional[float] = None
    deposit_receipt_number: Optional[str] = None


class UndertakingUnapproveBody(BaseModel):
    """Reason required when unapproving an undertaking (audit)."""
    reason: str


class ReopenVisitBody(BaseModel):
    """Reason required for reopening a closed visit (audit)."""
    reason: str


class CreateFromGovernmentExportResponse(BaseModel):
    """Result of creating a companion visit from an uploaded GHIMS OPD or IPD export."""

    visit: CompanionVisitResponse
    export_kind: str  # opd | ipd
    added_count: int
    failed: List[Dict[str, Any]]


def _try_add_visit_item_from_government_line(
    db: Session,
    visit_id: int,
    description: str,
    quantity: float,
    created_by_id: int,
) -> tuple[bool, Optional[dict], Optional[str]]:
    """
    Match one government service line to the price list and insert a CompanionVisitItem.
    Does not commit. On success returns (True, extra, None) where extra has keys:
    added, match_type, matched_code, matched_name, matched_service_type, category, unit_price.
    """
    desc = (description or "").strip()
    qty = float(quantity) if quantity is not None else 1.0
    if not desc:
        return False, None, "Empty description"
    if qty <= 0:
        return False, None, "Invalid quantity"

    candidates: list = []
    for st in ("INVESTIGATIONS", "ULTRASOUND", "X RAY", "DAY SURGERY", "MAJOR SURGERY", "DRESSING AND TREATMENT ROOM", "DRESSING", "OXYGEN"):
        candidates.extend(search_price_items_all_tables(db, search_term=desc, service_type=st, file_type="procedure") or [])
    candidates.extend(search_price_items_all_tables(db, search_term=desc, file_type="product") or [])
    if not candidates:
        candidates = search_price_items_all_tables(db, search_term=normalize_service_name(desc), file_type=None) or []

    picked = _pick_best_price_match(candidates, desc)
    if not picked:
        return False, None, "No price list match found"

    type_name, item = picked

    matched_code = None
    matched_name = None
    matched_service_type = None
    category = None
    unit_price = 0.0

    if type_name == "product":
        matched_code = getattr(item, "medication_code", None) or getattr(item, "g_drg_code", None)
        matched_name = getattr(item, "product_name", None) or desc
        matched_service_type = None
        category = "drug"
        if matched_code:
            unit_price = float(get_price_from_all_tables(db, str(matched_code), is_insured=True))
    else:
        matched_code = getattr(item, "g_drg_code", None)
        matched_name = getattr(item, "service_name", None) or desc
        matched_service_type = getattr(item, "service_type", None)
        category = _service_type_to_category(matched_service_type)
        if matched_code:
            unit_price = float(
                get_price_from_all_tables(
                    db,
                    str(matched_code),
                    is_insured=True,
                    service_type=matched_service_type,
                    procedure_name=matched_name,
                )
            )

    if not matched_code:
        return False, None, "Matched price item has no code"

    new_item = CompanionVisitItem(
        companion_visit_id=visit_id,
        item_code=str(matched_code).strip(),
        item_name=str(matched_name).strip() or desc,
        category=category or "lab",
        unit_price=float(unit_price),
        quantity=float(qty),
        created_by_id=created_by_id,
    )
    db.add(new_item)
    db.flush()
    db.refresh(new_item)

    u = db.query(User).filter(User.id == getattr(new_item, "created_by_id", None)).first()
    added = {
        "id": new_item.id,
        "companion_visit_id": new_item.companion_visit_id,
        "item_code": new_item.item_code,
        "item_name": new_item.item_name,
        "category": new_item.category,
        "unit_price": float(new_item.unit_price),
        "quantity": float(new_item.quantity),
        "created_at": new_item.created_at,
        "created_by_id": getattr(new_item, "created_by_id", None),
        "created_by_name": (u.full_name or u.username) if u else None,
        "receipt_number": new_item.receipt_number,
        "paid_at": new_item.paid_at,
        "paid_by_id": new_item.paid_by_id,
        "paid_by_name": None,
        "payment_method": new_item.payment_method,
        "admission_deposit_applied": getattr(new_item, "admission_deposit_applied", None),
        "admission_deposit_line_receipt": getattr(new_item, "admission_deposit_line_receipt", None),
    }

    extra = {
        "added": added,
        "match_type": type_name,
        "matched_code": str(matched_code),
        "matched_name": matched_name,
        "matched_service_type": matched_service_type,
        "category": category,
        "unit_price": float(unit_price),
    }
    return True, extra, None


def _companion_item_row_amount(it: CompanionVisitItem) -> float:
    return float(it.unit_price or 0) * float(it.quantity or 1)


def _companion_item_cancelled(it: CompanionVisitItem) -> bool:
    return bool(getattr(it, "cancelled", False))


ADMISSION_DEPOSIT_PAYMENT_METHOD = "admission_deposit"
MIXED_DEPOSIT_CASH_PAYMENT_METHOD = "mixed"


def _admission_deposit_applied_on_item(it: CompanionVisitItem) -> float:
    """Amount of admission deposit pool applied to this line."""
    v_raw = getattr(it, "admission_deposit_applied", None)
    if v_raw is not None and float(v_raw) > 0.005:
        return float(v_raw)
    if (getattr(it, "payment_method", None) or "").strip() == ADMISSION_DEPOSIT_PAYMENT_METHOD:
        return _companion_item_row_amount(it)
    return 0.0


def _companion_item_is_paid(it: CompanionVisitItem) -> bool:
    T = round(_companion_item_row_amount(it), 2)
    if T <= 0:
        return True
    v_raw = getattr(it, "admission_deposit_applied", None)
    pm = (getattr(it, "payment_method", None) or "").strip()
    ln = (getattr(it, "admission_deposit_line_receipt", None) or "").strip()
    rn = (it.receipt_number or "").strip()

    # Legacy: full line from deposit, synthetic stored in receipt_number only
    if v_raw is None and pm == ADMISSION_DEPOSIT_PAYMENT_METHOD:
        return bool(rn and it.paid_at)

    if v_raw is not None:
        d = float(v_raw)
        rem = round(T - d, 2)
        if rem <= 0.005:
            return bool(ln and it.paid_at)
        return bool(ln and rn and it.paid_at)

    return bool(rn and it.paid_at)


def _billing_summary_for_items(items: List[CompanionVisitItem], deposit: float) -> Tuple[float, float, float]:
    """Returns (bill_total, paid_amount, balance_due). Matches companion billing UI logic."""
    total = sum(_companion_item_row_amount(it) for it in items if not _companion_item_cancelled(it))
    paid = sum(
        _companion_item_row_amount(it)
        for it in items
        if not _companion_item_cancelled(it) and _companion_item_is_paid(it)
    )
    bal = max(0.0, float(total) - float(paid) - float(deposit or 0.0))
    return (float(total), float(paid), float(bal))


def _admission_deposit_consumed_from_items(items: List[CompanionVisitItem]) -> float:
    consumed = 0.0
    for it in items:
        if _companion_item_cancelled(it):
            continue
        consumed += _admission_deposit_applied_on_item(it)
    return float(consumed)


def _admission_deposit_remaining_for_visit(visit: CompanionVisit, items: List[CompanionVisitItem]) -> float:
    cap = float(getattr(visit, "admission_deposit_amount", None) or 0.0)
    if cap <= 0:
        return 0.0
    return max(0.0, round(cap - _admission_deposit_consumed_from_items(items), 2))


def _max_admission_deposit_receipt_suffix(items: List[CompanionVisitItem], base: str) -> int:
    if not base:
        return 0
    pat = re.compile(rf"^{re.escape(base)}-(\d+)$")
    max_n = 0
    for it in items:
        candidates = [(getattr(it, "admission_deposit_line_receipt", None) or "").strip()]
        pm = (getattr(it, "payment_method", None) or "").strip()
        if pm == ADMISSION_DEPOSIT_PAYMENT_METHOD and getattr(it, "admission_deposit_applied", None) is None:
            candidates.append((it.receipt_number or "").strip())
        for rn in candidates:
            if not rn:
                continue
            m = pat.match(rn)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return max_n


def _batch_visit_billing_summaries(db: Session, visits: List[CompanionVisit]) -> Dict[int, Tuple[float, float, float]]:
    if not visits:
        return {}
    ids = [v.id for v in visits]
    deposit_map = {v.id: float(getattr(v, "undertaking_deposit_amount", None) or 0) for v in visits}
    all_items = db.query(CompanionVisitItem).filter(CompanionVisitItem.companion_visit_id.in_(ids)).all()
    by_vid: Dict[int, List[CompanionVisitItem]] = defaultdict(list)
    for it in all_items:
        by_vid[it.companion_visit_id].append(it)
    return {vid: _billing_summary_for_items(by_vid.get(vid, []), deposit_map.get(vid, 0.0)) for vid in ids}


def _visit_all_items_paid(visit_id: int, db: Session) -> bool:
    """True if every bill item is fully paid (including deposit + top-up splits)."""
    items = db.query(CompanionVisitItem).filter(CompanionVisitItem.companion_visit_id == visit_id).all()
    if not items:
        return True
    for it in items:
        if _companion_item_cancelled(it):
            continue
        if not _companion_item_is_paid(it):
            return False
    return True


@router.post("/", response_model=CompanionVisitResponse, status_code=status.HTTP_201_CREATED)
def create_companion_visit(
    data: CompanionVisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Records", "Billing", "Admin"])),
):
    """
    Create a companion visit (service) from external system identifiers.
    Records use this when they receive card number and visit number from the government system.
    """
    # Normalize for uniqueness check
    card = (data.external_card_number or "").strip()
    visit = (data.external_visit_number or "").strip()
    if not card or not visit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="external_card_number and external_visit_number are required",
        )
    existing = (
        db.query(CompanionVisit)
        .filter(
            CompanionVisit.external_card_number == card,
            CompanionVisit.external_visit_number == visit,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A visit with this card number and visit number already exists",
        )
    visit_obj = CompanionVisit(
        external_card_number=card,
        external_visit_number=visit,
        client_name=(data.client_name or "").strip() or None,
        status="open",
        created_by=get_effective_creator_id(db, current_user),
    )
    db.add(visit_obj)
    db.commit()
    db.refresh(visit_obj)
    return _visit_to_response(visit_obj, db)


@router.get("/", response_model=List[CompanionVisitResponse])
def list_companion_visits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    card_number: Optional[str] = Query(None, description="Filter by external card number"),
    visit_number: Optional[str] = Query(None, description="Filter by external visit number"),
    status_filter: Optional[str] = Query(None, description="Filter by status: open | closed"),
    undertaking_status: Optional[str] = Query(None, description="Filter by undertaking_status: pending | approved | rejected"),
    date_from: Optional[date] = Query(None, description="From date (created_at)"),
    date_to: Optional[date] = Query(None, description="To date (created_at)"),
):
    """
    List companion visits with optional filters.
    Used by Records to see created services; by Lab/Scan/Xray/Billing to find a visit; by Management for pending undertakings.
    """
    q = db.query(CompanionVisit)
    if card_number and card_number.strip():
        q = q.filter(CompanionVisit.external_card_number.like(f"%{card_number.strip()}%"))
    if visit_number and visit_number.strip():
        q = q.filter(CompanionVisit.external_visit_number.like(f"%{visit_number.strip()}%"))
    if status_filter and status_filter.strip():
        q = q.filter(CompanionVisit.status == status_filter.strip().lower())
    if undertaking_status and undertaking_status.strip():
        q = q.filter(CompanionVisit.undertaking_status == undertaking_status.strip().lower())
    if date_from:
        q = q.filter(CompanionVisit.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(CompanionVisit.created_at <= datetime.combine(date_to, datetime.max.time()))
    q = q.order_by(CompanionVisit.created_at.desc())
    visits = q.all()
    summaries = _batch_visit_billing_summaries(db, visits)
    return [_visit_to_response(v, db, billing=summaries.get(v.id)) for v in visits]


@router.post(
    "/create-from-government-export",
    response_model=CreateFromGovernmentExportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_companion_visit_from_government_export(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Records", "Admin"])),
):
    """
    Create a companion visit from a GHIMS OPD billing export or IPD invoice (Excel/HTML).

    Parses the file, creates the visit (card + visit/claim number), auto-matches each line to the
    co-payment price list, and saves the same snapshot used by OPD/IPD reconcile so later
    "check vs government" runs without re-uploading.
    """
    import hashlib

    fn = (file.filename or "upload").strip()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    try:
        export_kind, export = parse_government_export_auto(data, filename=fn)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    if export_kind == "opd":
        card = (export.patient_no or "").strip()
        vn = (export.claim_no or "").strip()
        client_name = (export.patient_name or "").strip() or None
    else:
        card = (export.patient_no or "").strip()
        # IPD: companion visit number must match GHIMS visit number, not admission number.
        vn = (export.visit_no or export.invoice_no or "").strip()
        client_name = (export.patient_name or "").strip() or None

    if not card or not vn:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read card number and visit/claim number from the export.",
        )

    existing = (
        db.query(CompanionVisit)
        .filter(
            CompanionVisit.external_card_number == card,
            CompanionVisit.external_visit_number == vn,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "A visit with this card number and visit number already exists. Open it and use government import from the bill view if needed.",
                "existing_visit_id": existing.id,
            },
        )

    visit_obj = CompanionVisit(
        external_card_number=card,
        external_visit_number=vn,
        client_name=client_name,
        status="open",
        created_by=get_effective_creator_id(db, current_user),
    )
    db.add(visit_obj)
    db.flush()

    creator_id = get_effective_creator_id(db, current_user)
    failed: List[Dict[str, Any]] = []
    added_count = 0
    for ln in export.lines:
        ok, _extra, reason = _try_add_visit_item_from_government_line(
            db, visit_obj.id, ln.description, _json_finite_qty(ln.quantity), creator_id
        )
        if ok:
            added_count += 1
        else:
            failed.append({"description": ln.description, "reason": reason or "Unknown"})

    if added_count == 0:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "No export lines matched the Hospital price list.",
                "failed": failed,
            },
        )

    sha = hashlib.sha256(data).hexdigest()
    lines_json = json.dumps([_snapshot_line_dict_from_parsed(ln) for ln in export.lines], ensure_ascii=False)

    if export_kind == "opd":
        snap = CompanionGovernmentOpdExport(
            companion_visit_id=visit_obj.id,
            claim_no=(export.claim_no or "").strip(),
            patient_no=(export.patient_no or "").strip(),
            claim_status=export.claim_status,
            insurance_no=export.insurance_no,
            patient_name=export.patient_name,
            service_date=export.service_date,
            service_type=export.service_type,
            file_sha256=sha,
            lines_json=lines_json,
            imported_by_id=creator_id,
        )
        db.add(snap)
    else:
        snap = CompanionGovernmentIpdExport(
            companion_visit_id=visit_obj.id,
            invoice_no=export.invoice_no,
            admission_no=export.admission_no,
            visit_no=export.visit_no,
            patient_no=export.patient_no,
            patient_name=export.patient_name,
            invoice_date=export.invoice_date,
            admission_date=export.admission_date,
            discharge_date=export.discharge_date,
            insurance_no=export.insurance_no,
            billing_info=export.billing_info,
            file_sha256=sha,
            lines_json=lines_json,
            imported_by_id=creator_id,
        )
        db.add(snap)

    db.commit()
    db.refresh(visit_obj)
    summaries = _batch_visit_billing_summaries(db, [visit_obj])
    visit_resp = _visit_to_response(visit_obj, db, billing=summaries.get(visit_obj.id))
    return CreateFromGovernmentExportResponse(
        visit=visit_resp,
        export_kind=export_kind,
        added_count=added_count,
        failed=failed,
    )


# --- Active investigations (Lab Head chooses which appear as cards) ---

@router.get("/active-investigations")
def list_active_investigations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List g_drg_codes that are shown as cards on Add Investigation page. Any authenticated user can read."""
    rows = db.query(CompanionActiveInvestigation).order_by(CompanionActiveInvestigation.g_drg_code).all()
    return [{"g_drg_code": r.g_drg_code} for r in rows]


class ActiveInvestigationCreate(BaseModel):
    g_drg_code: str


@router.post("/active-investigations", status_code=status.HTTP_201_CREATED)
def add_active_investigation(
    data: ActiveInvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab Head", "Doctor", "PA", "Admin"])),
):
    """Add an investigation to the card list. Lab Head, Doctor, PA, or Admin."""
    code = (data.g_drg_code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="g_drg_code is required")
    existing = db.query(CompanionActiveInvestigation).filter(CompanionActiveInvestigation.g_drg_code == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in card list")
    row = CompanionActiveInvestigation(g_drg_code=code)
    db.add(row)
    db.commit()
    return {"g_drg_code": code}


@router.delete("/active-investigations/{g_drg_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_active_investigation(
    g_drg_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Lab Head", "Doctor", "PA", "Admin"])),
):
    """Remove an investigation from the card list. Lab Head, Doctor, PA, or Admin."""
    row = db.query(CompanionActiveInvestigation).filter(CompanionActiveInvestigation.g_drg_code == g_drg_code).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in card list")
    db.delete(row)
    db.commit()
    return None


# --- Active scans (Scan Head chooses which appear as cards) ---

@router.get("/active-scans")
def list_active_scans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List g_drg_codes that are shown as cards on Add Scan page. Any authenticated user can read."""
    rows = db.query(CompanionActiveScan).order_by(CompanionActiveScan.g_drg_code).all()
    return [{"g_drg_code": r.g_drg_code} for r in rows]


class ActiveScanCreate(BaseModel):
    g_drg_code: str


@router.post("/active-scans", status_code=status.HTTP_201_CREATED)
def add_active_scan(
    data: ActiveScanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Scan", "Scan Head", "Doctor", "PA", "Admin"])),
):
    """Add a scan to the card list. Scan, Scan Head, Doctor, PA, or Admin."""
    code = (data.g_drg_code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="g_drg_code is required")
    existing = db.query(CompanionActiveScan).filter(CompanionActiveScan.g_drg_code == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in card list")
    row = CompanionActiveScan(g_drg_code=code)
    db.add(row)
    db.commit()
    return {"g_drg_code": code}


@router.delete("/active-scans/{g_drg_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_active_scan(
    g_drg_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Scan", "Scan Head", "Doctor", "PA", "Admin"])),
):
    """Remove a scan from the card list. Scan, Scan Head, Doctor, PA, or Admin."""
    row = db.query(CompanionActiveScan).filter(CompanionActiveScan.g_drg_code == g_drg_code).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in card list")
    db.delete(row)
    db.commit()
    return None


# --- Active X-rays (Xray Head chooses which appear as cards) ---

@router.get("/active-xrays")
def list_active_xrays(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List g_drg_codes that are shown as cards on Add X-ray page. Any authenticated user can read."""
    rows = db.query(CompanionActiveXray).order_by(CompanionActiveXray.g_drg_code).all()
    return [{"g_drg_code": r.g_drg_code} for r in rows]


class ActiveXrayCreate(BaseModel):
    g_drg_code: str


@router.post("/active-xrays", status_code=status.HTTP_201_CREATED)
def add_active_xray(
    data: ActiveXrayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Xray", "Xray Head", "Doctor", "PA", "Admin"])),
):
    """Add an X-ray to the card list. Xray, Xray Head, Doctor, PA, or Admin."""
    code = (data.g_drg_code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="g_drg_code is required")
    existing = db.query(CompanionActiveXray).filter(CompanionActiveXray.g_drg_code == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in card list")
    row = CompanionActiveXray(g_drg_code=code)
    db.add(row)
    db.commit()
    return {"g_drg_code": code}


@router.delete("/active-xrays/{g_drg_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_active_xray(
    g_drg_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Xray", "Xray Head", "Doctor", "PA", "Admin"])),
):
    """Remove an X-ray from the card list. Xray, Xray Head, Doctor, PA, or Admin."""
    row = db.query(CompanionActiveXray).filter(CompanionActiveXray.g_drg_code == g_drg_code).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in card list")
    db.delete(row)
    db.commit()
    return None


# --- Active day surgeries (Nurse/Doctor/PA choose which appear as cards) ---

@router.get("/active-day-surgeries")
def list_active_day_surgeries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List g_drg_codes that are shown as cards on Add Day Surgery page. Any authenticated user can read."""
    rows = db.query(CompanionActiveDaySurgery).order_by(CompanionActiveDaySurgery.g_drg_code).all()
    return [{"g_drg_code": r.g_drg_code} for r in rows]


class ActiveDaySurgeryCreate(BaseModel):
    g_drg_code: str


@router.post("/active-day-surgeries", status_code=status.HTTP_201_CREATED)
def add_active_day_surgery(
    data: ActiveDaySurgeryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Add a day surgery to the card list. Nurse, Doctor, PA, or Admin."""
    code = (data.g_drg_code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="g_drg_code is required")
    existing = db.query(CompanionActiveDaySurgery).filter(CompanionActiveDaySurgery.g_drg_code == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in card list")
    row = CompanionActiveDaySurgery(g_drg_code=code)
    db.add(row)
    db.commit()
    return {"g_drg_code": code}


@router.delete("/active-day-surgeries/{g_drg_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_active_day_surgery(
    g_drg_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Remove a day surgery from the card list. Nurse, Doctor, PA, or Admin."""
    row = db.query(CompanionActiveDaySurgery).filter(CompanionActiveDaySurgery.g_drg_code == g_drg_code).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in card list")
    db.delete(row)
    db.commit()
    return None


# --- Active major surgeries (Nurse/Doctor/PA choose which appear as cards) ---

@router.get("/active-major-surgeries")
def list_active_major_surgeries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List g_drg_codes that are shown as cards on Add Major Surgery page. Any authenticated user can read."""
    rows = db.query(CompanionActiveMajorSurgery).order_by(CompanionActiveMajorSurgery.g_drg_code).all()
    return [{"g_drg_code": r.g_drg_code} for r in rows]


class ActiveMajorSurgeryCreate(BaseModel):
    g_drg_code: str


@router.post("/active-major-surgeries", status_code=status.HTTP_201_CREATED)
def add_active_major_surgery(
    data: ActiveMajorSurgeryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Add a major surgery to the card list. Nurse, Doctor, PA, or Admin."""
    code = (data.g_drg_code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="g_drg_code is required")
    existing = db.query(CompanionActiveMajorSurgery).filter(CompanionActiveMajorSurgery.g_drg_code == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in card list")
    row = CompanionActiveMajorSurgery(g_drg_code=code)
    db.add(row)
    db.commit()
    return {"g_drg_code": code}


@router.delete("/active-major-surgeries/{g_drg_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_active_major_surgery(
    g_drg_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Remove a major surgery from the card list. Nurse, Doctor, PA, or Admin."""
    row = db.query(CompanionActiveMajorSurgery).filter(CompanionActiveMajorSurgery.g_drg_code == g_drg_code).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in card list")
    db.delete(row)
    db.commit()
    return None


# --- Active dressing / treatment room (Nurse/Doctor/PA choose which appear as cards) ---

@router.get("/active-dressings")
def list_active_dressings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List g_drg_codes that are shown as cards on Dressing room page. Any authenticated user can read."""
    rows = db.query(CompanionActiveDressing).order_by(CompanionActiveDressing.g_drg_code).all()
    return [{"g_drg_code": r.g_drg_code} for r in rows]


class ActiveDressingCreate(BaseModel):
    g_drg_code: str


@router.post("/active-dressings", status_code=status.HTTP_201_CREATED)
def add_active_dressing(
    data: ActiveDressingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Add a dressing/treatment room service to the card list. Nurse, Doctor, PA, or Admin."""
    code = (data.g_drg_code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="g_drg_code is required")
    existing = db.query(CompanionActiveDressing).filter(CompanionActiveDressing.g_drg_code == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in card list")
    row = CompanionActiveDressing(g_drg_code=code)
    db.add(row)
    db.commit()
    return {"g_drg_code": code}


@router.delete("/active-dressings/{g_drg_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_active_dressing(
    g_drg_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Remove a dressing/treatment room service from the card list. Nurse, Doctor, PA, or Admin."""
    row = db.query(CompanionActiveDressing).filter(CompanionActiveDressing.g_drg_code == g_drg_code).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in card list")
    db.delete(row)
    db.commit()
    return None


# Ward stock preview for companion inventory debit — MUST stay above any `/{visit_id}` route so
# `/companion-visits/ward-stock` is not matched as visit_id = "ward-stock".


class CompanionWardStockItem(BaseModel):
    """Aggregated ward stock for one product code (sums quantity across store rows)."""

    product_code: str
    product_name: str
    quantity: float


@router.get("/ward-stock", response_model=List[CompanionWardStockItem])
def companion_department_stock_list(
    ward: str = Query(..., min_length=1, description="Department/ward name (must match ward stock)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(["Nurse", "Doctor", "PA", "Pharmacy", "Pharmacy Head", "Billing", "Admin"])
    ),
):
    """List products in stock for a department (for companion inventory debit item pickers)."""
    w = (ward or "").strip()
    if not w:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ward is required")

    rows = (
        db.query(
            WardStock.product_code.label("product_code"),
            func.max(WardStock.product_name).label("product_name"),
            func.sum(WardStock.quantity).label("quantity"),
        )
        .filter(WardStock.ward == w)
        .group_by(WardStock.product_code)
        .order_by(func.max(WardStock.product_name))
        .all()
    )
    return [
        CompanionWardStockItem(
            product_code=r.product_code,
            product_name=(r.product_name or "").strip() or r.product_code,
            quantity=float(r.quantity or 0),
        )
        for r in rows
    ]


# --- Active oxygen (Nurse/Doctor/PA choose which appear as cards) ---

@router.get("/active-oxygens")
def list_active_oxygens(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List g_drg_codes that are shown as cards on Add Oxygen page. Any authenticated user can read."""
    rows = db.query(CompanionActiveOxygen).order_by(CompanionActiveOxygen.g_drg_code).all()
    return [{"g_drg_code": r.g_drg_code} for r in rows]


class ActiveOxygenCreate(BaseModel):
    g_drg_code: str


@router.post("/active-oxygens", status_code=status.HTTP_201_CREATED)
def add_active_oxygen(
    data: ActiveOxygenCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Add an oxygen service to the card list. Nurse, Doctor, PA, or Admin."""
    code = (data.g_drg_code or "").strip()
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="g_drg_code is required")
    existing = db.query(CompanionActiveOxygen).filter(CompanionActiveOxygen.g_drg_code == code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in card list")
    row = CompanionActiveOxygen(g_drg_code=code)
    db.add(row)
    db.commit()
    return {"g_drg_code": code}


@router.delete("/active-oxygens/{g_drg_code}", status_code=status.HTTP_204_NO_CONTENT)
def remove_active_oxygen(
    g_drg_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Remove an oxygen service from the card list. Nurse, Doctor, PA, or Admin."""
    row = db.query(CompanionActiveOxygen).filter(CompanionActiveOxygen.g_drg_code == g_drg_code).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not in card list")
    db.delete(row)
    db.commit()
    return None


# --- Parse government drugs PDF (drug name + quantity) ---

def _parse_drugs_pdf_bytes(data: bytes) -> List[dict]:
    """Extract drug name and quantity from PDF. Returns list of { drug_name, quantity }."""
    try:
        import pdfplumber
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF parsing not available (install pdfplumber)",
        )
    out = []
    seen = set()
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            # If this is a scanned/image PDF, pdfplumber won't have any chars to parse.
            # In that case, require OCR (Tesseract) rather than silently returning empty.
            if (not getattr(page, "chars", None) or len(page.chars) == 0) and getattr(page, "images", None) and len(page.images) > 0:
                # Try OCR if available
                if shutil.which("tesseract"):
                    try:
                        import pytesseract  # type: ignore
                        from PIL import Image  # type: ignore
                    except Exception:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="This PDF is scanned (image-based). Install pytesseract + pillow to OCR it, or upload a text-based PDF.",
                        )

                    try:
                        # Render page to image (pdfplumber uses pypdfium2 under the hood)
                        pil_img = page.to_image(resolution=200).original
                        if not isinstance(pil_img, Image.Image):
                            pil_img = pil_img.convert("RGB")
                        text = pytesseract.image_to_string(pil_img)
                    except Exception as e:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"OCR failed: {str(e)}",
                        )

                    for line in (text or "").splitlines():
                        line = line.strip()
                        if not line or len(line) < 2:
                            continue
                        last_num = re.search(r"[\d.,]+\s*$", line)
                        if last_num:
                            try:
                                qty = float(last_num.group().replace(",", "").strip())
                            except ValueError:
                                qty = 1.0
                            name = line[: last_num.start()].strip()
                        else:
                            name = line
                            qty = 1.0
                        if not name:
                            continue
                        if name.lower() in ("drug", "drug name", "quantity", "qty", "no", "no.", "item", "medication"):
                            continue
                        key = (name.lower(), qty)
                        if key in seen:
                            continue
                        seen.add(key)
                        out.append({"drug_name": name, "quantity": qty if qty > 0 else 1.0})
                    continue
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="This PDF is scanned (image-based) and has no selectable text. Install Tesseract OCR (and pytesseract) or upload a text-based PDF.",
                )

            tables = page.extract_tables()
            if tables:
                for table in tables:
                    for row in table:
                        if not row or not any(cell and str(cell).strip() for cell in row):
                            continue
                        cells = [str(c or "").strip() for c in row]
                        text_parts = []
                        qty = None
                        for c in cells:
                            if not c:
                                continue
                            num = re.match(r"^\d+(?:\.\d+)?$", c.strip())
                            if num and qty is None:
                                qty = float(num.group())
                            else:
                                text_parts.append(c)
                        name = " ".join(text_parts).strip() if text_parts else ""
                        if not name:
                            continue
                        if name.lower() in ("drug", "drug name", "quantity", "qty", "no", "no.", "item", "medication"):
                            continue
                        qty = qty if qty is not None and qty > 0 else 1.0
                        key = (name.lower(), qty)
                        if key in seen:
                            continue
                        seen.add(key)
                        out.append({"drug_name": name, "quantity": qty})
            text = page.extract_text()
            if text and not tables:
                for line in text.splitlines():
                    line = line.strip()
                    if not line or len(line) < 2:
                        continue
                    last_num = re.search(r"[\d.,]+\s*$", line)
                    if last_num:
                        try:
                            qty = float(last_num.group().replace(",", "").strip())
                        except ValueError:
                            qty = 1.0
                        name = line[: last_num.start()].strip()
                    else:
                        name = line
                        qty = 1.0
                    if not name or (name.lower(), qty) in seen:
                        continue
                    seen.add((name.lower(), qty))
                    out.append({"drug_name": name, "quantity": qty})
    return out


class ParsedDrugLine(BaseModel):
    drug_name: str
    quantity: float


class GovernmentServiceLineResponse(BaseModel):
    description: str
    quantity: float
    unit: Optional[str] = None
    total: Optional[float] = None
    normalized: str


class CompanionBilledItemResponse(BaseModel):
    id: int
    item_code: str
    item_name: str
    category: str
    unit_price: float
    quantity: float
    receipt_number: Optional[str] = None
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    normalized: str


class CompanionOpdGovernmentReconciliationResponse(BaseModel):
    """Reconciliation result for OPD or IPD government export vs companion bill."""
    visit_id: int
    external_card_number: str
    external_visit_number: str

    claim_status: Optional[str] = None
    insurance_no: Optional[str] = None
    claim_no: Optional[str] = None
    patient_name: Optional[str] = None
    patient_no: Optional[str] = None
    service_date: Optional[str] = None
    service_type: Optional[str] = None

    # IPD-specific (optional; when source is IPD invoice)
    invoice_no: Optional[str] = None
    admission_no: Optional[str] = None
    visit_no: Optional[str] = None
    invoice_date: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    billing_info: Optional[str] = None

    government_lines: List[GovernmentServiceLineResponse]
    billed_items: List[CompanionBilledItemResponse]

    missing_in_billing: List[GovernmentServiceLineResponse]
    extra_in_billing: List[CompanionBilledItemResponse]
    quantity_mismatches: List[dict]
    imported_at: Optional[datetime] = None
    imported_by_id: Optional[int] = None
    imported_by_name: Optional[str] = None
    file_sha256: Optional[str] = None


def _build_companion_reconciliation_response(
    *,
    visit: CompanionVisit,
    export_meta: dict,
    gov_lines: list[dict],
    billed_items: list[dict],
    import_info: Optional[dict] = None,
) -> dict:
    def _tokens(s: str) -> set[str]:
        # normalized strings are already lowercase-ish; keep only alphanum tokens
        return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if t}

    def _similarity(a: str, b: str) -> float:
        ta = _tokens(a)
        tb = _tokens(b)
        if not ta or not tb:
            return 0.0
        inter = len(ta & tb)
        union = len(ta | tb)
        return inter / union if union else 0.0

    def _best_match(target_norm: str, candidates: list[str]) -> Optional[str]:
        if not target_norm:
            return None
        # exact first
        if target_norm in candidates:
            return target_norm
        # containment next (covers "hepatitis b surface antigen hbv" vs "hepatitis b surface antigen")
        for c in candidates:
            if not c:
                continue
            if c in target_norm or target_norm in c:
                # require at least 3 tokens to avoid very short accidental matches
                if len(_tokens(c)) >= 3 and len(_tokens(target_norm)) >= 3:
                    return c
        # token-overlap fallback
        best = None
        best_score = 0.0
        for c in candidates:
            if not c:
                continue
            score = _similarity(target_norm, c)
            if score > best_score:
                best_score = score
                best = c
        # Threshold chosen to avoid accidental matches but allow minor construction differences
        if best and best_score >= 0.75:
            return best
        return None

    gov_by_norm: dict[str, list[dict]] = {}
    for g in gov_lines:
        gov_by_norm.setdefault(g["normalized"], []).append(g)

    billed_by_norm: dict[str, list[dict]] = {}
    for b in billed_items:
        billed_by_norm.setdefault(b["normalized"], []).append(b)

    billed_norms = [k for k in billed_by_norm.keys() if k]

    missing_in_billing: list[dict] = []
    quantity_mismatches: list[dict] = []

    matched_billed_norms: set[str] = set()

    for gov_norm, glines in gov_by_norm.items():
        if not gov_norm:
            continue
        match_norm = _best_match(gov_norm, billed_norms)
        if not match_norm:
            missing_in_billing.extend(glines)
            continue
        matched_billed_norms.add(match_norm)
        gov_qty = sum(_json_finite_qty(x.get("quantity")) for x in glines)
        billed_qty = sum(_json_finite_qty(x.get("quantity")) for x in billed_by_norm.get(match_norm, []))
        if abs(gov_qty - billed_qty) > 1e-6:
            quantity_mismatches.append(
                {
                    "normalized": match_norm,
                    "government_quantity": gov_qty,
                    "billed_quantity": billed_qty,
                    "government_lines": glines,
                    "billed_items": billed_by_norm.get(match_norm, []),
                }
            )

    extra_in_billing: list[dict] = []
    for billed_norm, blines in billed_by_norm.items():
        if not billed_norm:
            continue
        if billed_norm not in matched_billed_norms:
            # If a billed norm matches any gov norm fuzzily, don't mark as extra.
            gov_norms = [k for k in gov_by_norm.keys() if k]
            if _best_match(billed_norm, gov_norms):
                continue
            extra_in_billing.extend(blines)

    out = {
        "visit_id": visit.id,
        "external_card_number": visit.external_card_number,
        "external_visit_number": visit.external_visit_number,
        "claim_status": export_meta.get("claim_status"),
        "insurance_no": export_meta.get("insurance_no"),
        "claim_no": export_meta.get("claim_no"),
        "patient_name": export_meta.get("patient_name"),
        "patient_no": export_meta.get("patient_no"),
        "service_date": export_meta.get("service_date"),
        "service_type": export_meta.get("service_type"),
        "invoice_no": export_meta.get("invoice_no"),
        "admission_no": export_meta.get("admission_no"),
        "visit_no": export_meta.get("visit_no"),
        "invoice_date": export_meta.get("invoice_date"),
        "admission_date": export_meta.get("admission_date"),
        "discharge_date": export_meta.get("discharge_date"),
        "billing_info": export_meta.get("billing_info"),
        "government_lines": gov_lines,
        "billed_items": billed_items,
        "missing_in_billing": missing_in_billing,
        "extra_in_billing": extra_in_billing,
        "quantity_mismatches": quantity_mismatches,
        "imported_at": None,
        "imported_by_id": None,
        "imported_by_name": None,
        "file_sha256": None,
    }
    if import_info:
        out.update({k: import_info.get(k) for k in ["imported_at", "imported_by_id", "imported_by_name", "file_sha256"]})
    return out


@router.get("/{visit_id}/government-opd-export/reconcile", response_model=CompanionOpdGovernmentReconciliationResponse)
def reconcile_companion_visit_from_saved_government_export(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "PA", "Admin"])),
):
    """
    Reconcile using the last saved government OPD export for this visit (no file upload required).
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    snap = db.query(CompanionGovernmentOpdExport).filter(CompanionGovernmentOpdExport.companion_visit_id == visit_id).first()
    if not snap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No government OPD export imported for this visit yet.")

    import json

    gov_raw = json.loads(snap.lines_json or "[]")
    gov_lines = [
        {
            "description": x.get("description"),
            "quantity": float(x.get("quantity") or 0),
            "unit": x.get("unit"),
            "total": x.get("total"),
            "normalized": normalize_service_name(x.get("description") or ""),
        }
        for x in gov_raw
        if x.get("description")
    ]

    items = (
        db.query(CompanionVisitItem)
        .filter(CompanionVisitItem.companion_visit_id == visit_id)
        .order_by(CompanionVisitItem.created_at.asc())
        .all()
    )
    billed_items = [
        {
            "id": it.id,
            "item_code": it.item_code,
            "item_name": it.item_name,
            "category": it.category,
            "unit_price": float(it.unit_price),
            "quantity": float(it.quantity),
            "receipt_number": it.receipt_number,
            "created_by_id": getattr(it, "created_by_id", None),
            "normalized": normalize_service_name(it.item_name),
        }
        for it in items
        if not bool(getattr(it, "cancelled", False))
    ]
    uids = {x.get("created_by_id") for x in billed_items if x.get("created_by_id")}
    if uids:
        rows = db.query(User).filter(User.id.in_(list(uids))).all()
        user_map = {u.id: (u.full_name or u.username) for u in rows}
        for x in billed_items:
            cid = x.get("created_by_id")
            if cid:
                x["created_by_name"] = user_map.get(cid)

    imported_by_name = None
    if snap.imported_by_id:
        u = db.query(User).filter(User.id == snap.imported_by_id).first()
        if u:
            imported_by_name = u.full_name or u.username

    export_meta = {
        "claim_status": snap.claim_status,
        "insurance_no": snap.insurance_no,
        "claim_no": snap.claim_no,
        "patient_name": snap.patient_name,
        "patient_no": snap.patient_no,
        "service_date": snap.service_date,
        "service_type": snap.service_type,
    }
    import_info = {
        "imported_at": snap.imported_at,
        "imported_by_id": snap.imported_by_id,
        "imported_by_name": imported_by_name,
        "file_sha256": snap.file_sha256,
    }
    return _build_companion_reconciliation_response(
        visit=visit, export_meta=export_meta, gov_lines=gov_lines, billed_items=billed_items, import_info=import_info
    )


@router.delete("/{visit_id}/government-opd-export", status_code=status.HTTP_204_NO_CONTENT)
def clear_saved_government_opd_export(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"])),
):
    """Admin-only: delete the saved gov OPD export snapshot for a visit."""
    snap = db.query(CompanionGovernmentOpdExport).filter(CompanionGovernmentOpdExport.companion_visit_id == visit_id).first()
    if not snap:
        return None
    db.delete(snap)
    db.commit()
    return None


# --- IPD (in-patient) government invoice: save, reconcile, clear (same flow as OPD) ---

@router.get("/{visit_id}/government-ipd-export/reconcile", response_model=CompanionOpdGovernmentReconciliationResponse)
def reconcile_companion_visit_from_saved_ipd_export(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "PA", "Admin"])),
):
    """Reconcile using the last saved government IPD invoice for this visit (no file upload)."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    snap = db.query(CompanionGovernmentIpdExport).filter(CompanionGovernmentIpdExport.companion_visit_id == visit_id).first()
    if not snap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No government IPD invoice imported for this visit yet.")

    import json
    gov_raw = json.loads(snap.lines_json or "[]")
    gov_lines = [
        {
            "description": x.get("description"),
            "quantity": float(x.get("quantity") or 0),
            "unit": x.get("unit"),
            "total": x.get("total"),
            "normalized": normalize_service_name(x.get("description") or ""),
        }
        for x in gov_raw
        if x.get("description")
    ]
    items = (
        db.query(CompanionVisitItem)
        .filter(CompanionVisitItem.companion_visit_id == visit_id)
        .order_by(CompanionVisitItem.created_at.asc())
        .all()
    )
    billed_items = [
        {
            "id": it.id,
            "item_code": it.item_code,
            "item_name": it.item_name,
            "category": it.category,
            "unit_price": float(it.unit_price),
            "quantity": float(it.quantity),
            "receipt_number": it.receipt_number,
            "created_by_id": getattr(it, "created_by_id", None),
            "normalized": normalize_service_name(it.item_name),
        }
        for it in items
        if not bool(getattr(it, "cancelled", False))
    ]
    uids = {x.get("created_by_id") for x in billed_items if x.get("created_by_id")}
    if uids:
        rows = db.query(User).filter(User.id.in_(list(uids))).all()
        user_map = {u.id: (u.full_name or u.username) for u in rows}
        for x in billed_items:
            cid = x.get("created_by_id")
            if cid:
                x["created_by_name"] = user_map.get(cid)
    imported_by_name = None
    if snap.imported_by_id:
        u = db.query(User).filter(User.id == snap.imported_by_id).first()
        if u:
            imported_by_name = u.full_name or u.username
    export_meta = {
        "claim_no": snap.admission_no,
        "patient_no": snap.patient_no,
        "patient_name": snap.patient_name,
        "service_date": snap.invoice_date or snap.admission_date,
        "insurance_no": snap.insurance_no,
        "invoice_no": snap.invoice_no,
        "admission_no": snap.admission_no,
        "visit_no": snap.visit_no,
        "invoice_date": snap.invoice_date,
        "admission_date": snap.admission_date,
        "discharge_date": snap.discharge_date,
        "billing_info": snap.billing_info,
    }
    import_info = {
        "imported_at": snap.imported_at,
        "imported_by_id": snap.imported_by_id,
        "imported_by_name": imported_by_name,
        "file_sha256": snap.file_sha256,
    }
    return _build_companion_reconciliation_response(
        visit=visit, export_meta=export_meta, gov_lines=gov_lines, billed_items=billed_items, import_info=import_info
    )


@router.delete("/{visit_id}/government-ipd-export", status_code=status.HTTP_204_NO_CONTENT)
def clear_saved_government_ipd_export(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"])),
):
    """Admin-only: delete the saved gov IPD invoice snapshot for a visit."""
    snap = db.query(CompanionGovernmentIpdExport).filter(CompanionGovernmentIpdExport.companion_visit_id == visit_id).first()
    if not snap:
        return None
    db.delete(snap)
    db.commit()
    return None


@router.post("/{visit_id}/reconcile-ipd-government", response_model=CompanionOpdGovernmentReconciliationResponse)
async def reconcile_companion_visit_with_ipd_government_export(
    visit_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "PA", "Admin"])),
):
    """
    Upload government IPD (in-patient) invoice; save snapshot and return reconciliation.
    Re-import when new data is added on GHIMS. Same add-missing / find-price flow as OPD.
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if not file.filename or not (file.filename.lower().endswith(".xls") or file.filename.lower().endswith(".xlsx")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be .xls or .xlsx")
    data = await file.read()
    try:
        export = parse_government_ipd_export(data, filename=file.filename or "upload")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    import hashlib, json
    sha = hashlib.sha256(data).hexdigest()
    gov_lines = [
        {
            "description": ln.description,
            "quantity": float(ln.quantity),
            "unit": ln.unit,
            "total": ln.total,
            "normalized": normalize_service_name(ln.description),
        }
        for ln in export.lines
    ]
    lines_json = json.dumps(
        [{"description": ln.description, "quantity": float(ln.quantity), "unit": ln.unit, "total": ln.total} for ln in export.lines],
        ensure_ascii=False,
    )
    snap = db.query(CompanionGovernmentIpdExport).filter(CompanionGovernmentIpdExport.companion_visit_id == visit_id).first()
    if snap:
        snap.invoice_no = export.invoice_no
        snap.admission_no = export.admission_no
        snap.visit_no = export.visit_no
        snap.patient_no = export.patient_no
        snap.patient_name = export.patient_name
        snap.invoice_date = export.invoice_date
        snap.admission_date = export.admission_date
        snap.discharge_date = export.discharge_date
        snap.insurance_no = export.insurance_no
        snap.billing_info = export.billing_info
        snap.file_sha256 = sha
        snap.lines_json = lines_json
        snap.imported_by_id = get_effective_creator_id(db, current_user)
        snap.imported_at = utcnow()
    else:
        snap = CompanionGovernmentIpdExport(
            companion_visit_id=visit_id,
            invoice_no=export.invoice_no,
            admission_no=export.admission_no,
            visit_no=export.visit_no,
            patient_no=export.patient_no,
            patient_name=export.patient_name,
            invoice_date=export.invoice_date,
            admission_date=export.admission_date,
            discharge_date=export.discharge_date,
            insurance_no=export.insurance_no,
            billing_info=export.billing_info,
            file_sha256=sha,
            lines_json=lines_json,
            imported_by_id=get_effective_creator_id(db, current_user),
        )
        db.add(snap)
    db.commit()

    items = (
        db.query(CompanionVisitItem)
        .filter(CompanionVisitItem.companion_visit_id == visit_id)
        .order_by(CompanionVisitItem.created_at.asc())
        .all()
    )
    billed_items = [
        {
            "id": it.id,
            "item_code": it.item_code,
            "item_name": it.item_name,
            "category": it.category,
            "unit_price": float(it.unit_price),
            "quantity": float(it.quantity),
            "receipt_number": it.receipt_number,
            "created_by_id": getattr(it, "created_by_id", None),
            "normalized": normalize_service_name(it.item_name),
        }
        for it in items
        if not bool(getattr(it, "cancelled", False))
    ]
    uids = {x.get("created_by_id") for x in billed_items if x.get("created_by_id")}
    user_map = {}
    if uids:
        rows = db.query(User).filter(User.id.in_(list(uids))).all()
        user_map = {u.id: (u.full_name or u.username) for u in rows}
        for x in billed_items:
            cid = x.get("created_by_id")
            if cid:
                x["created_by_name"] = user_map.get(cid)
    imported_by_name = current_user.full_name or current_user.username
    export_meta = {
        "claim_no": export.admission_no,
        "patient_no": export.patient_no,
        "patient_name": export.patient_name,
        "service_date": export.invoice_date or export.admission_date,
        "insurance_no": export.insurance_no,
        "invoice_no": export.invoice_no,
        "admission_no": export.admission_no,
        "visit_no": export.visit_no,
        "invoice_date": export.invoice_date,
        "admission_date": export.admission_date,
        "discharge_date": export.discharge_date,
        "billing_info": export.billing_info,
    }
    import_info = {
        "imported_at": snap.imported_at,
        "imported_by_id": snap.imported_by_id,
        "imported_by_name": imported_by_name,
        "file_sha256": snap.file_sha256,
    }
    return _build_companion_reconciliation_response(
        visit=visit, export_meta=export_meta, gov_lines=gov_lines, billed_items=billed_items, import_info=import_info
    )


class AddMissingFromGovernmentLine(BaseModel):
    description: str
    quantity: float = 1.0


class AddMissingFromGovernmentRequest(BaseModel):
    """
    Bulk-add missing government services to a Companion visit.
    The system will lookup the co-payment price from the HMS price list and use the quantity from the export.
    """

    category: str  # lab | scan | xray | drug | inpatient
    lines: List[AddMissingFromGovernmentLine]


class AddMissingFromGovernmentResult(BaseModel):
    added: List[CompanionVisitItemResponse]
    failed: List[dict]


class PriceSuggestion(BaseModel):
    item_code: str
    item_name: str
    file_type: str
    service_type: Optional[str] = None
    unit_price: float
    score: float


class PriceSuggestionsResponse(BaseModel):
    query: str
    category: str
    suggestions: List[PriceSuggestion]


class ConfirmFromGovernmentLine(BaseModel):
    """Single government line to confirm into billing using price list."""
    description: str
    quantity: float = 1.0


class ConfirmFromGovernmentResponse(BaseModel):
    added: Optional[CompanionVisitItemResponse] = None
    matched: bool
    match_type: Optional[str] = None  # procedure | surgery | unmapped_drg | product
    matched_code: Optional[str] = None
    matched_name: Optional[str] = None
    matched_service_type: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[float] = None
    reason: Optional[str] = None


def _category_to_service_type(category: str) -> Optional[str]:
    c = (category or "").strip().lower()
    if c == "lab":
        return "INVESTIGATIONS"
    if c == "scan":
        return "ULTRASOUND"
    if c == "xray":
        return "X RAY"
    if c == "day_surgery":
        return "DAY SURGERY"
    if c == "major_surgery":
        return "MAJOR SURGERY"
    if c == "dressing":
        return "DRESSING AND TREATMENT ROOM"
    if c == "oxygen":
        return "OXYGEN"
    return None


def _service_type_to_category(service_type: Optional[str]) -> str:
    st = (service_type or "").strip().upper()
    if st == "INVESTIGATIONS":
        return "lab"
    if st == "ULTRASOUND":
        return "scan"
    if st == "X RAY":
        return "xray"
    if st == "DAY SURGERY":
        return "day_surgery"
    if st == "MAJOR SURGERY":
        return "major_surgery"
    if st == "DRESSING AND TREATMENT ROOM" or st == "DRESSING":
        return "dressing"
    if st == "OXYGEN":
        return "oxygen"
    return "lab"


def _pick_best_price_match(results: list, description: str):
    """
    results: list of tuples (type_name, model_instance) from search_price_items_all_tables
    Prefer exact/contains/fuzzy name match, then first result.
    """
    def _tokens(s: str) -> set[str]:
        return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if t}

    def _similarity(a: str, b: str) -> float:
        ta = _tokens(a)
        tb = _tokens(b)
        if not ta or not tb:
            return 0.0
        inter = len(ta & tb)
        union = len(ta | tb)
        return inter / union if union else 0.0

    target = normalize_service_name(description)
    if not results:
        return None

    scored: list[tuple[float, int, tuple]] = []
    for type_name, item in results:
        name = getattr(item, "service_name", None) or getattr(item, "product_name", None) or ""
        cand = normalize_service_name(str(name))
        if not cand or not target:
            continue

        # exact
        if cand == target:
            score = 1.0
        # contains (covers GHIMS longer constructions)
        elif cand in target or target in cand:
            # require at least 3 tokens to avoid accidental matches
            if len(_tokens(cand)) >= 3 and len(_tokens(target)) >= 3:
                score = 0.95
            else:
                score = _similarity(target, cand)
        else:
            score = _similarity(target, cand)

        # Prefer procedure rows if tied (OPD services)
        type_bias = 0 if type_name == "procedure" else 1
        scored.append((score, type_bias, (type_name, item)))

    if scored:
        scored.sort(key=lambda x: (-x[0], x[1]))
        best_score, _, best = scored[0]
        # Safety threshold: accept only strong matches; otherwise fallback to first search result.
        if best_score >= 0.75:
            return best

    return results[0]


def _tokens_lower(s: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", (s or "").lower()) if t}


def _jaccard(a: str, b: str) -> float:
    ta = _tokens_lower(a)
    tb = _tokens_lower(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _score_name_match(query_norm: str, cand_norm: str) -> float:
    if not query_norm or not cand_norm:
        return 0.0
    if query_norm == cand_norm:
        return 1.0
    if (cand_norm in query_norm or query_norm in cand_norm) and len(_tokens_lower(cand_norm)) >= 3:
        return 0.95
    return _jaccard(query_norm, cand_norm)


@router.get("/{visit_id}/price-suggestions", response_model=PriceSuggestionsResponse)
def get_price_suggestions_for_government_line(
    visit_id: int,
    category: str,
    q: str,
    limit: int = 15,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "PA", "Admin"])),
):
    """
    Suggest similar price list items for a government line description (for officer confirmation).
    Uses fuzzy matching tolerant of extra wording/structure.
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    cat = (category or "").strip().lower()
    if cat not in ("lab", "scan", "xray", "drug", "inpatient", "day_surgery", "major_surgery", "dressing", "oxygen", "inventory_debit"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")

    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="q is required")

    service_type = _category_to_service_type(cat)
    query_norm = normalize_service_name(query)

    # Narrow initial search using first few tokens (avoid pulling huge tables)
    toks = list(_tokens_lower(query_norm))
    narrow = " ".join(toks[:4]) if toks else query_norm

    if cat in ("lab", "scan", "xray", "day_surgery", "major_surgery", "dressing", "oxygen") and service_type:
        raw = search_price_items_all_tables(db, search_term=narrow, service_type=service_type, file_type="procedure")
        if not raw:
            raw = search_price_items_all_tables(db, search_term=query_norm, service_type=service_type, file_type="procedure")
    elif cat == "drug" or cat == "inventory_debit":
        raw = search_price_items_all_tables(db, search_term=narrow, file_type="product")
        if not raw:
            raw = search_price_items_all_tables(db, search_term=query_norm, file_type="product")
    else:
        raw = search_price_items_all_tables(db, search_term=narrow, file_type=None)
        if not raw:
            raw = search_price_items_all_tables(db, search_term=query_norm, file_type=None)

    suggestions: list[dict] = []
    for type_name, item in raw:
        name = getattr(item, "service_name", None) or getattr(item, "product_name", None) or ""
        cand_norm = normalize_service_name(str(name))
        score = _score_name_match(query_norm, cand_norm)
        if score <= 0:
            continue

        if type_name == "product":
            code = getattr(item, "medication_code", None) or getattr(item, "g_drg_code", None)
            unit = get_price_from_all_tables(db, str(code), is_insured=True) if code else 0.0
            suggestions.append(
                {
                    "item_code": str(code),
                    "item_name": getattr(item, "product_name", None) or str(name),
                    "file_type": type_name,
                    "service_type": getattr(item, "sub_category_1", None) or getattr(item, "sub_category_2", None),
                    "unit_price": float(unit),
                    "score": float(score),
                }
            )
        else:
            code = getattr(item, "g_drg_code", None)
            unit = (
                get_price_from_all_tables(db, str(code), is_insured=True, service_type=service_type, procedure_name=getattr(item, "service_name", None))
                if code
                else 0.0
            )
            suggestions.append(
                {
                    "item_code": str(code),
                    "item_name": getattr(item, "service_name", None) or str(name),
                    "file_type": type_name,
                    "service_type": getattr(item, "service_type", None),
                    "unit_price": float(unit),
                    "score": float(score),
                }
            )

    suggestions.sort(key=lambda x: (-x["score"], x["item_name"]))
    suggestions = suggestions[: max(1, min(50, int(limit)))]

    return {"query": query, "category": cat, "suggestions": suggestions}


@router.post("/{visit_id}/items/confirm-from-opd-export-line", response_model=ConfirmFromGovernmentResponse)
def confirm_single_item_from_opd_export_line(
    visit_id: int,
    payload: ConfirmFromGovernmentLine,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "PA", "Admin"])),
):
    """
    Confirm a single government line into Companion billing with minimal human interaction.

    - Auto-matches the best price list entry (fuzzy matching).
    - Auto-detects category (lab/scan/xray/drug) based on matched service_type/table.
    - Uses quantity from government line.
    - Allowed even if visit is closed (billing may need to finish after closure).
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    qty = float(payload.quantity) if payload.quantity is not None else 1.0
    ok, extra, reason = _try_add_visit_item_from_government_line(
        db,
        visit_id,
        payload.description or "",
        qty,
        get_effective_creator_id(db, current_user),
    )
    if not ok or not extra:
        return {"matched": False, "reason": reason or "Failed"}

    db.commit()
    return {
        "added": extra["added"],
        "matched": True,
        "match_type": extra["match_type"],
        "matched_code": extra["matched_code"],
        "matched_name": extra["matched_name"],
        "matched_service_type": extra["matched_service_type"],
        "category": extra["category"],
        "unit_price": extra["unit_price"],
    }


@router.post("/{visit_id}/items/add-missing-from-opd-export", response_model=AddMissingFromGovernmentResult)
def add_missing_items_from_opd_export(
    visit_id: int,
    payload: AddMissingFromGovernmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "PA", "Admin"])),
):
    """
    Bulk add items to a Companion visit by matching government export descriptions to the HMS price list.

    - Uses price list co-payment (insured) pricing.
    - Uses export quantity.
    - Adds created_by_id for audit.
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    # Allowed for Billing/Admin even if visit is closed (billing may continue after closure).

    category = (payload.category or "").strip().lower()
    if category not in ("lab", "scan", "xray", "drug", "inpatient", "day_surgery", "major_surgery", "dressing", "oxygen"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")

    service_type = _category_to_service_type(category)
    added: list[dict] = []
    failed: list[dict] = []

    for ln in payload.lines or []:
        desc = (ln.description or "").strip()
        qty = float(ln.quantity) if ln.quantity is not None else 1.0
        if not desc:
            failed.append({"description": desc, "reason": "Empty description"})
            continue
        if qty <= 0:
            failed.append({"description": desc, "reason": "Invalid quantity"})
            continue

        try:
            # Try searching the price list by description.
            # For lab/scan/xray/surgeries/dressing, restrict to procedures with matching service_type for better accuracy.
            if category in ("lab", "scan", "xray", "day_surgery", "major_surgery", "dressing", "oxygen") and service_type:
                candidates = search_price_items_all_tables(db, search_term=desc, service_type=service_type, file_type="procedure")
                if not candidates:
                    # Fallback: use normalized description (removes parentheses and punctuation)
                    candidates = search_price_items_all_tables(
                        db, search_term=normalize_service_name(desc), service_type=service_type, file_type="procedure"
                    )
            elif category == "drug":
                candidates = search_price_items_all_tables(db, search_term=desc, file_type="product")
                if not candidates:
                    candidates = search_price_items_all_tables(db, search_term=normalize_service_name(desc), file_type="product")
            else:
                candidates = search_price_items_all_tables(db, search_term=desc, file_type=None)
                if not candidates:
                    candidates = search_price_items_all_tables(db, search_term=normalize_service_name(desc), file_type=None)

            picked = _pick_best_price_match(candidates, desc)
            if not picked:
                failed.append({"description": desc, "reason": "No price list match found"})
                continue

            type_name, item = picked
            if type_name == "product":
                item_code = getattr(item, "medication_code", None) or getattr(item, "g_drg_code", None)
                item_name = getattr(item, "product_name", None) or desc
                price = get_price_from_all_tables(db, str(item_code), is_insured=True, service_type=None, procedure_name=None) if item_code else 0.0
            else:
                item_code = getattr(item, "g_drg_code", None)
                item_name = getattr(item, "service_name", None) or desc
                price = get_price_from_all_tables(
                    db,
                    str(item_code),
                    is_insured=True,
                    service_type=service_type,
                    procedure_name=item_name,
                ) if item_code else 0.0

            if item_code is None or str(item_code).strip() == "":
                failed.append({"description": desc, "reason": "Matched price item has no code"})
                continue

            # Create item on the visit
            new_item = CompanionVisitItem(
                companion_visit_id=visit_id,
                item_code=str(item_code).strip(),
                item_name=str(item_name).strip() or desc,
                category=category,
                unit_price=float(price),
                quantity=float(qty),
                created_by_id=get_effective_creator_id(db, current_user),
            )
            db.add(new_item)
            db.flush()
            u = db.query(User).filter(User.id == getattr(new_item, "created_by_id", None)).first()
            added.append(
                {
                    "id": new_item.id,
                    "companion_visit_id": new_item.companion_visit_id,
                    "item_code": new_item.item_code,
                    "item_name": new_item.item_name,
                    "category": new_item.category,
                    "unit_price": float(new_item.unit_price),
                    "quantity": float(new_item.quantity),
                    "created_at": new_item.created_at,
                    "created_by_id": getattr(new_item, "created_by_id", None),
                    "created_by_name": (u.full_name or u.username) if u else None,
                    "receipt_number": new_item.receipt_number,
                    "paid_at": new_item.paid_at,
                    "paid_by_id": new_item.paid_by_id,
                    "paid_by_name": None,
                    "payment_method": new_item.payment_method,
                    "admission_deposit_applied": getattr(new_item, "admission_deposit_applied", None),
                    "admission_deposit_line_receipt": getattr(new_item, "admission_deposit_line_receipt", None),
                }
            )
        except Exception as e:
            failed.append({"description": desc, "reason": str(e)})

    db.commit()
    return {"added": added, "failed": failed}


@router.post("/{visit_id}/reconcile-opd-government", response_model=CompanionOpdGovernmentReconciliationResponse)
async def reconcile_companion_visit_with_opd_government_export(
    visit_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "PA", "Admin"])),
):
    """
    Companion Billing reconciliation against government OPD export.

    IMPORTANT matching constraints:
    - Government claim_no MUST match CompanionVisit.external_visit_number
    - Government patient_no MUST match CompanionVisit.external_card_number
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")

    data = await file.read()
    export = parse_government_opd_export(data, filename=file.filename or "upload")

    import hashlib, json
    sha = hashlib.sha256(data).hexdigest()

    claim_no = (export.claim_no or "").strip()
    patient_no = (export.patient_no or "").strip()
    if not claim_no or not patient_no:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read claim_no and patient_no from the uploaded file.",
        )

    # Enforce identity match: government -> companion visit
    if claim_no != (visit.external_visit_number or "").strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Visit number mismatch. File claim_no='{claim_no}' but selected visit is '{visit.external_visit_number}'.",
        )
    if patient_no != (visit.external_card_number or "").strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Card number mismatch. File patient_no='{patient_no}' but selected visit card is '{visit.external_card_number}'.",
        )

    gov_lines = [
        {
            "description": ln.description,
            "quantity": float(ln.quantity),
            "unit": ln.unit,
            "total": ln.total,
            "normalized": normalize_service_name(ln.description),
        }
        for ln in export.lines
    ]

    # Save snapshot for future checks (upload once, reuse later)
    snap = db.query(CompanionGovernmentOpdExport).filter(CompanionGovernmentOpdExport.companion_visit_id == visit_id).first()
    lines_json = json.dumps(
        [{"description": ln.description, "quantity": float(ln.quantity), "unit": ln.unit, "total": ln.total} for ln in export.lines],
        ensure_ascii=False,
    )
    if snap:
        snap.claim_no = claim_no
        snap.patient_no = patient_no
        snap.claim_status = export.claim_status
        snap.insurance_no = export.insurance_no
        snap.patient_name = export.patient_name
        snap.service_date = export.service_date
        snap.service_type = export.service_type
        snap.file_sha256 = sha
        snap.lines_json = lines_json
        snap.imported_by_id = get_effective_creator_id(db, current_user)
        snap.imported_at = utcnow()
    else:
        snap = CompanionGovernmentOpdExport(
            companion_visit_id=visit_id,
            claim_no=claim_no,
            patient_no=patient_no,
            claim_status=export.claim_status,
            insurance_no=export.insurance_no,
            patient_name=export.patient_name,
            service_date=export.service_date,
            service_type=export.service_type,
            file_sha256=sha,
            lines_json=lines_json,
            imported_by_id=get_effective_creator_id(db, current_user),
        )
        db.add(snap)
    db.commit()

    items = (
        db.query(CompanionVisitItem)
        .filter(CompanionVisitItem.companion_visit_id == visit_id)
        .order_by(CompanionVisitItem.created_at.asc())
        .all()
    )
    billed_items = [
        {
            "id": it.id,
            "item_code": it.item_code,
            "item_name": it.item_name,
            "category": it.category,
            "unit_price": float(it.unit_price),
            "quantity": float(it.quantity),
            "receipt_number": it.receipt_number,
            "created_by_id": getattr(it, "created_by_id", None),
            "normalized": normalize_service_name(it.item_name),
        }
        for it in items
        if not bool(getattr(it, "cancelled", False))
    ]
    # attach names
    uids = {x.get("created_by_id") for x in billed_items if x.get("created_by_id")}
    user_map = {}
    if uids:
        rows = db.query(User).filter(User.id.in_(list(uids))).all()
        user_map = {u.id: (u.full_name or u.username) for u in rows}
        for x in billed_items:
            cid = x.get("created_by_id")
            if cid:
                x["created_by_name"] = user_map.get(cid)

    imported_by_name = current_user.full_name or current_user.username
    export_meta = {
        "claim_status": export.claim_status,
        "insurance_no": export.insurance_no,
        "claim_no": export.claim_no,
        "patient_name": export.patient_name,
        "patient_no": export.patient_no,
        "service_date": export.service_date,
        "service_type": export.service_type,
    }
    import_info = {
        "imported_at": snap.imported_at,
        "imported_by_id": snap.imported_by_id,
        "imported_by_name": imported_by_name,
        "file_sha256": snap.file_sha256,
    }
    return _build_companion_reconciliation_response(
        visit=visit, export_meta=export_meta, gov_lines=gov_lines, billed_items=billed_items, import_info=import_info
    )


@router.post("/parse-drugs-pdf", response_model=List[ParsedDrugLine])
def parse_drugs_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Doctor", "PA", "Admin"])),
):
    """Parse a government-issued drugs PDF and return list of drug name + quantity. Does not add to any visit."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a PDF")
    data = file.file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF too large (max 10MB)")
    try:
        lines = _parse_drugs_pdf_bytes(data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Could not parse PDF: {str(e)}")
    return [ParsedDrugLine(drug_name=x["drug_name"], quantity=x["quantity"]) for x in lines]


def _normalize_header(h: str) -> str:
    return (h or "").strip().lower().replace(".", "").replace("_", " ")


_DRUG_HEADER_SKIP = frozenset({
    "drug", "drug name", "drugs", "item", "items", "item description", "item desc", "description",
    "quantity", "qty", "qty.", "no", "no.", "s/no", "sr no", "sr.", "medication",
    "medicines", "name", "particulars", "particular", "remarks", "rate", "amount", "uom",
})


def _is_header_like(s: str) -> bool:
    t = (s or "").strip().lower()
    if not t or len(t) > 120:
        return False
    if t in _DRUG_HEADER_SKIP:
        return True
    if re.match(r"^[\d.]+\s*$", t) or re.match(r"^[\d.]+\s+(item|description|quantity|qty|drug|no\.?)\s*$", t):
        return True
    return False


def _parse_drugs_excel_bytes(data: bytes, filename: str) -> List[dict]:
    """Extract item description and quantity from Excel (.xls, .xlsx) or HTML saved as .xls."""
    out: List[dict] = []
    seen: set = set()
    desc_col_name = None
    qty_col_name = None

    def add_row(name: str, qty: float) -> None:
        nonlocal out, seen
        if not name or _is_header_like(name):
            return
        try:
            q = float(qty) if qty is not None else 1.0
        except (TypeError, ValueError):
            q = 1.0
        if q <= 0 or q > 99999:
            return
        key = (name.strip().lower(), q)
        if key in seen:
            return
        seen.add(key)
        out.append({"drug_name": name.strip(), "quantity": q})

    # HTML saved as .xls (e.g. government export)
    if data.lstrip().startswith(b"<"):
        try:
            import pandas as pd
            dfs = pd.read_html(io.BytesIO(data))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not read Excel/HTML: {str(e)}",
            )
        for df in dfs:
            if df.empty or len(df.columns) < 2:
                continue
            cols = [str(c).strip() for c in df.columns]
            desc_idx = qty_idx = -1
            for i, c in enumerate(cols):
                n = _normalize_header(c)
                if "item" in n and "desc" in n or n == "item desc" or n == "description":
                    desc_idx = i
                if n in ("qty", "quantity") or "qty" in n:
                    qty_idx = i
            if desc_idx < 0 or qty_idx < 0:
                continue
            for _, row in df.iterrows():
                try:
                    name = row.iloc[desc_idx]
                    qty_val = row.iloc[qty_idx]
                except IndexError:
                    continue
                if pd.isna(name) or (isinstance(name, str) and not name.strip()):
                    continue
                name_str = str(name).strip() if name is not None else ""
                if not name_str or name_str.lower().startswith("dispensed by"):
                    continue
                # Skip if quantity cell looks like header text (e.g. "Qty" as data)
                if pd.notna(qty_val) and isinstance(qty_val, str) and qty_val.strip().lower() in ("qty", "quantity"):
                    continue
                add_row(name_str, qty_val)
            if out:
                return out
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No table with 'Item description' and 'Quantity' columns found in the file.",
        )

    # Binary .xlsx
    if filename.lower().endswith(".xlsx"):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not open Excel file: {str(e)}",
            )
        try:
            for ws in wb.worksheets:
                rows = list(ws.iter_rows(values_only=True))
                if len(rows) < 2:
                    continue
                header = [str(c or "").strip() for c in rows[0]]
                desc_idx = qty_idx = -1
                for i, c in enumerate(header):
                    n = _normalize_header(c)
                    if "item" in n and "desc" in n or n == "description":
                        desc_idx = i
                    if n in ("qty", "quantity") or "qty" in n:
                        qty_idx = i
                if desc_idx < 0 or qty_idx < 0:
                    continue
                for row in rows[1:]:
                    if not row or desc_idx >= len(row):
                        continue
                    name = row[desc_idx]
                    name_str = str(name).strip() if name is not None else ""
                    if not name_str or name_str.lower().startswith("dispensed by"):
                        continue
                    qty_val = row[qty_idx] if qty_idx < len(row) else 1
                    add_row(name_str, qty_val)
                if out:
                    return out
        finally:
            wb.close()
    else:
        # .xls binary (xlrd)
        try:
            import xlrd
            wb = xlrd.open_workbook(file_contents=data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not open .xls file (is it HTML saved as .xls?): {str(e)}",
            )
        for sheet_idx in range(wb.nsheets):
            sh = wb.sheet_by_index(sheet_idx)
            if sh.nrows < 2:
                continue
            header = [str(sh.cell_value(0, c)).strip() for c in range(sh.ncols)]
            desc_idx = qty_idx = -1
            for i, c in enumerate(header):
                n = _normalize_header(c)
                if "item" in n and "desc" in n or n == "description":
                    desc_idx = i
                if n in ("qty", "quantity") or "qty" in n:
                    qty_idx = i
            if desc_idx < 0 or qty_idx < 0:
                continue
            for r in range(1, sh.nrows):
                if desc_idx >= sh.ncols:
                    continue
                name = sh.cell_value(r, desc_idx)
                name_str = str(name).strip() if name else ""
                if not name_str or name_str.lower().startswith("dispensed by"):
                    continue
                qty_val = sh.cell_value(r, qty_idx) if qty_idx < sh.ncols else 1
                add_row(name_str, qty_val)
            if out:
                return out

    if not out:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No table with 'Item description' and 'Quantity' columns found in the file.",
        )
    return out


@router.post("/parse-drugs-excel", response_model=List[ParsedDrugLine])
def parse_drugs_excel(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Doctor", "PA", "Admin"])),
):
    """Parse Excel (.xls or .xlsx) and return list of item description + quantity. Uses only Item description and Quantity columns."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name required")
    ext = file.filename.lower()
    if not (ext.endswith(".xls") or ext.endswith(".xlsx")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be .xls or .xlsx")
    data = file.file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File too large (max 10MB)")
    try:
        lines = _parse_drugs_excel_bytes(data, file.filename or "")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Could not parse Excel: {str(e)}")
    return [ParsedDrugLine(drug_name=x["drug_name"], quantity=x["quantity"]) for x in lines]


def _visit_to_response(
    visit: CompanionVisit,
    db: Session,
    billing: Optional[Tuple[float, float, float]] = None,
) -> CompanionVisitResponse:
    """Build visit response with optional undertaking_*_by_name fields and billing totals."""
    req_by_name = None
    if getattr(visit, "undertaking_requested_by_id", None):
        u = db.query(User).filter(User.id == visit.undertaking_requested_by_id).first()
        if u:
            req_by_name = u.full_name or u.username
    approved_by_name = None
    if getattr(visit, "undertaking_approved_by_id", None):
        u = db.query(User).filter(User.id == visit.undertaking_approved_by_id).first()
        if u:
            approved_by_name = u.full_name or u.username
    unapproved_by_name = None
    if getattr(visit, "undertaking_unapproved_by_id", None):
        u = db.query(User).filter(User.id == visit.undertaking_unapproved_by_id).first()
        if u:
            unapproved_by_name = u.full_name or u.username
    items_for_admission = db.query(CompanionVisitItem).filter(CompanionVisitItem.companion_visit_id == visit.id).all()
    if billing is None:
        dep = float(getattr(visit, "undertaking_deposit_amount", None) or 0)
        billing = _billing_summary_for_items(items_for_admission, dep)
    bill_total, paid_amount, balance_due = billing
    adm_amt = getattr(visit, "admission_deposit_amount", None)
    adm_rn = getattr(visit, "admission_deposit_receipt_number", None)
    adm_rem = _admission_deposit_remaining_for_visit(visit, items_for_admission)
    return CompanionVisitResponse(
        id=visit.id,
        external_card_number=visit.external_card_number,
        external_visit_number=visit.external_visit_number,
        client_name=visit.client_name,
        status=visit.status,
        created_by=visit.created_by,
        created_at=visit.created_at,
        updated_at=visit.updated_at,
        closed_at=getattr(visit, "closed_at", None),
        closed_by_id=getattr(visit, "closed_by_id", None),
        reopened_at=getattr(visit, "reopened_at", None),
        reopened_by_id=getattr(visit, "reopened_by_id", None),
        reopen_reason=getattr(visit, "reopen_reason", None),
        undertaking_status=getattr(visit, "undertaking_status", None),
        undertaking_deposit_amount=getattr(visit, "undertaking_deposit_amount", None),
        undertaking_deposit_receipt_number=getattr(visit, "undertaking_deposit_receipt_number", None),
        undertaking_requested_at=getattr(visit, "undertaking_requested_at", None),
        undertaking_requested_by_id=getattr(visit, "undertaking_requested_by_id", None),
        undertaking_requested_by_name=req_by_name,
        undertaking_approved_at=getattr(visit, "undertaking_approved_at", None),
        undertaking_approved_by_id=getattr(visit, "undertaking_approved_by_id", None),
        undertaking_approved_by_name=approved_by_name,
        undertaking_unapproved_at=getattr(visit, "undertaking_unapproved_at", None),
        undertaking_unapproved_by_id=getattr(visit, "undertaking_unapproved_by_id", None),
        undertaking_unapproved_by_name=unapproved_by_name,
        undertaking_unapprove_reason=getattr(visit, "undertaking_unapprove_reason", None),
        admission_deposit_amount=float(adm_amt) if adm_amt is not None else None,
        admission_deposit_receipt_number=(adm_rn or None),
        admission_deposit_remaining=adm_rem,
        bill_total=bill_total,
        paid_amount=paid_amount,
        balance_due=balance_due,
    )


@router.get("/{visit_id}", response_model=CompanionVisitResponse)
def get_companion_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single companion visit by id. Includes undertaking_requested_by_name for Management approval view."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    return _visit_to_response(visit, db)


@router.post("/{visit_id}/close", response_model=CompanionVisitResponse)
def close_companion_visit(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"])),
):
    """Close the visit. Allowed when all bill items are paid, or when undertaking has been approved. No further services can be added after close."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status == "closed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visit is already closed")
    all_paid = _visit_all_items_paid(visit_id, db)
    undertaking_approved = (visit.undertaking_status or "").strip().lower() == "approved"
    if not all_paid and not undertaking_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot close: not all items are paid and no approved undertaking. Either ensure all items are paid or request an undertaking for Management to approve.",
        )
    now = datetime.utcnow()
    visit.status = "closed"
    visit.closed_at = now
    visit.closed_by_id = get_effective_creator_id(db, current_user)
    db.commit()
    db.refresh(visit)
    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"Closed companion visit for card {visit.external_card_number} (visit {visit.external_visit_number}).")
    return _visit_to_response(visit, db)


@router.post("/{visit_id}/reopen", response_model=CompanionVisitResponse)
def reopen_companion_visit(
    request: Request,
    visit_id: int,
    data: ReopenVisitBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"])),
):
    """Reopen a closed visit. Admin only. Reason is required for auditing."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "closed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visit is not closed")
    reason = (data.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason for reopening is required for auditing")
    now = datetime.utcnow()
    visit.status = "open"
    visit.reopened_at = now
    visit.reopened_by_id = get_effective_creator_id(db, current_user)
    visit.reopen_reason = reason
    db.commit()
    db.refresh(visit)
    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"Admin reopened companion visit for card {visit.external_card_number} (reason: {reason[:50]}).")
    return _visit_to_response(visit, db)


@router.post("/{visit_id}/undertaking/request", response_model=CompanionVisitResponse)
def request_undertaking(
    visit_id: int,
    data: UndertakingRequestBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"])),
):
    """Start an undertaking process (client will pay later). Optional deposit_amount. Management must approve before the visit can be closed."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status == "closed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot request undertaking for a closed visit")
    if (visit.undertaking_status or "").strip().lower() in ("pending", "approved"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Undertaking already requested or approved")
    now = datetime.utcnow()
    visit.undertaking_status = "pending"
    visit.undertaking_requested_at = now
    visit.undertaking_requested_by_id = get_effective_creator_id(db, current_user)
    if data.deposit_amount is not None:
        visit.undertaking_deposit_amount = float(data.deposit_amount) if data.deposit_amount >= 0 else None
    else:
        visit.undertaking_deposit_amount = None
    if data.deposit_receipt_number is not None:
        visit.undertaking_deposit_receipt_number = (data.deposit_receipt_number or "").strip() or None
    else:
        visit.undertaking_deposit_receipt_number = None
    # reset any prior unapprove audit fields
    visit.undertaking_unapproved_at = None
    visit.undertaking_unapproved_by_id = None
    visit.undertaking_unapprove_reason = None
    db.commit()
    db.refresh(visit)
    return _visit_to_response(visit, db)


@router.patch("/{visit_id}/undertaking", response_model=CompanionVisitResponse)
def update_undertaking(
    visit_id: int,
    data: UndertakingUpdateBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update deposit amount on a pending undertaking. Only the officer who requested it or Billing/Admin."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if (visit.undertaking_status or "").strip().lower() != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending undertaking to update")
    roles = _get_user_roles(current_user, db)
    if visit.undertaking_requested_by_id != current_user.id and "Admin" not in roles and "Billing" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the officer who requested the undertaking or Billing/Admin can edit it")
    if data.deposit_amount is not None:
        visit.undertaking_deposit_amount = float(data.deposit_amount) if data.deposit_amount >= 0 else None
    if data.deposit_receipt_number is not None:
        visit.undertaking_deposit_receipt_number = (data.deposit_receipt_number or "").strip() or None
    db.commit()
    db.refresh(visit)
    return _visit_to_response(visit, db)


@router.post("/{visit_id}/undertaking/cancel", response_model=CompanionVisitResponse)
def cancel_undertaking(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending undertaking (e.g. when client pays in full). Only requester or Admin."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if (visit.undertaking_status or "").strip().lower() != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending undertaking to cancel")
    if visit.undertaking_requested_by_id != current_user.id and "Admin" not in _get_user_roles(current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the officer who requested the undertaking or Admin can cancel it")
    visit.undertaking_status = None
    visit.undertaking_deposit_amount = None
    visit.undertaking_deposit_receipt_number = None
    visit.undertaking_requested_at = None
    visit.undertaking_requested_by_id = None
    visit.undertaking_approved_at = None
    visit.undertaking_approved_by_id = None
    visit.undertaking_unapproved_at = None
    visit.undertaking_unapproved_by_id = None
    visit.undertaking_unapprove_reason = None
    db.commit()
    db.refresh(visit)
    return _visit_to_response(visit, db)


@router.post("/{visit_id}/undertaking/delete", response_model=CompanionVisitResponse)
def delete_undertaking_admin(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Admin"])),
):
    """Delete an undertaking record from a visit (Admin only). Clears all undertaking fields regardless of status."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    # If there's no undertaking to delete, return current state
    if not getattr(visit, "undertaking_requested_at", None) and not getattr(visit, "undertaking_status", None):
        return _visit_to_response(visit, db)
    visit.undertaking_status = None
    visit.undertaking_deposit_amount = None
    visit.undertaking_deposit_receipt_number = None
    visit.undertaking_requested_at = None
    visit.undertaking_requested_by_id = None
    visit.undertaking_approved_at = None
    visit.undertaking_approved_by_id = None
    visit.undertaking_unapproved_at = None
    visit.undertaking_unapproved_by_id = None
    visit.undertaking_unapprove_reason = None
    db.commit()
    db.refresh(visit)
    return _visit_to_response(visit, db)


@router.post("/{visit_id}/undertaking/approve", response_model=CompanionVisitResponse)
def approve_undertaking(
    request: Request,
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Management", "Admin"])),
):
    """Approve an undertaking. Management or Admin. After approval, the visit can be closed even with unpaid items."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if (visit.undertaking_status or "").strip().lower() != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending undertaking to approve")
    now = datetime.utcnow()
    visit.undertaking_status = "approved"
    visit.undertaking_approved_at = now
    visit.undertaking_approved_by_id = get_effective_creator_id(db, current_user)
    db.commit()
    db.refresh(visit)
    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"{current_user.full_name or current_user.username} ({current_user.role}) approved undertaking for companion visit (card {visit.external_card_number}).")
    return _visit_to_response(visit, db)


@router.post("/{visit_id}/undertaking/reject", response_model=CompanionVisitResponse)
def reject_undertaking(
    request: Request,
    visit_id: int,
    data: UndertakingUnapproveBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Management", "Admin"])),
):
    """Reject a pending undertaking. Management or Admin. Sets status to rejected and records reason."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if (visit.undertaking_status or "").strip().lower() != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending undertakings can be rejected")
    reason = (data.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason is required to reject an undertaking")
    now = datetime.utcnow()
    visit.undertaking_status = "rejected"
    visit.undertaking_unapproved_at = now
    visit.undertaking_unapproved_by_id = get_effective_creator_id(db, current_user)
    visit.undertaking_unapprove_reason = reason
    # clear any approval stamps (safety)
    visit.undertaking_approved_at = None
    visit.undertaking_approved_by_id = None
    db.commit()
    db.refresh(visit)
    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"{current_user.full_name or current_user.username} ({current_user.role}) rejected undertaking for companion visit (card {visit.external_card_number}). Reason: {reason[:80]}.")
    return _visit_to_response(visit, db)


@router.post("/{visit_id}/undertaking/revert-reject", response_model=CompanionVisitResponse)
def revert_rejected_undertaking(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Management", "Admin"])),
):
    """Revert a rejected undertaking back to pending. Management can revert their own rejections; Admin can revert any."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if (visit.undertaking_status or "").strip().lower() != "rejected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only rejected undertakings can be reverted")
    roles = _get_user_roles(current_user, db)
    if "Admin" not in roles and visit.undertaking_unapproved_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only revert undertakings you rejected")
    # back to pending and clear the rejection stamps (so it doesn't still look rejected)
    visit.undertaking_status = "pending"
    visit.undertaking_unapproved_at = None
    visit.undertaking_unapproved_by_id = None
    visit.undertaking_unapprove_reason = None
    db.commit()
    db.refresh(visit)
    return _visit_to_response(visit, db)


@router.post("/{visit_id}/undertaking/unapprove", response_model=CompanionVisitResponse)
def unapprove_undertaking(
    visit_id: int,
    data: UndertakingUnapproveBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Management", "Admin"])),
):
    """Unapprove an undertaking. Reason required for auditing. Sets status back to pending."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if (visit.undertaking_status or "").strip().lower() != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only approved undertakings can be unapproved")
    # Management can only reverse their own approval; Admin can reverse any.
    roles = _get_user_roles(current_user, db)
    if "Admin" not in roles and visit.undertaking_approved_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only reverse undertakings you approved")
    reason = (data.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason is required to unapprove an undertaking")
    now = datetime.utcnow()
    visit.undertaking_status = "pending"
    visit.undertaking_unapproved_at = now
    visit.undertaking_unapproved_by_id = get_effective_creator_id(db, current_user)
    visit.undertaking_unapprove_reason = reason
    # clear approval stamps
    visit.undertaking_approved_at = None
    visit.undertaking_approved_by_id = None
    db.commit()
    db.refresh(visit)
    return _visit_to_response(visit, db)


def _get_user_roles(user: User, db: Session) -> List[str]:
    """Return primary + additional roles for user."""
    from sqlalchemy.orm import joinedload
    u = db.query(User).options(joinedload(User.additional_roles)).filter(User.id == user.id).first()
    if not u:
        return [user.role]
    roles = [u.role]
    if u.additional_roles:
        roles.extend([ur.role for ur in u.additional_roles])
    return roles


def _can_edit_or_delete(visit: CompanionVisit, current_user: User, db: Session, action: str) -> bool:
    """
    Edit/delete: if open -> Records, Admin, Billing (Billing often creates visits from GHIMS upload).
    If closed -> only Admin.
    """
    user_roles = _get_user_roles(current_user, db)
    if "Admin" in user_roles:
        return True
    if visit.status == "closed":
        return False
    if action == "edit":
        return any(r in ["Records", "Admin", "Billing"] for r in user_roles)
    return any(r in ["Records", "Admin", "Billing"] for r in user_roles)


@router.patch("/{visit_id}", response_model=CompanionVisitResponse)
def update_companion_visit(
    visit_id: int,
    data: CompanionVisitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a companion visit (card number, visit number, client_name, status).
    Card/visit number can be corrected only when visit is open (officer error).
    Open visits: Records, Admin, or Billing can update (Billing can mark as closed).
    Closed visits: only Admin can update (client_name, status only; card/visit not changeable).
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if not _can_edit_or_delete(visit, current_user, db, "edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can edit a closed visit",
        )
    # Card number and visit number: only when visit is open (so officer can fix errors)
    if visit.status == "open" and (data.external_card_number is not None or data.external_visit_number is not None):
        card = (data.external_card_number or "").strip()
        visit_no = (data.external_visit_number or "").strip()
        if not card or not visit_no:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both external_card_number and external_visit_number are required when changing them",
            )
        existing = (
            db.query(CompanionVisit)
            .filter(
                CompanionVisit.external_card_number == card,
                CompanionVisit.external_visit_number == visit_no,
                CompanionVisit.id != visit_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A visit with this card number and visit number already exists",
            )
        visit.external_card_number = card
        visit.external_visit_number = visit_no
    if data.client_name is not None:
        visit.client_name = (data.client_name or "").strip() or None
    if data.admission_deposit_amount is not None or data.admission_deposit_receipt_number is not None:
        user_roles = _get_user_roles(current_user, db)
        if visit.status != "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admission deposit can only be changed on an open visit",
            )
        if not any(r in user_roles for r in ("Billing", "Admin")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Billing or Admin can set admission deposit",
            )
        visit_items = db.query(CompanionVisitItem).filter(CompanionVisitItem.companion_visit_id == visit_id).all()
        consumed = _admission_deposit_consumed_from_items(visit_items)
        if data.admission_deposit_amount is not None:
            amt = float(data.admission_deposit_amount)
            if amt < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="admission_deposit_amount cannot be negative",
                )
            if amt < consumed - 0.005:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Cannot reduce admission deposit below GH¢ {consumed:.2f} already applied to bill lines. "
                        "Reverse payments on those lines first if you need to lower the deposit cap."
                    ),
                )
            if amt == 0:
                visit.admission_deposit_amount = None
                visit.admission_deposit_receipt_number = None
            else:
                visit.admission_deposit_amount = amt
        if data.admission_deposit_receipt_number is not None:
            rn = (data.admission_deposit_receipt_number or "").strip() or None
            visit.admission_deposit_receipt_number = rn
        dep_now = float(getattr(visit, "admission_deposit_amount", None) or 0)
        if dep_now > 0 and not (visit.admission_deposit_receipt_number or "").strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="admission_deposit_receipt_number is required when admission deposit amount is set",
            )
        if dep_now <= 0:
            visit.admission_deposit_amount = None
            visit.admission_deposit_receipt_number = None
    if data.status is not None:
        s = (data.status or "").strip().lower()
        if s not in ("open", "closed"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="status must be 'open' or 'closed'",
            )
        if s == "closed":
            all_paid = _visit_all_items_paid(visit_id, db)
            undertaking_approved = (getattr(visit, "undertaking_status", None) or "").strip().lower() == "approved"
            if not all_paid and not undertaking_approved:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot close: not all items are paid and no approved undertaking.",
                )
            visit.closed_at = datetime.utcnow()
            visit.closed_by_id = get_effective_creator_id(db, current_user)
        visit.status = s
    db.commit()
    db.refresh(visit)
    return _visit_to_response(visit, db)


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_companion_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a companion visit and all dependent rows (bill lines, saved government imports, inventory debits).
    Open visits: Records, Billing, or Admin. Closed visits: only Admin.
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if not _can_edit_or_delete(visit, current_user, db, "delete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can delete a closed visit",
        )
    # Explicit cleanup so deletes succeed even when the DB does not enforce ON DELETE CASCADE (e.g. SQLite without FK pragma).
    db.query(CompanionGovernmentOpdExport).filter(CompanionGovernmentOpdExport.companion_visit_id == visit_id).delete(
        synchronize_session=False
    )
    db.query(CompanionGovernmentIpdExport).filter(CompanionGovernmentIpdExport.companion_visit_id == visit_id).delete(
        synchronize_session=False
    )
    db.query(CompanionInventoryDebit).filter(CompanionInventoryDebit.companion_visit_id == visit_id).delete(
        synchronize_session=False
    )
    db.query(CompanionVisitItem).filter(CompanionVisitItem.companion_visit_id == visit_id).delete(synchronize_session=False)
    db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).delete(synchronize_session=False)
    db.commit()
    return None


# --- Companion visit items (line items for billing: lab, scan, xray, drug) ---

class CompanionVisitItemCreate(BaseModel):
    """Payload for adding an item to a companion visit."""
    item_code: str
    item_name: str
    category: str  # lab, scan, xray, drug, oxygen, ...
    unit_price: float
    quantity: float = 1.0
    start_time: Optional[datetime] = None  # required for oxygen (billed hourly)
    end_time: Optional[datetime] = None


class CompanionVisitItemResponse(BaseModel):
    """Single line item on a companion visit."""
    id: int
    companion_visit_id: int
    item_code: str
    item_name: str
    category: str
    unit_price: float
    quantity: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    created_by_id: Optional[int] = None
    created_by_name: Optional[str] = None
    cancelled: bool = False
    cancelled_at: Optional[datetime] = None
    cancelled_by_id: Optional[int] = None
    cancelled_by_name: Optional[str] = None
    cancel_reason: Optional[str] = None
    receipt_number: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_by_id: Optional[int] = None
    paid_by_name: Optional[str] = None
    payment_method: Optional[str] = None
    admission_deposit_applied: Optional[float] = None
    admission_deposit_line_receipt: Optional[str] = None

    class Config:
        from_attributes = True


class CancelVisitItemResult(BaseModel):
    """Cancel result. If hard_deleted=True, item was removed (superadmin)."""
    hard_deleted: bool = False
    item: Optional[CompanionVisitItemResponse] = None


class CompanionVisitItemUpdate(BaseModel):
    """Payload for updating a companion visit item (e.g. custom inpatient fee)."""
    item_name: Optional[str] = None
    unit_price: Optional[float] = None


@router.get("/{visit_id}/items", response_model=List[CompanionVisitItemResponse])
def list_companion_visit_items(
    visit_id: int,
    category: Optional[str] = Query(None, description="Filter by category: lab, scan, xray, drug"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List line items for a companion visit. Optionally filter by category."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    q = db.query(CompanionVisitItem).filter(CompanionVisitItem.companion_visit_id == visit_id)
    if category and category.strip():
        q = q.filter(CompanionVisitItem.category == category.strip().lower())
    q = q.order_by(CompanionVisitItem.created_at.asc())
    items = q.all()
    # Attach created_by_name (best-effort)
    user_ids = {it.created_by_id for it in items if getattr(it, "created_by_id", None)}
    user_ids |= {it.cancelled_by_id for it in items if getattr(it, "cancelled_by_id", None)}
    user_ids |= {it.paid_by_id for it in items if getattr(it, "paid_by_id", None)}
    users = {}
    if user_ids:
        rows = db.query(User).filter(User.id.in_(list(user_ids))).all()
        users = {u.id: (u.full_name or u.username) for u in rows}
    out = []
    for it in items:
        # Pydantic from_attributes does not auto-add computed fields, so return dicts.
        out.append(
            {
                "id": it.id,
                "companion_visit_id": it.companion_visit_id,
                "item_code": it.item_code,
                "item_name": it.item_name,
                "category": it.category,
                "unit_price": float(it.unit_price),
                "quantity": float(it.quantity),
                "start_time": getattr(it, "start_time", None),
                "end_time": getattr(it, "end_time", None),
                "created_at": it.created_at,
                "created_by_id": getattr(it, "created_by_id", None),
                "created_by_name": users.get(getattr(it, "created_by_id", None)),
                "cancelled": bool(getattr(it, "cancelled", False)),
                "cancelled_at": getattr(it, "cancelled_at", None),
                "cancelled_by_id": getattr(it, "cancelled_by_id", None),
                "cancelled_by_name": users.get(getattr(it, "cancelled_by_id", None)),
                "cancel_reason": getattr(it, "cancel_reason", None),
                "receipt_number": it.receipt_number,
                "paid_at": it.paid_at,
                "paid_by_id": it.paid_by_id,
                "paid_by_name": users.get(getattr(it, "paid_by_id", None)),
                "payment_method": it.payment_method,
                "admission_deposit_applied": getattr(it, "admission_deposit_applied", None),
                "admission_deposit_line_receipt": getattr(it, "admission_deposit_line_receipt", None),
            }
        )
    return out


@router.post("/{visit_id}/items", response_model=CompanionVisitItemResponse, status_code=status.HTTP_201_CREATED)
def add_companion_visit_item(
    visit_id: int,
    data: CompanionVisitItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a line item (e.g. lab investigation) to a companion visit. Only when visit is open."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add items to a closed visit",
        )
    cat = (data.category or "").strip().lower()
    if cat not in ("lab", "scan", "xray", "drug", "inpatient", "day_surgery", "major_surgery", "dressing", "oxygen", "inventory_debit"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category must be one of: lab, scan, xray, drug, inpatient, day_surgery, major_surgery, dressing, oxygen, inventory_debit",
        )
    quantity = float(data.quantity) if data.quantity else 1.0
    start_time = data.start_time
    end_time = data.end_time
    if cat == "oxygen":
        if not start_time or not end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Oxygen requires start date/time and end date/time (billed hourly)",
            )
        if end_time <= start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date/time must be after start date/time",
            )
        quantity = (end_time - start_time).total_seconds() / 3600.0
        if quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duration must be positive",
            )
    item = CompanionVisitItem(
        companion_visit_id=visit_id,
        item_code=(data.item_code or "").strip(),
        item_name=(data.item_name or "").strip() or data.item_code,
        category=cat,
        unit_price=float(data.unit_price),
        quantity=quantity,
        start_time=start_time,
        end_time=end_time,
        created_by_id=get_effective_creator_id(db, current_user),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    # return with created_by_name for immediate UI display
    u = db.query(User).filter(User.id == getattr(item, "created_by_id", None)).first()
    return {
        "id": item.id,
        "companion_visit_id": item.companion_visit_id,
        "item_code": item.item_code,
        "item_name": item.item_name,
        "category": item.category,
        "unit_price": float(item.unit_price),
        "quantity": float(item.quantity),
        "start_time": getattr(item, "start_time", None),
        "end_time": getattr(item, "end_time", None),
        "created_at": item.created_at,
        "created_by_id": getattr(item, "created_by_id", None),
        "created_by_name": (u.full_name or u.username) if u else None,
        "cancelled": bool(getattr(item, "cancelled", False)),
        "cancelled_at": getattr(item, "cancelled_at", None),
        "cancelled_by_id": getattr(item, "cancelled_by_id", None),
        "cancelled_by_name": None,
        "cancel_reason": getattr(item, "cancel_reason", None),
        "receipt_number": item.receipt_number,
        "paid_at": item.paid_at,
        "paid_by_id": item.paid_by_id,
        "paid_by_name": None,
        "payment_method": item.payment_method,
        "admission_deposit_applied": getattr(item, "admission_deposit_applied", None),
        "admission_deposit_line_receipt": getattr(item, "admission_deposit_line_receipt", None),
    }


class CancelVisitItemBody(BaseModel):
    reason: str


@router.post("/{visit_id}/items/{item_id}/cancel", response_model=CancelVisitItemResult)
def cancel_companion_visit_item(
    request: Request,
    visit_id: int,
    item_id: int,
    data: CancelVisitItemBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "PA", "Nurse", "Admin"])),
):
    """
    Soft-cancel a companion bill item (strike-through) with required reason.
    - Normal users: keeps record (who/when/why)
    - Superadmin (ghost): hard deletes instead (no record)
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel items on a closed visit")

    item = db.query(CompanionVisitItem).filter(
        CompanionVisitItem.id == item_id,
        CompanionVisitItem.companion_visit_id == visit_id,
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    if _companion_item_is_paid(item):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel an item that has been paid")

    reason = (data.reason or "").strip()
    if not reason:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cancellation reason is required")

    if is_super_admin(current_user):
        # Ghost superadmin: no cancellation record; hard-delete from DB.
        db.delete(item)
        db.commit()
        return {"hard_deleted": True, "item": None}

    item.cancelled = True
    item.cancelled_at = utcnow()
    item.cancelled_by_id = current_user.id
    item.cancel_reason = reason
    db.commit()
    db.refresh(item)

    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"Cancelled companion bill item '{item.item_name}' for visit {visit.external_visit_number}.")

    u = db.query(User).filter(User.id == item.cancelled_by_id).first()
    u_paid = db.query(User).filter(User.id == getattr(item, "paid_by_id", None)).first()
    u_created = db.query(User).filter(User.id == getattr(item, "created_by_id", None)).first()
    return {"hard_deleted": False, "item": {
        "id": item.id,
        "companion_visit_id": item.companion_visit_id,
        "item_code": item.item_code,
        "item_name": item.item_name,
        "category": item.category,
        "unit_price": float(item.unit_price),
        "quantity": float(item.quantity),
        "start_time": getattr(item, "start_time", None),
        "end_time": getattr(item, "end_time", None),
        "created_at": item.created_at,
        "created_by_id": getattr(item, "created_by_id", None),
        "created_by_name": (u_created.full_name or u_created.username) if u_created else None,
        "cancelled": True,
        "cancelled_at": item.cancelled_at,
        "cancelled_by_id": item.cancelled_by_id,
        "cancelled_by_name": (u.full_name or u.username) if u else None,
        "cancel_reason": item.cancel_reason,
        "receipt_number": item.receipt_number,
        "paid_at": item.paid_at,
        "paid_by_id": item.paid_by_id,
        "paid_by_name": (u_paid.full_name or u_paid.username) if u_paid else None,
        "payment_method": item.payment_method,
        "admission_deposit_applied": getattr(item, "admission_deposit_applied", None),
        "admission_deposit_line_receipt": getattr(item, "admission_deposit_line_receipt", None),
    }}


@router.delete("/{visit_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_companion_visit_item(
    visit_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"])),
):
    """Hard-delete a line item from a companion visit. Superadmin only; others must cancel with reason."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove items from a closed visit",
        )
    item = db.query(CompanionVisitItem).filter(
        CompanionVisitItem.id == item_id,
        CompanionVisitItem.companion_visit_id == visit_id,
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if _companion_item_is_paid(item):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an item that has been paid (receipt issued)",
        )
    if not is_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hard delete is only allowed for superadmin. Use Cancel (with reason) instead.",
        )
    db.delete(item)
    db.commit()
    return None


@router.patch("/{visit_id}/items/{item_id}", response_model=CompanionVisitItemResponse)
def update_companion_visit_item(
    visit_id: int,
    item_id: int,
    data: CompanionVisitItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Doctor", "PA", "Admin"])),
):
    """Update a line item (e.g. custom inpatient fee name/amount). Only when visit is open and item unpaid. Inpatient editable by Admin only."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit items on a closed visit",
        )
    item = db.query(CompanionVisitItem).filter(
        CompanionVisitItem.id == item_id,
        CompanionVisitItem.companion_visit_id == visit_id,
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if _companion_item_is_paid(item):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit an item that has been paid (receipt issued)",
        )
    if item.category == "inpatient":
        from sqlalchemy.orm import joinedload
        user_with_roles = db.query(User).options(joinedload(User.additional_roles)).filter(User.id == current_user.id).first()
        roles = [current_user.role]
        if user_with_roles and getattr(user_with_roles, "additional_roles", None):
            roles += [ur.role for ur in user_with_roles.additional_roles]
        if "Admin" not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Admin can edit custom inpatient fee items",
            )
    if data.item_name is not None:
        item.item_name = (data.item_name or "").strip() or item.item_name
    if data.unit_price is not None:
        item.unit_price = float(data.unit_price)
    db.commit()
    db.refresh(item)
    return item


class MarkItemsPaidBody(BaseModel):
    receipt_number: Optional[str] = None
    item_ids: List[int]
    payment_method: Optional[str] = None
    use_admission_deposit: bool = False


@router.post("/{visit_id}/items/mark-paid")
def mark_companion_visit_items_paid(
    request: Request,
    visit_id: int,
    data: MarkItemsPaidBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"])),
):
    """Record payment: set receipt_number, paid_at, paid_by_id and payment_method on the given items. Billing or Admin only."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    now = datetime.utcnow()
    updated = 0
    last_receipt: Optional[str] = None

    if data.use_admission_deposit:
        base_amt = float(getattr(visit, "admission_deposit_amount", None) or 0)
        base_rn = (getattr(visit, "admission_deposit_receipt_number", None) or "").strip()
        if base_amt <= 0 or not base_rn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No admission deposit on file. Save deposit amount and receipt on the visit first, or turn off 'use admission deposit' and enter a payment receipt.",
            )
        all_items = db.query(CompanionVisitItem).filter(CompanionVisitItem.companion_visit_id == visit_id).all()
        remaining_pool = _admission_deposit_remaining_for_visit(visit, all_items)
        seen: Set[int] = set()
        to_mark: List[CompanionVisitItem] = []
        for raw_id in data.item_ids or []:
            if raw_id in seen:
                continue
            seen.add(raw_id)
            item = db.query(CompanionVisitItem).filter(
                CompanionVisitItem.id == raw_id,
                CompanionVisitItem.companion_visit_id == visit_id,
            ).first()
            if not item or _companion_item_cancelled(item) or _companion_item_is_paid(item):
                continue
            row_amt = _companion_item_row_amount(item)
            if row_amt <= 0:
                continue
            to_mark.append(item)
        allocations: List[Tuple[CompanionVisitItem, float, float]] = []
        rem = round(remaining_pool, 2)
        for item in to_mark:
            row_amt = round(_companion_item_row_amount(item), 2)
            from_dep = round(min(rem, row_amt), 2)
            allocations.append((item, from_dep, row_amt))
            rem = round(rem - from_dep, 2)
        if not allocations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No unpaid lines selected.",
            )
        any_dep = any(a[1] > 0.005 for a in allocations)
        if not any_dep:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No admission deposit balance left for these lines. Turn off 'Pay from admission deposit' and record a payment receipt for the full amount.",
            )
        total_top = round(sum(a[2] - a[1] for a in allocations), 2)
        cash_rn = (data.receipt_number or "").strip()
        pm_cash = (data.payment_method or "").strip() or "cash"
        if total_top > 0.005 and not cash_rn:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"GH¢ {total_top:.2f} is still due after applying the admission deposit to these lines. "
                    "Enter the top-up receipt number (same receipt you give the client for that balance)."
                ),
            )
        if total_top <= 0.005:
            cash_rn = ""
        seq = _max_admission_deposit_receipt_suffix(all_items, base_rn)
        eff_uid = get_effective_creator_id(db, current_user)
        for item, from_dep, row_amt in allocations:
            cash_part = round(row_amt - from_dep, 2)
            if from_dep > 0.005:
                seq += 1
                syn = f"{base_rn}-{seq}"
                item.admission_deposit_applied = from_dep
                item.admission_deposit_line_receipt = syn
            else:
                item.admission_deposit_applied = None
                item.admission_deposit_line_receipt = None
            if cash_part > 0.005:
                item.receipt_number = cash_rn
                item.payment_method = MIXED_DEPOSIT_CASH_PAYMENT_METHOD if from_dep > 0.005 else pm_cash
            else:
                item.receipt_number = None
                item.payment_method = ADMISSION_DEPOSIT_PAYMENT_METHOD
            item.paid_at = now
            item.paid_by_id = eff_uid
            updated += 1
            if cash_part > 0.005 and from_dep > 0.005:
                last_receipt = f"{item.admission_deposit_line_receipt}+{cash_rn}"
            elif cash_part > 0.005:
                last_receipt = cash_rn
            else:
                last_receipt = item.admission_deposit_line_receipt
        db.commit()
        from app.core.audit import set_audit_summary
        set_audit_summary(
            request,
            f"Marked {updated} item(s) using admission deposit (and top-up receipt where needed) for companion visit.",
        )
        return {"updated": updated, "receipt_number": last_receipt, "used_admission_deposit": True, "top_up_amount": total_top}

    receipt_number = (data.receipt_number or "").strip()
    if not receipt_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="receipt_number is required when not paying from admission deposit",
        )
    payment_method = (data.payment_method or "").strip() or None
    for item_id in data.item_ids or []:
        item = db.query(CompanionVisitItem).filter(
            CompanionVisitItem.id == item_id,
            CompanionVisitItem.companion_visit_id == visit_id,
        ).first()
        if item and not _companion_item_is_paid(item):
            item.receipt_number = receipt_number
            item.paid_at = now
            item.paid_by_id = get_effective_creator_id(db, current_user)
            item.payment_method = payment_method
            item.admission_deposit_applied = None
            item.admission_deposit_line_receipt = None
            updated += 1
            last_receipt = receipt_number
    db.commit()
    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"Marked {updated} item(s) as paid for companion visit (receipt {receipt_number}).")
    return {"updated": updated, "receipt_number": last_receipt, "used_admission_deposit": False}


class RefundItemsBody(BaseModel):
    item_ids: List[int]


@router.post("/{visit_id}/items/refund")
def refund_companion_visit_items(
    request: Request,
    visit_id: int,
    data: RefundItemsBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"])),
):
    """Reverse payment: clear receipt_number, paid_at, paid_by_id and payment_method on the given items. Billing or Admin only."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    updated = 0
    for item_id in data.item_ids or []:
        item = db.query(CompanionVisitItem).filter(
            CompanionVisitItem.id == item_id,
            CompanionVisitItem.companion_visit_id == visit_id,
        ).first()
        if item and _companion_item_is_paid(item):
            item.receipt_number = None
            item.paid_at = None
            item.paid_by_id = None
            item.payment_method = None
            item.admission_deposit_applied = None
            item.admission_deposit_line_receipt = None
            updated += 1
    db.commit()
    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"Refunded {updated} item(s) for companion visit (card {visit.external_card_number}).")
    return {"updated": updated}


# --- Companion inventory debits (department-chosen ward stock; optional charge to copayment bill) ---


class CompanionInventoryDebitCreate(BaseModel):
    requesting_department: str
    product_code: str
    product_name: str
    quantity: float = 1.0
    unit_price: Optional[float] = None
    notes: Optional[str] = None
    charge_to_client: bool = False


class CompanionInventoryDebitLineIn(BaseModel):
    """One line for batch create (same as single create + charge flag)."""

    requesting_department: str
    product_code: str
    product_name: str
    quantity: float = 1.0
    unit_price: Optional[float] = None
    notes: Optional[str] = None
    charge_to_client: bool = False


class CompanionInventoryDebitBatchBody(BaseModel):
    items: List[CompanionInventoryDebitLineIn]


class CompanionInventoryDebitUpdate(BaseModel):
    quantity: Optional[float] = None
    notes: Optional[str] = None


def _companion_inventory_debit_dict(db: Session, d: CompanionInventoryDebit) -> dict:
    rec = db.query(User).filter(User.id == d.recorded_by_id).first()
    rel = db.query(User).filter(User.id == d.released_by_id).first() if d.released_by_id else None
    return {
        "id": d.id,
        "companion_visit_id": d.companion_visit_id,
        "requesting_department": d.requesting_department,
        "product_code": d.product_code,
        "product_name": d.product_name,
        "quantity": d.quantity,
        "unit_price": d.unit_price,
        "total_price": d.total_price,
        "notes": d.notes,
        "recorded_by_id": d.recorded_by_id,
        "recorded_by_name": (rec.full_name or rec.username) if rec else None,
        "created_at": d.created_at,
        "is_released": d.is_released,
        "released_by_id": d.released_by_id,
        "released_by_name": (rel.full_name or rel.username) if rel else None,
        "released_at": d.released_at,
        "charged_to_client": d.charged_to_client,
        "companion_visit_item_id": d.companion_visit_item_id,
        "charged_at": d.charged_at,
    }


def _ward_stock_return_to_ward(
    db: Session, dept: str, product_code: str, product_name: str, qty: float
) -> None:
    """Put quantity back into ward stock (first matching row, or new row)."""
    if qty <= 0:
        return
    rows = (
        db.query(WardStock)
        .filter(and_(WardStock.ward == dept, WardStock.product_code == product_code))
        .order_by(WardStock.id)
        .all()
    )
    if rows:
        rows[0].quantity = float(rows[0].quantity) + qty
    else:
        db.add(
            WardStock(
                ward=dept,
                product_code=product_code,
                product_name=(product_name or "").strip() or product_code,
                quantity=qty,
            )
        )


def _charge_debit_to_bill_inner(
    db: Session,
    visit_id: int,
    debit: CompanionInventoryDebit,
    current_user: User,
) -> None:
    item = CompanionVisitItem(
        companion_visit_id=visit_id,
        item_code=debit.product_code,
        item_name=f"Inventory: {debit.product_name}",
        category="inventory_debit",
        unit_price=float(debit.unit_price),
        quantity=float(debit.quantity),
        created_by_id=get_effective_creator_id(db, current_user),
    )
    db.add(item)
    db.flush()
    debit.charged_to_client = True
    debit.companion_visit_item_id = item.id
    debit.charged_at = utcnow()


def _create_companion_inventory_debit_inner(
    db: Session,
    visit: CompanionVisit,
    data: CompanionInventoryDebitCreate,
    current_user: User,
) -> CompanionInventoryDebit:
    dept = (data.requesting_department or "").strip()
    if not dept:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="requesting_department is required")
    product_code = (data.product_code or "").strip()
    product_name = (data.product_name or "").strip()
    if not product_code or not product_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="product_code and product_name are required")
    qty = float(data.quantity or 0)
    if qty <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity must be positive")

    stock_rows = (
        db.query(WardStock)
        .filter(and_(WardStock.ward == dept, WardStock.product_code == product_code))
        .order_by(WardStock.id)
        .all()
    )
    available_quantity = sum(float(r.quantity) for r in stock_rows) if stock_rows else 0.0
    if available_quantity < qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient stock in {dept}. Available: {available_quantity}, Required: {qty}. "
                "Submit a pharmacy requisition to restock this department, then try again."
            ),
        )

    if data.unit_price is not None:
        unit_price = float(data.unit_price)
    else:
        unit_price = get_price_from_all_tables(db, product_code, True)
        if unit_price == 0.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product_name}' has no price — provide unit_price.",
            )
    total_price = unit_price * qty

    remaining = qty
    for row in stock_rows:
        if remaining <= 0:
            break
        rq = float(row.quantity)
        if rq <= 0:
            continue
        take = min(rq, remaining)
        row.quantity = rq - take
        remaining -= take

    debit = CompanionInventoryDebit(
        companion_visit_id=visit.id,
        requesting_department=dept,
        product_code=product_code,
        product_name=product_name,
        quantity=qty,
        unit_price=unit_price,
        total_price=total_price,
        notes=(data.notes or "").strip() or None,
        recorded_by_id=get_effective_creator_id(db, current_user),
    )
    db.add(debit)
    db.flush()
    return debit


@router.get("/{visit_id}/inventory-debits")
def list_companion_inventory_debits(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    rows = (
        db.query(CompanionInventoryDebit)
        .filter(CompanionInventoryDebit.companion_visit_id == visit_id)
        .order_by(CompanionInventoryDebit.created_at.desc())
        .all()
    )
    return [_companion_inventory_debit_dict(db, d) for d in rows]


@router.post("/{visit_id}/inventory-debits", status_code=status.HTTP_201_CREATED)
def create_companion_inventory_debit(
    visit_id: int,
    data: CompanionInventoryDebitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Record ward stock used for this companion visit. Optionally add to client bill in one step."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record inventory debits on a closed visit",
        )

    debit = _create_companion_inventory_debit_inner(db, visit, data, current_user)
    if data.charge_to_client:
        _charge_debit_to_bill_inner(db, visit_id, debit, current_user)
    db.commit()
    db.refresh(debit)
    return _companion_inventory_debit_dict(db, debit)


@router.post("/{visit_id}/inventory-debits/batch", status_code=status.HTTP_201_CREATED)
def create_companion_inventory_debits_batch(
    visit_id: int,
    body: CompanionInventoryDebitBatchBody,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Pharmacy", "Pharmacy Head", "Billing", "Admin"])),
):
    """Record multiple inventory debits; optionally add each to the client bill via charge_to_client on each line."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record inventory debits on a closed visit",
        )
    if not body.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="items cannot be empty")

    out = []
    try:
        for line in body.items:
            data = CompanionInventoryDebitCreate(
                requesting_department=line.requesting_department,
                product_code=line.product_code,
                product_name=line.product_name,
                quantity=line.quantity,
                unit_price=line.unit_price,
                notes=line.notes,
                charge_to_client=line.charge_to_client,
            )
            debit = _create_companion_inventory_debit_inner(db, visit, data, current_user)
            if line.charge_to_client:
                _charge_debit_to_bill_inner(db, visit_id, debit, current_user)
            out.append(debit)
        db.commit()
        for debit in out:
            db.refresh(debit)
    except HTTPException:
        db.rollback()
        raise
    return [_companion_inventory_debit_dict(db, d) for d in out]


@router.post("/{visit_id}/inventory-debits/{debit_id}/charge-to-bill")
def charge_companion_inventory_debit_to_bill(
    visit_id: int,
    debit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(["Billing", "Nurse", "Doctor", "PA", "Pharmacy", "Pharmacy Head", "Admin"])
    ),
):
    """Add a billing line (category inventory_debit) and link this stock debit to the client's bill."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add bill lines to a closed visit",
        )
    debit = (
        db.query(CompanionInventoryDebit)
        .filter(
            CompanionInventoryDebit.id == debit_id,
            CompanionInventoryDebit.companion_visit_id == visit_id,
        )
        .first()
    )
    if not debit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory debit not found")
    if debit.charged_to_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This debit is already on the client's bill",
        )

    _charge_debit_to_bill_inner(db, visit_id, debit, current_user)

    db.commit()
    db.refresh(debit)
    item = db.query(CompanionVisitItem).filter(CompanionVisitItem.id == debit.companion_visit_item_id).first()
    creator = db.query(User).filter(User.id == item.created_by_id).first() if item else None
    return {
        "debit": _companion_inventory_debit_dict(db, debit),
        "item": (
            {
                "id": item.id,
                "companion_visit_id": item.companion_visit_id,
                "item_code": item.item_code,
                "item_name": item.item_name,
                "category": item.category,
                "unit_price": float(item.unit_price),
                "quantity": float(item.quantity),
                "created_at": item.created_at,
                "created_by_id": item.created_by_id,
                "created_by_name": (creator.full_name or creator.username) if creator else None,
            }
            if item
            else None
        ),
    }


@router.patch("/{visit_id}/inventory-debits/{debit_id}")
def update_companion_inventory_debit(
    visit_id: int,
    debit_id: int,
    data: CompanionInventoryDebitUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Adjust quantity (stock adjusted) or notes. Not allowed after pharmacy release or if bill line is paid."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visit must be open")
    debit = (
        db.query(CompanionInventoryDebit)
        .filter(
            CompanionInventoryDebit.id == debit_id,
            CompanionInventoryDebit.companion_visit_id == visit_id,
        )
        .first()
    )
    if not debit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory debit not found")
    if debit.is_released:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit — inventory already released by pharmacy",
        )

    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No updates provided")

    if "notes" in updates:
        debit.notes = (updates["notes"] or "").strip() or None

    if "quantity" in updates and updates["quantity"] is not None:
        new_qty = float(updates["quantity"])
        if new_qty <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quantity must be positive")
        old_qty = float(debit.quantity)
        delta = new_qty - old_qty
        dept = debit.requesting_department
        pc = debit.product_code
        pn = debit.product_name
        if abs(delta) > 1e-9:
            if delta > 0:
                stock_rows = (
                    db.query(WardStock)
                    .filter(and_(WardStock.ward == dept, WardStock.product_code == pc))
                    .order_by(WardStock.id)
                    .all()
                )
                avail = sum(float(r.quantity) for r in stock_rows) if stock_rows else 0.0
                if avail < delta:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Insufficient stock to increase quantity. Available: {avail}, "
                            f"need extra: {delta}."
                        ),
                    )
                rem = delta
                for row in stock_rows:
                    if rem <= 0:
                        break
                    rq = float(row.quantity)
                    if rq <= 0:
                        continue
                    take = min(rq, rem)
                    row.quantity = rq - take
                    rem -= take
            else:
                _ward_stock_return_to_ward(db, dept, pc, pn, -delta)
        debit.quantity = new_qty
        debit.total_price = float(debit.unit_price) * new_qty
        if debit.charged_to_client and debit.companion_visit_item_id:
            item = (
                db.query(CompanionVisitItem)
                .filter(
                    CompanionVisitItem.id == debit.companion_visit_item_id,
                    CompanionVisitItem.companion_visit_id == visit_id,
                )
                .first()
            )
            if item and _companion_item_is_paid(item):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change quantity — bill line is already paid",
                )
            if item:
                item.quantity = new_qty

    db.commit()
    db.refresh(debit)
    return _companion_inventory_debit_dict(db, debit)


@router.delete("/{visit_id}/inventory-debits/{debit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_companion_inventory_debit(
    visit_id: int,
    debit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Nurse", "Doctor", "PA", "Admin"])),
):
    """Remove a debit and restore ward stock. Not allowed after pharmacy release or if bill line is paid."""
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if visit.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Visit must be open")
    debit = (
        db.query(CompanionInventoryDebit)
        .filter(
            CompanionInventoryDebit.id == debit_id,
            CompanionInventoryDebit.companion_visit_id == visit_id,
        )
        .first()
    )
    if not debit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory debit not found")
    if debit.is_released:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete — pharmacy has already released this debit",
        )
    if debit.charged_to_client and debit.companion_visit_item_id:
        item = (
            db.query(CompanionVisitItem)
            .filter(CompanionVisitItem.id == debit.companion_visit_item_id)
            .first()
        )
        if item and _companion_item_is_paid(item):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete — bill line is already paid",
            )
        if item:
            db.delete(item)
    _ward_stock_return_to_ward(
        db,
        debit.requesting_department,
        debit.product_code,
        debit.product_name,
        float(debit.quantity),
    )
    db.delete(debit)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
