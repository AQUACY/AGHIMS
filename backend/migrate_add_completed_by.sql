-- Migration: Add completed_by column to investigations table

-- SQLite
-- ALTER TABLE investigations ADD COLUMN completed_by INTEGER;

-- MySQL
ALTER TABLE investigations ADD COLUMN completed_by INTEGER NULL;

-- PostgreSQL
-- ALTER TABLE investigations ADD COLUMN completed_by INTEGER;

