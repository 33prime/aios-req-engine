-- Add title column to business_drivers for compact row display
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS title TEXT;

-- Backfill: first sentence or first 80 chars of description
UPDATE business_drivers
SET title = CASE
    WHEN position('.' IN description) > 0 AND position('.' IN description) <= 80
    THEN left(description, position('.' IN description))
    ELSE left(description, 80)
END
WHERE title IS NULL AND description IS NOT NULL;
