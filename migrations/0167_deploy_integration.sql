-- Deployment integration columns for prototypes

ALTER TABLE prototypes ADD COLUMN IF NOT EXISTS netlify_site_id TEXT;
ALTER TABLE prototypes ADD COLUMN IF NOT EXISTS netlify_site_url TEXT;
