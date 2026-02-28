-- Deprecate v0 integration columns
-- Columns kept for migration compatibility but no longer written to

COMMENT ON COLUMN prototypes.v0_chat_id IS 'DEPRECATED — v0 integration removed';
COMMENT ON COLUMN prototypes.v0_demo_url IS 'DEPRECATED — v0 integration removed';
COMMENT ON COLUMN prototypes.v0_model IS 'DEPRECATED — v0 integration removed';
