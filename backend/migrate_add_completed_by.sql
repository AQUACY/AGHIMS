-- Migration: Add completed_by column to investigations table

-- SQLite
ALTER TABLE investigations ADD COLUMN completed_by INTEGER;

-- MySQL/PostgreSQL (same syntax)
-- ALTER TABLE investigations ADD COLUMN completed_by INTEGER;

