-- Migration script to add finalized_by column to encounters table
-- Run this SQL directly on your database

-- Check if column already exists (for SQLite)
-- For MySQL/PostgreSQL, you can skip this check or use appropriate syntax

-- SQLite syntax:
ALTER TABLE encounters 
ADD COLUMN finalized_by INTEGER;

-- For MySQL, you can also add a foreign key constraint:
-- ALTER TABLE encounters 
-- ADD COLUMN finalized_by INTEGER,
-- ADD CONSTRAINT fk_encounters_finalized_by 
-- FOREIGN KEY (finalized_by) REFERENCES users(id);

-- For PostgreSQL:
-- ALTER TABLE encounters 
-- ADD COLUMN finalized_by INTEGER REFERENCES users(id);

