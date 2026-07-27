"""
NHIA CCC integration — NeHFAMS OTAC REST API (otac.nhia.gov.gh) or legacy CCC portal scraper.
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple
import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.patient import Patient
from app.services.nhia_exceptions import NhiaIntegrationError  # noqa: F401 — re-exported for API modules
from app.services.nhia_html_parser import NhiaClaimCodeData, parse_claim_code_html

logger = logging.getLogger(__name__)

_SESSION: Optional[httpx.Client] = None
_SESSION_EXPIRES_AT: float = 0.0


def _mask_hin(hin: Optional[str]) -> str:
    if not hin:
        return "****"
    hin = hin.strip()
    if len(hin) <= 4:
        return "****"
    return f"{'*' * (len(hin) - 4)}{hin[-4:]}"


def _base_url() -> str:
    return (settings.NHIA_CCC_BASE_URL or "https://otac.nhia.gov.gh").rstrip("/")


def _uses_otac_api() -> bool:
    """True when configured to use the NHIA NeHFAMS OTAC REST API."""
    url = _base_url().lower()
    return "otac.nhia.gov.gh" in url


def _session_ttl_seconds() -> int:
    return max(60, int(settings.NHIA_SESSION_TTL_SECONDS or 1800))


def _ssl_verify_setting():
    """
    httpx verify argument: use Mozilla CA bundle via certifi on Windows/macOS,
    optional custom bundle, or disable when NHIA_SSL_VERIFY=false.
    """
    if not settings.NHIA_SSL_VERIFY:
        logger.warning("NHIA SSL certificate verification is disabled (NHIA_SSL_VERIFY=false)")
        return False

    custom = (settings.NHIA_SSL_CA_BUNDLE or "").strip()
    if custom:
        return custom

    try:
        import certifi

        return certifi.where()
    except ImportError:
        return True


def _get_client() -> httpx.Client:
    global _SESSION, _SESSION_EXPIRES_AT
    now = time.time()
    if _SESSION is None or now >= _SESSION_EXPIRES_AT:
        if _SESSION is not None:
            try:
                _SESSION.close()
            except Exception:
                pass
        _SESSION = httpx.Client(
            base_url=_base_url(),
            timeout=httpx.Timeout(settings.NHIA_REQUEST_TIMEOUT_SECONDS or 30.0),
            follow_redirects=True,
            verify=_ssl_verify_setting(),
            headers={
                "User-Agent": "HMS-NHIA-Integration/1.0",
                "Accept": "application/json, text/html, */*",
            },
        )
        _SESSION_EXPIRES_AT = now + _session_ttl_seconds()
    return _SESSION


def _reset_session() -> None:
    global _SESSION, _SESSION_EXPIRES_AT
    if _SESSION is not None:
        try:
            _SESSION.close()
        except Exception:
            pass
    _SESSION = None
    _SESSION_EXPIRES_AT = 0.0


def _portal_json_post(client: httpx.Client, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """POST JSON to NHIA CCC portal and validate standard response envelope."""
    resp = client.post(
        path,
        json=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    if resp.status_code >= 500:
        raise NhiaIntegrationError(
            f"NHIA server error ({resp.status_code}).",
            retryable=True,
        )
    if resp.status_code >= 400:
        raise NhiaIntegrationError(
            f"NHIA rejected request ({resp.status_code}).",
            retryable=resp.status_code >= 500,
        )

    try:
        payload = resp.json()
    except ValueError as exc:
        raise NhiaIntegrationError(
            "NHIA returned an invalid response.",
            retryable=True,
        ) from exc

    if not payload.get("isSuccess", payload.get("IsSuccess")):
        message = (
            payload.get("error")
            or payload.get("message")
            or payload.get("Message")
            or "NHIA request failed"
        )
        raise NhiaIntegrationError(str(message).strip() or "NHIA request failed", retryable=False)

    return payload


def _is_portal_authenticated(client: httpx.Client) -> bool:
    try:
        resp = client.get("/Home/membershipcheck")
        return resp.status_code == 200 and "newclaimsCode1" in (resp.text or "")
    except httpx.HTTPError:
        return False


def _login(client: httpx.Client) -> None:
    """
    Authenticate with NHIA CCC portal.
    Portal expects JSON POST /Home/Index with userName + password (mobile + password).
    """
    username = (settings.NHIA_USERNAME or "").strip()
    password = settings.NHIA_PASSWORD or ""
    if not username or not password:
        raise NhiaIntegrationError(
            "NHIA portal credentials are not configured (NHIA_USERNAME / NHIA_PASSWORD).",
            retryable=False,
        )

    client.get("/")
    payload = _portal_json_post(
        client,
        "/Home/Index",
        {"userName": username, "password": password},
    )
    redirect = payload.get("redirect") or ""
    if redirect and "login" in redirect.lower():
        raise NhiaIntegrationError(
            "NHIA portal rejected the configured credentials.",
            retryable=False,
        )
    if not _is_portal_authenticated(client):
        raise NhiaIntegrationError(
            "Unable to authenticate with NHIA portal. Check NHIA_USERNAME (mobile) and NHIA_PASSWORD.",
            retryable=False,
        )
    logger.info("NHIA portal login succeeded")


def _ensure_session(*, force_refresh: bool = False) -> httpx.Client:
    if not settings.NHIA_INTEGRATION_ENABLED:
        raise NhiaIntegrationError("NHIA integration is disabled.", retryable=False)

    client = _get_client()
    if force_refresh:
        _reset_session()
        client = _get_client()

    if force_refresh or not _is_portal_authenticated(client):
        _login(client)
    return client


# Ghana Card on NHIA portal: GHA-123456789-0 (case-insensitive prefix)
_GHANA_CARD_PATTERN = re.compile(
    r"^GHA-\d+-\d{1,2}$",
    re.IGNORECASE,
)


def detect_card_type_from_member_id(member_id: str) -> str:
    """
    Choose NHIA portal card type from member / insurance identifier.
    GHA-xxxxxx-x → GHANACARD; otherwise NHISCARD (NHIS membership number).
    """
    normalized = (member_id or "").strip()
    if _GHANA_CARD_PATTERN.match(normalized):
        return "GHANACARD"
    return _default_card_type_fallback()


def _default_card_type_fallback() -> str:
    card_type = (settings.NHIA_DEFAULT_CARD_TYPE or "NHISCARD").strip().upper()
    if card_type not in ("NHISCARD", "GHANACARD"):
        return "NHISCARD"
    return card_type


def _fetch_claim_code_html(client: httpx.Client, hin: str) -> str:
    """
    Run the NHIA CCC portal wizard for a member number and return claim-code HTML.
    Flow: membershipcheck (option 1) -> cardType -> cardNumber -> ClaimCode page.
    """
    hin = hin.strip()
    card_type = detect_card_type_from_member_id(hin)
    logger.info("NHIA card type selected: %s", card_type)
    _portal_json_post(client, "/Home/membershipcheck", {"option": 1})
    _portal_json_post(client, "/Home/cardType", {"cardType": card_type})
    payload = _portal_json_post(client, "/Home/cardNumber", {"cardNumber": hin})

    redirect = (payload.get("redirect") or "/Home/ClaimCode").strip()
    path = redirect if redirect.startswith("/") else f"/{redirect}"
    resp = client.get(path)
    if resp.status_code >= 400:
        raise NhiaIntegrationError(
            f"Failed to load NHIA claim code page ({resp.status_code}).",
            retryable=True,
        )
    html = resp.text or ""
    if "claimCodeBlock" not in html:
        raise NhiaIntegrationError(
            "NHIA claim code page did not contain expected content.",
            retryable=True,
        )
    return html


def lookup_member_by_hin(
    hin: str,
    *,
    otac: Optional[str] = None,
    force_refresh: bool = False,
) -> NhiaClaimCodeData:
    """Fetch CCC / membership data from NHIA for a member number (HIN)."""
    hin = (hin or "").strip()
    if not hin:
        raise NhiaIntegrationError("Insurance / NHIS member number is required.", retryable=False)

    if _uses_otac_api():
        from app.services.nhia_otac_api import lookup_member_by_hin_otac

        started = time.perf_counter()
        masked = _mask_hin(hin)
        logger.info("NHIA OTAC API lookup started for HIN %s", masked)
        try:
            data = lookup_member_by_hin_otac(hin, otac=otac, force_refresh=force_refresh)
        except NhiaIntegrationError:
            logger.warning("NHIA OTAC API lookup failed for HIN %s", masked)
            raise
        except httpx.TimeoutException as exc:
            raise NhiaIntegrationError("NHIA API request timed out.", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise NhiaIntegrationError("Unable to reach NHIA API.", retryable=True) from exc
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "NHIA OTAC API lookup succeeded for HIN %s in %dms (status=%s)",
            masked,
            elapsed_ms,
            (data.status or "unknown").upper(),
        )
        return data

    started = time.perf_counter()
    masked = _mask_hin(hin)
    logger.info("NHIA lookup started for HIN %s", masked)

    try:
        client = _ensure_session(force_refresh=force_refresh)
        html = _fetch_claim_code_html(client, hin)
        data = parse_claim_code_html(html)
        if not data.ccc:
            detail = (data.status or "NHIA did not return a CCC for this member.").strip()
            lower = detail.lower()
            if any(
                token in lower
                for token in ("error", "bad request", "failed", "invalid", "not found")
            ):
                raise NhiaIntegrationError(
                    f"NHIA membership lookup failed: {detail}",
                    retryable=False,
                )
            raise NhiaIntegrationError(
                detail or "NHIA did not return a CCC for this member. Verify the NHIS number.",
                retryable=False,
            )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "NHIA lookup succeeded for HIN %s in %dms (status=%s)",
            masked,
            elapsed_ms,
            (data.status or "unknown").upper(),
        )
        return data
    except NhiaIntegrationError:
        logger.warning("NHIA lookup failed for HIN %s", masked)
        raise
    except httpx.TimeoutException as exc:
        logger.warning("NHIA lookup timeout for HIN %s", masked)
        raise NhiaIntegrationError("NHIA portal request timed out.", retryable=True) from exc
    except httpx.HTTPError as exc:
        logger.warning("NHIA lookup network error for HIN %s", masked)
        err_text = str(exc)
        if "CERTIFICATE_VERIFY_FAILED" in err_text or "certificate verify failed" in err_text.lower():
            raise NhiaIntegrationError(
                "SSL certificate verification failed connecting to NHIA. "
                "Restart the backend after `pip install certifi`, or set NHIA_SSL_VERIFY=false in .env "
                "(less secure; use only on trusted networks).",
                retryable=False,
            ) from exc
        raise NhiaIntegrationError("Unable to reach NHIA portal.", retryable=True) from exc
    except ValueError as exc:
        logger.warning("NHIA lookup parse error for HIN %s", masked)
        raise NhiaIntegrationError(
            "NHIA returned an unexpected claim code page. Try again or verify the member number.",
            retryable=True,
        ) from exc


def _parse_portal_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _split_nhia_name(full_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not full_name:
        return None, None
    parts = full_name.strip().split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _normalize_gender(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    v = value.strip().upper()
    if v.startswith("M"):
        return "M"
    if v.startswith("F"):
        return "F"
    return None


def apply_nhia_data_to_patient(
    patient: Patient, data: NhiaClaimCodeData, *, ccc_only: bool = False
) -> None:
    """Map parsed NHIA fields onto HMS patient record.

    When ccc_only is True (Get CCC during encounter), only update CCC-related fields
    so registration-time name/DOB (e.g. baby of parent) are not overwritten.
    """
    status = (data.status or "").strip().upper()
    if data.ccc:
        patient.ccc_number = data.ccc.strip()
    if status:
        patient.ccc_status = status
        patient.nhis_active = status == "ACTIVE"

    if ccc_only:
        return

    if data.hin:
        patient.hin = data.hin.strip()
        if not ccc_only:
            patient.insured = True

    if data.name:
        first, rest = _split_nhia_name(data.name)
        if first:
            patient.name = first
        if rest:
            patient.surname = rest

    dob = _parse_portal_date(data.dob)
    if dob:
        patient.date_of_birth = dob

    gender = _normalize_gender(data.gender)
    if gender:
        patient.gender = gender

    start = _parse_portal_date(data.start)
    end = _parse_portal_date(data.end)
    if start:
        patient.insurance_start_date = start
    if end:
        patient.insurance_end_date = end


def generate_patient_ccc(
    db: Session,
    patient_id: int,
    *,
    otac: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load patient, verify eligibility, fetch CCC from NHIA, persist, return payload.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise NhiaIntegrationError("Patient not found.", retryable=False)

    if not patient.insurance_id:
        raise NhiaIntegrationError(
            "Patient has no NHIS / insurance number. Treat as cash patient.",
            retryable=False,
        )

    if patient.insured and not patient.nhis_active:
        raise NhiaIntegrationError(
            "NHIS card is marked inactive for this patient. Cash and carry applies.",
            retryable=False,
        )

    hin = patient.insurance_id.strip()
    started = time.perf_counter()

    try:
        data = lookup_member_by_hin(hin, otac=otac)
    except NhiaIntegrationError as exc:
        if exc.retryable:
            try:
                data = lookup_member_by_hin(hin, otac=otac, force_refresh=True)
            except NhiaIntegrationError:
                raise
        else:
            raise

    apply_nhia_data_to_patient(patient, data, ccc_only=True)
    db.commit()
    db.refresh(patient)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "NHIA CCC generation completed for patient_id=%s in %dms success=%s",
        patient_id,
        elapsed_ms,
        True,
    )

    return {
        "success": True,
        "message": "CCC generated successfully",
        "data": {
            "ccc": data.ccc,
            "status": data.status,
            "name": data.name,
            "hin": data.hin,
            "dob": data.dob,
            "gender": data.gender,
            "start": data.start,
            "end": data.end,
        },
        "patient": patient,
    }
