"""
Create/upgrade AI claim vetting tables (SQLite / SQLAlchemy).
On MySQL prod use migrate_create_ai_claim_vetting_mysql.py.
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.models.ai_claim_vetting import AiClaimVettingFinding, AiClaimVettingJob


def migrate():
    if settings.DATABASE_MODE.lower() == "mysql":
        print("Skipping SQLite AI claim vetting migration (DATABASE_MODE=mysql)")
        return
    print("Creating AI claim vetting tables (if missing)...")
    AiClaimVettingJob.__table__.create(engine, checkfirst=True)
    AiClaimVettingFinding.__table__.create(engine, checkfirst=True)
    with engine.begin() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE ai_claim_vetting_findings ADD COLUMN job_id INTEGER "
                "REFERENCES ai_claim_vetting_jobs(id)"
            ))
            print("Added ai_claim_vetting_findings.job_id")
        except Exception:
            print("ai_claim_vetting_findings.job_id already exists (or alter skipped)")
    print("Done.")


if __name__ == "__main__":
    migrate()
