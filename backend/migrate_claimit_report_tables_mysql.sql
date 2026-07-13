-- Create ClaimIT report batch and error tables (MySQL)
-- Run from backend folder: mysql -u root -p hms < migrate_claimit_report_tables_mysql.sql
-- Or run in MySQL Workbench / phpMyAdmin against database 'hms'.

CREATE TABLE IF NOT EXISTS claimit_report_batches (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NULL,
  file_name VARCHAR(255) NOT NULL,
  uploaded_at DATETIME NULL,
  uploaded_by_id INT NULL,
  summary JSON NULL,
  error_count INT DEFAULT 0,
  INDEX ix_claimit_report_batches_uploaded_at (uploaded_at),
  CONSTRAINT fk_claimit_report_batches_uploaded_by
    FOREIGN KEY (uploaded_by_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS claimit_report_errors (
  id INT AUTO_INCREMENT PRIMARY KEY,
  batch_id INT NOT NULL,
  claim_claim_id VARCHAR(50) NOT NULL,
  outcome VARCHAR(20) NOT NULL,
  error_messages JSON NOT NULL,
  row_index INT NULL,
  INDEX ix_claimit_report_errors_batch_id (batch_id),
  INDEX ix_claimit_report_errors_claim_claim_id (claim_claim_id),
  CONSTRAINT fk_claimit_report_errors_batch
    FOREIGN KEY (batch_id) REFERENCES claimit_report_batches(id) ON DELETE CASCADE
);
