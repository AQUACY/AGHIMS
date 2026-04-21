#!/usr/bin/env python3
"""
Generate RSA keypair + random secrets and print exact .env lines for:
  - license-portal (signing + verify endpoint)
  - HMS backend (verification + activation)

Usage (from repo root):
  python scripts/generate_license_material.py --output-dir ./license-secrets --issuer-slug my-brand

Requires: cryptography (pip install cryptography)
"""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate license RSA keys and env snippets.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./license-secrets"),
        help="Directory to write license_private.pem and license_public.pem",
    )
    parser.add_argument(
        "--issuer-slug",
        required=True,
        help="Short stable id embedded in signed licenses (set same on portal ISSUER_SLUG and HMS LICENSE_ISSUER_SLUG).",
    )
    parser.add_argument(
        "--distribution-id",
        default="",
        help="Optional UUID/string; if set, printed for both sides (LICENSE_DISTRIBUTION_ID / DISTRIBUTION_ID).",
    )
    parser.add_argument(
        "--license-host",
        default="http://127.0.0.1:9500",
        help="Base URL for license portal (no trailing path); HMS LICENSE_VERIFY_URL will be {host}/api",
    )
    args = parser.parse_args()

    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        print("Install cryptography: python -m pip install cryptography", file=sys.stderr)
        return 1

    out: Path = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    priv_path = out / "license_private.pem"
    pub_path = out / "license_public.pem"

    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_path.write_bytes(priv_pem)
    pub_path.write_bytes(pub_pem)

    verify_secret = secrets.token_urlsafe(32)
    portal_jwt = secrets.token_urlsafe(48)
    setup_token = secrets.token_urlsafe(32)
    portal_admin_password = secrets.token_urlsafe(16)

    host = str(args.license_host).rstrip("/")
    verify_url = f"{host}/api"
    issuer = args.issuer_slug.strip()
    dist = (args.distribution_id or "").strip()

    priv_posix = priv_path.as_posix()
    pub_posix = pub_path.as_posix()

    print()
    print("=" * 72)
    print("FILES WRITTEN")
    print("=" * 72)
    print(f"  Private (portal only, never on HMS): {priv_path}")
    print(f"  Public (HMS only):                    {pub_path}")
    print()
    print("=" * 72)
    print("license-portal/.env  (append or merge these lines)")
    print("=" * 72)
    print(f'RSA_PRIVATE_KEY_FILE="{priv_posix}"')
    print(f'ISSUER_SLUG="{issuer}"')
    if dist:
        print(f'DISTRIBUTION_ID="{dist}"')
    print(f'VERIFY_SHARED_SECRET="{verify_secret}"')
    print(f'PORTAL_JWT_SECRET="{portal_jwt}"')
    print("PORTAL_ADMIN_USERNAME=license_admin")
    print(f'PORTAL_ADMIN_PASSWORD="{portal_admin_password}"')
    print()
    print("=" * 72)
    print("HMS backend/.env  (append or merge these lines)")
    print("=" * 72)
    print("LICENSE_ENFORCEMENT=true")
    print(f'LICENSE_RSA_PUBLIC_KEY_FILE="{pub_posix}"')
    print(f'LICENSE_ISSUER_SLUG="{issuer}"')
    if dist:
        print(f'LICENSE_DISTRIBUTION_ID="{dist}"')
    print(f'LICENSE_VERIFY_URL="{verify_url}"')
    print(f'LICENSE_VERIFY_API_KEY="{verify_secret}"')
    print("LICENSE_ONLINE_CHECK_INTERVAL_HOURS=24")
    print("LICENSE_ONLINE_GRACE_SECONDS=172800")
    print("LICENSE_ONLINE_BOOTSTRAP_MAX_DAYS=7")
    print(f'LICENSE_SETUP_TOKEN="{setup_token}"')
    print()
    print("=" * 72)
    print("AFTER FIRST DEPLOY")
    print("=" * 72)
    print("  1) Run HMS migration once (adds license_activated_at):")
    print("       cd backend && python migrate_add_license_activated_at.py")
    print("  2) Start license portal from license-portal/ with its .env, then open /ui/")
    print("  3) Create a license, download signed.json, use HMS /license-setup with LICENSE_SETUP_TOKEN")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
