-- Add icd10 column to claim_procedures (run with MySQL client if Python script times out)
--
-- Usage (from backend folder, adjust user/password):
--   mysql -u root -p hms < migrate_add_claim_procedure_icd10_mysql.sql
-- Or paste into MySQL Workbench / phpMyAdmin and run.
--
-- If you get "Duplicate column name 'icd10'", the column already exists; you're done.

ALTER TABLE claim_procedures
ADD COLUMN icd10 VARCHAR(50) NULL AFTER gdrg_code;
