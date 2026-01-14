-- Migration: Add evidence-based tracking to insights table
-- Enhances Red Team insights with evidence chain, reasoning, suggested questions, and confidence

-- Add evidence_chain column (array of Evidence objects with source attribution)
ALTER TABLE insights
ADD COLUMN IF NOT EXISTS evidence_chain JSONB DEFAULT '[]'::jsonb;

-- Add reasoning column (detailed explanation based on evidence)
ALTER TABLE insights
ADD COLUMN IF NOT EXISTS reasoning TEXT;

-- Add suggested_questions column (questions to resolve the gap)
ALTER TABLE insights
ADD COLUMN IF NOT EXISTS suggested_questions JSONB DEFAULT '[]'::jsonb;

-- Add confidence column (0.0-1.0 confidence score)
ALTER TABLE insights
ADD COLUMN IF NOT EXISTS confidence DECIMAL(3,2)
CHECK (confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0));

-- Add comments for documentation
COMMENT ON COLUMN insights.evidence_chain IS 'Array of Evidence objects with source attribution (signals, research, personas, features)';
COMMENT ON COLUMN insights.reasoning IS 'Detailed explanation of why this gap exists based on evidence';
COMMENT ON COLUMN insights.suggested_questions IS 'Array of specific questions that would help resolve this gap';
COMMENT ON COLUMN insights.confidence IS 'Confidence score (0.0-1.0) based on quality and quantity of evidence';

-- Create index on confidence for filtering high-confidence insights
CREATE INDEX IF NOT EXISTS idx_insights_confidence ON insights(confidence)
WHERE confidence IS NOT NULL;
