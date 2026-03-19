-- Chat routing instrumentation: tracks tier classification, latency, and cost per message.
-- Enables data-driven optimization of the 5-tier intent routing system.

CREATE TABLE IF NOT EXISTS chat_routing_log (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    message_id uuid,
    conversation_id uuid,
    raw_message text,
    classified_tier int NOT NULL,
    retrieval_strategy text NOT NULL,
    classifier_source text NOT NULL DEFAULT 'regex',
    intent_type text,
    complexity text,
    latency_ms int,
    tokens_in int DEFAULT 0,
    tokens_out int DEFAULT 0,
    estimated_cost decimal(10, 6) DEFAULT 0,
    compressed_token_count int,
    original_token_count int,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Primary query pattern: dashboard analytics per project over time
CREATE INDEX idx_chat_routing_log_project_created
    ON chat_routing_log (project_id, created_at DESC);

-- Secondary: filter by tier for routing analysis
CREATE INDEX idx_chat_routing_log_tier
    ON chat_routing_log (classified_tier, created_at DESC);

COMMENT ON TABLE chat_routing_log IS 'Per-message telemetry for chat v7 tier routing. Async insert, never blocks response.';
