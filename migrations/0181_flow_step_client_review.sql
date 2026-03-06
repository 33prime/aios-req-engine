-- Migration 0181: Add client review flags to solution flow steps
-- Allows consultants to flag specific steps for client validation in upcoming calls

ALTER TABLE solution_flow_steps
  ADD COLUMN needs_client_review boolean NOT NULL DEFAULT false,
  ADD COLUMN review_reason text,
  ADD COLUMN review_target_stakeholder_id uuid REFERENCES stakeholders(id),
  ADD COLUMN review_resolved_at timestamptz;

CREATE INDEX idx_flow_steps_needs_review
  ON solution_flow_steps (flow_id) WHERE needs_client_review = true;
