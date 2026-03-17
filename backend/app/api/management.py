"""
Management API: transactions (OPD + Companion) and undertaking approval support.
Access: Management, Admin.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
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
    service_type: Optional[str] = Query(None, description="Filter by service type/category (partial match)"),
    user_id: Optional[int] = Query(None, description="Filter by user who took the transaction (OPD only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Management", "Admin"])),
):
    """
    List monetary transactions from OPD (receipts) and Companion (paid visit items).
    Filters: date range, client, service type, user (OPD only).
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
        if service_type and service_type.strip():
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
    if service_type and service_type.strip():
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
