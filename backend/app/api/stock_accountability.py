"""
Stocktaking sheets, GHIMS drug names, and dispense-report reconciliation.

Quantity on hand in a local store is not consulted. A unit may request a
GHIMS drug by name. Dispensing stays in GHIMS. This module accounts for
what a shift received and what the dispense report says left.
"""
from collections import defaultdict
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import inspect, or_, text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_inventory_mode_access
from app.models.pharmacy_requisition import PharmacyRequisition, RequisitionStatus
from app.models.requisition_item import RequisitionItem
from app.models.stock_accountability import (
    DispenseReport,
    DispenseReportLine,
    GhimsCatalogItem,
    StocktakingLine,
    StocktakingSheet,
)
from app.models.user import User
from app.models.ward import Ward
from app.services.dispense_report_parser import DispenseReportError, parse_dispense_report
from app.services.stock_names import match_drug

router = APIRouter(prefix="/stock-accountability", tags=["stock-accountability"])

SHIFTS = {"morning", "afternoon", "night"}
SHEET_STATUSES = {"open", "closed"}
_R_COLUMNS = ("mon_r", "tue_r", "wed_r", "thu_r", "fri_r")


def ensure_stock_accountability_schema(db: Session) -> None:
    """Add the shift column on requisitions. New tables come from create_all."""
    bind = db.get_bind()
    insp = inspect(bind)
    if "pharmacy_requisitions" not in insp.get_table_names():
        return
    columns = {col["name"] for col in insp.get_columns("pharmacy_requisitions")}
    if "shift" in columns:
        return
    db.execute(text("ALTER TABLE pharmacy_requisitions ADD COLUMN shift VARCHAR(20) NULL"))
    db.commit()


class CatalogItemResponse(BaseModel):
    drug_id: str
    drug_name: str

    class Config:
        from_attributes = True


class SheetLineResponse(BaseModel):
    id: int
    drug_id: Optional[str] = None
    medicine_name: str
    sort_order: int
    mon_r: Optional[float] = None
    mon_st: Optional[float] = None
    tue_r: Optional[float] = None
    wed_r: Optional[float] = None
    thu_r: Optional[float] = None
    fri_r: Optional[float] = None
    fri_am_st: Optional[float] = None
    fri_cb: Optional[float] = None

    class Config:
        from_attributes = True


class SheetResponse(BaseModel):
    id: int
    department_id: int
    department_name: Optional[str] = None
    shift: str
    period_from: date
    period_to: date
    prepared_by: Optional[str] = None
    checked_by: Optional[str] = None
    notes: Optional[str] = None
    status: str
    created_at: datetime
    lines: List[SheetLineResponse] = []

    class Config:
        from_attributes = True


class SheetCreate(BaseModel):
    department_id: int
    shift: str
    period_from: date
    period_to: date
    prepared_by: Optional[str] = None
    checked_by: Optional[str] = None


class LineWrite(BaseModel):
    id: int
    mon_r: Optional[float] = None
    mon_st: Optional[float] = None
    tue_r: Optional[float] = None
    wed_r: Optional[float] = None
    thu_r: Optional[float] = None
    fri_r: Optional[float] = None
    fri_am_st: Optional[float] = None
    fri_cb: Optional[float] = None


class SheetUpdate(BaseModel):
    shift: Optional[str] = None
    period_from: Optional[date] = None
    period_to: Optional[date] = None
    prepared_by: Optional[str] = None
    checked_by: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    lines: Optional[List[LineWrite]] = None


class LineCreate(BaseModel):
    drug_id: str = Field(..., min_length=1)


class ReportSummary(BaseModel):
    id: int
    period_from: date
    period_to: date
    facility_name: Optional[str] = None
    source_filename: Optional[str] = None
    line_count: int
    created_at: datetime


def _check_shift(value: str) -> str:
    shift = (value or "").strip().lower()
    if shift not in SHIFTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shift must be morning, afternoon, or night.",
        )
    return shift


def _sheet_or_404(db: Session, sheet_id: int) -> StocktakingSheet:
    sheet = db.query(StocktakingSheet).filter(StocktakingSheet.id == sheet_id).first()
    if not sheet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stocktaking sheet not found")
    return sheet


def _to_sheet(sheet: StocktakingSheet, department_name: Optional[str]) -> SheetResponse:
    return SheetResponse(
        id=sheet.id,
        department_id=sheet.department_id,
        department_name=department_name,
        shift=sheet.shift,
        period_from=sheet.period_from,
        period_to=sheet.period_to,
        prepared_by=sheet.prepared_by,
        checked_by=sheet.checked_by,
        notes=sheet.notes,
        status=sheet.status,
        created_at=sheet.created_at,
        lines=[SheetLineResponse.model_validate(line) for line in sheet.lines],
    )


def _num(value: Optional[float]) -> float:
    return float(value or 0)


def expected_dispensed(line: StocktakingLine) -> Optional[float]:
    """Monday stocktake + requisitions received through Friday − Friday closing balance."""
    if line.fri_cb is None:
        return None
    received = _num(line.mon_st) + sum(_num(getattr(line, col)) for col in _R_COLUMNS)
    return received - _num(line.fri_cb)


def upsert_catalog(db: Session, drug_id: str, drug_name: str) -> None:
    drug_id = (drug_id or "").strip()
    drug_name = (drug_name or "").strip()
    if not drug_id or not drug_name:
        return
    row = db.query(GhimsCatalogItem).filter(GhimsCatalogItem.drug_id == drug_id).first()
    if row:
        if row.drug_name != drug_name:
            row.drug_name = drug_name[:500]
        return
    db.add(GhimsCatalogItem(drug_id=drug_id[:80], drug_name=drug_name[:500]))


def _ghims_connection():
    try:
        from app.services.ghims_live_compare import _connect
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    try:
        return _connect()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read GHIMS. {exc}",
        ) from exc


@router.get("/ghims-drugs")
def list_ghims_drugs(
    q: str = "",
    limit: int = 80,
    current_user: User = Depends(require_inventory_mode_access()),
):
    """Live drug list from GHIMS for this hospital, plus the exchange category MapBranchItems uses."""
    limit = max(1, min(int(limit or 80), 200))
    needle = (q or "").strip()
    like = f"%{needle}%"
    conn = _ghims_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT TOP 1 BranchID, BranchName
            FROM dbo.Branch
            WHERE BranchName LIKE '%ASESEWA%'
            ORDER BY BranchID
            """
        )
        branch = cur.fetchone()
        branch_id = branch[0] if branch else "E0032"
        branch_name = branch[1] if branch else branch_id
        name_filter = ""
        query_params = [limit, f"{branch_id}%", branch_id]
        if needle:
            name_filter = " AND (d.DrugName LIKE ? OR d.DrugID LIKE ?)"
            query_params.extend([like, like])
        cur.execute(
            f"""
            SELECT TOP (?)
                d.DrugID,
                d.DrugName,
                t.DrugTypeName,
                m.DrugModeName,
                b.BillGroupName,
                u.UnitOfMeasureName,
                d.ProdDate1,
                (
                    SELECT COUNT(*)
                    FROM dbo.DrugStockLevel s
                    WHERE s.DrugID = d.DrugID AND s.DrugStoreID LIKE ?
                ) AS store_rows
            FROM dbo.Drug d
            LEFT JOIN dbo.DrugType t ON t.DrugTypeID = d.DrugTypeID
            LEFT JOIN dbo.DrugMode m ON m.DrugModeID = d.DrugModeID
            LEFT JOIN dbo.BillGroup b ON b.BillGroupID = d.BillGroupID
            LEFT JOIN dbo.UnitOfMeasure u ON u.UnitOfMeasureID = d.UnitOfMeasureID
            WHERE d.DrugGroupID = ?
            {name_filter}
            ORDER BY d.ProdDate1 DESC
            """,
            query_params,
        )
        drugs = []
        for row in cur.fetchall():
            created = row[6].isoformat(sep=" ", timespec="seconds") if row[6] else None
            drugs.append(
                {
                    "drug_id": row[0],
                    "drug_name": row[1],
                    "drug_type": row[2],
                    "drug_mode": row[3],
                    "bill_group": row[4],
                    "unit": row[5],
                    "created_at": created,
                    "on_store": int(row[7] or 0) > 0,
                    "store_rows": int(row[7] or 0),
                }
            )
        exchange = []
        if needle:
            cur.execute(
                """
                SELECT TOP 20 item_name, exchange_item_code, service_type
                FROM dbo.NHIExchangeItems
                WHERE item_name LIKE ? OR exchange_item_code LIKE ?
                ORDER BY item_name
                """,
                [like, like],
            )
            for row in cur.fetchall():
                exchange.append(
                    {
                        "item_name": row[0],
                        "exchange_item_code": row[1],
                        "service_type": row[2],
                    }
                )
    finally:
        conn.close()
    return {
        "branch_id": branch_id,
        "branch_name": branch_name,
        "drugs": drugs,
        "exchange": exchange,
    }


@router.get("/catalog", response_model=List[CatalogItemResponse])
def search_catalog(
    q: str = "",
    limit: int = 40,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    """GHIMS drug names a unit may request. Stock quantity is not returned."""
    limit = max(1, min(limit, 100))
    query = db.query(GhimsCatalogItem)
    needle = (q or "").strip()
    if needle:
        like = f"%{needle}%"
        query = query.filter(
            or_(GhimsCatalogItem.drug_name.ilike(like), GhimsCatalogItem.drug_id.ilike(like))
        )
    rows = query.order_by(GhimsCatalogItem.drug_name.asc()).limit(limit).all()
    return rows


@router.post("/catalog/sync")
def sync_catalog_from_ghims(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    """Copy DrugID and DrugName from the GHIMS store. Quantities are not copied."""
    try:
        from app.services.ghims_live_compare import _connect
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    try:
        conn = _connect()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read the GHIMS drug list. {exc}",
        ) from exc
    known = {row.drug_id for row in db.query(GhimsCatalogItem.drug_id).all()}
    imported = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DrugID, DrugName FROM dbo.Drug WHERE DrugName IS NOT NULL")
        for drug_id, drug_name in cursor.fetchall():
            code = str(drug_id or "").strip()
            if not code:
                continue
            if code not in known:
                imported += 1
                known.add(code)
            upsert_catalog(db, code, str(drug_name or ""))
        db.commit()
    finally:
        conn.close()
    total = db.query(GhimsCatalogItem).count()
    return {"imported": imported, "total": total}


@router.get("/sheets", response_model=List[SheetResponse])
def list_sheets(
    department_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    query = db.query(StocktakingSheet)
    if department_id:
        query = query.filter(StocktakingSheet.department_id == department_id)
    sheets = query.order_by(StocktakingSheet.period_from.desc(), StocktakingSheet.id.desc()).all()
    names = {
        ward.id: ward.name
        for ward in db.query(Ward).filter(Ward.id.in_([s.department_id for s in sheets] or [0])).all()
    }
    return [_to_sheet(sheet, names.get(sheet.department_id)) for sheet in sheets]


@router.post("/sheets", response_model=SheetResponse, status_code=status.HTTP_201_CREATED)
def create_sheet(
    payload: SheetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    if payload.period_to < payload.period_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The end date is before the start date.")
    department = db.query(Ward).filter(Ward.id == payload.department_id).first()
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    sheet = StocktakingSheet(
        department_id=payload.department_id,
        shift=_check_shift(payload.shift),
        period_from=payload.period_from,
        period_to=payload.period_to,
        prepared_by=(payload.prepared_by or "").strip() or None,
        checked_by=(payload.checked_by or "").strip() or None,
        status="open",
        created_by=current_user.id,
    )
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    return _to_sheet(sheet, department.name)


@router.get("/sheets/{sheet_id}", response_model=SheetResponse)
def get_sheet(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    sheet = _sheet_or_404(db, sheet_id)
    department = db.query(Ward).filter(Ward.id == sheet.department_id).first()
    return _to_sheet(sheet, department.name if department else None)


@router.put("/sheets/{sheet_id}", response_model=SheetResponse)
def update_sheet(
    sheet_id: int,
    payload: SheetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    sheet = _sheet_or_404(db, sheet_id)
    if payload.shift is not None:
        sheet.shift = _check_shift(payload.shift)
    if payload.period_from is not None:
        sheet.period_from = payload.period_from
    if payload.period_to is not None:
        sheet.period_to = payload.period_to
    if sheet.period_to < sheet.period_from:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The end date is before the start date.")
    if payload.prepared_by is not None:
        sheet.prepared_by = payload.prepared_by.strip() or None
    if payload.checked_by is not None:
        sheet.checked_by = payload.checked_by.strip() or None
    if payload.notes is not None:
        sheet.notes = payload.notes.strip() or None
    if payload.status is not None:
        status_value = payload.status.strip().lower()
        if status_value not in SHEET_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status must be open or closed.")
        sheet.status = status_value
    if payload.lines:
        by_id = {line.id: line for line in sheet.lines}
        for incoming in payload.lines:
            line = by_id.get(incoming.id)
            if not line:
                continue
            for field in (
                "mon_r",
                "mon_st",
                "tue_r",
                "wed_r",
                "thu_r",
                "fri_r",
                "fri_am_st",
                "fri_cb",
            ):
                setattr(line, field, getattr(incoming, field))
    db.commit()
    db.refresh(sheet)
    department = db.query(Ward).filter(Ward.id == sheet.department_id).first()
    return _to_sheet(sheet, department.name if department else None)


@router.post("/sheets/{sheet_id}/lines", response_model=SheetResponse)
def add_sheet_line(
    sheet_id: int,
    payload: LineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    sheet = _sheet_or_404(db, sheet_id)
    drug = db.query(GhimsCatalogItem).filter(GhimsCatalogItem.drug_id == payload.drug_id.strip()).first()
    if not drug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That name is not on the GHIMS list. Load the GHIMS names, or upload a dispense report that contains it.",
        )
    if any(line.drug_id == drug.drug_id for line in sheet.lines):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That medicine is already on this sheet.")
    order = max((line.sort_order for line in sheet.lines), default=0) + 1
    db.add(
        StocktakingLine(
            sheet_id=sheet.id,
            drug_id=drug.drug_id,
            medicine_name=drug.drug_name,
            sort_order=order,
        )
    )
    db.commit()
    db.refresh(sheet)
    department = db.query(Ward).filter(Ward.id == sheet.department_id).first()
    return _to_sheet(sheet, department.name if department else None)


@router.delete("/sheets/{sheet_id}/lines/{line_id}", response_model=SheetResponse)
def delete_sheet_line(
    sheet_id: int,
    line_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    sheet = _sheet_or_404(db, sheet_id)
    line = next((item for item in sheet.lines if item.id == line_id), None)
    if not line:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medicine row not found")
    db.delete(line)
    db.commit()
    db.refresh(sheet)
    department = db.query(Ward).filter(Ward.id == sheet.department_id).first()
    return _to_sheet(sheet, department.name if department else None)


@router.post("/sheets/{sheet_id}/fill-requisitions", response_model=SheetResponse)
def fill_from_requisitions(
    sheet_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    """Write served quantities into the R columns for this shift and week.

    Monday stocktake and Friday closing balance are left as entered.
    """
    sheet = _sheet_or_404(db, sheet_id)
    requisitions = (
        db.query(PharmacyRequisition)
        .filter(
            PharmacyRequisition.department_id == sheet.department_id,
            PharmacyRequisition.shift == sheet.shift,
            PharmacyRequisition.status.in_(
                [RequisitionStatus.FULFILLED, RequisitionStatus.PARTIALLY_FULFILLED]
            ),
        )
        .all()
    )
    totals = defaultdict(lambda: {col: 0.0 for col in _R_COLUMNS})
    names = {}
    for req in requisitions:
        when = req.fulfilled_at or req.updated_at
        if not when:
            continue
        served_on = when.date()
        if served_on < sheet.period_from or served_on > sheet.period_to:
            continue
        column = {0: "mon_r", 1: "tue_r", 2: "wed_r", 3: "thu_r"}.get(served_on.weekday(), "fri_r")
        items = db.query(RequisitionItem).filter(RequisitionItem.requisition_id == req.id).all()
        for item in items:
            qty = float(item.fulfilled_quantity or 0)
            if qty <= 0:
                continue
            key = (item.product_code or "").strip() or (item.product_name or "").strip()
            totals[key][column] += qty
            names[key] = (item.product_code, item.product_name)

    lines_by_drug = {line.drug_id: line for line in sheet.lines if line.drug_id}
    lines_by_name = {line.medicine_name: line for line in sheet.lines}
    order = max((line.sort_order for line in sheet.lines), default=0)
    for key, columns in totals.items():
        product_code, product_name = names[key]
        code = (product_code or "").strip()
        label = (product_name or product_code or "Item")[:500]
        line = lines_by_drug.get(code) or lines_by_name.get(label)
        if line is None:
            order += 1
            line = StocktakingLine(
                sheet_id=sheet.id,
                drug_id=code[:80] or None,
                medicine_name=label,
                sort_order=order,
            )
            db.add(line)
            sheet.lines.append(line)
            if line.drug_id:
                lines_by_drug[line.drug_id] = line
            lines_by_name[line.medicine_name] = line
        for col, qty in columns.items():
            setattr(line, col, qty or None)
    db.commit()
    db.refresh(sheet)
    department = db.query(Ward).filter(Ward.id == sheet.department_id).first()
    result = _to_sheet(sheet, department.name if department else None)
    return result


@router.get("/reports", response_model=List[ReportSummary])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    reports = db.query(DispenseReport).order_by(DispenseReport.period_from.desc(), DispenseReport.id.desc()).all()
    return [
        ReportSummary(
            id=report.id,
            period_from=report.period_from,
            period_to=report.period_to,
            facility_name=report.facility_name,
            source_filename=report.source_filename,
            line_count=len(report.lines),
            created_at=report.created_at,
        )
        for report in reports
    ]


@router.post("/reports/upload", response_model=ReportSummary, status_code=status.HTTP_201_CREATED)
async def upload_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The file is empty.")
    html = raw.decode("utf-8", errors="replace")
    try:
        parsed = parse_dispense_report(html)
    except DispenseReportError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    report = DispenseReport(
        period_from=parsed["period_from"],
        period_to=parsed["period_to"],
        facility_name=parsed.get("facility_name"),
        source_filename=(file.filename or "dispense-report.xls")[:300],
        uploaded_by=current_user.id,
    )
    db.add(report)
    db.flush()
    for line in parsed["lines"]:
        db.add(
            DispenseReportLine(
                report_id=report.id,
                payer_group=line["payer_group"][:80] if line["payer_group"] else None,
                payer_scheme=line["payer_scheme"][:200] if line["payer_scheme"] else None,
                drug_id=line["drug_id"][:80],
                drug_name=line["drug_name"][:500],
                quantity_sold=line["quantity_sold"],
                amount=line["amount"],
            )
        )
        upsert_catalog(db, line["drug_id"], line["drug_name"])
    db.commit()
    db.refresh(report)
    return ReportSummary(
        id=report.id,
        period_from=report.period_from,
        period_to=report.period_to,
        facility_name=report.facility_name,
        source_filename=report.source_filename,
        line_count=len(parsed["lines"]),
        created_at=report.created_at,
    )


def _report_quantities(report: DispenseReport) -> dict:
    """Sum quantity sold per drug across payer groups."""
    totals = {}
    for line in report.lines:
        bucket = totals.setdefault(
            line.drug_id,
            {"drug_id": line.drug_id, "drug_name": line.drug_name, "quantity": 0.0, "payers": defaultdict(float)},
        )
        bucket["quantity"] += float(line.quantity_sold or 0)
        bucket["payers"][line.payer_group or ""] += float(line.quantity_sold or 0)
    return totals


@router.get("/sheets/{sheet_id}/reconciliation")
def reconcile_sheet(
    sheet_id: int,
    report_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_inventory_mode_access()),
):
    sheet = _sheet_or_404(db, sheet_id)
    report = None
    if report_id:
        report = db.query(DispenseReport).filter(DispenseReport.id == report_id).first()
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispense report not found")
    else:
        overlapping = (
            db.query(DispenseReport)
            .filter(
                DispenseReport.period_from <= sheet.period_to,
                DispenseReport.period_to >= sheet.period_from,
            )
            .order_by(DispenseReport.id.desc())
            .all()
        )
        report = overlapping[0] if overlapping else None

    rows = []
    dispensed_ids = set()
    quantities = _report_quantities(report) if report else {}
    candidates = [{"drug_id": key, "drug_name": value["drug_name"]} for key, value in quantities.items()]

    for line in sheet.lines:
        expected = expected_dispensed(line)
        received = _num(line.mon_st) + sum(_num(getattr(line, col)) for col in _R_COLUMNS)
        actual = None
        matched_name = None
        ambiguous = False
        options = []
        if report:
            bucket = quantities.get(line.drug_id) if line.drug_id else None
            if bucket:
                actual = bucket["quantity"]
                matched_name = bucket["drug_name"]
                dispensed_ids.add(line.drug_id)
            else:
                found = match_drug(line.medicine_name, candidates)
                ambiguous = found.ambiguous
                options = [{"drug_id": opt["drug_id"], "drug_name": opt["drug_name"]} for opt in found.options]
                if found.drug_id and found.drug_id in quantities:
                    actual = quantities[found.drug_id]["quantity"]
                    matched_name = found.drug_name
                    dispensed_ids.add(found.drug_id)
        difference = None if expected is None or actual is None else round(actual - expected, 4)
        if expected is None:
            state = "needs_closing_balance"
        elif not report:
            state = "no_report"
        elif ambiguous and actual is None:
            state = "ambiguous"
        elif actual is None and expected == 0:
            state = "no_movement"
        elif actual is None:
            state = "missing_from_report"
        elif abs(difference) < 0.001:
            state = "balanced"
        elif difference > 0:
            state = "report_higher"
        else:
            state = "sheet_higher"
        rows.append(
            {
                "line_id": line.id,
                "medicine_name": line.medicine_name,
                "drug_id": line.drug_id,
                "taken": received,
                "closing_balance": line.fri_cb,
                "expected_dispensed": expected,
                "dispensed": actual,
                "matched_name": matched_name,
                "difference": difference,
                "state": state,
                "options": options,
            }
        )

    extra = []
    if report:
        for drug_id, bucket in quantities.items():
            if drug_id in dispensed_ids:
                continue
            extra.append(
                {
                    "drug_id": drug_id,
                    "drug_name": bucket["drug_name"],
                    "quantity": bucket["quantity"],
                    "payers": dict(bucket["payers"]),
                }
            )
        extra.sort(key=lambda item: item["drug_name"].lower())

    covers = False
    if report:
        covers = report.period_from <= sheet.period_from and report.period_to >= sheet.period_to
    return {
        "sheet_id": sheet.id,
        "report": None
        if not report
        else {
            "id": report.id,
            "period_from": report.period_from.isoformat(),
            "period_to": report.period_to.isoformat(),
            "facility_name": report.facility_name,
            "source_filename": report.source_filename,
            "covers_sheet": covers,
        },
        "rows": rows,
        "dispensed_not_on_sheet": extra,
    }
