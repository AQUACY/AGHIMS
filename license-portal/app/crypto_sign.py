import base64
import json
from typing import Any, Dict

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _load_private_key(pem: str):
    pem = (pem or "").strip()
    if not pem:
        raise ValueError("Missing RSA private key PEM")
    return serialization.load_pem_private_key(
        pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )


def resolved_private_key_pem(settings) -> str:
    path = (settings.RSA_PRIVATE_KEY_FILE or "").strip()
    if path:
        from pathlib import Path

        return Path(path).read_text(encoding="utf-8")
    return (settings.RSA_PRIVATE_KEY_PEM or "").strip()


def canonical_claims_bytes(claims: Dict[str, Any]) -> bytes:
    return json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_claims(claims: Dict[str, Any], private_key_pem: str) -> str:
    key = _load_private_key(private_key_pem)
    msg = canonical_claims_bytes(claims)
    sig = key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode("ascii")


def build_signed_document(claims: Dict[str, Any], private_key_pem: str) -> Dict[str, Any]:
    signature_b64 = sign_claims(claims, private_key_pem)
    return {"claims": claims, "signature_b64": signature_b64}
