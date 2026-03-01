-- Add rich asset and context fields to solution flow steps
-- for prototype planning agent consumption

-- Step-level image (user-uploaded screenshot or reference image)
ALTER TABLE solution_flow_steps
ADD COLUMN IF NOT EXISTS image_url TEXT,
ADD COLUMN IF NOT EXISTS image_caption TEXT;

-- Structured data model for this step (explicit entity shapes)
ALTER TABLE solution_flow_steps
ADD COLUMN IF NOT EXISTS data_model JSONB DEFAULT '[]'::jsonb;
-- Array of: {entity: "Order", fields: [{name: "total", type: "currency"}, ...]}

-- Freeform "how should this feel" description from user
ALTER TABLE solution_flow_steps
ADD COLUMN IF NOT EXISTS feel_description TEXT;
