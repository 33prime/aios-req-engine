-- Migration: Extend field_attributions entity_type constraint
-- Adds business_driver, stakeholder, competitor_ref, risk to allowed entity types

-- Drop existing constraint
ALTER TABLE field_attributions
DROP CONSTRAINT IF EXISTS field_attributions_entity_type_check;

-- Add updated constraint with all entity types
ALTER TABLE field_attributions
ADD CONSTRAINT field_attributions_entity_type_check
CHECK (entity_type IN (
    -- Product entities
    'feature',
    'persona',
    'vp_step',
    'prd_section',
    -- Strategic foundation entities
    'business_driver',
    'stakeholder',
    'competitor_ref',
    'risk'
));

COMMENT ON CONSTRAINT field_attributions_entity_type_check ON field_attributions IS
    'Supported entity types for field-level attribution tracking';
