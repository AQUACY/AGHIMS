"""
Fetch NHIA CCC for GHIMS imported claim editing (preview only).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.datetime_utils import utcnow
from app.services.nhia_integration import NhiaIntegrationError, lookup_member_by_hin


def _today_iso() -> str:
    return utcnow().date().isoformat()


def _preview_ghims_payload_dates(payload: Dict[str, Any], claim_check_code: str, day: str) -> Dict[str, Any]:
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


def fetch_ccc_preview_for_ghims_payload(
    payload: Dict[str, Any],
    *,
    member_no: Optional[str] = None,
    otac: Optional[str] = None,
) -> Dict[str, Any]:
    hin = (member_no or (payload or {}).get("memberNo") or "").strip()
    if not hin:
        raise NhiaIntegrationError(
            "Member number is required to fetch CCC.",
            retryable=False,
        )

    data = lookup_member_by_hin(hin, otac=otac)
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
