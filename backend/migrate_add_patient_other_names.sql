-- Migration: Add other_names column to patients table
-- This SQL file can be run manually if needed

-- For SQLite:
ALTER TABLE patients ADD COLUMN other_names VARCHAR(255);

-- For MySQL:
-- ALTER TABLE patients ADD COLUMN other_names VARCHAR(255) NULL;

