"""
Installation license evaluation: signed file + optional online verification with grace.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.app_license_activation_log import AppLicenseActivationLog
from app.models.app_license_state import AppLicenseState
from app.models.facility_settings import FacilitySettings
from app.services.license_crypto import parse_iso_datetime, verify_document


def _resolved_public_pem() -> str:
    path = (getattr(settings, "LICENSE_RSA_PUBLIC_KEY_FILE", "") or "").strip()
    if path:
        from pathlib import Path

        return Path(path).read_text(encoding="utf-8").strip()
    return (getattr(settings, "LICENSE_RSA_PUBLIC_KEY_PEM", "") or "").strip()


def _normalize_naive(dt):
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None):
        return dt.replace(tzinfo=None)
    return dt


def _ensure_bootstrap_anchor(db: Session, row: AppLicenseState, now) -> None:
    """Legacy DBs: anchor signed-file-only window from first evaluation after upgrade."""
    if row.license_activated_at is not None:
        return
    if not row.signed_document_json:
        return
    row.license_activated_at = now
    db.commit()
    db.refresh(row)


def _clock_rollback_error(now, row: AppLicenseState) -> Optional[str]:
    tol_seconds = max(0, int(getattr(settings, "LICENSE_CLOCK_ROLLBACK_TOLERANCE_SECONDS", 300) or 300))
    last_seen = _normalize_naive(row.last_evaluated_at)
    if last_seen is None:
        return None
    if now + timedelta(seconds=tol_seconds) < last_seen:
        return (
            "System clock appears to have moved backward beyond allowed tolerance. "
            "Correct device date/time and retry."
        )
    return None


def _checkpoint_evaluation_clock(db: Session, row: AppLicenseState, now) -> None:
    last_seen = _normalize_naive(row.last_evaluated_at)
    if last_seen is None or now > last_seen:
        row.last_evaluated_at = now
        db.commit()
        db.refresh(row)


def _singleton(db: Session) -> AppLicenseState:
    row = db.query(AppLicenseState).filter(AppLicenseState.id == 1).first()
    if not row:
        row = AppLicenseState(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_installation_license_row(db: Session) -> AppLicenseState:
    """Single installation license row (for API layers that must not import private helpers)."""
    return _singleton(db)


def enforcement_enabled() -> bool:
    return bool(getattr(settings, "LICENSE_ENFORCEMENT", False))


def analyze_untrusted_document(db: Session, document: Any) -> Dict[str, Any]:
    """
    Read-only checks for pasted JSON (Admin/Management security testing). Does not store anything.
    """
    checks: list[Dict[str, Any]] = []

    def add(passed: bool, label: str, detail: str) -> None:
        checks.append({"pass": passed, "label": label, "detail": detail})

    if not isinstance(document, dict):
        add(False, "JSON shape", "Root value must be a JSON object.")
        return {"ok": False, "checks": checks, "claims_preview": None}

    claims = document.get("claims")
    sig_b64 = document.get("signature_b64")
    add(isinstance(claims, dict), "Claims field", "claims must be an object" if not isinstance(claims, dict) else "claims object present")
    add(bool(isinstance(sig_b64, str) and sig_b64.strip()), "Signature field", "signature_b64 must be a non-empty string")

    if not isinstance(claims, dict):
        return {"ok": False, "checks": checks, "claims_preview": None}

    try:
        pem = _resolved_public_pem()
    except Exception as e:
        add(False, "Public key load", str(e))
        return {"ok": False, "checks": checks, "claims_preview": None}

    if not pem:
        add(False, "Public key", "Set LICENSE_RSA_PUBLIC_KEY_FILE or LICENSE_RSA_PUBLIC_KEY_PEM on the server.")
        return {"ok": False, "checks": checks, "claims_preview": None}

    ok, err, parsed = verify_document(document, pem)
    add(ok, "RSA signature", err or "Signature verifies against installed public key.")
    if not ok or not parsed:
        return {"ok": False, "checks": checks, "claims_preview": None}

    expected_issuer = (getattr(settings, "LICENSE_ISSUER_SLUG", "") or "").strip()
    if expected_issuer:
        match = (parsed.get("issuer_slug") or "").strip() == expected_issuer
        add(
            match,
            "issuer_slug",
            f"Expected {expected_issuer!r}; file has {(parsed.get('issuer_slug') or '')!r}.",
        )
    else:
        add(True, "issuer_slug", "LICENSE_ISSUER_SLUG not set on server (not checked).")

    dist = (getattr(settings, "LICENSE_DISTRIBUTION_ID", "") or "").strip()
    if dist:
        match = (parsed.get("distribution_id") or "").strip() == dist
        add(
            match,
            "distribution_id",
            f"Expected {dist!r}; file has {(parsed.get('distribution_id') or '')!r}.",
        )
    else:
        add(True, "distribution_id", "LICENSE_DISTRIBUTION_ID not set (not checked).")

    fc_claim = parsed.get("facility_code")
    fc_s = str(fc_claim).strip() if fc_claim is not None and str(fc_claim).strip() else None
    installed = _facility_code(db)
    if fc_s:
        match = bool(installed and installed == fc_s)
        add(
            match,
            "facility_code",
            f"License bound to {fc_s!r}; this installation uses {installed!r}.",
        )
    else:
        add(True, "facility_code", "License does not bind a facility code.")

    now = utcnow()
    if now.tzinfo:
        now = now.replace(tzinfo=None)
    vf = parse_iso_datetime(parsed.get("valid_from"))
    vu = parse_iso_datetime(parsed.get("valid_until"))
    if vf:
        add(now >= vf, "valid_from", f"Not-before: {vf.isoformat()} (app time {now.isoformat()}).")
    else:
        add(True, "valid_from", "No valid_from in file.")

    if vu:
        add(now <= vu, "valid_until", f"Expiry: {vu.isoformat()} (app time {now.isoformat()}).")
    else:
        add(False, "valid_until", "Missing or unparsable valid_until.")

    lid = (parsed.get("license_id") or "").strip()
    add(bool(lid), "license_id", "license_id is present" if lid else "license_id is required.")

    preview = {
        "license_id": lid or None,
        "customer_label": (parsed.get("customer_label") or "")[:200] or None,
        "valid_until": vu.isoformat() if vu else None,
        "facility_code_in_license": fc_s,
        "facility_code_installed": installed,
    }
    all_pass = all(c["pass"] for c in checks)
    return {"ok": all_pass, "checks": checks, "claims_preview": preview}


def _facility_code(db: Session) -> Optional[str]:
    fs = db.query(FacilitySettings).order_by(FacilitySettings.id).first()
    if not fs or not (fs.facility_code or "").strip():
        return None
    return (fs.facility_code or "").strip()


def _claims_from_stored(row: AppLicenseState) -> Optional[Dict[str, Any]]:
    if not row.signed_document_json:
        return None
    try:
        doc = json.loads(row.signed_document_json)
        claims = doc.get("claims")
        return claims if isinstance(claims, dict) else None
    except Exception:
        return None


def _verify_stored_document(db: Session, row: AppLicenseState) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    if not row.signed_document_json:
        return False, "No license file has been activated", None
    try:
        document = json.loads(row.signed_document_json)
    except Exception as e:
        return False, f"Stored license is not valid JSON: {e}", None
    pem = _resolved_public_pem()
    ok, err, claims = verify_document(document, pem)
    if not ok or not claims:
        return False, err or "Verification failed", None
    expected_issuer = (getattr(settings, "LICENSE_ISSUER_SLUG", "") or "").strip()
    if expected_issuer and (claims.get("issuer_slug") or "").strip() != expected_issuer:
        return False, "issuer_slug does not match this installation", None
    dist = (getattr(settings, "LICENSE_DISTRIBUTION_ID", "") or "").strip()
    if dist and (claims.get("distribution_id") or "").strip() != dist:
        return False, "distribution_id does not match this installation", None
    fc_claim = claims.get("facility_code")
    if fc_claim is not None and str(fc_claim).strip():
        fac = _facility_code(db)
        if not fac or fac != str(fc_claim).strip():
            return False, "facility_code in license does not match this facility", None
    now = utcnow()
    if now.tzinfo:
        now = now.replace(tzinfo=None)
    vf = parse_iso_datetime(claims.get("valid_from"))
    vu = parse_iso_datetime(claims.get("valid_until"))
    if vf and now < vf:
        return False, "License is not yet valid", claims
    if not vu:
        return False, "License has no valid_until", claims
    if now > vu:
        return False, "License has expired", claims
    lid = (claims.get("license_id") or "").strip()
    if not lid:
        return False, "License claims missing license_id", claims
    if row.license_public_id and row.license_public_id != lid:
        return False, "license_id does not match stored activation", claims
    return True, None, claims


def _try_online_refresh(db: Session, row: AppLicenseState, claims: Dict[str, Any]) -> None:
    base = (getattr(settings, "LICENSE_VERIFY_URL", "") or "").strip().rstrip("/")
    if not base:
        return
    api_key = (getattr(settings, "LICENSE_VERIFY_API_KEY", "") or "").strip()
    if not api_key:
        return
    interval_h = int(getattr(settings, "LICENSE_ONLINE_CHECK_INTERVAL_HOURS", 24) or 24)
    now = utcnow()
    if now.tzinfo:
        now = now.replace(tzinfo=None)
    if row.last_online_check_at:
        loc = row.last_online_check_at
        if loc.tzinfo:
            loc = loc.replace(tzinfo=None)
        if now - loc < timedelta(hours=max(1, interval_h)):
            return
    url = f"{base}/verify/online"
    license_id = (claims.get("license_id") or "").strip()
    facility_code = _facility_code(db)
    body = json.dumps(
        {"license_id": license_id, "facility_code": facility_code},
        separators=(",", ":"),
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-License-Server-Key": api_key,
        },
    )
    row.last_online_check_at = now
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
        db.commit()
        return
    if not payload.get("ok"):
        db.commit()
        return
    vu = parse_iso_datetime(payload.get("valid_until"))
    row.last_online_ok_at = now
    if vu:
        row.last_server_valid_until = vu
    db.commit()


def evaluate(db: Session, refresh_online: bool = True) -> Dict[str, Any]:
    """
    Returns a dict suitable for API responses.
    """
    if not enforcement_enabled():
        return {
            "enforcement_enabled": False,
            "has_valid_license": True,
            "valid_until": None,
            "online_ok": None,
            "in_grace_period": False,
            "license_id": None,
            "customer_label": None,
            "issuer_slug": None,
            "online_bootstrap_max_days": None,
            "online_bootstrap_deadline": None,
            "online_bootstrap_seconds_remaining": None,
            "awaiting_first_online_verify": False,
            "message": None,
        }

    row = _singleton(db)
    ok_file, err_file, claims = _verify_stored_document(db, row)
    if refresh_online and ok_file and claims:
        _try_online_refresh(db, row, claims)
        db.refresh(row)

    now = utcnow()
    if now.tzinfo:
        now = now.replace(tzinfo=None)

    rollback_error = _clock_rollback_error(now, row)
    if rollback_error:
        return {
            "enforcement_enabled": True,
            "has_valid_license": False,
            "valid_until": None,
            "online_ok": None,
            "in_grace_period": False,
            "license_id": (row.license_public_id or None),
            "customer_label": None,
            "issuer_slug": None,
            "online_bootstrap_max_days": None,
            "online_bootstrap_deadline": None,
            "online_bootstrap_seconds_remaining": None,
            "awaiting_first_online_verify": False,
            "message": rollback_error,
        }

    _checkpoint_evaluation_clock(db, row, now)

    grace = int(getattr(settings, "LICENSE_ONLINE_GRACE_SECONDS", 172800) or 172800)
    verify_url = (getattr(settings, "LICENSE_VERIFY_URL", "") or "").strip()

    server_still = False
    in_grace = False
    last_ok_naive = None
    if verify_url and row.last_online_ok_at:
        lo = row.last_online_ok_at
        if lo.tzinfo:
            lo = lo.replace(tzinfo=None)
        last_ok_naive = lo
        if row.last_server_valid_until:
            su = row.last_server_valid_until
            if su.tzinfo:
                su = su.replace(tzinfo=None)
            if now <= su:
                server_still = True
        if last_ok_naive and (now - last_ok_naive) <= timedelta(seconds=grace):
            in_grace = True

    has_valid = False
    message = err_file
    valid_until = None
    license_id = None
    customer = None
    issuer_slug = None

    bootstrap_deadline_iso = None
    bootstrap_seconds_remaining = None
    awaiting_first_online_verify = False
    max_boot_days = max(1, min(int(getattr(settings, "LICENSE_ONLINE_BOOTSTRAP_MAX_DAYS", 7) or 7), 365))

    if ok_file and claims:
        valid_until = parse_iso_datetime(claims.get("valid_until"))
        license_id = (claims.get("license_id") or "").strip() or None
        customer = (claims.get("customer_label") or "").strip() or None
        issuer_slug = (claims.get("issuer_slug") or "").strip() or None
        if not verify_url:
            has_valid = True
        elif row.last_online_ok_at is None:
            _ensure_bootstrap_anchor(db, row, now)
            db.refresh(row)
            act = _normalize_naive(row.license_activated_at)
            if act is None:
                has_valid = False
                message = "Missing license activation timestamp; re-import the signed license file."
            else:
                deadline = act + timedelta(days=max_boot_days)
                bootstrap_deadline_iso = deadline.isoformat()
                bootstrap_seconds_remaining = max(0, int((deadline - now).total_seconds()))
                has_valid = now <= deadline
                awaiting_first_online_verify = bool(has_valid and verify_url)
                if not has_valid:
                    message = (
                        f"Online license verification must succeed within {max_boot_days} days "
                        "of activation (or first run after upgrade). Connect to the license service or contact support."
                    )
        else:
            has_valid = bool(server_still or in_grace)
            if not has_valid:
                message = "Online verification failed or grace period ended; connect to the internet or contact support."

    return {
        "enforcement_enabled": True,
        "has_valid_license": bool(has_valid),
        "valid_until": valid_until.isoformat() if valid_until else None,
        "online_ok": server_still if verify_url else None,
        "in_grace_period": bool(in_grace and not server_still) if verify_url else False,
        "license_id": license_id,
        "customer_label": customer,
        "issuer_slug": issuer_slug,
        "online_bootstrap_max_days": max_boot_days if verify_url else None,
        "online_bootstrap_deadline": bootstrap_deadline_iso,
        "online_bootstrap_seconds_remaining": bootstrap_seconds_remaining,
        "awaiting_first_online_verify": awaiting_first_online_verify,
        "message": message if not has_valid else None,
    }


def append_activation_log(db: Session, claims: Dict[str, Any]) -> None:
    vu = parse_iso_datetime(claims.get("valid_until"))
    fc = claims.get("facility_code")
    fc_s = str(fc).strip() if fc is not None and str(fc).strip() else None
    lid = (claims.get("license_id") or "").strip()[:64]
    cust = str(claims.get("customer_label") or "")[:255]
    db.add(
        AppLicenseActivationLog(
            license_public_id=lid or "unknown",
            customer_label=cust,
            valid_until=vu,
            facility_code_in_license=fc_s,
        )
    )


def build_panel_current_file(db: Session, row: AppLicenseState) -> Dict[str, Any]:
    """Summary of stored file for admin UI (even when facility / dates fail full runtime check)."""
    installed = _facility_code(db)
    base: Dict[str, Any] = {
        "has_file": bool(row.signed_document_json),
        "license_id": None,
        "customer_label": None,
        "valid_until": None,
        "facility_code_in_license": None,
        "facility_code_installed": installed,
        "facility_matches": None,
        "signature_valid": False,
        "verification_error": None,
    }
    if not row.signed_document_json:
        return base
    try:
        document = json.loads(row.signed_document_json)
    except Exception as e:
        base["verification_error"] = f"Invalid JSON: {e}"
        return base
    pem = _resolved_public_pem()
    ok, err, claims = verify_document(document, pem)
    if not ok or not claims:
        base["verification_error"] = err or "Invalid document"
        return base
    base["signature_valid"] = True
    fc_claim = claims.get("facility_code")
    fc_s = str(fc_claim).strip() if fc_claim is not None and str(fc_claim).strip() else None
    base["license_id"] = (claims.get("license_id") or "").strip() or None
    base["customer_label"] = (claims.get("customer_label") or "").strip() or None
    vu = parse_iso_datetime(claims.get("valid_until"))
    base["valid_until"] = vu.isoformat() if vu else None
    base["facility_code_in_license"] = fc_s
    if not fc_s:
        base["facility_matches"] = True
    else:
        base["facility_matches"] = bool(installed and installed == fc_s)
    return base


def list_activation_history(db: Session, limit: int = 25) -> list:
    rows = (
        db.query(AppLicenseActivationLog)
        .order_by(AppLicenseActivationLog.id.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "activated_at": r.activated_at.isoformat() if r.activated_at else None,
                "license_public_id": r.license_public_id,
                "customer_label": r.customer_label,
                "valid_until": r.valid_until.isoformat() if r.valid_until else None,
                "facility_code_in_license": r.facility_code_in_license,
            }
        )
    return out


def assert_login_allowed(db: Session) -> None:
    from fastapi import HTTPException, status

    ev = evaluate(db, refresh_online=True)
    if not ev["enforcement_enabled"] or ev["has_valid_license"]:
        return
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail=ev.get("message") or "License is not valid or has expired.",
    )


def activate_from_document(
    db: Session,
    document: Dict[str, Any],
) -> Tuple[bool, str]:
    pem = _resolved_public_pem()
    ok, err, claims = verify_document(document, pem)
    if not ok or not claims:
        return False, err or "Invalid document"
    expected_issuer = (getattr(settings, "LICENSE_ISSUER_SLUG", "") or "").strip()
    if expected_issuer and (claims.get("issuer_slug") or "").strip() != expected_issuer:
        return False, "issuer_slug does not match this installation"
    dist = (getattr(settings, "LICENSE_DISTRIBUTION_ID", "") or "").strip()
    if dist and (claims.get("distribution_id") or "").strip() != dist:
        return False, "distribution_id does not match this installation"
    fc_claim = claims.get("facility_code")
    if fc_claim is not None and str(fc_claim).strip():
        fac = _facility_code(db)
        if not fac or fac != str(fc_claim).strip():
            return False, "facility_code in license does not match this facility settings"
    now = utcnow()
    if now.tzinfo:
        now = now.replace(tzinfo=None)
    vf = parse_iso_datetime(claims.get("valid_from"))
    vu = parse_iso_datetime(claims.get("valid_until"))
    if vf and now < vf:
        return False, "License is not yet valid"
    if not vu or now > vu:
        return False, "License is missing valid_until or has already expired"
    lid = (claims.get("license_id") or "").strip()
    if not lid:
        return False, "claims.license_id is required"
    append_activation_log(db, claims)
    row = _singleton(db)
    row.license_public_id = lid
    row.signed_document_json = json.dumps(document, separators=(",", ":"))
    row.last_online_ok_at = None
    row.last_server_valid_until = None
    row.last_online_check_at = None
    row.license_activated_at = now
    row.last_evaluated_at = now
    db.commit()
    return True, "License activated"
