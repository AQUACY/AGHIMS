"""
Management API: transactions (OPD + Companion) and undertaking approval support.
Access: Management, Admin.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.models.user import User
from app.models.bill import Bill, Receipt, ReceiptItem, BillItem
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.companion_visit import CompanionVisit
from app.models.companion_visit_item import CompanionVisitItem

router = APIRouter(prefix="/management", tags=["management"])

# Charge-type buckets: OPD matches substrings in department / procedure / receipt line text;
# Companion matches bill line category values on companion_visit_items.
SERVICE_GROUPS: Dict[str, Dict[str, Any]] = {
    "labs": {
        "opd_substrings": (
            "investig",
            "laboratory",
            "laborato",
            "in-house lab",
            "inhouse lab",
            " haematology",
            " hematology",
            " biochem",
            "microbiology",
            "serology",
            "fbc",
            "full blood",
        ),
        "companion_categories": ("lab",),
    },
    "scans": {
        "opd_substrings": (
            "ultrasound",
            "echograph",
            " u/s ",
            "scan",
            "ct scan",
            "mri",
            "doppler",
        ),
        "companion_categories": ("scan",),
    },
    "xray": {
        "opd_substrings": ("x ray", "x-ray", "xray", "radiograph"),
        "companion_categories": ("xray",),
    },
    "pharmacy": {
        "opd_substrings": ("pharma", "drug", "medicine", "dispens", "chemist"),
        "companion_categories": ("drug",),
    },
    "day_surgery": {
        "opd_substrings": ("day surgery", "daysurgery"),
        "companion_categories": ("day_surgery",),
    },
    "major_surgery": {
        "opd_substrings": (
            "major surgery",
            "adult surgery",
            "elective surgery",
            "open surgery",
            "mahs",  # common shorthand
        ),
        "companion_categories": ("major_surgery",),
    },
    "dressing": {
        "opd_substrings": ("dressing", "treatment room", "minor procedure"),
        "companion_categories": ("dressing",),
    },
    "oxygen": {
        "opd_substrings": ("oxygen", "o2 therapy"),
        "companion_categories": ("oxygen",),
    },
    "inpatient": {
        "opd_substrings": ("inpatient", " ipd ", " ward", "admission fee", "admission"),
        "companion_categories": ("inpatient",),
    },
}


def _normalized_service_group(raw: Optional[str]) -> Optional[str]:
    if not raw or not str(raw).strip():
        return None
    key = str(raw).strip().lower()
    return key if key in SERVICE_GROUPS else None


def _opd_haystack_for_receipt(encounter: Encounter, receipt: Receipt) -> str:
    parts = [encounter.department or "", encounter.procedure_name or ""]
    for ri in receipt.receipt_items or []:
        bi = getattr(ri, "bill_item", None)
        if bi:
            parts.append(bi.category or "")
            parts.append(bi.item_name or "")
    return " ".join(parts).lower()


def _opd_matches_charge_group(haystack_lower: str, group_key: str) -> bool:
    spec = SERVICE_GROUPS.get(group_key)
    if not spec:
        return True
    needles = spec.get("opd_substrings") or ()
    return any(n in haystack_lower for n in needles)


def _pending_opd_group_or_clauses(group_key: str) -> List[Any]:
    spec = SERVICE_GROUPS.get(group_key)
    if not spec:
        return []
    out = []
    for needle in spec.get("opd_substrings") or ():
        t = f"%{needle}%"
        out.append(Encounter.department.ilike(t))
        out.append(Encounter.procedure_name.ilike(t))
    return out


class TransactionRow(BaseModel):
    """Single transaction row for reporting (OPD or Companion)."""
    source: str  # "opd" | "companion"
    transaction_date: datetime
    client_name: Optional[str] = None
    client_identifier: Optional[str] = None  # card_number or external_card_number
    amount: float
    service_type: Optional[str] = None  # category or department
    user_name: Optional[str] = None  # who took the transaction (OPD: issued_by; Companion: paid_by_id)
    receipt_number: Optional[str] = None
    payment_method: Optional[str] = None
    encounter_id: Optional[int] = None
    visit_id: Optional[int] = None

    class Config:
        from_attributes = True


class TransactionsResponse(BaseModel):
    """List of transactions and optional summary."""
    transactions: List[TransactionRow]
    total_amount: float


class PendingPaymentRow(BaseModel):
    """Single pending (not fully paid) bill row for OPD or Companion."""
    source: str  # "opd" | "companion"
    pending_date: datetime
    client_name: Optional[str] = None
    client_identifier: Optional[str] = None
    amount_due: float
    service_type: Optional[str] = None
    encounter_id: Optional[int] = None
    visit_id: Optional[int] = None


class PendingPaymentsResponse(BaseModel):
    """List of pending payments and total due."""
    pending: List[PendingPaymentRow]
    total_due: float


class UserOption(BaseModel):
    """Minimal user for filter dropdown."""
    id: int
    full_name: Optional[str] = None
    username: str


@router.get("/users", response_model=List[UserOption])
def list_users_for_filter(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Management", "Admin"])),
):
    """List users (id, name) for transaction filter dropdown."""
    users = db.query(User).filter(User.is_active == True).order_by(User.full_name, User.username).all()
    return [UserOption(id=u.id, full_name=u.full_name, username=u.username) for u in users]


@router.get("/transactions", response_model=TransactionsResponse)
def list_transactions(
    start_date: Optional[date] = Query(None, description="From date (inclusive)"),
    end_date: Optional[date] = Query(None, description="To date (inclusive)"),
    client: Optional[str] = Query(None, description="Filter by client name or card (partial match)"),
    service_type: Optional[str] = Query(None, description="Filter by service label (partial match); ignored if service_group is set"),
    service_group: Optional[str] = Query(
        None,
        description="Filter by charge type: labs, scans, xray, pharmacy, day_surgery, major_surgery, dressing, oxygen, inpatient",
    ),
    user_id: Optional[int] = Query(None, description="Filter by user who took the transaction (OPD only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Management", "Admin"])),
):
    """
    List monetary transactions from OPD (receipts) and Companion (paid visit items).
    Filters: date range, client, service_group (charge category) or service_type, user (OPD only).
    """
    transactions: List[TransactionRow] = []
    total_amount = 0.0

    # --- OPD: Receipts (non-refunded) with Bill -> Encounter -> Patient, User (issued_by) ---
    opd_query = (
        db.query(Receipt)
        .join(Bill, Receipt.bill_id == Bill.id)
        .join(Encounter, Bill.encounter_id == Encounter.id)
        .join(Patient, Encounter.patient_id == Patient.id)
        .filter(Receipt.refunded == False)
    )
    if start_date:
        opd_query = opd_query.filter(
            Receipt.issued_at >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        opd_query = opd_query.filter(
            Receipt.issued_at <= datetime.combine(end_date, datetime.max.time())
        )
    if user_id:
        opd_query = opd_query.filter(Receipt.issued_by == user_id)
    if client and client.strip():
        term = f"%{client.strip()}%"
        opd_query = opd_query.filter(
            (Patient.name.ilike(term)) |
            (Patient.surname.ilike(term)) |
            (Patient.other_names.ilike(term)) |
            (Patient.card_number.ilike(term))
        )
    opd_query = opd_query.order_by(Receipt.issued_at.desc())

    # Eager-load Bill -> Encounter -> Patient and receipt items
    from sqlalchemy.orm import joinedload
    opd_receipts = (
        opd_query.options(
            joinedload(Receipt.bill).joinedload(Bill.encounter).joinedload(Encounter.patient),
            joinedload(Receipt.receipt_items).joinedload(ReceiptItem.bill_item),
        )
        .all()
    )
    user_ids = {r.issued_by for r in opd_receipts}
    users_by_id = {}
    if user_ids:
        for u in db.query(User).filter(User.id.in_(user_ids)).all():
            users_by_id[u.id] = u.full_name or u.username

    for r in opd_receipts:
        bill = r.bill
        encounter = bill.encounter
        patient = encounter.patient
        client_name = f"{patient.name or ''} {patient.surname or ''} {patient.other_names or ''}".strip() or None
        # Service type: encounter department or first bill item category
        service_type_val = encounter.department or encounter.procedure_name
        if not service_type_val and r.receipt_items:
            first_item = r.receipt_items[0].bill_item
            if first_item:
                service_type_val = first_item.category or first_item.item_name
        hay = _opd_haystack_for_receipt(encounter, r)
        sg_key = _normalized_service_group(service_group)
        if sg_key:
            if not _opd_matches_charge_group(hay, sg_key):
                continue
        elif service_type and service_type.strip():
            if not service_type_val or service_type.strip().lower() not in (service_type_val or "").lower():
                continue
        user_name = users_by_id.get(r.issued_by)
        row = TransactionRow(
            source="opd",
            transaction_date=r.issued_at,
            client_name=client_name,
            client_identifier=patient.card_number,
            amount=r.amount_paid,
            service_type=service_type_val,
            user_name=user_name,
            receipt_number=r.receipt_number,
            payment_method=r.payment_method,
            encounter_id=encounter.id,
            visit_id=None,
        )
        transactions.append(row)
        total_amount += r.amount_paid

    # --- Companion: paid visit items (receipt_number / paid_at set) ---
    comp_query = (
        db.query(CompanionVisitItem, CompanionVisit)
        .join(CompanionVisit, CompanionVisitItem.companion_visit_id == CompanionVisit.id)
        .filter(CompanionVisitItem.receipt_number.isnot(None))
        .filter(CompanionVisitItem.paid_at.isnot(None))
    )
    if start_date:
        comp_query = comp_query.filter(
            CompanionVisitItem.paid_at >= datetime.combine(start_date, datetime.min.time())
        )
    if end_date:
        comp_query = comp_query.filter(
            CompanionVisitItem.paid_at <= datetime.combine(end_date, datetime.max.time())
        )
    if client and client.strip():
        term = f"%{client.strip()}%"
        comp_query = comp_query.filter(
            (CompanionVisit.external_card_number.ilike(term)) |
            (CompanionVisit.client_name.ilike(term))
        )
    sg_tr = _normalized_service_group(service_group)
    if sg_tr:
        spec_tr = SERVICE_GROUPS.get(sg_tr)
        cats = spec_tr.get("companion_categories") if spec_tr else None
        if cats:
            comp_query = comp_query.filter(CompanionVisitItem.category.in_(list(cats)))
    elif service_type and service_type.strip():
        comp_query = comp_query.filter(
            CompanionVisitItem.category.ilike(f"%{service_type.strip()}%")
        )
    comp_query = comp_query.order_by(CompanionVisitItem.paid_at.desc())
    comp_rows = comp_query.all()

    # Preload users for companion payments (paid_by_id)
    comp_user_ids = {it.paid_by_id for (it, _visit) in comp_rows if getattr(it, "paid_by_id", None)}
    comp_users_by_id = {}
    if comp_user_ids:
        for u in db.query(User).filter(User.id.in_(comp_user_ids)).all():
            comp_users_by_id[u.id] = u.full_name or u.username

    for it, visit in comp_rows:
        amount = (it.unit_price or 0) * (it.quantity or 1)
        user_name = None
        if getattr(it, "paid_by_id", None):
            user_name = comp_users_by_id.get(it.paid_by_id)
        row = TransactionRow(
            source="companion",
            transaction_date=it.paid_at,
            client_name=visit.client_name,
            client_identifier=visit.external_card_number,
            amount=amount,
            service_type=it.category,
            user_name=user_name,
            receipt_number=it.receipt_number,
            payment_method=getattr(it, "payment_method", None),
            encounter_id=None,
            visit_id=visit.id,
        )
        transactions.append(row)
        total_amount += amount

    # Sort combined by date desc
    transactions.sort(key=lambda t: t.transaction_date, reverse=True)

    return TransactionsResponse(transactions=transactions, total_amount=round(total_amount, 2))


def _companion_item_row_amount(it: CompanionVisitItem) -> float:
    return float(it.unit_price or 0) * float(it.quantity or 1)


def _companion_item_cancelled(it: CompanionVisitItem) -> bool:
    return bool(getattr(it, "cancelled", False))


def _companion_item_is_fully_paid(it: CompanionVisitItem) -> bool:
    total = round(_companion_item_row_amount(it), 2)
    if total <= 0:
        return True
    pm = (getattr(it, "payment_method", None) or "").strip()
    rn = (getattr(it, "receipt_number", None) or "").strip()
    dep_ln = (getattr(it, "admission_deposit_line_receipt", None) or "").strip()
    dep_applied = getattr(it, "admission_deposit_applied", None)

    if dep_applied is not None:
        rem = round(total - float(dep_applied), 2)
        if rem <= 0.01:
            return bool(dep_ln and getattr(it, "paid_at", None))
        return bool(dep_ln and rn and getattr(it, "paid_at", None))

    # Legacy and cash-only fallback
    if pm == "admission_deposit":
        return bool((dep_ln or rn) and getattr(it, "paid_at", None))
    return bool(rn and getattr(it, "paid_at", None))


@router.get("/pending-payments", response_model=PendingPaymentsResponse)
def list_pending_payments(
    start_date: Optional[date] = Query(None, description="From date (inclusive)"),
    end_date: Optional[date] = Query(None, description="To date (inclusive)"),
    client: Optional[str] = Query(None, description="Filter by client name or card (partial match)"),
    service_type: Optional[str] = Query(None, description="Partial match on department/procedure or category; ignored if service_group is set"),
    service_group: Optional[str] = Query(
        None,
        description="Filter by charge type: labs, scans, xray, pharmacy, day_surgery, major_surgery, dressing, oxygen, inpatient",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Management", "Admin"])),
):
    """
    List pending payments:
    - OPD bills with outstanding balance
    - Companion bill lines not fully paid yet
    """
    rows: List[PendingPaymentRow] = []
    total_due = 0.0

    # --- OPD pending bills ---
    opd_q = (
        db.query(Bill, Encounter, Patient)
        .join(Encounter, Bill.encounter_id == Encounter.id)
        .join(Patient, Encounter.patient_id == Patient.id)
        .filter(Bill.is_paid == False)
    )
    if start_date:
        opd_q = opd_q.filter(Bill.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        opd_q = opd_q.filter(Bill.created_at <= datetime.combine(end_date, datetime.max.time()))
    if client and client.strip():
        term = f"%{client.strip()}%"
        opd_q = opd_q.filter(
            (Patient.name.ilike(term))
            | (Patient.surname.ilike(term))
            | (Patient.other_names.ilike(term))
            | (Patient.card_number.ilike(term))
        )
    sg_pe = _normalized_service_group(service_group)
    if sg_pe:
        clauses = _pending_opd_group_or_clauses(sg_pe)
        if clauses:
            opd_q = opd_q.filter(or_(*clauses))
    elif service_type and service_type.strip():
        t = f"%{service_type.strip()}%"
        opd_q = opd_q.filter((Encounter.department.ilike(t)) | (Encounter.procedure_name.ilike(t)))

    for bill, enc, patient in opd_q.order_by(Bill.created_at.desc()).all():
        due = float((bill.total_amount or 0) - (bill.paid_amount or 0))
        if due <= 0.01:
            continue
        name = f"{patient.name or ''} {patient.surname or ''} {patient.other_names or ''}".strip() or None
        row = PendingPaymentRow(
            source="opd",
            pending_date=bill.created_at,
            client_name=name,
            client_identifier=patient.card_number,
            amount_due=due,
            service_type=enc.department or enc.procedure_name,
            encounter_id=enc.id,
            visit_id=None,
        )
        rows.append(row)
        total_due += due

    # --- Companion pending line items ---
    comp_q = (
        db.query(CompanionVisitItem, CompanionVisit)
        .join(CompanionVisit, CompanionVisitItem.companion_visit_id == CompanionVisit.id)
    )
    if start_date:
        comp_q = comp_q.filter(CompanionVisitItem.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        comp_q = comp_q.filter(CompanionVisitItem.created_at <= datetime.combine(end_date, datetime.max.time()))
    if client and client.strip():
        term = f"%{client.strip()}%"
        comp_q = comp_q.filter(
            (CompanionVisit.external_card_number.ilike(term))
            | (CompanionVisit.client_name.ilike(term))
        )
    sg_pc = _normalized_service_group(service_group)
    if sg_pc:
        spec_pc = SERVICE_GROUPS.get(sg_pc)
        cats_pc = spec_pc.get("companion_categories") if spec_pc else None
        if cats_pc:
            comp_q = comp_q.filter(CompanionVisitItem.category.in_(list(cats_pc)))
    elif service_type and service_type.strip():
        comp_q = comp_q.filter(CompanionVisitItem.category.ilike(f"%{service_type.strip()}%"))

    for it, visit in comp_q.order_by(CompanionVisitItem.created_at.desc()).all():
        if _companion_item_cancelled(it) or _companion_item_is_fully_paid(it):
            continue
        due = _companion_item_row_amount(it)
        row = PendingPaymentRow(
            source="companion",
            pending_date=it.created_at,
            client_name=visit.client_name,
            client_identifier=visit.external_card_number,
            amount_due=due,
            service_type=it.category,
            encounter_id=None,
            visit_id=visit.id,
        )
        rows.append(row)
        total_due += due

    rows.sort(key=lambda r: r.pending_date, reverse=True)
    return PendingPaymentsResponse(pending=rows, total_due=round(total_due, 2))
