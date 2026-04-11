"""
Inventory reports: requisitions and store stock, scoped like /inventory-analytics/dashboard.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
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
from app.models.ward import Ward
from app.models.store import Store, StoreKind
from app.models.pharmacy_requisition import PharmacyRequisition, RequisitionStatus
from app.models.requisition_item import RequisitionItem
from app.models.store_stock import StoreStock, StockStatus

router = APIRouter(prefix="/inventory-reports", tags=["inventory-reports"])


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


def _parse_range(start_date: str, end_date: str) -> Tuple[datetime, datetime]:
    try:
        s = datetime.strptime(start_date.strip(), "%Y-%m-%d")
        e = datetime.strptime(end_date.strip(), "%Y-%m-%d")
    except ValueError as ex:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD.",
        ) from ex
    s = s.replace(hour=0, minute=0, second=0, microsecond=0)
    e = e.replace(hour=23, minute=59, second=59, microsecond=999999)
    return s, e


class RequisitionReportRow(BaseModel):
    requisition_id: int
    requisition_number: str
    created_at: datetime
    status: str
    department_name: Optional[str] = None
    ward_legacy: Optional[str] = None
    store_id: int
    store_name: str
    store_kind: str
    line_count: int
    total_requested_qty: float


class RequisitionReportResponse(BaseModel):
    start_date: str
    end_date: str
    rows: List[RequisitionReportRow]
    summary_by_status: Dict[str, int] = Field(default_factory=dict)


class StoreStockReportRow(BaseModel):
    store_id: int
    store_name: str
    store_kind: str
    product_code: str
    product_name: str
    batch_number: str
    expiry_date: Optional[str] = None
    quantity: float
    status: str
    unit_price: Optional[float] = None
    line_value: Optional[float] = None


class StoreStockReportResponse(BaseModel):
    as_of: datetime
    rows: List[StoreStockReportRow]
    totals: Dict[str, Any] = Field(default_factory=dict)


def _effective_store_ids(
    db: Session,
    store_ids_eff: Optional[List[int]],
    store_kind: Optional[str],
) -> Optional[List[int]]:
    """Apply pharmacy vs general filter. Intersects with store_ids_eff when both are set."""
    if store_kind not in (StoreKind.PHARMACY.value, StoreKind.GENERAL.value):
        return store_ids_eff
    kind_ids = [
        r[0]
        for r in db.query(Store.id)
        .filter(Store.store_kind == store_kind, Store.is_active == True)
        .all()
    ]
    if not kind_ids:
        return []
    if store_ids_eff is not None:
        return [x for x in store_ids_eff if x in kind_ids]
    return kind_ids


def _scope_and_filters(
    db: Session,
    current_user: User,
    store_id: Optional[int],
    department: Optional[str],
    store_kind: Optional[str],
):
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
    store_ids_eff = _effective_store_ids(db, store_ids_eff, store_kind)
    if store_ids_eff is not None and len(store_ids_eff) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No stores match the selected store type within your access scope.",
        )
    return store_ids_eff, dept_names_eff


@router.get("/requisitions", response_model=None)
def report_requisitions(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    store_id: Optional[int] = Query(None),
    department: Optional[str] = Query(None, description="Department/ward name filter"),
    store_kind: Optional[str] = Query(None, description="Filter stores: general (main) or pharmacy"),
    export_csv: bool = Query(False, description="Download CSV instead of JSON"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    if store_kind is not None and store_kind not in (StoreKind.PHARMACY.value, StoreKind.GENERAL.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="store_kind must be 'general' or 'pharmacy'",
        )
    start_dt, end_dt = _parse_range(start_date, end_date)
    if end_dt < start_dt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="end_date must be on or after start_date")

    store_ids_eff, dept_names_eff = _scope_and_filters(db, current_user, store_id, department, store_kind)

    q = db.query(PharmacyRequisition).filter(
        PharmacyRequisition.created_at >= start_dt,
        PharmacyRequisition.created_at <= end_dt,
    )
    if store_ids_eff is not None:
        q = q.filter(PharmacyRequisition.store_id.in_(store_ids_eff))
    q = _filter_rq_by_departments(q, db, dept_names_eff)
    rows_orm = q.order_by(PharmacyRequisition.created_at.desc()).all()

    req_ids = [r.id for r in rows_orm]
    item_counts: Dict[int, Dict[str, float]] = {}
    if req_ids:
        items = db.query(RequisitionItem).filter(RequisitionItem.requisition_id.in_(req_ids)).all()
        for it in items:
            rid = it.requisition_id
            if rid not in item_counts:
                item_counts[rid] = {"lines": 0, "qty": 0.0}
            item_counts[rid]["lines"] += 1
            item_counts[rid]["qty"] += float(it.requested_quantity or 0)

    store_ids_needed = {r.store_id for r in rows_orm}
    dept_ids_needed = {r.department_id for r in rows_orm if r.department_id}
    stores_map = {s.id: s for s in db.query(Store).filter(Store.id.in_(list(store_ids_needed))).all()} if store_ids_needed else {}
    wards_map = {w.id: w for w in db.query(Ward).filter(Ward.id.in_(list(dept_ids_needed))).all()} if dept_ids_needed else {}

    summary_by_status: Dict[str, int] = {}
    out_rows: List[RequisitionReportRow] = []
    for r in rows_orm:
        st = stores_map.get(r.store_id)
        dept = wards_map.get(r.department_id) if r.department_id else None
        status_key = r.status.value if hasattr(r.status, "value") else str(r.status)
        summary_by_status[status_key] = summary_by_status.get(status_key, 0) + 1
        ic = item_counts.get(r.id, {"lines": 0, "qty": 0.0})
        sk = st.store_kind if st and getattr(st, "store_kind", None) else StoreKind.GENERAL.value
        out_rows.append(
            RequisitionReportRow(
                requisition_id=r.id,
                requisition_number=r.requisition_number,
                created_at=r.created_at,
                status=status_key,
                department_name=dept.name if dept else None,
                ward_legacy=r.ward,
                store_id=r.store_id,
                store_name=st.name if st else "",
                store_kind=sk,
                line_count=int(ic["lines"]),
                total_requested_qty=round(ic["qty"], 4),
            )
        )

    if export_csv:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                "requisition_number",
                "created_at",
                "status",
                "department",
                "ward_legacy",
                "store_name",
                "store_kind",
                "line_count",
                "total_requested_qty",
            ]
        )
        for row in out_rows:
            w.writerow(
                [
                    row.requisition_number,
                    row.created_at.isoformat(),
                    row.status,
                    row.department_name or "",
                    row.ward_legacy or "",
                    row.store_name,
                    row.store_kind,
                    row.line_count,
                    row.total_requested_qty,
                ]
            )
        buf.seek(0)
        filename = f"inventory_requisitions_{start_date}_{end_date}.csv"
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return RequisitionReportResponse(
        start_date=start_date,
        end_date=end_date,
        rows=out_rows,
        summary_by_status=summary_by_status,
    )


@router.get("/store-stock", response_model=None)
def report_store_stock(
    store_id: Optional[int] = Query(None),
    department: Optional[str] = Query(None),
    store_kind: Optional[str] = Query(None, description="Filter stores: general or pharmacy"),
    stock_status: Optional[str] = Query(
        None,
        description="APPROVED, PENDING, REJECTED, EXPIRED, or omit for all",
    ),
    export_csv: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    if store_kind is not None and store_kind not in (StoreKind.PHARMACY.value, StoreKind.GENERAL.value):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="store_kind must be 'general' or 'pharmacy'",
        )
    store_ids_eff, _dept_names_eff = _scope_and_filters(db, current_user, store_id, department, store_kind)

    ss_q = db.query(StoreStock)
    if store_ids_eff is not None:
        ss_q = ss_q.filter(StoreStock.store_id.in_(store_ids_eff))
    if stock_status:
        try:
            st_enum = StockStatus(stock_status.upper())
            ss_q = ss_q.filter(StoreStock.status == st_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid stock_status. Use APPROVED, PENDING, REJECTED, or EXPIRED.",
            )

    stocks = ss_q.order_by(StoreStock.store_id, StoreStock.product_name).all()
    now = utcnow()
    out_rows: List[StoreStockReportRow] = []
    total_qty = 0.0
    total_val = 0.0
    by_status: Dict[str, int] = {}

    stock_store_ids = {s.store_id for s in stocks}
    stores_map = {st.id: st for st in db.query(Store).filter(Store.id.in_(list(stock_store_ids))).all()} if stock_store_ids else {}

    for s in stocks:
        st = stores_map.get(s.store_id)
        sk = st.store_kind if st and getattr(st, "store_kind", None) else StoreKind.GENERAL.value
        stat = s.status.value if hasattr(s.status, "value") else str(s.status)
        by_status[stat] = by_status.get(stat, 0) + 1
        qty = float(s.quantity or 0)
        up = float(s.unit_price) if s.unit_price is not None else None
        lv = qty * up if up is not None else None
        total_qty += qty
        if lv is not None:
            total_val += lv
        exp = s.expiry_date.isoformat() if s.expiry_date else None
        out_rows.append(
            StoreStockReportRow(
                store_id=s.store_id,
                store_name=st.name if st else "",
                store_kind=sk,
                product_code=s.product_code or "",
                product_name=s.product_name or "",
                batch_number=s.batch_number or "",
                expiry_date=exp,
                quantity=round(qty, 4),
                status=stat,
                unit_price=round(up, 4) if up is not None else None,
                line_value=round(lv, 2) if lv is not None else None,
            )
        )

    totals: Dict[str, Any] = {
        "lines": len(out_rows),
        "quantity": round(total_qty, 4),
        "value": round(total_val, 2) if total_val else None,
        "by_status": by_status,
    }

    if export_csv:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                "store_name",
                "store_kind",
                "product_code",
                "product_name",
                "batch_number",
                "expiry_date",
                "quantity",
                "status",
                "unit_price",
                "line_value",
            ]
        )
        for row in out_rows:
            w.writerow(
                [
                    row.store_name,
                    row.store_kind,
                    row.product_code,
                    row.product_name,
                    row.batch_number,
                    row.expiry_date or "",
                    row.quantity,
                    row.status,
                    row.unit_price if row.unit_price is not None else "",
                    row.line_value if row.line_value is not None else "",
                ]
            )
        buf.seek(0)
        filename = f"inventory_store_stock_{now.strftime('%Y%m%d_%H%M')}.csv"
        return StreamingResponse(
            iter([buf.getvalue()]),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return StoreStockReportResponse(as_of=now, rows=out_rows, totals=totals)
