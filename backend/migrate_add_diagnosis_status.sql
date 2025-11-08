-- Migration script to add diagnosis_status column to diagnoses table
-- Run this SQL directly on your database

-- SQLite syntax:
ALTER TABLE diagnoses 
ADD COLUMN diagnosis_status VARCHAR(20);

-- For MySQL:
-- ALTER TABLE diagnoses 
-- ADD COLUMN diagnosis_status VARCHAR(20);

-- For PostgreSQL:
-- ALTER TABLE diagnoses 
-- ADD COLUMN diagnosis_status VARCHAR(20);

-- Note: This column stores 'new', 'old', or 'recurring' values
-- It is nullable, so existing diagnoses will have NULL values

