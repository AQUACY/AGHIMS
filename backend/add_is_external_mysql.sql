-- Migration: Add is_external column to prescriptions table (MySQL)
-- Run this SQL command directly on your MySQL database

ALTER TABLE prescriptions ADD COLUMN is_external INT DEFAULT 0 NOT NULL;

