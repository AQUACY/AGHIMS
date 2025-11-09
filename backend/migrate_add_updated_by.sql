-- Migration: Add updated_by column to lab_results table

-- SQLite
ALTER TABLE lab_results ADD COLUMN updated_by INTEGER;

-- MySQL/PostgreSQL (same syntax)
-- ALTER TABLE lab_results ADD COLUMN updated_by INTEGER;

