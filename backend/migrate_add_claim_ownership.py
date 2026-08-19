"""
Add claim ownership/demarcation columns to claim_xml_import_items.

Ownership is organizational (who owns the claim for workload), not access control.
Anyone who can vet may still vet; pharmacy_vetted_by / doctor_vetted_by track who actually vetted.
"""
from sqlalchemy import text

from app.core.database import engine


IMPORT_COLS = [
    ("assigned_to_id", "INTEGER NULL"),
    ("assigned_at", "DATETIME NULL"),
    ("assigned_by_id", "INTEGER NULL"),
    ("assignment_note", "VARCHAR(255) NULL"),
]

BATCH_COLS = [
    ("demarcation_rules", "JSON NULL"),
]


def _add_columns(conn, table: str, cols):
    existing = _existing_columns(conn, table)
    if not existing:
        print(f"Table {table} not found — skip (will be created on first import / ensure)")
        return
    for name, typ in cols:
        if name in existing:
            print(f"{table}.{name} already exists")
            continue
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
        print(f"Added {table}.{name}")


def _existing_columns(conn, table: str) -> set:
    dialect = engine.dialect.name
    try:
        if dialect == "mysql":
            rows = conn.execute(text(f"SHOW COLUMNS FROM {table}")).fetchall()
            return {r[0] for r in rows}
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return {r[1] for r in rows}
    except Exception as e:
        err = str(e).lower()
        if "no such table" in err or "doesn't exist" in err:
            return set()
        raise


def migrate():
    with engine.begin() as conn:
        _add_columns(conn, "claim_xml_import_items", IMPORT_COLS)
        _add_columns(conn, "claim_xml_import_batches", BATCH_COLS)
    print("Claim ownership migration complete")


if __name__ == "__main__":
    migrate()
