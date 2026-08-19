"""Create ai_claim_vetting_rules and seed default facility rules (SQLite)."""
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.models.ai_claim_vetting import AiClaimVettingRule
from app.services.ai_claim_vetting.configurable_rules import SEED_RULES


def migrate():
    if settings.DATABASE_MODE.lower() == "mysql":
        print("Skipping SQLite rules migration (DATABASE_MODE=mysql). Use migrate_create_ai_claim_vetting_rules_mysql.py")
        return

    print("Creating ai_claim_vetting_rules (if missing)...")
    AiClaimVettingRule.__table__.create(engine, checkfirst=True)

    db = SessionLocal()
    try:
        for seed in SEED_RULES:
            existing = (
                db.query(AiClaimVettingRule)
                .filter(AiClaimVettingRule.rule_code == seed["rule_code"])
                .first()
            )
            if existing:
                print(f"  seed {seed['rule_code']} already present")
                continue
            row = AiClaimVettingRule(
                rule_code=seed["rule_code"],
                name=seed["name"],
                description=seed.get("description"),
                enabled=bool(seed.get("enabled", True)),
                severity=seed.get("severity") or "warning",
                priority=int(seed.get("priority") or 100),
                analysis_modes=seed.get("analysis_modes") or ["phase1"],
                applies_to=seed.get("applies_to") or "ghims_import",
                is_system=bool(seed.get("is_system", True)),
                condition=seed.get("condition") or {},
                suggested_action=seed.get("suggested_action"),
                finding_template=seed.get("finding_template"),
                recommendation_template=seed.get("recommendation_template"),
                requires_human_review=bool(seed.get("requires_human_review", True)),
            )
            db.add(row)
            print(f"  seeded {seed['rule_code']}")
        db.commit()
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
