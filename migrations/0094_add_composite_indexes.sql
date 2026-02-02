-- =============================================================================
-- Add composite indexes for common query patterns
-- =============================================================================

-- Signal chunks: frequently queried by signal_id with ORDER BY created_at DESC
-- Used by get_research_chunks() and other chunk listing endpoints
CREATE INDEX IF NOT EXISTS idx_signal_chunks_signal_created
  ON signal_chunks(signal_id, created_at DESC);

-- Memory edges: frequently queried by to_node_id + edge_type
-- Used by get_memory_visualization() to count supports/contradicts per belief
CREATE INDEX IF NOT EXISTS idx_memory_edges_to_type
  ON memory_edges(to_node_id, edge_type);
