"""
Sync product_prices so only NHIA-listed medications are active (featured).

- Activates products whose medication_code is in the NHIA list
- Archives other Pharmacy products (is_active=False)
- Leaves Non-Drug / consumable products alone by default

Dry-run by default. Pass --apply to write changes.

Usage (from repo root, with backend venv):

  backend/venv/Scripts/python.exe nhia-product-compare/sync_products_to_nhia_list.py
  backend/venv/Scripts/python.exe nhia-product-compare/sync_products_to_nhia_list.py --apply
  backend/venv/Scripts/python.exe nhia-product-compare/sync_products_to_nhia_list.py --apply --nhia "path/to/NHIA.xlsx"
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
DEFAULT_NHIA = Path(__file__).resolve().parent / "NHIA List (1).xlsx"


def bootstrap_backend_env() -> None:
    """
    Ensure we load backend/.env (MySQL) instead of an empty SQLite fallback.
    pydantic-settings reads .env from the process CWD.
    """
    if not BACKEND_DIR.is_dir():
        raise SystemExit(f"Backend directory not found: {BACKEND_DIR}")

    os.chdir(BACKEND_DIR)
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    # Clear cached settings if any previous import used the wrong CWD
    for mod in list(sys.modules):
        if mod == "app" or mod.startswith("app."):
            del sys.modules[mod]


def load_nhia_codes(nhia_path: Path) -> set[str]:
    df = pd.read_excel(nhia_path)
    code_col = None
    for c in df.columns:
        if str(c).strip().upper() in ("CODE", "MEDICATION CODE", "MEDICATION_CODE"):
            code_col = c
            break
    if code_col is None:
        raise SystemExit(f"Could not find CODE column in {nhia_path}. Columns: {list(df.columns)}")

    codes = {
        str(v).strip().upper()
        for v in df[code_col].dropna().tolist()
        if str(v).strip() and str(v).strip().lower() != "nan"
    }
    return codes


def main() -> None:
    parser = argparse.ArgumentParser(description="Feature only NHIA-listed pharmacy products")
    parser.add_argument(
        "--nhia",
        type=Path,
        default=DEFAULT_NHIA,
        help=f"Path to NHIA Excel list (default: {DEFAULT_NHIA})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to the database (default is dry-run)",
    )
    parser.add_argument(
        "--all-products",
        action="store_true",
        help="Also archive non-Pharmacy product rows not in the NHIA list (dangerous for consumables)",
    )
    args = parser.parse_args()

    nhia_path = args.nhia if args.nhia.is_absolute() else (Path.cwd() / args.nhia).resolve()
    # Resolve NHIA path before chdir (relative paths are usually from repo root)
    if not nhia_path.exists():
        alt = DEFAULT_NHIA
        if alt.exists():
            nhia_path = alt
        else:
            raise SystemExit(f"NHIA file not found: {args.nhia}")

    bootstrap_backend_env()

    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.models.product_price import ProductPrice

    db_label = settings.DATABASE_URL
    if "@" in db_label:
        db_label = db_label.split("@", 1)[1]
    print(f"Using database: mode={settings.DATABASE_MODE} -> {db_label}")

    nhia_codes = load_nhia_codes(nhia_path)
    print(f"NHIA codes loaded: {len(nhia_codes)} from {nhia_path}")

    db = SessionLocal()
    try:
        products = db.query(ProductPrice).all()
        print(f"Product rows in DB: {len(products)}")
        if len(products) == 0:
            print(
                "\nWARNING: product_prices is empty on this connection.\n"
                "Check DATABASE_MODE in backend/.env (should be mysql for the live app)."
            )

        activate = []
        archive = []
        skipped_non_pharmacy = []
        already_ok_active = 0
        already_ok_archived = 0

        for p in products:
            code = (p.medication_code or "").strip().upper()
            sub2 = (p.sub_category_2 or "").strip()
            is_pharmacy = sub2.lower() == "pharmacy"
            in_nhia = bool(code) and code in nhia_codes

            if in_nhia:
                if p.is_active:
                    already_ok_active += 1
                else:
                    activate.append(p)
                continue

            # Not in NHIA list
            if is_pharmacy or args.all_products:
                if not p.is_active:
                    already_ok_archived += 1
                else:
                    archive.append(p)
            else:
                skipped_non_pharmacy.append(p)

        print("\n=== Plan ===")
        print(f"  Activate (in NHIA, currently archived): {len(activate)}")
        print(f"  Archive  (Pharmacy not in NHIA, currently active): {len(archive)}")
        print(f"  Already active & in NHIA: {already_ok_active}")
        print(f"  Already archived & not in NHIA (pharmacy scope): {already_ok_archived}")
        print(f"  Skipped non-Pharmacy (left unchanged): {len(skipped_non_pharmacy)}")

        if activate:
            print("\nSample to activate:")
            for p in activate[:8]:
                print(f"  + {p.medication_code} | {p.product_name}")
        if archive:
            print("\nSample to archive:")
            for p in archive[:8]:
                print(f"  - {p.medication_code} | {p.product_name}")

        missing_in_db = sorted(
            nhia_codes
            - {
                (p.medication_code or "").strip().upper()
                for p in products
                if p.medication_code
            }
        )
        print(f"\nNHIA codes not found in product_prices at all: {len(missing_in_db)}")
        if missing_in_db[:10]:
            print("  e.g.", ", ".join(missing_in_db[:10]))

        if not args.apply:
            print("\nDry-run only. Re-run with --apply to write changes.")
            return

        for p in activate:
            p.is_active = True
        for p in archive:
            p.is_active = False
        db.commit()
        print(f"\nApplied: activated {len(activate)}, archived {len(archive)}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
