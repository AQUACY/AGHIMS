"""
Companion (copayment) visits API.

Service creation and listing for Companion mode. All identifiers (card number, visit number)
come from the external government system; no internal patient/encounter IDs are used.
"""
import io
import re
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.core.database import get_db
from app.core.dependencies import require_role, get_current_user
from app.core.audit import get_effective_creator_id
from app.models.user import User
from app.models.companion_visit import CompanionVisit
from app.models.companion_visit_item import CompanionVisitItem
from app.models.companion_active_investigation import CompanionActiveInvestigation
from app.models.companion_active_scan import CompanionActiveScan
from app.models.companion_active_xray import CompanionActiveXray

router = APIRouter(prefix="/companion-visits", tags=["companion-visits"])


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


def _visit_all_items_paid(visit_id: int, db: Session) -> bool:
    """True if every bill item has been paid (receipt_number set or amount 0)."""
    items = db.query(CompanionVisitItem).filter(CompanionVisitItem.companion_visit_id == visit_id).all()
    if not items:
        return True
    for it in items:
        amount = (it.unit_price or 0) * (it.quantity or 1)
        if amount > 0 and not (it.receipt_number or it.paid_at):
            return False
    return True


@router.post("/", response_model=CompanionVisitResponse, status_code=status.HTTP_201_CREATED)
def create_companion_visit(
    data: CompanionVisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Records", "Admin"])),
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
    return visit_obj


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
    return [_visit_to_response(v, db) for v in visits]


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
    current_user: User = Depends(require_role(["Lab Head", "Admin"])),
):
    """Add an investigation to the card list. Lab Head or Admin only."""
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
    current_user: User = Depends(require_role(["Lab Head", "Admin"])),
):
    """Remove an investigation from the card list. Lab Head or Admin only."""
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
    current_user: User = Depends(require_role(["Scan", "Scan Head", "Admin"])),
):
    """Add a scan to the card list. Scan, Scan Head, or Admin."""
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
    current_user: User = Depends(require_role(["Scan", "Scan Head", "Admin"])),
):
    """Remove a scan from the card list. Scan, Scan Head, or Admin."""
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
    current_user: User = Depends(require_role(["Xray", "Xray Head", "Admin"])),
):
    """Add an X-ray to the card list. Xray, Xray Head, or Admin."""
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
    current_user: User = Depends(require_role(["Xray", "Xray Head", "Admin"])),
):
    """Remove an X-ray from the card list. Xray, Xray Head, or Admin."""
    row = db.query(CompanionActiveXray).filter(CompanionActiveXray.g_drg_code == g_drg_code).first()
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


@router.post("/parse-drugs-pdf", response_model=List[ParsedDrugLine])
def parse_drugs_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"])),
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
    current_user: User = Depends(require_role(["Pharmacy", "Pharmacy Head", "Admin"])),
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


def _visit_to_response(visit: CompanionVisit, db: Session) -> CompanionVisitResponse:
    """Build visit response with optional undertaking_*_by_name fields."""
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
    Edit/delete: if open -> Records, Admin (edit also Billing for marking closed).
    If closed -> only Admin.
    """
    user_roles = _get_user_roles(current_user, db)
    if "Admin" in user_roles:
        return True
    if visit.status == "closed":
        return False
    if action == "edit":
        return any(r in ["Records", "Admin", "Billing"] for r in user_roles)
    return any(r in ["Records", "Admin"] for r in user_roles)


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
    return visit


@router.delete("/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_companion_visit(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a companion visit.
    Open visits: Records or Admin can delete. Closed visits: only Admin can delete.
    """
    visit = db.query(CompanionVisit).filter(CompanionVisit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Visit not found")
    if not _can_edit_or_delete(visit, current_user, db, "delete"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin can delete a closed visit",
        )
    db.delete(visit)
    db.commit()
    return None


# --- Companion visit items (line items for billing: lab, scan, xray, drug) ---

class CompanionVisitItemCreate(BaseModel):
    """Payload for adding an item to a companion visit."""
    item_code: str
    item_name: str
    category: str  # lab, scan, xray, drug
    unit_price: float
    quantity: float = 1.0


class CompanionVisitItemResponse(BaseModel):
    """Single line item on a companion visit."""
    id: int
    companion_visit_id: int
    item_code: str
    item_name: str
    category: str
    unit_price: float
    quantity: float
    created_at: datetime
    receipt_number: Optional[str] = None
    paid_at: Optional[datetime] = None
    paid_by_id: Optional[int] = None
    payment_method: Optional[str] = None

    class Config:
        from_attributes = True


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
    return q.all()


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
    if cat not in ("lab", "scan", "xray", "drug", "inpatient"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="category must be one of: lab, scan, xray, drug, inpatient",
        )
    item = CompanionVisitItem(
        companion_visit_id=visit_id,
        item_code=(data.item_code or "").strip(),
        item_name=(data.item_name or "").strip() or data.item_code,
        category=cat,
        unit_price=float(data.unit_price),
        quantity=float(data.quantity) if data.quantity else 1.0,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{visit_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_companion_visit_item(
    visit_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["Billing", "Admin"])),
):
    """Remove a line item from a companion visit. Only when visit is open. Billing/Admin only. Inpatient fee only deletable by Admin."""
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
    if item.receipt_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an item that has been paid (receipt issued)",
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
                detail="Only Admin can delete custom inpatient fee items",
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
    current_user: User = Depends(require_role(["Billing", "Admin"])),
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
    if item.receipt_number:
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
    receipt_number: str
    item_ids: List[int]
    payment_method: Optional[str] = None


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
    receipt_number = (data.receipt_number or "").strip()
    if not receipt_number:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="receipt_number is required")
    payment_method = (data.payment_method or "").strip() or None
    now = datetime.utcnow()
    updated = 0
    for item_id in data.item_ids or []:
        item = db.query(CompanionVisitItem).filter(
            CompanionVisitItem.id == item_id,
            CompanionVisitItem.companion_visit_id == visit_id,
        ).first()
        if item and not item.receipt_number:
            item.receipt_number = receipt_number
            item.paid_at = now
            item.paid_by_id = get_effective_creator_id(db, current_user)
            item.payment_method = payment_method
            updated += 1
    db.commit()
    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"Marked {updated} item(s) as paid for companion visit (receipt {receipt_number}).")
    return {"updated": updated, "receipt_number": receipt_number}


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
        if item and item.receipt_number:
            item.receipt_number = None
            item.paid_at = None
            item.paid_by_id = None
            item.payment_method = None
            updated += 1
    db.commit()
    from app.core.audit import set_audit_summary
    set_audit_summary(request, f"Refunded {updated} item(s) for companion visit (card {visit.external_card_number}).")
    return {"updated": updated}
