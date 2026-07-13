from __future__ import annotations

import io
import math
import re
from dataclasses import dataclass
from typing import Any, Literal, Optional, Union

import pandas as pd


@dataclass(frozen=True)
class GovernmentServiceLine:
    description: str
    quantity: float
    unit: Optional[str] = None
    total: Optional[float] = None


@dataclass(frozen=True)
class GovernmentOpdExport:
    claim_status: Optional[str]
    insurance_no: Optional[str]
    claim_no: Optional[str]
    patient_name: Optional[str]
    patient_no: Optional[str]
    service_date: Optional[str]
    service_type: Optional[str]
    lines: list[GovernmentServiceLine]


@dataclass(frozen=True)
class GovernmentIpdExport:
    """Parsed government in-patient invoice (HTML/.xls export)."""
    invoice_no: Optional[str]
    visit_no: Optional[str]
    admission_no: Optional[str]
    patient_no: Optional[str]
    patient_name: Optional[str]
    invoice_date: Optional[str]
    admission_date: Optional[str]
    discharge_date: Optional[str]
    insurance_no: Optional[str]
    billing_info: Optional[str]
    lines: list[GovernmentServiceLine]


_WS_RE = re.compile(r"\s+")
_BRACKET_RE = re.compile(r"\[[^\]]*\]")
_PAREN_RE = re.compile(r"\([^)]*\)")


def normalize_service_name(value: str) -> str:
    """
    Best-effort normalization for cross-system matching.
    - Lowercase
    - Remove prefixes like 'Investigation:' / 'Prescription:' / 'Diagnosis:'
    - Remove bracketed qualifiers: 'Foo [Consultation]' -> 'Foo'
    - Collapse whitespace and strip punctuation-like separators
    """
    v = (value or "").strip()
    v = re.sub(r"^(investigation|prescription|diagnosis)\s*:\s*", "", v, flags=re.IGNORECASE)
    v = _BRACKET_RE.sub("", v)
    # Remove parenthetical qualifiers. This fixes common gov-vs-HMS mismatches like:
    # - "Routine Urine Examination (Urine R/E)" vs "Routine Urine Examination"
    # - extra spacing inside parentheses "( HBSAG)" vs "(HBSAG)"
    v = _PAREN_RE.sub("", v)
    v = v.replace("\u2003", " ").replace("\xa0", " ")
    v = _WS_RE.sub(" ", v).strip().lower()
    v = re.sub(r"[|/]+", " ", v)
    v = _WS_RE.sub(" ", v).strip()
    return v


def _bytes_looks_like_html(contents: bytes) -> bool:
    """True if content is likely HTML (including HTML saved as .xls). Not used for real .xlsx (ZIP)."""
    if not contents:
        return False
    # Office Open XML (.xlsx) is a ZIP; never treat as HTML.
    if len(contents) >= 2 and contents[:2] == b"PK":
        return False
    sample = contents[: min(len(contents), 500_000)].lower()
    return b"<html" in sample or b"<!doctype html" in sample or b"<table" in sample


def _flatten_dataframes_for_meta(dfs: list, max_rows_per_sheet: int = 55, max_sheets: int = 8) -> str:
    """Turn leading rows of spreadsheet tables into one string for the same regex meta extractors used on HTML."""
    parts: list[str] = []
    for df in dfs[:max_sheets]:
        try:
            n = min(max_rows_per_sheet, len(df))
            for i in range(n):
                row = df.iloc[i]
                for x in row.tolist():
                    s = str(x).strip()
                    if s and s.lower() != "nan":
                        parts.append(s)
        except Exception:
            continue
    return " ".join(parts)


def _decode_bytes_for_html(contents: bytes) -> str:
    """GHIMS HTML exports may be UTF-8, UTF-8 BOM, Windows-1252, or UTF-16."""
    if not contents:
        return ""
    if contents[:3] == b"\xef\xbb\xbf":
        return contents.decode("utf-8-sig", errors="replace")
    if contents[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return contents.decode("utf-16", errors="replace")
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return contents.decode(enc)
        except UnicodeDecodeError:
            continue
    return contents.decode("utf-8", errors="replace")


def _read_html_tables_from_string(html: str) -> list:
    """pandas.read_html often returns [] for messy GHIMS pages; try flavors + per-table BeautifulSoup."""
    if not html or not html.strip():
        return []
    out: list = []
    flavors = (None, "lxml", "html5lib", "bs4")
    for flavor in flavors:
        try:
            kw: dict = {"keep_default_na": False}
            if flavor is not None:
                kw["flavor"] = flavor
            found = pd.read_html(io.StringIO(html), **kw)
            if found:
                out.extend(found)
                break
        except (ValueError, ImportError, TypeError):
            continue
    if out:
        return out
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for table in soup.find_all("table"):
            frag = str(table)
            for flavor in (None, "lxml", "html5lib", "bs4"):
                try:
                    kw = {"keep_default_na": False}
                    if flavor is not None:
                        kw["flavor"] = flavor
                    sub = pd.read_html(io.StringIO(frag), **kw)
                    if sub:
                        out.extend(sub)
                        break
                except (ValueError, ImportError, TypeError):
                    continue
    except ImportError:
        pass
    return out


def _try_read_excel_all_sheets(contents: bytes) -> tuple[list, bool]:
    """Returns (list of non-empty DataFrames, True if any sheet had rows)."""
    try:
        raw = pd.read_excel(io.BytesIO(contents), sheet_name=None, engine=None)
    except Exception:
        return [], False
    dfs = list(raw.values()) if isinstance(raw, dict) else [raw]
    non_empty = [d for d in dfs if d is not None and not d.empty]
    return non_empty, bool(non_empty)


def _load_government_export_tables(contents: bytes, *, filename: str) -> tuple[list, str]:
    """
    Returns (tables as list of DataFrames, text blob for meta regexes).
    Supports HTML exports (including .xls that are really HTML) and binary .xlsx / .xls.
    """
    fn = (filename or "").lower()
    spreadsheet_ext = fn.endswith(".xlsx") or fn.endswith(".xls") or fn.endswith(".csv")

    # 1) Real spreadsheet: .xlsx / binary .xls (not HTML-in-disguise)
    if spreadsheet_ext and not _bytes_looks_like_html(contents):
        dfs, ok = _try_read_excel_all_sheets(contents)
        if ok:
            return dfs, _flatten_dataframes_for_meta(dfs)
        # Excel open failed or every sheet empty — fall through to HTML attempts

    # 2) HTML (or .xls/.xlsx that is actually HTML / failed binary read)
    html = _decode_bytes_for_html(contents)
    tables = _read_html_tables_from_string(html)
    if tables:
        return tables, html

    # 3) Still nothing: retry Excel (BIFF .xls can falsely match _bytes_looks_like_html; read_html may return [])
    if spreadsheet_ext and not fn.endswith(".csv"):
        dfs, ok = _try_read_excel_all_sheets(contents)
        if ok:
            return dfs, _flatten_dataframes_for_meta(dfs)

    # 4) Single-sheet CSV saved with wrong extension
    if spreadsheet_ext and fn.endswith(".csv"):
        try:
            df = pd.read_csv(io.BytesIO(contents), header=None, encoding_errors="replace")
            if df is not None and not df.empty:
                return [df], _flatten_dataframes_for_meta([df])
        except Exception:
            pass

    return [], html


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    # numpy / other numeric scalars
    if hasattr(value, "dtype") and hasattr(value, "item"):
        try:
            x = float(value.item())
            return x if math.isfinite(x) else None
        except (TypeError, ValueError, OverflowError):
            return None
    s = str(value).strip()
    if not s or s.lower() in ("nan", "inf", "-inf", "infinity", "-infinity"):
        return None
    # remove currency symbols and commas
    s = re.sub(r"[^\d.\-]", "", s)
    if not s:
        return None
    try:
        x = float(s)
        return x if math.isfinite(x) else None
    except ValueError:
        return None


def _extract_meta(html: str) -> dict[str, Optional[str]]:
    # The export tends to be one long HTML page with repeated labels, and
    # sometimes the label/value are separated by HTML tags. We first strip tags
    # into a single text blob, then run regexes on the text.
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("\u2003", " ").replace("\xa0", " ")
    text = _WS_RE.sub(" ", text).strip()

    def _grab(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            return None
        v = _WS_RE.sub(" ", m.group(1)).strip()
        return v or None

    # Some exports concatenate words after status (e.g. "PENDINGASESEWA..."), so capture only the leading token.
    claim_status = _grab(r"CLAIM STATUS\s*:\s*([A-Z_]+)")
    if claim_status:
        claim_status = claim_status.strip().upper()

    insurance_no = _grab(r"Insurance No\.?\s*([A-Za-z0-9-]+)")
    claim_no = _grab(r"Claim No\.?\s*([A-Za-z0-9-]+)")
    patient_name = _grab(r"Patient Name\s*([A-Za-z ,.'-]+?)\s*Patient No\.")
    patient_no = _grab(r"Patient No\.?\s*([A-Za-z0-9-]+)")
    service_date = _grab(r"\bDate\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})\b")
    service_type = _grab(r"Service Type\s*([A-Za-z ]+?)(?:\s+Contact No\.|\s+Attending Doctor|\s+DIAGNOSIS|\s+Open Folder|$)")

    return {
        "claim_status": claim_status,
        "insurance_no": insurance_no,
        "claim_no": claim_no,
        "patient_name": patient_name,
        "patient_no": patient_no,
        "service_date": service_date,
        "service_type": service_type,
    }


def _extract_meta_ipd(html: str) -> dict[str, Optional[str]]:
    """Extract meta from official in-patient invoice HTML (e.g. OFFICIAL IN-PATIENT INVOICE)."""
    text = re.sub(r"<[^>]+>", " ", html)
    text = text.replace("\u2003", " ").replace("\xa0", " ")
    text = _WS_RE.sub(" ", text).strip()

    def _grab(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if not m:
            return None
        v = _WS_RE.sub(" ", m.group(1)).strip()
        return v or None

    invoice_no = _grab(r"Invoice No\.?\s*:\s*([A-Za-z0-9\-]+)")
    if not invoice_no:
        invoice_no = _grab(r"Invoice No\.?\s*([A-Za-z0-9\-]+)")
    date_str = _grab(r"Date\s*:\s*<u>?\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4}\s+[0-9]{1,2}:[0-9]{2}(:[0-9]{2})?)")
    if not date_str:
        date_str = _grab(r"Date\s*:\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})")
    visit_no = _grab(r"Visit No\.?\s*([A-Za-z0-9\-]+)")
    admission_no = _grab(r"Admission No\.?\s*([A-Za-z0-9\-]+)")
    patient_no = _grab(r"Patient No\.?\s*([A-Za-z0-9\-]+)")
    patient_name = _grab(r"Patient Name\s*([A-Za-z ,.'\-]+?)(?:\s+</td>|\s+Gender|\s*$)")
    if not patient_name:
        patient_name = _grab(r"tdInputInpID\">\s*([A-Za-z ,.'\-]+)")
    insurance_no = _grab(r"InsuranceNo\s*([A-Za-z0-9\-]+)")
    billing_info = _grab(r"Billing Info\.?\s*([A-Za-z0-9\s\-]+?)(?:\s+InsuranceNo|\s*$)")
    admission_date = _grab(r"1\.\s*Admission Date\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})")
    discharge_date = _grab(r"Discharge Date\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})")
    visit_date = _grab(r"Visit Date\s*([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})")

    return {
        "invoice_no": invoice_no,
        "visit_no": visit_no,
        "admission_no": admission_no,
        "patient_no": patient_no,
        "patient_name": (patient_name or "").strip() or None,
        "invoice_date": date_str,
        "admission_date": admission_date or visit_date,
        "discharge_date": discharge_date,
        "insurance_no": insurance_no,
        "billing_info": (billing_info or "").strip() or None,
    }


def _parse_services_table_to_lines(tables: list, filename: str = "upload") -> list[GovernmentServiceLine]:
    """Find first table with SERVICE DESCRIPTION / QTY and return line items. Shared by OPD and IPD."""
    for df in tables:
        sample = df.head(60).astype(str).apply(lambda col: col.str.lower())
        flat = " ".join(sample.values.ravel().tolist())
        # Some exports omit a NO. / S/N column; only require description + quantity columns.
        if "service description" not in flat or "qty" not in flat:
            continue
        for i in range(min(len(df), 80)):
            row = [str(x).strip().lower() for x in df.iloc[i].tolist()]
            if any(x == "service description" for x in row) and any(x == "qty" for x in row):
                header = [str(x).strip() for x in df.iloc[i].tolist()]
                data = df.iloc[i + 1 :].copy()
                data.columns = header

                def _col(name: str) -> Optional[str]:
                    for c in data.columns:
                        if str(c).strip().lower() == name.lower():
                            return c
                    return None

                col_no = _col("NO.")
                col_desc = _col("SERVICE DESCRIPTION")
                col_qty = _col("QTY")
                col_unit = _col("UNIT")
                col_total = _col("TOTAL")
                if not col_desc or not col_qty:
                    continue

                lines: list[GovernmentServiceLine] = []
                for _, row in data.iterrows():
                    desc = str(row.get(col_desc, "")).strip()
                    if not desc or desc.lower().startswith("total bill"):
                        continue
                    if col_no:
                        no_val = str(row.get(col_no, "")).strip()
                        if no_val and not re.fullmatch(r"\d+(\.\d+)?", no_val):
                            continue
                        if not no_val:
                            continue
                    qty = _safe_float(row.get(col_qty))
                    if qty is None:
                        continue
                    unit = str(row.get(col_unit, "")).strip() if col_unit else None
                    total = _safe_float(row.get(col_total)) if col_total else None
                    desc = desc.replace("\u2003", " ").replace("\xa0", " ")
                    desc = _WS_RE.sub(" ", desc).strip()
                    lines.append(GovernmentServiceLine(description=desc, quantity=float(qty), unit=unit or None, total=total))
                return lines
    raise ValueError("Could not locate services table header (SERVICE DESCRIPTION / QTY)")


def parse_government_ipd_export(contents: bytes, *, filename: str = "upload") -> GovernmentIpdExport:
    """
    Parses the government IPD (in-patient) invoice export.
    Same table structure as OPD (NO., SERVICE DESCRIPTION, QTY, UNIT, TOTAL); meta is IPD-specific.
    """
    tables, meta_src = _load_government_export_tables(contents, filename=filename)
    if not tables:
        raise ValueError(
            f"No tables found in {filename}. Export the GHIMS billing or IPD invoice in the usual HTML/Excel format "
            "with a grid that includes SERVICE DESCRIPTION and QTY columns."
        )
    meta = _extract_meta_ipd(meta_src)
    lines = _parse_services_table_to_lines(tables, filename)

    return GovernmentIpdExport(
        invoice_no=meta.get("invoice_no"),
        visit_no=meta.get("visit_no"),
        admission_no=meta.get("admission_no"),
        patient_no=meta.get("patient_no"),
        patient_name=meta.get("patient_name"),
        invoice_date=meta.get("invoice_date"),
        admission_date=meta.get("admission_date"),
        discharge_date=meta.get("discharge_date"),
        insurance_no=meta.get("insurance_no"),
        billing_info=meta.get("billing_info"),
        lines=lines,
    )


def parse_government_opd_export(contents: bytes, *, filename: str = "upload") -> GovernmentOpdExport:
    """
    Parses the government OPD billing export.
    Notes:
    - Many ".xls" files are actually HTML (Excel-compatible) exports.
    - We parse with pandas.read_html (lxml) which is already a backend dependency.
    - True .xlsx / binary .xls use pandas.read_excel.
    """
    tables, meta_src = _load_government_export_tables(contents, filename=filename)
    if not tables:
        raise ValueError(
            f"No tables found in {filename}. Export the GHIMS OPD billing file in the usual HTML/Excel format "
            "with a grid that includes SERVICE DESCRIPTION and QTY columns."
        )
    meta = _extract_meta(meta_src)
    lines = _parse_services_table_to_lines(tables, filename)

    return GovernmentOpdExport(
        claim_status=meta.get("claim_status"),
        insurance_no=meta.get("insurance_no"),
        claim_no=meta.get("claim_no"),
        patient_name=meta.get("patient_name"),
        patient_no=meta.get("patient_no"),
        service_date=meta.get("service_date"),
        service_type=meta.get("service_type"),
        lines=lines,
    )


def parse_government_export_auto(
    contents: bytes, *, filename: str = "upload"
) -> tuple[Literal["opd", "ipd"], Union[GovernmentOpdExport, GovernmentIpdExport]]:
    """
    Parse a single GHIMS upload and classify as OPD billing export vs IPD invoice.
    Parses service lines once; uses header text hints when both OPD and IPD meta match.
    """
    tables, meta_src = _load_government_export_tables(contents, filename=filename)
    if not tables:
        raise ValueError(
            f"No tables found in {filename}. If this is a true Excel file, ensure it is not password-protected or empty; "
            "if it is the web export, save as from GHIMS again (HTML/.xls) so the service grid is included."
        )
    lines = _parse_services_table_to_lines(tables, filename)
    low = meta_src[:20000].lower()
    m_o = _extract_meta(meta_src)
    m_i = _extract_meta_ipd(meta_src)

    opd = GovernmentOpdExport(
        claim_status=m_o.get("claim_status"),
        insurance_no=m_o.get("insurance_no"),
        claim_no=m_o.get("claim_no"),
        patient_name=m_o.get("patient_name"),
        patient_no=m_o.get("patient_no"),
        service_date=m_o.get("service_date"),
        service_type=m_o.get("service_type"),
        lines=lines,
    )
    ipd = GovernmentIpdExport(
        invoice_no=m_i.get("invoice_no"),
        visit_no=m_i.get("visit_no"),
        admission_no=m_i.get("admission_no"),
        patient_no=m_i.get("patient_no"),
        patient_name=m_i.get("patient_name"),
        invoice_date=m_i.get("invoice_date"),
        admission_date=m_i.get("admission_date"),
        discharge_date=m_i.get("discharge_date"),
        insurance_no=m_i.get("insurance_no"),
        billing_info=m_i.get("billing_info"),
        lines=lines,
    )

    opd_ok = bool((opd.patient_no or "").strip() and (opd.claim_no or "").strip() and len(lines) > 0)
    ipd_visit_key = (ipd.visit_no or ipd.invoice_no or "").strip()
    ipd_ok = bool((ipd.patient_no or "").strip() and ipd_visit_key and len(lines) > 0)

    ipd_hint = "in-patient" in low or "inpatient" in low
    opd_hint = "claim status" in low or ("claim no" in low and "service type" in low)

    if opd_ok and ipd_ok:
        if ipd_hint and not opd_hint:
            return "ipd", ipd
        if opd_hint and not ipd_hint:
            return "opd", opd
        return "opd", opd
    if opd_ok:
        return "opd", opd
    if ipd_ok:
        return "ipd", ipd

    raise ValueError(
        "Could not parse as government OPD or IPD export. "
        "Use a GHIMS OPD billing export (claim + patient numbers) or an in-patient invoice with service lines."
    )

