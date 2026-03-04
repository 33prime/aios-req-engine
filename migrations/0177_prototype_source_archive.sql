-- Add storage archive path to prototype builds
ALTER TABLE prototype_builds
  ADD COLUMN IF NOT EXISTS storage_archive_path TEXT;

-- Create the prototype-sources storage bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES ('prototype-sources', 'prototype-sources', false, 10485760)
ON CONFLICT (id) DO NOTHING;
