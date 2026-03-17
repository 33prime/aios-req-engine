# Sentry Debug — Investigate Production Errors

Use Sentry MCP tools to investigate a production error and map it back to local code.

## Arguments
$ARGUMENTS

Arguments can be: a Sentry issue URL, an issue ID, error text to search, or `recent` to check latest issues.

## Steps

1. **Identify the organization and project.** Use `mcp__sentry__find_organizations` and `mcp__sentry__find_projects` to discover the AIOS Sentry project if not already known. Cache these for subsequent calls.

2. **Find the issue:**
   - If argument is a URL or issue ID → `mcp__sentry__get_issue_details` directly
   - If argument is error text → `mcp__sentry__search_issues` with the text as query
   - If argument is `recent` → `mcp__sentry__search_issues` with a broad query, sort by date
   - If no argument → ask the user what to investigate

3. **Gather context** (run these in parallel where possible):
   - `mcp__sentry__search_issue_events` to get recent occurrences
   - `mcp__sentry__get_issue_tag_values` for `environment`, `release`, `user`, `browser` tags
   - If there's a trace ID → `mcp__sentry__get_trace_details`
   - If there are attachments → `mcp__sentry__get_event_attachment`

4. **Map to local code:**
   - Extract file paths and line numbers from the stack trace
   - Use `Read` to open those files locally at the relevant lines
   - Cross-reference with known gotchas:
     - LLM API timeouts (Anthropic, OpenAI)
     - Supabase query failures (missing RLS, bad FK)
     - JSON parsing errors (Anthropic content block is TextBlock, not string)
     - Missing env vars in Railway deployment
   - Check if the error matches any pattern in `docs/context/backend-patterns.md`

5. **Report findings:**

   ```
   SENTRY INVESTIGATION
   Issue: {title} ({issue_id})
   Status: {status} | First seen: {date} | Events: {count}
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Stack Trace (key frames):
     → {file}:{line} — {function}
     → {file}:{line} — {function}

   Root Cause:
     {explanation of what went wrong}

   Local Files:
     → {local_file}:{line} — {what needs to change}

   Known Gotcha Match: {yes/no — which gotcha if yes}

   Suggested Fix:
     {specific code changes or configuration fix}

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

6. **Offer next steps**: fix the code, check if it's already fixed in current branch, or investigate related issues.

## Notes
- Sentry MCP tools require the Sentry integration to be configured
- If MCP tools are unavailable, inform the user and suggest checking `.claude/settings.json` for Sentry configuration
- Never expose API keys, auth tokens, or user PII from Sentry events
