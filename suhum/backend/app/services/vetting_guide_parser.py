"""
Parse vetting guide CSV rows into structured reference data for claim vetting.
"""
from __future__ import annotations

import csv
import io
import re
from typing import Any, Dict, List, Optional


def normalize_claim_id(raw: Optional[str]) -> str:
    s = str(raw or "").strip().upper()
    if not s:
        return ""
    if s.startswith("CLA-"):
        return s
    return f"CLA-{s}"


def _split_lines(text: Optional[str]) -> List[str]:
    if not text:
        return []
    return [ln.strip() for ln in str(text).replace("\r\n", "\n").split("\n") if ln.strip()]


def _parse_service_line(line: str) -> Dict[str, Any]:
    raw = line.strip()
    name = raw
    suffix = ""
    if "--" in raw:
        parts = raw.rsplit("--", 1)
        name = parts[0].strip()
        suffix = parts[1].strip()
    return {
        "raw": raw,
        "name": name,
        "suffix": suffix,
        "kind": "procedure",
    }


def _parse_drug_line(line: str) -> Dict[str, Any]:
    raw = line.strip()
    out: Dict[str, Any] = {
        "raw": raw,
        "medicine_code": "",
        "quantity": "",
        "dose": "",
        "frequency": "",
        "duration": "",
        "kind": "medicine",
    }
    # OMEPRATA1 x14 — 20 MG BDS for 7
    m = re.match(
        r"^([A-Za-z0-9]+)\s+x\s*(\d+(?:\.\d+)?)\s*[—\-–]\s*(.+)$",
        raw,
        flags=re.IGNORECASE,
    )
    if not m:
        # Fallback: leading token as code
        tok = raw.split(None, 1)[0] if raw else ""
        if re.match(r"^[A-Za-z0-9]{4,}$", tok or ""):
            out["medicine_code"] = tok.upper()
        return out

    out["medicine_code"] = m.group(1).upper()
    out["quantity"] = m.group(2)
    rest = m.group(3).strip()
    for_match = re.search(r"\bfor\s+(\d+(?:\.\d+)?(?:\s*days?)?)\s*$", rest, flags=re.IGNORECASE)
    if for_match:
        out["duration"] = for_match.group(1).strip()
        rest = rest[: for_match.start()].strip()

    tokens = rest.split()
    if len(tokens) >= 2 and re.match(r"^\d", tokens[0]):
        out["dose"] = f"{tokens[0]} {' '.join(tokens[1:-1])}".strip() if len(tokens) > 2 else f"{tokens[0]} {tokens[1]}"
        out["frequency"] = tokens[-1].upper() if len(tokens) >= 2 else ""
    else:
        out["dose"] = rest
    return out


def _parse_investigation_line(line: str) -> Dict[str, Any]:
    raw = line.strip()
    return {
        "raw": raw,
        "name": raw,
        "kind": "investigation",
    }


def parse_vetting_row(row: Dict[str, str]) -> Dict[str, Any]:
    services = [_parse_service_line(x) for x in _split_lines(row.get("services_billed"))]
    investigations = [_parse_investigation_line(x) for x in _split_lines(row.get("investigations"))]
    medicines = [_parse_drug_line(x) for x in _split_lines(row.get("drugs_dispensed"))]
    prescriptions = [_parse_drug_line(x) for x in _split_lines(row.get("prescriptions"))]

    return {
        "visit_type": (row.get("visit_type") or "").strip(),
        "entity_id": (row.get("entity_id") or "").strip(),
        "claim_id": normalize_claim_id(row.get("claim_id")),
        "service_date": (row.get("service_date") or "").strip(),
        "patient_no": (row.get("patient_no") or "").strip(),
        "patient_name": (row.get("patient_name") or "").strip(),
        "member_no": (row.get("member_no") or "").strip(),
        "clinical": {
            "presenting_complaint": (row.get("presenting_complaint") or "").strip(),
            "odq": (row.get("odq") or "").strip(),
            "on_examination": (row.get("on_examination") or "").strip(),
            "chief_complaint_full": (row.get("chief_complaint_full") or "").strip(),
            "history_present_illness": (row.get("history_present_illness") or "").strip(),
            "doctor_notes": (row.get("doctor_notes") or "").strip(),
            "nurse_notes": (row.get("nurse_notes") or "").strip(),
            "diagnosis": (row.get("diagnosis") or "").strip(),
            "provisional_diagnosis": (row.get("provisional_diagnosis") or "").strip(),
            "vitals": (row.get("vitals") or "").strip(),
            "general_examination": (row.get("general_examination") or "").strip(),
            "referral_notes": (row.get("referral_notes") or "").strip(),
            "other_notes": (row.get("other_notes") or "").strip(),
            "full_clinical_text": (row.get("full_clinical_text") or "").strip(),
        },
        "services": services,
        "investigations": investigations,
        "medicines": medicines or prescriptions,
        "prescriptions": prescriptions,
    }


def parse_vetting_guide_csv(content: str) -> List[Dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(content))
    rows: List[Dict[str, Any]] = []
    for row in reader:
        if not row:
            continue
        claim_id = normalize_claim_id(row.get("claim_id"))
        if not claim_id:
            continue
        parsed = parse_vetting_row(row)
        rows.append({
            "claim_id": claim_id,
            "raw_row": dict(row),
            "parsed": parsed,
        })
    return rows
