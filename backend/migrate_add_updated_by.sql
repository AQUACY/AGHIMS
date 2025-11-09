-- Migration: Add updated_by column to lab_results, scan_results, and xray_results tables

-- SQLite
-- ALTER TABLE lab_results ADD COLUMN updated_by INTEGER;
-- ALTER TABLE scan_results ADD COLUMN updated_by INTEGER;
-- ALTER TABLE xray_results ADD COLUMN updated_by INTEGER;

-- MySQL
ALTER TABLE lab_results ADD COLUMN updated_by INTEGER NULL;
ALTER TABLE scan_results ADD COLUMN updated_by INTEGER NULL;
ALTER TABLE xray_results ADD COLUMN updated_by INTEGER NULL;

-- PostgreSQL
-- ALTER TABLE lab_results ADD COLUMN updated_by INTEGER;
-- ALTER TABLE scan_results ADD COLUMN updated_by INTEGER;
-- ALTER TABLE xray_results ADD COLUMN updated_by INTEGER;

