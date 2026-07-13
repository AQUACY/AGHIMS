"""
GHIMS patient card number helpers.
Format example: E-0032-26050735
"""
from __future__ import annotations

import re
from typing import Optional

from app.core.config import settings

# Letter-facility segment-8-digit serial (e.g. E-0032-26050735)
GHIMS_CARD_PATTERN = re.compile(r"^[A-Za-z]-\d{4}-\d{8}$")

GHANA_CARD_PATTERN = re.compile(r"^GHA-\d+-\d$", re.IGNORECASE)


def ghims_card_numbers_enabled() -> bool:
    return bool(getattr(settings, "GHIMS_CARD_NUMBERS_ENABLED", False))


def is_valid_ghims_card_number(value: Optional[str]) -> bool:
    if not value:
        return False
    return bool(GHIMS_CARD_PATTERN.match(value.strip()))


def normalize_ghims_card_number(value: str) -> str:
    """Normalize GHIMS card to uppercase letter prefix."""
    value = value.strip()
    if not is_valid_ghims_card_number(value):
        raise ValueError(
            "Invalid GHIMS card number. Expected format like E-0032-26050735."
        )
    parts = value.split("-")
    return f"{parts[0].upper()}-{parts[1]}-{parts[2]}"


def normalize_insurance_id(value: Optional[str]) -> Optional[str]:
    """Normalize NHIS / Ghana Card identifiers for duplicate checks."""
    if not value:
        return None
    cleaned = re.sub(r"\s+", "", value.strip())
    if GHANA_CARD_PATTERN.match(cleaned):
        return cleaned.upper()
    return cleaned
