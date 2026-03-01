-- Add 'bundling' status for npm install + build step between building and deploying
ALTER TABLE prototype_builds DROP CONSTRAINT IF EXISTS prototype_builds_status_check;
ALTER TABLE prototype_builds ADD CONSTRAINT prototype_builds_status_check
  CHECK (status IN ('pending','phase0','planning','rendering','building','bundling','merging','deploying','completed','failed'))
  NOT VALID;
ALTER TABLE prototype_builds VALIDATE CONSTRAINT prototype_builds_status_check;
