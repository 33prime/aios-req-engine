-- Migration: Add client_completed_at to prototype_sessions
-- Tracks when a client finishes their review

ALTER TABLE prototype_sessions
  ADD COLUMN IF NOT EXISTS client_completed_at TIMESTAMPTZ;
