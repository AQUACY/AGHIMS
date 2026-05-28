"""
Fetch NHIA CCC for claim editing (preview only — persisted on save/finalize).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Optional

from app.core.datetime_utils import utcnow
from app.models.claim import Claim
from app.services.nhia_integration import NhiaIntegrationError, lookup_member_by_hin


def _today_iso() -> str:
    return utcnow().date().isoformat()


def _preview_ghims_payload_dates(payload: Dict[str, Any], claim_check_code: str, day: str) -> Dict[str, Any]:
    """Build GHIMS payload preview with new claim check code and today's service dates."""
    p = dict(payload or {})
    p["claimCheckCode"] = claim_check_code

    dates = p.get("dateOfService")
    if isinstance(dates, list) and dates:
        p["dateOfService"] = [day for _ in dates]
    else:
        p["dateOfService"] = [day]

    for key in ("investigations", "medicines", "procedures"):
        rows = p.get(key)
        if not isinstance(rows, list):
            continue
        updated = []
        for row in rows:
            if not isinstance(row, dict):
                updated.append(row)
                continue
            r = dict(row)
            if r.get("serviceDate") or r.get("gdrgCode") or r.get("medicineCode") or r.get("description"):
                r["serviceDate"] = day
            updated.append(r)
        p[key] = updated
    return p


def fetch_ccc_preview_for_claim(
    claim: Claim,
    *,
    member_no: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch CCC from NHIA for a HMS claim. Does not write to the database;
    the frontend applies the preview and save/finalize persists changes.
    """
    hin = (member_no or claim.member_no or "").strip()
    if not hin:
        raise NhiaIntegrationError(
            "Member number (NHIS / insurance ID) is required to fetch CCC.",
            retryable=False,
        )

    data = lookup_member_by_hin(hin)
    ccc = (data.ccc or "").strip()
    if not ccc:
        raise NhiaIntegrationError("NHIA did not return a CCC.", retryable=False)

    day = _today_iso()
    return {
        "ccc": ccc,
        "claim_check_code": ccc,
        "status": data.status,
        "member_no": hin,
        "service_date": day,
        "first_visit": day,
        "second_visit": day,
        "third_visit": day,
        "fourth_visit": day,
    }


def fetch_ccc_preview_for_ghims_payload(
    payload: Dict[str, Any],
    *,
    member_no: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch CCC from NHIA and return a GHIMS payload preview (no database writes)."""
    hin = (member_no or (payload or {}).get("memberNo") or "").strip()
    if not hin:
        raise NhiaIntegrationError(
            "Member number is required to fetch CCC.",
            retryable=False,
        )

    data = lookup_member_by_hin(hin)
    ccc = (data.ccc or "").strip()
    if not ccc:
        raise NhiaIntegrationError("NHIA did not return a CCC.", retryable=False)

    day = _today_iso()
    updated = _preview_ghims_payload_dates(payload or {}, ccc, day)

    return {
        "ccc": ccc,
        "claim_check_code": ccc,
        "status": data.status,
        "member_no": hin,
        "service_date": day,
        "payload": updated,
    }
