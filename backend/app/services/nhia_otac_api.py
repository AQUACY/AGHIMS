"""
NHIA NeHFAMS OTAC REST API client (https://otac.nhia.gov.gh).

Endpoints:
  POST /api/login              — facility authentication
  POST /api/attendance/generate — generate CCC / attendance for a member
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.services.nhia_exceptions import NhiaIntegrationError
from app.services.nhia_html_parser import NhiaClaimCodeData, parse_otac_api_response

logger = logging.getLogger(__name__)

_SESSION: Optional[httpx.Client] = None
_SESSION_EXPIRES_AT: float = 0.0
_ACCESS_TOKEN: Optional[str] = None


def _base_url() -> str:
    return (settings.NHIA_CCC_BASE_URL or "https://otac.nhia.gov.gh").rstrip("/")


def _session_ttl_seconds() -> int:
    return max(60, int(settings.NHIA_SESSION_TTL_SECONDS or 1800))


def _ssl_verify_setting():
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


def _reset_session() -> None:
    global _SESSION, _SESSION_EXPIRES_AT, _ACCESS_TOKEN
    if _SESSION is not None:
        try:
            _SESSION.close()
        except Exception:
            pass
    _SESSION = None
    _SESSION_EXPIRES_AT = 0.0
    _ACCESS_TOKEN = None


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
                "User-Agent": "HMS-NHIA-OTAC-Integration/2.0",
                "Accept": "application/json",
            },
        )
        _SESSION_EXPIRES_AT = now + _session_ttl_seconds()
    return _SESSION


def _pick(data: Dict[str, Any], *keys: str) -> Any:
    if not isinstance(data, dict):
        return None
    lower_map = {str(k).lower(): v for k, v in data.items()}
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
        val = lower_map.get(key.lower())
        if val not in (None, ""):
            return val
    return None


def _format_validation_errors(payload: Dict[str, Any]) -> Optional[str]:
    errors = payload.get("errors")
    if not isinstance(errors, dict):
        return None
    parts = []
    for field, messages in errors.items():
        if isinstance(messages, list):
            for msg in messages:
                parts.append(f"{field}: {msg}")
        elif messages:
            parts.append(f"{field}: {messages}")
    return "; ".join(parts) if parts else None


def _response_error_message(payload: Any, *, fallback: str) -> str:
    if not isinstance(payload, dict):
        return fallback
    for key in ("statusMessage", "StatusMessage", "message", "Message", "error", "Error", "title"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    validation = _format_validation_errors(payload)
    if validation:
        return validation
    return fallback


def _is_success_payload(payload: Dict[str, Any]) -> bool:
    status_code = _pick(payload, "statusCode", "StatusCode")
    if status_code is not None:
        try:
            return int(status_code) == 0
        except (TypeError, ValueError):
            pass
    status_msg = (_pick(payload, "statusMessage", "StatusMessage", "message", "Message") or "").strip().lower()
    if "success" in status_msg:
        return True
    if status_msg and any(token in status_msg for token in ("fail", "error", "invalid", "denied", "unauthorized")):
        return False
    return True


def _extract_access_token(payload: Dict[str, Any]) -> Optional[str]:
    access_token_obj = payload.get("accessToken") or payload.get("AccessToken")
    if isinstance(access_token_obj, dict):
        token = _pick(access_token_obj, "token", "Token")
        if token:
            return str(token).strip()
    token = _pick(payload, "accessToken", "AccessToken", "token", "Token")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def _build_request_headers(*, authenticated: bool = True) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }
    if authenticated:
        if not _ACCESS_TOKEN:
            raise NhiaIntegrationError("NHIA session is not authenticated.", retryable=True)
        headers["Authorization"] = f"Bearer {_ACCESS_TOKEN}"
    return headers


def _api_request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    authenticated: bool = True,
) -> Dict[str, Any]:
    headers = _build_request_headers(authenticated=authenticated)

    try:
        resp = client.request(method, path, json=json_body, headers=headers)
    except httpx.TimeoutException as exc:
        raise NhiaIntegrationError("NHIA API request timed out.", retryable=True) from exc
    except httpx.HTTPError as exc:
        err_text = str(exc)
        if "CERTIFICATE_VERIFY_FAILED" in err_text or "certificate verify failed" in err_text.lower():
            raise NhiaIntegrationError(
                "SSL certificate verification failed connecting to NHIA. "
                "Set NHIA_SSL_VERIFY=false in .env on trusted networks, or install certifi.",
                retryable=False,
            ) from exc
        raise NhiaIntegrationError("Unable to reach NHIA API.", retryable=True) from exc

    if resp.status_code == 401 and authenticated:
        raise NhiaIntegrationError("NHIA session expired.", retryable=True)

    if resp.status_code >= 500:
        raise NhiaIntegrationError(
            f"NHIA server error ({resp.status_code}).",
            retryable=True,
        )

    try:
        payload = resp.json() if resp.content else {}
    except ValueError as exc:
        raise NhiaIntegrationError(
            "NHIA returned an invalid JSON response.",
            retryable=True,
        ) from exc

    if resp.status_code >= 400:
        message = _response_error_message(payload, fallback=f"NHIA rejected request ({resp.status_code}).")
        retryable = resp.status_code >= 500
        if "otac" in message.lower():
            retryable = False
        raise NhiaIntegrationError(message, retryable=retryable)

    if isinstance(payload, dict) and not _is_success_payload(payload):
        message = _response_error_message(payload, fallback="NHIA request failed.")
        raise NhiaIntegrationError(message, retryable=False)

    if not isinstance(payload, dict):
        return {}
    return payload


def _login(client: httpx.Client) -> None:
    global _ACCESS_TOKEN
    username = (settings.NHIA_USERNAME or "").strip()
    password = settings.NHIA_PASSWORD or ""
    if not username or not password:
        raise NhiaIntegrationError(
            "NHIA portal credentials are not configured (NHIA_USERNAME / NHIA_PASSWORD).",
            retryable=False,
        )

    login_body = {
        "userName": username,
        "password": password,
        "appVersion": None,
    }

    resp = client.post(
        "/api/login",
        json=login_body,
        headers=_build_request_headers(authenticated=False),
    )

    try:
        payload = resp.json() if resp.content else {}
    except ValueError as exc:
        raise NhiaIntegrationError(
            "NHIA login returned an invalid response.",
            retryable=True,
        ) from exc

    if resp.status_code >= 400:
        message = _response_error_message(payload, fallback="NHIA login failed.")
        raise NhiaIntegrationError(message, retryable=False)

    if not isinstance(payload, dict):
        raise NhiaIntegrationError("NHIA login returned an unexpected response.", retryable=True)

    token = _extract_access_token(payload)
    if not token:
        message = _response_error_message(payload, fallback="NHIA login did not return an access token.")
        raise NhiaIntegrationError(message, retryable=False)

    _ACCESS_TOKEN = token
    user_info = payload.get("userInfo") if isinstance(payload.get("userInfo"), dict) else {}
    user_name = _pick(user_info, "userName", "UserName")
    logger.info("NHIA OTAC API login succeeded for %s", user_name or username)


def _ensure_session(*, force_refresh: bool = False) -> httpx.Client:
    if not settings.NHIA_INTEGRATION_ENABLED:
        raise NhiaIntegrationError("NHIA integration is disabled.", retryable=False)

    if force_refresh:
        _reset_session()

    client = _get_client()
    if force_refresh or not _ACCESS_TOKEN:
        _login(client)
    return client


def _resolved_otac(otac: Optional[str]) -> Optional[str]:
    value = (otac or settings.NHIA_DEFAULT_OTAC or "").strip()
    return value or None


def _format_card_no(card_no: str, card_type: str) -> str:
    card_no = (card_no or "").strip()
    if card_type.upper() == "GHANACARD":
        return card_no.lower()
    return card_no


def _attendance_generate(
    client: httpx.Client,
    *,
    card_no: str,
    card_type: str,
    otac: Optional[str] = None,
) -> Dict[str, Any]:
    card_type = card_type.strip().upper()
    body: Dict[str, Any] = {
        "otac": _resolved_otac(otac),
        "bioMatchResult": None,
        "bmasTransactionID": None,
        "cardType": card_type,
        "cardNo": _format_card_no(card_no, card_type),
    }

    return _api_request(client, "POST", "/api/attendance/generate", json_body=body)


def _otac_required_message(payload: Dict[str, Any]) -> Optional[str]:
    status_msg = (_pick(payload, "statusMessage", "StatusMessage") or "").lower()
    if "otac" in status_msg and any(token in status_msg for token in ("required", "invalid", "enter", "provide")):
        return _pick(payload, "statusMessage", "StatusMessage")
    return None


def lookup_member_by_hin_otac(
    hin: str,
    *,
    otac: Optional[str] = None,
    force_refresh: bool = False,
) -> NhiaClaimCodeData:
    """Fetch CCC / membership data from NHIA NeHFAMS OTAC API."""
    from app.services.nhia_integration import detect_card_type_from_member_id

    hin = (hin or "").strip()
    if not hin:
        raise NhiaIntegrationError("Insurance / NHIS member number is required.", retryable=False)

    card_type = detect_card_type_from_member_id(hin)
    client = _ensure_session(force_refresh=force_refresh)

    try:
        payload = _attendance_generate(client, card_no=hin, card_type=card_type, otac=otac)
    except NhiaIntegrationError as exc:
        if exc.retryable and "session expired" in str(exc).lower():
            client = _ensure_session(force_refresh=True)
            payload = _attendance_generate(client, card_no=hin, card_type=card_type, otac=otac)
        elif "otac" in str(exc).lower() and not _resolved_otac(otac):
            raise NhiaIntegrationError(
                "NHIA requires a patient OTAC (4-digit One-Time Attendance Code). "
                "Ask the patient for their OTAC from *929# or the NHIA portal, then retry.",
                retryable=False,
            ) from exc
        else:
            raise

    data = parse_otac_api_response(payload)

    if not data.ccc:
        otac_msg = _otac_required_message(payload)
        if otac_msg and not _resolved_otac(otac):
            raise NhiaIntegrationError(otac_msg, retryable=False)

        detail = (_pick(payload, "statusMessage", "StatusMessage") or "").strip()
        if detail:
            raise NhiaIntegrationError(detail, retryable=False)
        raise NhiaIntegrationError(
            "NHIA did not return a CCC for this member. Verify the NHIS number and OTAC if required.",
            retryable=False,
        )

    return data
