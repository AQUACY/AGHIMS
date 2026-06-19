#!/usr/bin/env python3
"""
Copy price list tables from the main HMS database into Suhum's database.

Usage (from suhum/backend):
  python scripts/sync_price_list_from_main.py
  python scripts/sync_price_list_from_main.py --dry-run

Requires MAIN_DATABASE_URL in .env (or pass --main-url).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow running as script from suhum/backend
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import engine as suhum_engine, SessionLocal, Base
from app.models import (
    ICD10DRGMapping,
    ProcedurePrice,
    ProductPrice,
    SurgeryPrice,
    UnmappedDRGPrice,
)

PRICE_TABLES = [
    (ProcedurePrice, "procedure_prices"),
    (SurgeryPrice, "surgery_prices"),
    (ProductPrice, "product_prices"),
    (UnmappedDRGPrice, "unmapped_drg_prices"),
    (ICD10DRGMapping, "icd10_drg_mappings"),
]


def _row_to_dict(model, row):
    data = {}
    for col in model.__table__.columns:
        if col.name == "id":
            continue
        data[col.name] = getattr(row, col.name)
    return data


def sync_price_list(main_url: str, dry_run: bool = False) -> dict:
    if not main_url:
        raise SystemExit("MAIN_DATABASE_URL is required (set in .env or pass --main-url)")

    Base.metadata.create_all(bind=suhum_engine)

    main_engine = create_engine(main_url, pool_pre_ping=True)
    MainSession = sessionmaker(bind=main_engine)
    main_db = MainSession()
    suhum_db = SessionLocal()

    stats = {}
    try:
        inspector = inspect(main_engine)
        for model, table_name in PRICE_TABLES:
            if table_name not in inspector.get_table_names():
                stats[table_name] = {"skipped": True, "reason": "table missing on main DB"}
                continue

            rows = main_db.query(model).all()
            stats[table_name] = {"source_count": len(rows), "synced": 0}

            if dry_run:
                continue

            suhum_db.query(model).delete()
            for row in rows:
                suhum_db.add(model(**_row_to_dict(model, row)))
            suhum_db.flush()
            stats[table_name]["synced"] = len(rows)

        if not dry_run:
            suhum_db.commit()
    except Exception:
        suhum_db.rollback()
        raise
    finally:
        main_db.close()
        suhum_db.close()
        main_engine.dispose()

    return stats


def main():
    parser = argparse.ArgumentParser(description="Sync price list from main HMS to Suhum")
    parser.add_argument("--main-url", default=settings.MAIN_DATABASE_URL, help="Main HMS SQLAlchemy URL")
    parser.add_argument("--dry-run", action="store_true", help="Count rows only; do not write")
    args = parser.parse_args()

    stats = sync_price_list(args.main_url, dry_run=args.dry_run)
    print("Price list sync complete" + (" (dry run)" if args.dry_run else ""))
    for table, info in stats.items():
        print(f"  {table}: {info}")


if __name__ == "__main__":
    main()
