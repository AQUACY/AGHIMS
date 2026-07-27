"""
Patient registration validation: GHIMS cards, insurance duplicates, profile matches, baby rules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.datetime_utils import today
from app.models.patient import Patient
from app.services.ghims_settings import validate_ghims_card_number

_GHANA_CARD_PATTERN = re.compile(r"^GHA-\d+-\d{1,2}$", re.IGNORECASE)
_BABY_MAX_AGE_DAYS = 92  # ~3 months


@dataclass
class PatientSummary:
    id: int
    name: str
    surname: Optional[str]
    card_number: str
    date_of_birth: Optional[date]
    insurance_id: Optional[str]
    gender: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "surname": self.surname,
            "card_number": self.card_number,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "insurance_id": self.insurance_id,
            "gender": self.gender,
        }


def _normalize_insurance_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.strip()
    if _GHANA_CARD_PATTERN.match(cleaned):
        return cleaned.upper()
    return cleaned


def _patient_summary(patient: Patient) -> PatientSummary:
    return PatientSummary(
        id=patient.id,
        name=patient.name,
        surname=patient.surname,
        card_number=patient.card_number,
        date_of_birth=patient.date_of_birth,
        insurance_id=patient.insurance_id,
        gender=patient.gender,
    )


def _is_newborn_within_baby_window(dob: Optional[date]) -> bool:
    if not dob:
        return False
    return (today() - dob).days <= _BABY_MAX_AGE_DAYS


def _baby_name_from_parent(parent: Patient) -> str:
    first = (parent.name or "").strip()
    return f"Baby of {first}" if first else "Baby of"


def _names_match(a_name: str, a_surname: Optional[str], b_name: str, b_surname: Optional[str]) -> bool:
    an = (a_name or "").strip().lower()
    bn = (b_name or "").strip().lower()
    if an != bn:
        return False
    asur = (a_surname or "").strip().lower()
    bsur = (b_surname or "").strip().lower()
    if asur and bsur:
        return asur == bsur
    return True


def find_patients_by_insurance(db: Session, insurance_id: str) -> List[Patient]:
    normalized = _normalize_insurance_id(insurance_id)
    if not normalized:
        return []
    return [
        p
        for p in db.query(Patient)
        .filter(Patient.insurance_id.isnot(None))
        .filter(Patient.insurance_id != "")
        .all()
        if _normalize_insurance_id(p.insurance_id) == normalized
    ]


def find_similar_patients(
    db: Session,
    *,
    name: str,
    surname: Optional[str],
    date_of_birth: Optional[date],
    gender: Optional[str] = None,
) -> List[Patient]:
    if not date_of_birth:
        return []
    candidates = db.query(Patient).filter(Patient.date_of_birth == date_of_birth).all()
    matches: List[Patient] = []
    for patient in candidates:
        if not _names_match(name, surname, patient.name, patient.surname):
            continue
        if gender and patient.gender and patient.gender.upper() != gender.upper():
            continue
        matches.append(patient)
    return matches


def validate_new_patient_registration(
    db: Session,
    *,
    name: str,
    surname: Optional[str],
    gender: str,
    date_of_birth: Optional[date],
    insurance_id: Optional[str],
    card_number: Optional[str],
    ghims_mode: bool,
    force_register: bool = False,
) -> Dict[str, Any]:
    """
    Validate registration before create.
    Returns dict with status and optional existing patient / suggested baby names.
    """
    if ghims_mode:
        try:
            validate_ghims_card_number(card_number or "")
        except ValueError as exc:
            return {"status": "invalid_card", "message": str(exc)}

        existing_card = (
            db.query(Patient)
            .filter(Patient.card_number == (card_number or "").strip())
            .first()
        )
        if existing_card:
            return {
                "status": "card_duplicate",
                "message": "This GHIMS card number is already registered.",
                "existing_patient": _patient_summary(existing_card).to_dict(),
            }
    elif card_number and card_number.strip():
        existing_card = (
            db.query(Patient)
            .filter(Patient.card_number == card_number.strip())
            .first()
        )
        if existing_card:
            return {
                "status": "card_duplicate",
                "message": "This card number is already registered.",
                "existing_patient": _patient_summary(existing_card).to_dict(),
            }

    normalized_insurance = _normalize_insurance_id(insurance_id)
    if normalized_insurance:
        holders = find_patients_by_insurance(db, normalized_insurance)
        if holders:
            if _is_newborn_within_baby_window(date_of_birth):
                parent = holders[0]
                return {
                    "status": "insurance_baby_allowed",
                    "message": (
                        "This insurance is registered to an existing patient. "
                        "The new client appears to be a newborn — registration as a baby of the parent is allowed."
                    ),
                    "existing_patient": _patient_summary(parent).to_dict(),
                    "suggested_name": _baby_name_from_parent(parent),
                    "suggested_surname": parent.surname,
                }
            primary = holders[0]
            return {
                "status": "insurance_rejected",
                "message": (
                    "This insurance / Ghana card is already registered to another patient and cannot be used again "
                    "(newborn registration is only allowed within 3 months of birth). "
                    "Create a service for the existing client instead."
                ),
                "existing_patient": _patient_summary(primary).to_dict(),
            }

    similar = find_similar_patients(
        db,
        name=name,
        surname=surname,
        date_of_birth=date_of_birth,
        gender=gender,
    )
    if similar and not force_register:
        return {
            "status": "profile_duplicate",
            "message": (
                "A patient with the same name and date of birth already exists. "
                "Create a service for the existing patient, or confirm to register as a new person."
            ),
            "similar_patients": [_patient_summary(p).to_dict() for p in similar],
            "existing_patient": _patient_summary(similar[0]).to_dict(),
        }

    return {"status": "ok", "message": "Registration validation passed."}
