-- Migration: 0121_ci_log_action_summary.sql
-- Add action_summary column to client_intelligence_logs for human-readable summaries

ALTER TABLE client_intelligence_logs ADD COLUMN IF NOT EXISTS action_summary TEXT;
