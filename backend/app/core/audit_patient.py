"""
Helpers for human-readable patient references in audit trail summaries.
Prefer card number or insurance ID over internal database IDs.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional, Union

from app.models.patient import Patient

DateLike = Union[date, datetime, str, None]


def format_audit_display_date(value: DateLike) -> Optional[str]:
    """Format a date for auditors as DD-MM-YYYY."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:10] if len(text) > 10 else text, fmt).strftime("%d-%m-%Y")
        except ValueError:
            continue
    return text


def patient_audit_identifier(patient: Optional[Patient]) -> str:
    """Card number, insurance/member number, or name — never raw patient id."""
    if not patient:
        return "unknown patient"
    card = (patient.card_number or "").strip()
    if card:
        return card
    insurance = (patient.insurance_id or "").strip()
    if insurance:
        return f"insurance {insurance}"
    name = " ".join(
        p for p in [(patient.name or "").strip(), (patient.surname or "").strip()] if p
    ).strip()
    return name or "unknown patient"


def summarize_patient_registration(patient: Patient, card_number: str) -> str:
    ident = (card_number or patient_audit_identifier(patient)).strip()
    name = " ".join(
        p for p in [(patient.name or "").strip(), (patient.surname or "").strip()] if p
    ).strip()
    if name:
        return f"Registered new patient {name} (card {ident})."
    return f"Registered new patient with card {ident}."


def summarize_patient_update(patient: Patient) -> str:
    ident = patient_audit_identifier(patient)
    name = " ".join(
        p for p in [(patient.name or "").strip(), (patient.surname or "").strip()] if p
    ).strip()
    if name:
        return f"Updated patient {name} (card {ident})."
    return f"Updated patient record (card {ident})."


def summarize_nhia_ccc_generation(
    patient: Patient,
    *,
    ccc: Optional[str] = None,
    insurance_start: DateLike = None,
    insurance_end: DateLike = None,
) -> str:
    ident = patient_audit_identifier(patient)
    parts = [f"Generated NHIA CCC"]
    if ccc:
        parts[0] = f"Generated NHIA CCC {ccc.strip()}"
    parts.append(f"for patient {ident}")
    start_s = format_audit_display_date(insurance_start or patient.insurance_start_date)
    end_s = format_audit_display_date(insurance_end or patient.insurance_end_date)
    if start_s or end_s:
        period = []
        if start_s:
            period.append(f"start date : {start_s}")
        if end_s:
            period.append(f"end date : {end_s}")
        parts.append(f"with eligibility period of {' and '.join(period)}")
    return " ".join(parts) + "."


def summarize_patient_encounter(
    patient: Patient,
    *,
    encounter_id: int,
    service_type: str,
    ccc_number: Optional[str] = None,
    forced_cash: bool = False,
) -> str:
    ident = patient_audit_identifier(patient)
    parts = [f"Created {service_type or 'clinic'} encounter for patient {ident}"]
    if ccc_number:
        parts.append(f"with CCC {ccc_number}")
    if forced_cash:
        parts.append("(cash and carry — insured visit already exists today)")
    return " ".join(parts) + "."


def summarize_bill_for_patient(patient: Patient, amount: float, *, context: str = "encounter") -> str:
    ident = patient_audit_identifier(patient)
    return f"Saved a bill of {amount:.2f} cedis for patient {ident} ({context})."


def summarize_receipt_for_patient(patient: Patient, amount: float) -> str:
    ident = patient_audit_identifier(patient)
    return f"Recorded payment of {amount:.2f} cedis for patient {ident} (receipt)."
