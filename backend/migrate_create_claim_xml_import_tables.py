"""
Create claim_xml_import_batches and claim_xml_import_items tables.
Run from backend folder: python migrate_create_claim_xml_import_tables.py
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import engine
from app.models.claim_xml_import import ClaimXmlImportBatch, ClaimXmlImportItem

if __name__ == "__main__":
    print("Creating claim_xml_import_batches and claim_xml_import_items tables...")
    ClaimXmlImportBatch.__table__.create(engine, checkfirst=True)
    ClaimXmlImportItem.__table__.create(engine, checkfirst=True)
    with engine.begin() as conn:
        # Backward-compatible alters if table was created before payload/status fields existed.
        for stmt in [
            "ALTER TABLE claim_xml_import_items ADD COLUMN status VARCHAR(20) DEFAULT 'draft'",
            "ALTER TABLE claim_xml_import_items ADD COLUMN payload JSON",
            "ALTER TABLE claim_xml_import_items ADD COLUMN finalized_at DATETIME",
            "ALTER TABLE claim_xml_import_items ADD COLUMN flag_comment VARCHAR(800) NULL",
        ]:
            try:
                conn.exec_driver_sql(stmt)
            except Exception:
                pass
    print("Done.")
