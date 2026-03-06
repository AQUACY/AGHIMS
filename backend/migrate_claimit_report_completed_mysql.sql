-- Add completed_at and completed_by_id to claimit_report_errors (MySQL)
-- Run against database 'hms' (or your DB name).

ALTER TABLE claimit_report_errors
  ADD COLUMN completed_at DATETIME NULL,
  ADD COLUMN completed_by_id INT NULL,
  ADD CONSTRAINT fk_claimit_report_errors_completed_by
    FOREIGN KEY (completed_by_id) REFERENCES users(id) ON DELETE SET NULL;
