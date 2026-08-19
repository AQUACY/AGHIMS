"""Add analysis_mode to ai_claim_vetting_jobs (SQLite). Idempotent."""
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine


def migrate():
    if settings.DATABASE_MODE.lower() == "mysql":
        print("Skipping SQLite migration (DATABASE_MODE=mysql). Use migrate_add_ai_vetting_analysis_mode_mysql.py")
        return
    with engine.begin() as conn:
        try:
            conn.execute(
                text(
                    "ALTER TABLE ai_claim_vetting_jobs "
                    "ADD COLUMN analysis_mode VARCHAR(20) NOT NULL DEFAULT 'standard'"
                )
            )
            print("Added ai_claim_vetting_jobs.analysis_mode")
        except Exception:
            print("analysis_mode already exists (or alter skipped)")
    print("Done.")


if __name__ == "__main__":
    migrate()
