-- migrations/0083_add_pending_item_types.sql
-- Description: Add competitor, design_preference, stakeholder to pending_item_type enum
-- Date: 2026-01-26

-- Add new values to the pending_item_type enum
ALTER TYPE pending_item_type ADD VALUE IF NOT EXISTS 'competitor';
ALTER TYPE pending_item_type ADD VALUE IF NOT EXISTS 'design_preference';
ALTER TYPE pending_item_type ADD VALUE IF NOT EXISTS 'stakeholder';
