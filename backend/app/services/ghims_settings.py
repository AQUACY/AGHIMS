"""GHIMS integration settings (manual card numbers from government GHIMS)."""
from __future__ import annotations

import re

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.module_settings import ModuleSettings

GHIMS_MODULE_KEY = "ghims"
# Example: E-0032-26050735
GHIMS_CARD_PATTERN = re.compile(r"^[A-Za-z]-\d{4}-\d+$")


def is_ghims_card_mode(db: Session) -> bool:
    """When True, new patients must be registered with a GHIMS card number."""
    module = (
        db.query(ModuleSettings)
        .filter(ModuleSettings.module_key == GHIMS_MODULE_KEY)
        .first()
    )
    return bool(module and module.is_active)


def is_ghims_card_format(card_number: Optional[str]) -> bool:
    """True if the card number matches GHIMS pattern (e.g. E-0032-26050735)."""
    return bool(GHIMS_CARD_PATTERN.match((card_number or "").strip()))


def apply_patient_card_number_update(
    patient,
    new_card_number: Optional[str],
    db: Session,
    *,
    ghims_mode: bool,
) -> None:
    """
    Update patient card number. When GHIMS mode is on, validates GHIMS format.
    Preserves the previous card in legacy_card_number (first migration only).
    """
    if new_card_number is None:
        return
    new_raw = new_card_number.strip()
    if not new_raw:
        return

    current = (patient.card_number or "").strip()
    if new_raw.upper() == current.upper():
        return

    if ghims_mode:
        new_value = validate_ghims_card_number(new_raw)
    else:
        new_value = new_raw

    from app.models.patient import Patient

    conflict = (
        db.query(Patient)
        .filter(Patient.id != patient.id)
        .filter(func.upper(Patient.card_number) == new_value.upper())
        .first()
    )
    if conflict:
        raise ValueError(f"Card number '{new_value}' is already assigned to another patient.")

    if current and current.upper() != new_value.upper():
        if not patient.legacy_card_number:
            patient.legacy_card_number = current

    patient.card_number = new_value


def validate_ghims_card_number(card_number: str) -> str:
    """Return normalized GHIMS card number or raise ValueError."""
    normalized = (card_number or "").strip()
    if not normalized:
        raise ValueError("GHIMS card number is required when GHIMS mode is enabled.")
    if not GHIMS_CARD_PATTERN.match(normalized):
        raise ValueError(
            "Invalid GHIMS card number format. Expected pattern like E-0032-26050735."
        )
    return normalized.upper() if normalized[0].isalpha() else normalized
