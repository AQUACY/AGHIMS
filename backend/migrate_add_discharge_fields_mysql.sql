-- Migration: Add discharge outcome, condition, partial discharge fields, and final orders to ward_admissions table (MySQL)
-- Run these SQL statements manually if needed

-- Add discharge_outcome column
ALTER TABLE ward_admissions
ADD COLUMN discharge_outcome VARCHAR(50) NULL;

-- Add discharge_condition column
ALTER TABLE ward_admissions
ADD COLUMN discharge_condition VARCHAR(50) NULL;

-- Add partially_discharged_at column
ALTER TABLE ward_admissions
ADD COLUMN partially_discharged_at DATETIME NULL;

-- Add partially_discharged_by column
ALTER TABLE ward_admissions
ADD COLUMN partially_discharged_by INT NULL;

-- Add foreign key constraint for partially_discharged_by (optional, can skip if constraint name conflicts)
-- ALTER TABLE ward_admissions
-- ADD CONSTRAINT fk_ward_admissions_partially_discharged_by
-- FOREIGN KEY (partially_discharged_by) REFERENCES users(id);

-- Add final_orders column
ALTER TABLE ward_admissions
ADD COLUMN final_orders TEXT NULL;

