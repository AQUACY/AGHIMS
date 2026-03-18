from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Any, Optional

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


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return None
    # remove currency symbols and commas
    s = re.sub(r"[^\d.\-]", "", s)
    if not s:
        return None
    try:
        return float(s)
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
        if "service description" not in flat or "qty" not in flat or "no." not in flat:
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
    try:
        html = contents.decode("utf-8")
    except UnicodeDecodeError:
        html = contents.decode("cp1252", errors="replace")

    meta = _extract_meta_ipd(html)
    tables = pd.read_html(io.StringIO(html), keep_default_na=False)
    if not tables:
        raise ValueError(f"No tables found in {filename}")
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
    """
    try:
        html = contents.decode("utf-8")
    except UnicodeDecodeError:
        html = contents.decode("cp1252", errors="replace")

    meta = _extract_meta(html)
    tables = pd.read_html(io.StringIO(html), keep_default_na=False)
    if not tables:
        raise ValueError(f"No tables found in {filename}")
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

