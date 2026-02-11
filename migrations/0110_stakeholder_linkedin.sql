-- Migration: 0110_stakeholder_linkedin
-- Add linkedin_profile column to stakeholders table

ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS linkedin_profile TEXT;
