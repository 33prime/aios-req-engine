# DB Audit — Supabase Architect Agent Phase 2

Execute an approved audit plan against the live Supabase database. Cross-reference schema, queries, and RLS policies across three expert lenses and produce a scored database health report.

## Arguments
$ARGUMENTS

If a project name or ref is provided, look for its audit plan in `qa-reports/`.
If "quick" is provided, run schema overview + RLS coverage only.
If no arguments, check `qa-reports/` for the most recent db-audit-plan and confirm with the user.
If no plan exists, run the wizard flow inline (combined Phase 1 + Phase 2).

## Steps

### Phase 0: Load Audit Plan

1. **Find the plan:**
   - Search `qa-reports/` for `db-audit-plan-*.md` files
   - If multiple, use the most recent
   - If none found: offer to generate and execute in one pass (run `/db-audit-plan` inline)

2. **Confirm with user:**
   > Ready to execute database audit on [project] in [Quick/Full] mode.
   > [N] tables, [N] queries to analyze.
   > Proceed? (y/n)

### Phase 1: Schema Analysis (Schema Architect Lens)

3. **For each table in the plan**, evaluate:

   a. **Naming**: Does table/column naming follow a consistent convention?
   b. **Data types**: Flag issues per the type quality framework in AGENT.md
   c. **Nullability**: Are non-nullable columns actually enforced?
   d. **Defaults**: Do columns have sensible defaults?
   e. **Relationships**: Are FK constraints defined where expected?
   f. **Missing FKs**: Grep columns named `*_id` without actual FK constraints:
      ```sql
      SELECT c.table_name, c.column_name
      FROM information_schema.columns c
      WHERE c.table_schema = 'public'
        AND c.column_name LIKE '%_id'
        AND NOT EXISTS (
          SELECT 1 FROM information_schema.key_column_usage kcu
          JOIN information_schema.table_constraints tc
            ON kcu.constraint_name = tc.constraint_name
          WHERE tc.constraint_type = 'FOREIGN KEY'
            AND kcu.table_name = c.table_name
            AND kcu.column_name = c.column_name
        );
      ```

4. **Index analysis:**
   - For each index: is it actually used? Check `pg_stat_user_indexes.idx_scan`
   - For each FK column: does it have an index?
   - For each column used in `WHERE` or `ORDER BY` in codebase queries: does it have an index?

5. **Normalization check:**
   - Look for comma-separated values in text columns
   - Look for repeated column groups (col1, col2, col3 → should be a separate table)
   - Look for JSONB columns that should be relational (frequently queried fields inside JSONB)

### Phase 2: Query Analysis (Query Optimizer Lens)

6. **For each query identified in the codebase:**

   a. Construct the equivalent SQL
   b. Run `EXPLAIN ANALYZE` (SELECT queries only)
   c. Check for:
      - Seq Scan on tables >1000 rows → needs index
      - Nested Loop with high actual rows → inefficient join
      - Sort without index → needs index on sort column
      - High "rows removed by filter" → filter not pushed down

7. **N+1 Detection:**
   - For each loop that contains a `.from()` call:
     - Count how many queries it would generate for a typical list size
     - Provide the rewritten batch query using `.in()` or resource embedding

8. **Select * Audit:**
   - For each `.select('*')`:
     - Count how many columns the table has
     - Count how many columns the UI actually uses
     - Calculate wasted bandwidth: `(total_cols - used_cols) / total_cols`

9. **Pagination Audit:**
   - For each list query without `.range()` or `.limit()`:
     - Check table row count
     - If >100 rows: flag as missing pagination

### Phase 3: Security Analysis (Security Auditor Lens)

10. **RLS Coverage:**
    - For each public table:
      - Is RLS enabled? (`rowsecurity = true`)
      - If enabled, which operations have policies? (SELECT, INSERT, UPDATE, DELETE)
      - Does each policy use `auth.uid()` for user isolation?
      - Is the policy permissive or restrictive?

11. **Policy Quality:**
    For each RLS policy:
    ```sql
    SELECT tablename, policyname, cmd, qual, with_check
    FROM pg_policies WHERE schemaname = 'public';
    ```
    - `USING (true)` on non-public table → Critical: open to all authenticated users
    - Missing `WITH CHECK` on INSERT/UPDATE → potential data injection
    - Complex joins in policy → performance concern (document but don't penalize unless slow)

12. **Cross-reference client access:**
    - For each table accessed from client-side code (`.from('table')`):
      - Does it have RLS? If not: **Critical finding**
      - Does the RLS policy match the access pattern? (e.g., query filters by user_id, policy checks auth.uid() = user_id)

13. **Auth bypass vectors:**
    - Check if any tables are accessed without auth context
    - Check if service_role key is used in client-side code (should NEVER be)
    - Grep for `SUPABASE_SERVICE_ROLE_KEY` in frontend code

### Phase 4: Score and Report

14. **Calculate Database Health Score:**

    **Schema Quality (0–100, weight 25%):**
    - Start at 100
    - -5 per naming inconsistency
    - -10 per wrong data type (timestamp vs timestamptz, json vs jsonb)
    - -10 per missing FK on *_id column
    - -5 per missing default on non-nullable column
    - -5 per unnecessary denormalization

    **Index Coverage (0–100, weight 20%):**
    - Start at 100
    - -15 per seq scan on table >10K rows
    - -10 per unindexed FK column on table >1K rows
    - -5 per unindexed sort/filter column used in queries
    - -3 per completely unused index (write overhead for nothing)

    **Query Efficiency (0–100, weight 20%):**
    - Start at 100
    - -15 per N+1 pattern
    - -10 per select * on table with >10 columns
    - -10 per list query without pagination on table >100 rows
    - -5 per client-side filter that could be server-side

    **Security Posture (0–100, weight 25%):**
    - Start at 100
    - -25 per client-accessed table without RLS
    - -15 per table with incomplete policy coverage (missing operation)
    - -10 per `USING (true)` on non-public table
    - -10 per missing auth.uid() in policy on user data table
    - -20 for service_role key in client code

    **Naming & Consistency (0–100, weight 10%):**
    - Start at 100
    - -5 per table not following naming convention
    - -3 per column not following convention
    - -5 per inconsistent FK naming pattern

    **Overall** = weighted average. Grade: A (90+) | B (75–89) | C (60–74) | D (40–59) | F (<40)

15. **Generate the report** using the format in AGENT.md.

16. **Write the report:**
    - Save to `qa-reports/db-audit-[date].md`
    - Print summary (score + grade + top 3 critical findings)
    - If previous audit exists, show delta: "DB Health: 62 → 78 (+16)"

17. **Optional: Record to forge:**
    - If RTG Forge MCP available, call `record_event` with audit results

### Phase 5: Provide Fix Scripts

18. **For each finding, provide the exact SQL fix:**
    - Missing index → `CREATE INDEX ...`
    - Missing RLS → `ALTER TABLE ... ENABLE ROW LEVEL SECURITY; CREATE POLICY ...`
    - Wrong type → `ALTER TABLE ... ALTER COLUMN ... TYPE ...`
    - Missing FK → `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY ...`

19. **Group fixes into a migration script** the user can review and apply:
    ```sql
    -- Database Health Fixes — Generated [date]
    -- Review each statement before running!

    -- CRITICAL: Enable RLS
    ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "users own documents" ON documents
      USING (auth.uid() = user_id)
      WITH CHECK (auth.uid() = user_id);

    -- HIGH: Add missing indexes
    CREATE INDEX idx_events_created_at ON events (created_at DESC);

    -- MEDIUM: Fix data types
    ALTER TABLE user_profiles ALTER COLUMN metadata TYPE jsonb USING metadata::jsonb;
    ```

    Save to `qa-reports/db-fixes-[date].sql`

## Key Principles

- **Read-only during audit** — All fixes are OUTPUT as SQL, never executed. The user reviews and applies.
- **Cross-reference is king** — Schema without query context is useless. RLS without client access context is incomplete. Always triangulate.
- **Table size determines urgency** — A missing index on 50 rows is informational. On 2M rows it's critical.
- **Provide the exact fix** — Don't say "add an index." Say `CREATE INDEX idx_events_created_at ON events (created_at DESC);`
- **Distinguish Supabase tables from app tables** — Don't audit `auth.users`, `storage.objects`, or other Supabase-managed tables.
- **Score conservatively** — When in doubt, give the lower score. Inflated health scores create false confidence.
