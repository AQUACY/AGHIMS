"""
RSA-SHA256 signing and verification for offline license documents.

Document shape: {"claims": {...}, "signature_b64": "..."}
Canonical message: UTF-8 JSON of claims with sort_keys=True and compact separators.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def claims_canonical_bytes(claims: Dict[str, Any]) -> bytes:
    return json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_public_key_from_pem(pem: str):
    pem = (pem or "").strip()
    if not pem:
        raise ValueError("Empty public key PEM")
    return serialization.load_pem_public_key(pem.encode("utf-8"), backend=default_backend())


def verify_document(
    document: Dict[str, Any],
    public_key_pem: str,
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Returns (ok, error_message, claims).
    """
    if not isinstance(document, dict):
        return False, "License file must be a JSON object", None
    claims = document.get("claims")
    sig_b64 = document.get("signature_b64")
    if not isinstance(claims, dict):
        return False, "Missing or invalid claims", None
    if not isinstance(sig_b64, str) or not sig_b64.strip():
        return False, "Missing signature_b64", None
    try:
        signature = base64.b64decode(sig_b64, validate=True)
    except Exception:
        return False, "Invalid base64 signature", None
    try:
        pub = load_public_key_from_pem(public_key_pem)
    except Exception as e:
        return False, f"Invalid public key: {e}", None
    msg = claims_canonical_bytes(claims)
    try:
        pub.verify(
            signature,
            msg,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except Exception:
        return False, "Signature verification failed", None
    return True, None, claims


def parse_iso_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(s)
    except ValueError:
        return None
    if parsed.tzinfo:
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed
