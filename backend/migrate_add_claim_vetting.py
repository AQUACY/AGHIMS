"""
Add pharmacy/doctor vetting columns to claims and claim_xml_import_items.
"""
from sqlalchemy import text

from app.core.database import engine


CLAIM_COLS = [
    ("pharmacy_vetted_at", "DATETIME NULL"),
    ("pharmacy_vetted_by", "INTEGER NULL"),
    ("doctor_vetted_at", "DATETIME NULL"),
    ("doctor_vetted_by", "INTEGER NULL"),
]

IMPORT_COLS = list(CLAIM_COLS)


def _existing_columns(conn, table: str) -> set:
    dialect = engine.dialect.name
    if dialect == "mysql":
        rows = conn.execute(text(f"SHOW COLUMNS FROM {table}")).fetchall()
        return {r[0] for r in rows}
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def _add_columns(conn, table: str, cols):
    existing = _existing_columns(conn, table)
    for name, typ in cols:
        if name in existing:
            print(f"{table}.{name} already exists")
            continue
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
        print(f"Added {table}.{name}")


def _sync_status_from_vet_timestamps(conn):
    """Promote older timestamp-only vets into status values (status is source of truth)."""
    statements = [
        """
        UPDATE claims
        SET status = 'doctor_vetted'
        WHERE doctor_vetted_at IS NOT NULL
          AND status IN ('draft', 'reopened', 'flagged')
        """,
        """
        UPDATE claims
        SET status = 'pharmacy_vetted'
        WHERE pharmacy_vetted_at IS NOT NULL
          AND doctor_vetted_at IS NULL
          AND status IN ('draft', 'reopened', 'flagged')
        """,
        """
        UPDATE claim_xml_import_items
        SET status = 'doctor_vetted', flag_comment = NULL
        WHERE doctor_vetted_at IS NOT NULL
          AND status IN ('draft', 'flagged')
        """,
        """
        UPDATE claim_xml_import_items
        SET status = 'pharmacy_vetted', flag_comment = NULL
        WHERE pharmacy_vetted_at IS NOT NULL
          AND doctor_vetted_at IS NULL
          AND status IN ('draft', 'flagged')
        """,
    ]
    for sql in statements:
        result = conn.execute(text(sql))
        print(f"Synced status rows: {result.rowcount}")


def migrate():
    with engine.begin() as conn:
        _add_columns(conn, "claims", CLAIM_COLS)
        _add_columns(conn, "claim_xml_import_items", IMPORT_COLS)
        _sync_status_from_vet_timestamps(conn)
    print("Claim vetting migration complete")


if __name__ == "__main__":
    migrate()
