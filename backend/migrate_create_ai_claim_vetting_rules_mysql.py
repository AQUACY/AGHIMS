"""Create ai_claim_vetting_rules and seed default facility rules (MySQL). Idempotent."""
import json
import os
import sys
from datetime import datetime

import pymysql
from dotenv import load_dotenv

load_dotenv()

RULES_DDL = """
CREATE TABLE IF NOT EXISTS ai_claim_vetting_rules (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    rule_code VARCHAR(64) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 1,
    severity VARCHAR(30) NOT NULL DEFAULT 'warning',
    priority INT NOT NULL DEFAULT 100,
    analysis_modes JSON NULL,
    applies_to VARCHAR(30) NOT NULL DEFAULT 'ghims_import',
    is_system TINYINT(1) NOT NULL DEFAULT 0,
    `condition` JSON NOT NULL,
    suggested_action JSON NULL,
    finding_template VARCHAR(500) NULL,
    recommendation_template TEXT NULL,
    requires_human_review TINYINT(1) NOT NULL DEFAULT 1,
    created_by_id INT NULL,
    updated_by_id INT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NULL,
    UNIQUE KEY uq_ai_vet_rule_code (rule_code),
    INDEX ix_ai_vet_rule_enabled (enabled),
    CONSTRAINT fk_ai_vet_rule_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_ai_vet_rule_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

SEED_RULES = [
    {
        "rule_code": "member_no_leading_hyphen",
        "name": "Member No leading hyphen",
        "description": "Records sometimes prefix Member No with '-'. ClaimIT / NHIA numbers should not begin with a hyphen.",
        "enabled": 1,
        "severity": "critical",
        "priority": 10,
        "analysis_modes": ["phase1", "coding", "thorough"],
        "applies_to": "ghims_import",
        "is_system": 1,
        "condition": {"field": "memberNo", "op": "starts_with", "value": "-"},
        "suggested_action": {
            "type": "strip_prefix",
            "field": "memberNo",
            "value": "-",
            "details": {"prefix": "-"},
        },
        "finding_template": "Member No begins with a hyphen ('{value}').",
        "recommendation_template": "Remove the leading hyphen from Member No.",
        "requires_human_review": 1,
    },
    {
        "rule_code": "member_no_length_not_8",
        "name": "Member No length not 8",
        "description": "Typical NHIA member numbers are 8 characters. Skips Ghana Card format and 10-digit HIN-shaped values starting with 00.",
        "enabled": 1,
        "severity": "warning",
        "priority": 20,
        "analysis_modes": ["phase1", "coding", "thorough"],
        "applies_to": "ghims_import",
        "is_system": 1,
        "condition": {
            "field": "memberNo",
            "op": "length_ne",
            "value": 8,
            "skip_if_ghana_card": True,
            "skip_if_hin_shaped": True,
        },
        "suggested_action": {"type": "review_only", "field": "memberNo"},
        "finding_template": "Member No '{value}' is not 8 characters.",
        "recommendation_template": "Confirm the Member No against NHIA (usually 8 digits, no leading hyphen).",
        "requires_human_review": 1,
    },
    {
        "rule_code": "hin_format_check",
        "name": "HIN format (10 digits, starts with 00)",
        "description": "When HIN is present it is normally 10 characters and begins with 00.",
        "enabled": 1,
        "severity": "warning",
        "priority": 30,
        "analysis_modes": ["phase1", "coding", "thorough"],
        "applies_to": "ghims_import",
        "is_system": 1,
        "condition": {"field": "hin", "op": "hin_format_invalid"},
        "suggested_action": {"type": "review_only", "field": "hin"},
        "finding_template": "HIN '{value}' may be invalid (expect 10 characters starting with 00).",
        "recommendation_template": "Confirm HIN is 10 characters and begins with 00.",
        "requires_human_review": 1,
    },
]


def migrate():
    host = os.getenv("DB_HOST") or os.getenv("MYSQL_HOST") or "127.0.0.1"
    port = int(os.getenv("DB_PORT") or os.getenv("MYSQL_PORT") or 3306)
    user = os.getenv("DB_USER") or os.getenv("MYSQL_USER") or "root"
    password = os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD") or ""
    database = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB")
    if not database:
        print("DB_NAME / MYSQL_DATABASE not set", file=sys.stderr)
        sys.exit(1)

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        charset="utf8mb4",
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(RULES_DDL)
            print("Ensured ai_claim_vetting_rules")
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            for seed in SEED_RULES:
                cur.execute(
                    "SELECT id FROM ai_claim_vetting_rules WHERE rule_code=%s",
                    (seed["rule_code"],),
                )
                if cur.fetchone():
                    print(f"  seed {seed['rule_code']} already present")
                    continue
                cur.execute(
                    """
                    INSERT INTO ai_claim_vetting_rules (
                        rule_code, name, description, enabled, severity, priority,
                        analysis_modes, applies_to, is_system, `condition`, suggested_action,
                        finding_template, recommendation_template, requires_human_review, created_at
                    ) VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                    )
                    """,
                    (
                        seed["rule_code"],
                        seed["name"],
                        seed["description"],
                        seed["enabled"],
                        seed["severity"],
                        seed["priority"],
                        json.dumps(seed["analysis_modes"]),
                        seed["applies_to"],
                        seed["is_system"],
                        json.dumps(seed["condition"]),
                        json.dumps(seed["suggested_action"]),
                        seed["finding_template"],
                        seed["recommendation_template"],
                        seed["requires_human_review"],
                        now,
                    ),
                )
                print(f"  seeded {seed['rule_code']}")
        print("Done.")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
