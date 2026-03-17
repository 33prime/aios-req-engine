# Review — Adversarial Code Review

Spawn a fresh-eyes review agent to critique code changes against AIOS-specific quality standards.

## Arguments
$ARGUMENTS

Arguments: empty (uncommitted changes), a file path, `last-commit`, or `pr` (diff vs main).

## Steps

1. **Gather the diff to review:**
   - No argument → `git diff` + `git diff --cached` (all uncommitted changes)
   - File path → `git diff {path}` or read the file if untracked
   - `last-commit` → `git diff HEAD~1`
   - `pr` → `git diff main...HEAD`

   If the diff is empty, inform the user and exit.

2. **Spawn a review agent** using the Agent tool with this prompt:

   > You are a senior code reviewer for the AIOS requirements engineering platform. Review the following diff with fresh eyes. You have NO context about why these changes were made — evaluate them purely on quality.
   >
   > **AIOS-Specific Checklist:**
   > - [ ] No use of `get_llm()` — should use `AsyncAnthropic()` for new chains
   > - [ ] `StateGraph` nodes return dicts, not full state objects
   > - [ ] Anthropic content blocks accessed via `.text` on `TextBlock`
   > - [ ] No hardcoded colors — must use design tokens
   > - [ ] Schemas in `schemas_*.py`, not inline
   > - [ ] No business logic in API route handlers
   > - [ ] No sync Supabase calls in async routes
   > - [ ] `max_tokens` set explicitly for Anthropic calls
   > - [ ] `exclude_unset=True` on Pydantic `.model_dump()` where appropriate
   > - [ ] No service role key exposed to frontend
   > - [ ] Never mention Sonnet/Haiku/Netlify in user-facing build UI
   >
   > **General Checklist:**
   > - [ ] No obvious bugs (null refs, off-by-one, race conditions)
   > - [ ] No security issues (injection, XSS, exposed secrets)
   > - [ ] No N+1 query patterns
   > - [ ] No blocking calls in async functions
   > - [ ] Frozen contracts not modified (entity types, authority map)
   > - [ ] Nothing from don't-resurrect list reintroduced
   > - [ ] New files follow naming conventions
   >
   > **Classify each finding:**
   > - **CRITICAL**: Must fix before commit. Bugs, security issues, broken contracts.
   > - **WARNING**: Should fix. Performance, anti-patterns, gotcha violations.
   > - **NITPICK**: Optional. Style, naming, minor improvements.
   >
   > **Output format:**
   > ```
   > REVIEW: {summary}
   > ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   > {CRITICAL findings, if any}
   > {WARNING findings, if any}
   > {NITPICK findings, if any}
   > ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   > CRITICAL: {count} | WARNING: {count} | NITPICK: {count}
   > Verdict: {BLOCK / PASS WITH WARNINGS / CLEAN}
   > ```

3. **Report the findings** from the agent directly to the user.

4. **If CRITICAL findings exist:**
   - Ask the user if they want you to fix them
   - If yes, fix each CRITICAL finding
   - Re-run the review agent on the updated diff
   - Repeat until no CRITICALs remain

5. **Final output:**
   ```
   REVIEW COMPLETE
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Iterations: {count}
   Final: CRITICAL: {0} | WARNING: {n} | NITPICK: {n}
   Verdict: {PASS WITH WARNINGS / CLEAN}
   → Ready for commit
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```
