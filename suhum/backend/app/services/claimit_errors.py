"""ClaimIT error categorization and lookup for GHIMS import items."""
from __future__ import annotations

from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.claimit_report import ClaimItReportError
from app.models.claim_xml_import import ClaimXmlImportItem

CLAIMIT_SECTION_ORDER = [
    "client",
    "provider",
    "services",
    "procedures",
    "diagnosis",
    "investigations",
    "medicines",
    "other",
]


def empty_claimit_by_section() -> dict:
    return {s: [] for s in CLAIMIT_SECTION_ORDER}


def empty_claimit_errors() -> dict:
    return {"messages": [], "by_section": empty_claimit_by_section()}


def categorize_claimit_error_pairs(pairs: List[Tuple[Optional[str], str]]) -> dict:
    by_section = empty_claimit_by_section()
    for outcome, msg in pairs:
        if not msg or not isinstance(msg, str):
            continue
        lower = msg.lower()
        labeled = f"[{(outcome or 'ERROR').strip().upper()}] {msg}" if outcome else msg

        if (
            ("procedures/diagnoses" in lower.replace(" ", ""))
            or ("procedure" in lower and "diagnosis" in lower and ("opd" in lower or "ipd" in lower))
        ):
            by_section["procedures"].append(labeled)
            by_section["diagnosis"].append(labeled)
            continue

        if any(k in lower for k in (
            "member", "card serial", "hospital record", "insurance id", "patient",
            "surname", "other name", "date of birth", "age", "gender", "nhis number",
        )):
            by_section["client"].append(labeled)
        elif any(k in lower for k in ("provider", "scheme code", "month of claim")):
            by_section["provider"].append(labeled)
        elif any(k in lower for k in (
            "type of service", "opd", "ipd", "pharmacy", "attendance", "specialty",
            "specialties", "outcome", "principal gdrg", "service outcome",
        )):
            by_section["services"].append(labeled)
        elif any(k in lower for k in ("procedure", "surgery", "surgical")) and "diagnosis" not in lower:
            by_section["procedures"].append(labeled)
        elif any(k in lower for k in ("diagnosis", "icd-10", "icd10", "chief complaint", "gdrg")) and "procedure" not in lower and "surgery" not in lower:
            by_section["diagnosis"].append(labeled)
        elif any(k in lower for k in ("investigation", "lab", "x-ray", "xray", "scan")):
            by_section["investigations"].append(labeled)
        elif any(k in lower for k in (
            "drug", "medicine", "prescription", "frequency", "duration", "dose",
            "quantity", "pharmacy", "medication",
        )):
            by_section["medicines"].append(labeled)
        else:
            by_section["other"].append(labeled)
    return by_section


def get_claimit_errors_for_import_item(db: Session, item: ClaimXmlImportItem) -> dict:
    ids = {str(item.claim_claim_id or "").strip()}
    payload = item.payload or {}
    claim_id = str(payload.get("claimID") or payload.get("claimId") or "").strip()
    if claim_id:
        ids.add(claim_id)
    ids.discard("")
    if not ids:
        return empty_claimit_errors()

    rows = (
        db.query(ClaimItReportError)
        .filter(ClaimItReportError.claim_claim_id.in_(list(ids)))
        .order_by(ClaimItReportError.id.desc())
        .all()
    )
    pairs: List[Tuple[str, str]] = []
    seen = set()
    for row in rows:
        outcome = (row.outcome or "ERROR").strip().upper()
        for message in (row.error_messages or []):
            if not isinstance(message, str) or not message.strip():
                continue
            key = (outcome, message.strip())
            if key in seen:
                continue
            seen.add(key)
            pairs.append(key)

    by_section = categorize_claimit_error_pairs(pairs)
    messages = list(dict.fromkeys(f"[{o}] {t}" for o, t in pairs))
    return {"messages": messages, "by_section": by_section}
