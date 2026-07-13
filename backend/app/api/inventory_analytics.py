"""
Aggregated inventory analytics for dashboards (store stock, ward usage, requisitions, debits).
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.datetime_utils import utcnow
from app.core.dependencies import require_inventory_mode_access
from app.core.inventory_access import (
    get_inventory_dashboard_scope,
    resolve_inventory_dashboard_filters,
)
from app.models.user import User
from app.models.store_stock import StoreStock, StockStatus
from app.models.store import Store, StoreKind
from app.models.ward_stock import WardStock
from app.models.ward import Ward
from app.models.pharmacy_requisition import PharmacyRequisition, RequisitionStatus
from app.models.requisition_item import RequisitionItem
from app.models.inpatient_inventory_debit import InpatientInventoryDebit
from app.models.companion_inventory_debit import CompanionInventoryDebit

router = APIRouter(prefix="/inventory-analytics", tags=["inventory-analytics"])


class DashboardKpis(BaseModel):
    approved_store_stock_qty: float
    approved_store_stock_lines: int
    ward_stock_total_qty: Optional[float] = None
    ward_stock_lines: Optional[int] = None
    requisitions_pending: int
    requisitions_in_flight: int  # pending + approved + partial
    requisitions_created_period: int
    requisitions_fulfilled_period: int
    debit_units_period: float
    debit_events_period: int


class SeriesPoint(BaseModel):
    date: str  # YYYY-MM-DD
    usage_units: float
    requisitions_created: int
    requisitions_fulfilled: int


class TopProduct(BaseModel):
    product_code: str
    product_name: str
    debit_qty: float
    requisition_requested_qty: float


class RecentEvent(BaseModel):
    kind: str  # requisition | inpatient_debit | companion_debit
    at: datetime
    label: str
    detail: str
    ref_id: int


class InventoryDashboardResponse(BaseModel):
    period_days: int
    store_id: Optional[int] = None
    store_name: Optional[str] = None
    department: Optional[str] = None
    applied_store_ids: Optional[List[int]] = None
    applied_department_names: Optional[List[str]] = None
    kpis: DashboardKpis
    series: List[SeriesPoint]
    top_products: List[TopProduct]
    recent_events: List[RecentEvent]


def _daterange_keys(start: datetime, end: datetime) -> List[str]:
    out: List[str] = []
    d = start.date()
    end_d = end.date()
    while d <= end_d:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _filter_rq_by_departments(q, db: Session, dept_names: Optional[List[str]]):
    if not dept_names:
        return q
    if len(dept_names) == 1:
        dn = dept_names[0]
        w = db.query(Ward).filter(Ward.name == dn).first()
        if w:
            return q.filter(
                or_(PharmacyRequisition.department_id == w.id, PharmacyRequisition.ward == dn)
            )
        return q.filter(PharmacyRequisition.ward == dn)
    wards = db.query(Ward).filter(Ward.name.in_(dept_names)).all()
    ids = [x.id for x in wards]
    return q.filter(
        or_(
            PharmacyRequisition.department_id.in_(ids),
            PharmacyRequisition.ward.in_(dept_names),
        )
    )


@router.get("/dashboard", response_model=InventoryDashboardResponse)
def get_inventory_dashboard(
    store_id: Optional[int] = Query(None, description="Filter requisitions & store stock to this store"),
    department: Optional[str] = Query(
        None, description="Ward/department name (matches ward stock & debit filters)",
    ),
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    """
    Summary KPIs, daily series (usage vs requisitions), top products, and recent activity.
    Store/department filters are enforced server-side from assignments (IC/deputy, store staff) unless
    the user has Management/Admin/Pharmacy-wide access.
    """
    u = (
        db.query(User)
        .options(joinedload(User.additional_roles))
        .filter(User.id == current_user.id)
        .first()
    )
    if not u:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    additional = [r.role for r in u.additional_roles] if u.additional_roles else []

    scope = get_inventory_dashboard_scope(db, u, additional)
    store_ids_eff, dept_names_eff = resolve_inventory_dashboard_filters(scope, store_id, department)
    ic_department_only = not scope.unrestricted_filters and bool(scope.ic_managed_ward_names)

    now = utcnow()
    start = now - timedelta(days=days)

    # Display labels
    store_name: Optional[str] = None
    if store_ids_eff is not None and len(store_ids_eff) == 1:
        st = db.query(Store).filter(Store.id == store_ids_eff[0]).first()
        if st:
            tag = (
                "Pharmacy"
                if st.store_kind == StoreKind.PHARMACY.value
                else "General"
                if st.store_kind == StoreKind.GENERAL.value
                else None
            )
            store_name = f"{st.name} ({tag})" if tag else st.name
    elif store_ids_eff is not None and len(store_ids_eff) > 1:
        store_name = f"{len(store_ids_eff)} stores"

    dept_label: Optional[str] = None
    if dept_names_eff:
        dept_label = ", ".join(dept_names_eff) if len(dept_names_eff) > 1 else dept_names_eff[0]

    # --- KPI: approved store stock (not shown for IC-only department scope) ---
    approved_store_stock_qty = 0.0
    approved_store_stock_lines = 0
    if not ic_department_only:
        ss_q = db.query(StoreStock).filter(StoreStock.status == StockStatus.APPROVED)
        if store_ids_eff is not None:
            ss_q = ss_q.filter(StoreStock.store_id.in_(store_ids_eff))
        approved_rows = ss_q.all()
        approved_store_stock_qty = sum(float(r.quantity or 0) for r in approved_rows)
        approved_store_stock_lines = len(approved_rows)

    # --- KPI: ward stock ---
    ward_stock_total_qty: Optional[float] = None
    ward_stock_lines: Optional[int] = None
    if dept_names_eff:
        wrows = db.query(WardStock).filter(WardStock.ward.in_(dept_names_eff)).all()
        ward_stock_total_qty = sum(float(r.quantity or 0) for r in wrows)
        ward_stock_lines = len(wrows)

    # --- Requisition filters ---
    rq_base = db.query(PharmacyRequisition)
    if store_ids_eff is not None:
        rq_base = rq_base.filter(PharmacyRequisition.store_id.in_(store_ids_eff))
    rq_base = _filter_rq_by_departments(rq_base, db, dept_names_eff)

    requisitions_pending = rq_base.filter(PharmacyRequisition.status == RequisitionStatus.PENDING).count()
    requisitions_in_flight = rq_base.filter(
        PharmacyRequisition.status.in_(
            [
                RequisitionStatus.PENDING,
                RequisitionStatus.APPROVED,
                RequisitionStatus.PARTIALLY_FULFILLED,
            ]
        )
    ).count()

    rq_period = rq_base.filter(
        PharmacyRequisition.created_at >= start,
        PharmacyRequisition.created_at <= now,
    )
    requisitions_created_period = rq_period.count()

    rq_fulfilled_period = rq_base.filter(
        PharmacyRequisition.fulfilled_at.isnot(None),
        PharmacyRequisition.fulfilled_at >= start,
        PharmacyRequisition.fulfilled_at <= now,
    ).count()

    # --- Debits in period (inpatient + companion) ---
    ip_q = db.query(InpatientInventoryDebit).filter(
        InpatientInventoryDebit.used_at >= start,
        InpatientInventoryDebit.used_at <= now,
    )
    if dept_names_eff:
        ip_q = ip_q.filter(InpatientInventoryDebit.requesting_ward.in_(dept_names_eff))

    co_q = db.query(CompanionInventoryDebit).filter(
        CompanionInventoryDebit.created_at >= start,
        CompanionInventoryDebit.created_at <= now,
    )
    if dept_names_eff:
        co_q = co_q.filter(CompanionInventoryDebit.requesting_department.in_(dept_names_eff))

    ip_rows = ip_q.all()
    co_rows = co_q.all()
    debit_units_period = sum(float(r.quantity or 0) for r in ip_rows) + sum(float(r.quantity or 0) for r in co_rows)
    debit_events_period = len(ip_rows) + len(co_rows)

    kpis = DashboardKpis(
        approved_store_stock_qty=round(approved_store_stock_qty, 2),
        approved_store_stock_lines=approved_store_stock_lines,
        ward_stock_total_qty=round(ward_stock_total_qty, 2) if ward_stock_total_qty is not None else None,
        ward_stock_lines=ward_stock_lines,
        requisitions_pending=requisitions_pending,
        requisitions_in_flight=requisitions_in_flight,
        requisitions_created_period=requisitions_created_period,
        requisitions_fulfilled_period=rq_fulfilled_period,
        debit_units_period=round(debit_units_period, 2),
        debit_events_period=debit_events_period,
    )

    # --- Daily series ---
    date_keys = _daterange_keys(start, now)
    usage_by_day: Dict[str, float] = {k: 0.0 for k in date_keys}
    rq_create_by_day: Dict[str, int] = {k: 0 for k in date_keys}
    rq_fulfilled_by_day: Dict[str, int] = {k: 0 for k in date_keys}

    for r in ip_rows:
        if r.used_at:
            key = r.used_at.date().isoformat()
            if key in usage_by_day:
                usage_by_day[key] += float(r.quantity or 0)
    for r in co_rows:
        if r.created_at:
            key = r.created_at.date().isoformat()
            if key in usage_by_day:
                usage_by_day[key] += float(r.quantity or 0)

    for rq in rq_base.filter(
        PharmacyRequisition.created_at >= start,
        PharmacyRequisition.created_at <= now,
    ).all():
        if rq.created_at:
            key = rq.created_at.date().isoformat()
            if key in rq_create_by_day:
                rq_create_by_day[key] += 1

    for rq in rq_base.filter(
        PharmacyRequisition.fulfilled_at.isnot(None),
        PharmacyRequisition.fulfilled_at >= start,
        PharmacyRequisition.fulfilled_at <= now,
    ).all():
        if rq.fulfilled_at:
            key = rq.fulfilled_at.date().isoformat()
            if key in rq_fulfilled_by_day:
                rq_fulfilled_by_day[key] += 1

    series: List[SeriesPoint] = [
        SeriesPoint(
            date=d,
            usage_units=round(usage_by_day.get(d, 0.0), 3),
            requisitions_created=rq_create_by_day.get(d, 0),
            requisitions_fulfilled=rq_fulfilled_by_day.get(d, 0),
        )
        for d in date_keys
    ]

    # --- Top products (debits + requisition request lines in period) ---
    prod_debit: Dict[str, Dict[str, Any]] = {}
    for r in ip_rows:
        pc = (r.product_code or "").strip()
        if not pc:
            continue
        if pc not in prod_debit:
            prod_debit[pc] = {"name": r.product_name or pc, "dq": 0.0, "rq": 0.0}
        prod_debit[pc]["dq"] += float(r.quantity or 0)
        prod_debit[pc]["name"] = r.product_name or prod_debit[pc]["name"]
    for r in co_rows:
        pc = (r.product_code or "").strip()
        if not pc:
            continue
        if pc not in prod_debit:
            prod_debit[pc] = {"name": r.product_name or pc, "dq": 0.0, "rq": 0.0}
        prod_debit[pc]["dq"] += float(r.quantity or 0)

    rq_period_rows = rq_base.filter(
        PharmacyRequisition.created_at >= start,
        PharmacyRequisition.created_at <= now,
    ).all()
    rq_ids = [r.id for r in rq_period_rows]
    if rq_ids:
        items = (
            db.query(RequisitionItem)
            .filter(RequisitionItem.requisition_id.in_(rq_ids))
            .all()
        )
        for it in items:
            pc = (it.product_code or "").strip()
            if not pc:
                continue
            if pc not in prod_debit:
                prod_debit[pc] = {"name": it.product_name or pc, "dq": 0.0, "rq": 0.0}
            prod_debit[pc]["rq"] += float(it.requested_quantity or 0)
            prod_debit[pc]["name"] = it.product_name or prod_debit[pc]["name"]

    top_sorted = sorted(
        prod_debit.items(),
        key=lambda x: x[1]["dq"] + x[1]["rq"],
        reverse=True,
    )[:12]
    top_products = [
        TopProduct(
            product_code=k,
            product_name=v["name"],
            debit_qty=round(v["dq"], 3),
            requisition_requested_qty=round(v["rq"], 3),
        )
        for k, v in top_sorted
    ]

    # --- Recent events (mixed) ---
    recent_events: List[RecentEvent] = []
    for rq in rq_base.order_by(PharmacyRequisition.updated_at.desc()).limit(12).all():
        recent_events.append(
            RecentEvent(
                kind="requisition",
                at=rq.updated_at or rq.created_at,
                label=rq.requisition_number,
                detail=f"{str(rq.status)} · store #{rq.store_id}",
                ref_id=rq.id,
            )
        )
    ip_recent_q = db.query(InpatientInventoryDebit).filter(InpatientInventoryDebit.used_at >= start)
    if dept_names_eff:
        ip_recent_q = ip_recent_q.filter(InpatientInventoryDebit.requesting_ward.in_(dept_names_eff))
    for r in ip_recent_q.order_by(InpatientInventoryDebit.used_at.desc()).limit(8).all():
        recent_events.append(
            RecentEvent(
                kind="inpatient_debit",
                at=r.used_at,
                label=r.product_name[:80],
                detail=f"IPD · {r.requesting_ward} · qty {r.quantity}",
                ref_id=r.id,
            )
        )
    co_recent_q = db.query(CompanionInventoryDebit).filter(CompanionInventoryDebit.created_at >= start)
    if dept_names_eff:
        co_recent_q = co_recent_q.filter(CompanionInventoryDebit.requesting_department.in_(dept_names_eff))
    for r in co_recent_q.order_by(CompanionInventoryDebit.created_at.desc()).limit(8).all():
        recent_events.append(
            RecentEvent(
                kind="companion_debit",
                at=r.created_at or now,
                label=r.product_name[:80],
                detail=f"Companion · {r.requesting_department} · qty {r.quantity}",
                ref_id=r.id,
            )
        )

    recent_events.sort(key=lambda e: e.at, reverse=True)
    recent_events = recent_events[:20]

    resp_store_id = store_ids_eff[0] if store_ids_eff and len(store_ids_eff) == 1 else None

    return InventoryDashboardResponse(
        period_days=days,
        store_id=resp_store_id,
        store_name=store_name,
        department=dept_label,
        applied_store_ids=store_ids_eff,
        applied_department_names=dept_names_eff,
        kpis=kpis,
        series=series,
        top_products=top_products,
        recent_events=recent_events,
    )