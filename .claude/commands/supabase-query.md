# Supabase Query — Common Database Queries

Run preset or ad-hoc database queries against the AIOS Supabase instance via MCP tools.

## Arguments
$ARGUMENTS

Arguments: `health`, `entities`, `pipeline`, `chat`, `signals`, or a natural language query description.

## Safety Rules
- **NEVER** run DDL (CREATE, ALTER, DROP, TRUNCATE) through this command
- **ALWAYS** confirm with the user before running any mutation (INSERT, UPDATE, DELETE)
- Use the Supabase project ID: `fveyvialmiohrwvnmcip`
- All queries go through `mcp__supabase__execute_sql`

## Preset Queries

### `health` — System health overview
```sql
SELECT 'projects' as table_name, count(*) as row_count FROM projects
UNION ALL SELECT 'features', count(*) FROM features
UNION ALL SELECT 'personas', count(*) FROM personas
UNION ALL SELECT 'signals', count(*) FROM signals
UNION ALL SELECT 'conversations', count(*) FROM conversations
UNION ALL SELECT 'vp_steps', count(*) FROM vp_steps
UNION ALL SELECT 'prd_sections', count(*) FROM prd_sections
UNION ALL SELECT 'stakeholders', count(*) FROM stakeholders
UNION ALL SELECT 'solution_flow_steps', count(*) FROM solution_flow_steps
ORDER BY row_count DESC;
```

### `entities` — Confirmation status breakdown
```sql
SELECT
  'features' as entity_type,
  confirmation_status,
  count(*) as count
FROM features GROUP BY confirmation_status
UNION ALL
SELECT 'personas', confirmation_status, count(*) FROM personas GROUP BY confirmation_status
UNION ALL
SELECT 'stakeholders', confirmation_status, count(*) FROM stakeholders GROUP BY confirmation_status
ORDER BY entity_type, confirmation_status;
```

### `pipeline` — Recent signal processing
```sql
SELECT id, signal_type, status, created_at, updated_at
FROM signals
ORDER BY created_at DESC
LIMIT 20;
```

### `chat` — Chat routing stats (last 24h, requires migration 0187)
```sql
SELECT
  intent_tier,
  count(*) as count,
  round(avg(latency_ms)) as avg_latency_ms,
  round(avg(total_tokens)) as avg_tokens
FROM chat_routing_log
WHERE created_at > now() - interval '24 hours'
GROUP BY intent_tier
ORDER BY intent_tier;
```

### `signals` — Signal type distribution
```sql
SELECT
  signal_type,
  count(*) as count,
  max(created_at) as latest
FROM signals
GROUP BY signal_type
ORDER BY count DESC;
```

## Custom Queries

If the argument doesn't match a preset:
1. Interpret the natural language description
2. Generate a SELECT-only SQL query
3. Show the SQL to the user and ask for confirmation before executing
4. Execute via `mcp__supabase__execute_sql` with project ID `fveyvialmiohrwvnmcip`
5. Format and present results

## Output Format
```
SUPABASE QUERY: {preset_name or "Custom"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{formatted table of results}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rows: {count} | Executed: {timestamp}
```
