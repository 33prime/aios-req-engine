-- Add proof_scenario and success_measurement to outcomes
-- proof_scenario: filmable moment proving the outcome worked
-- success_measurement: observable evidence criterion

ALTER TABLE outcomes ADD COLUMN IF NOT EXISTS proof_scenario TEXT;
ALTER TABLE outcomes ADD COLUMN IF NOT EXISTS success_measurement TEXT;
