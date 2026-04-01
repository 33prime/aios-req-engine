# DB Audit Plan — Supabase Architect Agent Phase 1

Pull the real schema, RLS policies, and codebase queries from your project, then generate an audit plan for user review.

## Arguments
$ARGUMENTS

If a Supabase project ref or name is provided, target that project.
If "schema" / "queries" / "security" / "full" is provided, scope the audit to that focus area.
If no arguments, auto-detect the Supabase project and default to full audit.

## Steps

### Phase 0: Prerequisites Check

1. **Check Supabase MCP availability:**
   - Try to confirm `execute_sql` is available (either `mcp__claude_ai_Supabase__execute_sql` or `mcp__supabase__execute_sql`)
   - If not available, tell the user:
     ```
     Supabase MCP is required for database audits. You need either:
     - Claude AI Supabase MCP (built-in, enable in settings)
     - Standalone Supabase MCP server

     Add to .claude/settings.local.json:
       "mcp__claude_ai_Supabase__execute_sql",
       "mcp__claude_ai_Supabase__list_tables"
     ```
   - Do NOT proceed without database access.

2. **Identify the Supabase project:**
   - If $ARGUMENTS contains a project ref, use it
   - Otherwise, check `.env` or `.env.local` for `SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_PROJECT_REF`
   - If multiple projects found, ask the user which one
   - Confirm the project with the user before running queries

### Phase 1: Wizard Flow

3. **Audit scope** (from $ARGUMENTS or ask):
   > What kind of database audit do you want?
   > - **Quick**: Schema overview + RLS coverage check (~5 min)
   > - **Full**: All 3 lenses — schema + queries + security (~15 min)
   > - **Focused**: Pick one — schema / queries / security

4. **Specific concerns:**
   > Any specific concerns? (e.g., "queries are slow", "not sure RLS is right", "planning a migration")

### Phase 2: Schema Reconnaissance

5. **Pull the real schema** via `execute_sql`:

   a. Get all public tables with row counts:
   ```sql
   SELECT c.relname AS table_name, c.reltuples::bigint AS row_estimate
   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'public' AND c.relkind = 'r'
   ORDER BY c.reltuples DESC;
   ```

   b. Get all columns with types:
   ```sql
   SELECT table_name, column_name, data_type, is_nullable, column_default
   FROM information_schema.columns
   WHERE table_schema = 'public'
   ORDER BY table_name, ordinal_position;
   ```

   c. Get all foreign keys:
   ```sql
   SELECT
     tc.table_name, kcu.column_name,
     ccu.table_name AS foreign_table_name,
     ccu.column_name AS foreign_column_name,
     rc.delete_rule, rc.update_rule
   FROM information_schema.table_constraints tc
   JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
   JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
   JOIN information_schema.referential_constraints rc ON rc.constraint_name = tc.constraint_name
   WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
   ```

   d. Get all indexes:
   ```sql
   SELECT tablename, indexname, indexdef
   FROM pg_indexes WHERE schemaname = 'public'
   ORDER BY tablename;
   ```

   e. Get RLS status and policies:
   ```sql
   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
   ```
   ```sql
   SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
   FROM pg_policies WHERE schemaname = 'public';
   ```

   f. Get table sizes:
   ```sql
   SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) as total_size
   FROM pg_catalog.pg_statio_user_tables
   ORDER BY pg_total_relation_size(relid) DESC;
   ```

### Phase 3: Codebase Query Scan

6. **Find all Supabase client calls** in the codebase:
   - Grep for `.from(`, `.select(`, `.insert(`, `.update(`, `.delete(`, `.rpc(`
   - For each query found, record: file, line, table, operation, columns selected, filters
   - Identify N+1 patterns: loops containing `.from()` calls
   - Identify `select('*')` usage
   - Identify queries without pagination on list endpoints

7. **Map queries to tables:**
   Create a matrix of which tables are queried, from where, and how:
   ```
   QUERY MAP
   ═════════
   Table: profiles
     SELECT: src/hooks/useProfile.ts:12 — .select('id, name, avatar_url')
     UPDATE: src/api/profile.ts:45 — .update({ name, avatar_url })
     Filters: .eq('id', userId)

   Table: events
     SELECT: src/hooks/useEvents.ts:8 — .select('*')  ← WARNING: select *
     INSERT: src/api/events.ts:23 — .insert({ ... })
     Filters: .gte('created_at', weekAgo).order('created_at', { ascending: false })
     Pagination: NONE ← WARNING: no .range() or .limit()
   ```

### Phase 4: Generate Audit Plan

8. **Build the audit plan** based on schema + queries + RLS:

   For each table, determine what needs auditing:

   ```
   AUDIT PLAN: [Project Name]
   ═══════════════════════════════

   Project:   [name]
   Supabase:  [project ref]
   Tables:    [N public tables]
   Queries:   [N client queries found]
   Mode:      [Quick / Full / Focused]

   ── Schema Map ──
   [table]         [rows]    [cols]  [FKs]  [Indexes]  [RLS]
   profiles        1,234     8       1      3          ON (2 policies)
   events          2,100,000 12      2      1          ON (1 policy)
   documents       456       6       1      0          OFF ← ALERT
   settings        89        4       0      0          OFF
   ...

   ── Audit Focus Areas ──

   Schema Lens:
   - [ ] Check 'events' data types (12 columns, largest table)
   - [ ] Check 'documents' missing indexes (0 indexes, 456 rows)
   - [ ] Verify FK constraints on columns named *_id
   - [ ] Check for json vs jsonb usage
   ...

   Query Lens:
   - [ ] Run EXPLAIN ANALYZE on events query (2.1M rows, filtered by created_at)
   - [ ] Check N+1 pattern in useTeamMembers.ts
   - [ ] Evaluate select('*') usage in useEvents.ts
   ...

   Security Lens:
   - [ ] CRITICAL: 'documents' table has RLS disabled
   - [ ] Check policy completeness on 'events' (only 1 policy — which operations?)
   - [ ] Verify auth.uid() usage in all policies
   ...

   Estimated time: [N] minutes

   Ready to execute? (y/n/adjust)
   ```

9. **Save the plan:**
   - Create `qa-reports/` directory if it doesn't exist
   - Add `qa-reports/` to `.gitignore` if not already there
   - Write plan to `qa-reports/db-audit-plan-[date].md`
   - Tell the user: "Plan saved. Run `/db-audit` to execute."

## Key Principles

- **Read-only always** — Only run SELECT and EXPLAIN ANALYZE. Never modify the database.
- **Real data, not guesses** — Pull the actual schema. Don't assume table structure.
- **Cross-reference queries to schema** — A missing index only matters if a query hits that column.
- **Flag RLS gaps immediately** — Missing RLS on user data is always a critical finding, even in the plan phase.
- **Respect table size** — Prioritize optimization by row count. A 50-row table doesn't need index tuning.
