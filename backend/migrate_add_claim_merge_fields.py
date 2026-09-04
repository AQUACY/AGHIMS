"""
Add claim-merge columns:
- claim_xml_import_items.member_no (denormalized, indexed)
- claim_xml_import_items.merged_into_id
- claims.merged_into_id

Backfills member_no from GHIMS payload.memberNo.
"""
from sqlalchemy import text

from app.core.database import engine


def _existing_columns(conn, table: str) -> set:
    dialect = engine.dialect.name
    if dialect == "mysql":
        rows = conn.execute(text(f"SHOW COLUMNS FROM {table}")).fetchall()
        return {r[0] for r in rows}
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def _add_column(conn, table: str, name: str, typ: str) -> None:
    existing = _existing_columns(conn, table)
    if name in existing:
        print(f"{table}.{name} already exists")
        return
    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {typ}"))
    print(f"Added {table}.{name}")


def _index_exists(conn, table: str, index_name: str) -> bool:
    dialect = engine.dialect.name
    if dialect == "mysql":
        rows = conn.execute(text(f"SHOW INDEX FROM {table} WHERE Key_name = :name"), {"name": index_name}).fetchall()
        return bool(rows)
    rows = conn.execute(text(f"PRAGMA index_list({table})")).fetchall()
    return any(str(r[1]) == index_name for r in rows)


def _add_index(conn, table: str, index_name: str, column: str) -> None:
    if _index_exists(conn, table, index_name):
        print(f"Index {index_name} already exists")
        return
    conn.execute(text(f"CREATE INDEX {index_name} ON {table} ({column})"))
    print(f"Created {index_name}")


def _backfill_member_no(conn) -> None:
    dialect = engine.dialect.name
    if dialect == "mysql":
        sql = """
            UPDATE claim_xml_import_items
            SET member_no = NULLIF(TRIM(JSON_UNQUOTE(JSON_EXTRACT(payload, '$.memberNo'))), '')
            WHERE member_no IS NULL
              AND payload IS NOT NULL
        """
    else:
        sql = """
            UPDATE claim_xml_import_items
            SET member_no = NULLIF(TRIM(json_extract(payload, '$.memberNo')), '')
            WHERE member_no IS NULL
              AND payload IS NOT NULL
        """
    result = conn.execute(text(sql))
    print(f"Backfilled member_no on {result.rowcount} imported claim(s)")


def migrate():
    with engine.begin() as conn:
        _add_column(conn, "claim_xml_import_items", "member_no", "VARCHAR(100) NULL")
        _add_column(conn, "claim_xml_import_items", "merged_into_id", "INTEGER NULL")
        _add_column(conn, "claims", "merged_into_id", "INTEGER NULL")
        _add_index(conn, "claim_xml_import_items", "ix_claim_xml_import_items_member_no", "member_no")
        _add_index(conn, "claim_xml_import_items", "ix_claim_xml_import_items_merged_into_id", "merged_into_id")
        _add_index(conn, "claims", "ix_claims_merged_into_id", "merged_into_id")
        _backfill_member_no(conn)
    print("Claim merge fields migration complete")


if __name__ == "__main__":
    migrate()
