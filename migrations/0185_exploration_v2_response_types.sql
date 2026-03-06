-- Expand client_assumption_responses to support 3-way actions (great/refine/question)
-- in addition to legacy agree/disagree.

ALTER TABLE client_assumption_responses
  DROP CONSTRAINT IF EXISTS client_assumption_responses_response_check;

ALTER TABLE client_assumption_responses
  ADD CONSTRAINT client_assumption_responses_response_check
  CHECK (response IN ('agree', 'disagree', 'great', 'refine', 'question'));
