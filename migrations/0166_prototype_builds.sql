-- Prototype build tracking
-- Tracks automated build pipeline runs (Phase 0 → build → deploy)

CREATE TABLE prototype_builds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prototype_id UUID NOT NULL REFERENCES prototypes(id) ON DELETE CASCADE,
    project_id UUID NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','phase0','planning','rendering','building','merging','deploying','completed','failed')),
    streams_total INT DEFAULT 0,
    streams_completed INT DEFAULT 0,
    tasks_total INT DEFAULT 0,
    tasks_completed INT DEFAULT 0,
    total_tokens_used INT DEFAULT 0,
    total_cost_usd NUMERIC(8,4) DEFAULT 0,
    github_repo_url TEXT,
    netlify_site_id TEXT,
    deploy_url TEXT,
    errors JSONB DEFAULT '[]'::jsonb,
    build_log JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_proto_builds_prototype ON prototype_builds(prototype_id);
CREATE INDEX idx_proto_builds_project ON prototype_builds(project_id);
