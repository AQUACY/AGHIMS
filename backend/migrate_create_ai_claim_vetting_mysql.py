"""
Create/upgrade AI claim vetting tables (MySQL).
Idempotent.
"""
import os
import sys

import pymysql
from dotenv import load_dotenv

load_dotenv()

JOB_DDL = """
CREATE TABLE IF NOT EXISTS ai_claim_vetting_jobs (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    batch_id INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    total_items INT NOT NULL DEFAULT 0,
    processed_items INT NOT NULL DEFAULT 0,
    findings_count INT NOT NULL DEFAULT 0,
    item_ids JSON NULL,
    error_message TEXT NULL,
    summary_by_rule JSON NULL,
    started_by_id INT NULL,
    created_at DATETIME NOT NULL,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    INDEX ix_ai_vet_job_batch (batch_id),
    INDEX ix_ai_vet_job_status (status),
    CONSTRAINT fk_ai_vet_job_batch FOREIGN KEY (batch_id) REFERENCES claim_xml_import_batches(id),
    CONSTRAINT fk_ai_vet_job_user FOREIGN KEY (started_by_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

FINDINGS_DDL = """
CREATE TABLE IF NOT EXISTS ai_claim_vetting_findings (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    source_type VARCHAR(30) NOT NULL,
    source_id INT NULL,
    claim_claim_id VARCHAR(50) NULL,
    job_id INT NULL,
    rule_code VARCHAR(64) NOT NULL,
    finding VARCHAR(500) NOT NULL,
    severity VARCHAR(30) NOT NULL DEFAULT 'warning',
    explanation TEXT NULL,
    recommendation TEXT NULL,
    suggested_action JSON NULL,
    requires_human_review TINYINT(1) NOT NULL DEFAULT 1,
    provider VARCHAR(40) NOT NULL DEFAULT 'rules',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    human_decision_note TEXT NULL,
    decided_by_id INT NULL,
    decided_at DATETIME NULL,
    created_at DATETIME NOT NULL,
    created_by_id INT NULL,
    INDEX ix_ai_vet_source_type (source_type),
    INDEX ix_ai_vet_source_id (source_id),
    INDEX ix_ai_vet_claim_claim_id (claim_claim_id),
    INDEX ix_ai_vet_job_id (job_id),
    INDEX ix_ai_vet_rule_code (rule_code),
    INDEX ix_ai_vet_status (status),
    CONSTRAINT fk_ai_vet_decided_by FOREIGN KEY (decided_by_id) REFERENCES users(id),
    CONSTRAINT fk_ai_vet_created_by FOREIGN KEY (created_by_id) REFERENCES users(id),
    CONSTRAINT fk_ai_vet_finding_job FOREIGN KEY (job_id) REFERENCES ai_claim_vetting_jobs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


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
            cur.execute(JOB_DDL)
            print("ai_claim_vetting_jobs OK")
            cur.execute(FINDINGS_DDL)
            print("ai_claim_vetting_findings OK")
            try:
                cur.execute(
                    "ALTER TABLE ai_claim_vetting_findings ADD COLUMN job_id INT NULL"
                )
                print("Added ai_claim_vetting_findings.job_id")
            except pymysql.err.OperationalError as e:
                if e.args and e.args[0] == 1060:
                    print("ai_claim_vetting_findings.job_id already exists")
                else:
                    raise
            try:
                cur.execute(
                    "ALTER TABLE ai_claim_vetting_findings "
                    "ADD INDEX ix_ai_vet_job_id (job_id)"
                )
            except pymysql.err.OperationalError:
                pass
            try:
                cur.execute(
                    "ALTER TABLE ai_claim_vetting_findings "
                    "ADD CONSTRAINT fk_ai_vet_finding_job "
                    "FOREIGN KEY (job_id) REFERENCES ai_claim_vetting_jobs(id)"
                )
            except pymysql.err.OperationalError:
                pass
        print("AI claim vetting MySQL migration complete")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
