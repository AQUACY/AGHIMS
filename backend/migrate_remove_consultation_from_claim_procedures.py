"""
One-time cleanup: Remove from claim_procedures any rows where the description
is a main service request (e.g. General New Consultation Adult, Paediatric New Consultation)
rather than an actual surgery. These were wrongly copied into the surgery section in an earlier version.
Uses raw SQL only to avoid loading ORM models (prevents User/UserRole mapper errors when run standalone).
Run from backend directory: python migrate_remove_consultation_from_claim_procedures.py [--yes]
"""
import sys
import argparse
from pathlib import Path

# Ensure backend is on path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Same list as in app.services.xml_export (do not import xml_export or models to avoid ORM loading)
CONSULTATION_SERVICE_PROCEDURE_PHRASES = [
    "General New Consultation Adult",
    "General New Consultation Child",
    "Paediatric New Consultation",
    "General New Consultation",
    "New Consultation Adult",
    "New Consultation Child",
    "General Review Consultation Adult",
    "General Review Consultation Child",
    "Paediatric Review Consultation",
    "General Review Consultation",
    "New Review Consultation Adult",
    "New Review Consultation Child",
    "Review Consultation Adult",
    "Review Consultation Child",
    "Consultation",
]


def is_consultation_service_procedure(description: str) -> bool:
    """True if description is a main service request (e.g. consultation type), not an actual surgery."""
    if not description or not str(description).strip():
        return False
    d = str(description).strip().lower()
    return any(phrase.lower() in d for phrase in CONSULTATION_SERVICE_PROCEDURE_PHRASES)


def migrate(yes: bool = False):
    from sqlalchemy import text
    from app.core.database import engine

    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, claim_id, description, gdrg_code FROM claim_procedures"))
        rows = result.fetchall()
    to_delete = [
        {"id": row[0], "claim_id": row[1], "description": row[2], "gdrg_code": row[3]}
        for row in rows
        if is_consultation_service_procedure(row[2] or "")
    ]
    if not to_delete:
        print("No claim procedures found with consultation-type descriptions. Nothing to remove.")
        return
    print(f"Phrases that identify consultation (not surgery): {CONSULTATION_SERVICE_PROCEDURE_PHRASES}")
    print(f"Found {len(to_delete)} claim_procedure row(s) to remove:")
    for p in to_delete:
        print(f"  claim_id={p['claim_id']} id={p['id']} description={repr(p['description'])} gdrg_code={p['gdrg_code']}")
    if not yes:
        confirm = input("Proceed with deletion? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return
    with engine.begin() as conn:
        for p in to_delete:
            conn.execute(text("DELETE FROM claim_procedures WHERE id = :id"), {"id": p["id"]})
    print(f"Deleted {len(to_delete)} row(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove consultation-type entries from claim_procedures")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    migrate(yes=args.yes)
