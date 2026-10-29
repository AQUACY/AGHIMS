"""Independent pharmacy claim ownership / demarcation columns."""
from sqlalchemy import text

from app.core.database import engine


IMPORT_COLS = [
    ("pharmacy_assigned_to_id", "INTEGER NULL"),
    ("pharmacy_assigned_at", "DATETIME NULL"),
    ("pharmacy_assigned_by_id", "INTEGER NULL"),
    ("pharmacy_assignment_note", "VARCHAR(255) NULL"),
]

BATCH_COLS = [
    ("pharmacy_demarcation_rules", "JSON NULL"),
]


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


def _add_columns(conn, table: str, cols):
    existing = _existing_columns(conn, table)
    if not existing:
        print(f"Table {table} not found — skip")
        return
    for name, typ in cols:
        if name in existing:
            print(f"{table}.{name} already exists")
            continue
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
        print(f"Added {table}.{name}")


def migrate():
    with engine.begin() as conn:
        _add_columns(conn, "claim_xml_import_items", IMPORT_COLS)
        _add_columns(conn, "claim_xml_import_batches", BATCH_COLS)
    print("Pharmacy claim ownership migration complete")


if __name__ == "__main__":
    migrate()
