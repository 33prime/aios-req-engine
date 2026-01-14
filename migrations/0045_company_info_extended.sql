-- Extend company_info with additional fields for Company Information card

ALTER TABLE company_info
ADD COLUMN IF NOT EXISTS revenue TEXT,           -- e.g., "$1M-$10M", "Not specified"
ADD COLUMN IF NOT EXISTS address TEXT,           -- Full address
ADD COLUMN IF NOT EXISTS location TEXT,          -- Country/region e.g., "USA", "Europe"
ADD COLUMN IF NOT EXISTS employee_count TEXT;    -- e.g., "51-250 employees"

-- Add indexes for common queries
CREATE INDEX IF NOT EXISTS idx_company_info_location ON company_info(location) WHERE location IS NOT NULL;
