"""
Parse NHIA CCC portal HTML responses into structured data.
Isolated so scraper can be swapped for an official API later.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup


@dataclass
class NhiaClaimCodeData:
    status: Optional[str] = None
    ccc: Optional[str] = None
    name: Optional[str] = None
    hin: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "status": self.status,
            "ccc": self.ccc,
            "name": self.name,
            "hin": self.hin,
            "dob": self.dob,
            "gender": self.gender,
            "start": self.start,
            "end": self.end,
        }


_LABEL_ALIASES = {
    "status": ("status",),
    "ccc": ("ccc", "claim code", "claimcode"),
    "name": ("name",),
    "hin": ("hin", "hin #", "member no", "member number", "insurance", "nhis"),
    "dob": ("dob", "date of birth", "birth"),
    "gender": ("gender", "sex"),
    "start": ("start", "valid from", "cover start"),
    "end": ("end", "valid to", "cover end", "expiry"),
}

_PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "01-01-0001",
        "0001-01-01",
        "n/a",
        "na",
        "-",
    }
)


def _normalize_label(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip().lower())
    text = re.sub(r"[:#]+$", "", text).strip()
    return text


def _match_field(label: str) -> Optional[str]:
    norm = _normalize_label(label)
    for field, aliases in _LABEL_ALIASES.items():
        for alias in aliases:
            if norm == alias or norm.startswith(f"{alias} "):
                return field
    return None


def _clean_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    if cleaned.lower() in _PLACEHOLDER_VALUES:
        return None
    return cleaned or None


def _extract_label_value_pairs(block: BeautifulSoup) -> List[Tuple[str, str]]:
    """NHIA renders one claimCodeBlock div per field."""
    pairs: List[Tuple[str, str]] = []

    for div in block.select("div.claimCodeBlock"):
        strong = div.find("strong")
        if not strong:
            continue
        label = strong.get_text(" ", strip=True)
        # Value is text in the div after the <strong> label
        value_parts: List[str] = []
        for sibling in strong.next_siblings:
            if hasattr(sibling, "get_text"):
                part = sibling.get_text(" ", strip=True)
            else:
                part = str(sibling).strip()
            if part:
                value_parts.append(part)
        value = _clean_value(" ".join(value_parts))
        if label:
            pairs.append((label, value or ""))

    return pairs


def _apply_pairs(data: NhiaClaimCodeData, pairs: List[Tuple[str, str]]) -> None:
    for label, value in pairs:
        field = _match_field(label)
        if not field:
            continue
        cleaned = _clean_value(value)
        if cleaned:
            setattr(data, field, cleaned)


def _extract_alert_message(html: str) -> Optional[str]:
    match = re.search(
        r"utility\.alert\(\s*['\"]([^'\"]+)['\"]",
        html or "",
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return None


def parse_claim_code_html(html: str) -> NhiaClaimCodeData:
    """Extract claim code fields from NHIA portal HTML."""
    soup = BeautifulSoup(html or "", "html.parser")
    blocks = soup.select("div.claimCodeBlock")
    if not blocks:
        raise ValueError("NHIA response did not contain claim code details")

    data = NhiaClaimCodeData()
    _apply_pairs(data, _extract_label_value_pairs(soup))

    # Portal may surface fatal errors only in utility.alert(...)
    if not data.status:
        alert_msg = _extract_alert_message(html)
        if alert_msg:
            data.status = alert_msg

    if not any((data.ccc, data.hin, data.status, data.name)):
        raise ValueError("Could not parse NHIA claim code response")

    return data
