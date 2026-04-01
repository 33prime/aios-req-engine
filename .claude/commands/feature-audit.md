# Feature Audit — Feature Excellence Audit Phase 2

Execute an approved scenario plan against a live browser via Playwright MCP. Drives the browser, verifies DB state, scores the feature across 5 excellence dimensions, and produces an actionable report.

## Arguments
$ARGUMENTS

If a feature name is provided, look for its scenario plan in `qa-reports/`.
If no arguments, check `qa-reports/` for the most recent scenario plan and confirm with the user.
If no scenario plan exists, run the wizard flow inline (combined Phase 1 + Phase 2).

## Steps

### Phase 0: Load Scenario Plan

1. **Find the scenario plan:**
   - Search `qa-reports/[feature]/scenarios-*.md` files (also check `qa-reports/[feature]-scenarios-*.md` for backwards compatibility)
   - If multiple, use the most recent
   - If none found AND $ARGUMENTS provided: inform the user to run `/qa-scenarios [feature]` first, OR offer to generate and execute in one pass
   - If no plan and no arguments: ask "Which feature should I audit?"

2. **Read the plan:**
   - Parse the feature map (routes, components, APIs, DB tables)
   - Parse scenario matrix (QA, Product, UX scenarios)
   - Parse execution order and mode (Quick/Full)
   - Parse base URL and test credentials

3. **Confirm with user:**
   > Ready to execute [N] scenarios against [feature] in [Quick/Full] mode.
   > Base URL: [url]
   > Test user: [email]
   > Estimated time: [N] minutes
   >
   > Proceed? (y/n)

### Phase 1: Setup

4. **Initialize the browser:**
   - `browser_navigate` to the base URL
   - `browser_snapshot` — verify the app is running and accessible
   - If the app isn't running: "The app doesn't appear to be running at [URL]. Please start it and tell me when ready."

5. **Log in (if required):**
   - Follow the login procedure from the scenario plan or auto-detect
   - `browser_navigate` to login page
   - `browser_snapshot` — find email/password fields
   - `browser_fill_form` with test credentials
   - `browser_click` submit button
   - `browser_wait_for` URL change or authenticated state (15s timeout)
   - `browser_snapshot` — confirm logged in
   - If login fails: stop and report the issue. Don't proceed with a broken session.

6. **Initialize tracking:**
   - Start a results accumulator for the report
   - Track: bugs found, missing flows, UX issues, pass/fail per step
   - Track: console errors across the entire session

### Phase 2: Execute Audit Steps

Execute steps based on mode (Quick = 1,4,5,6 | Full = all 7).

#### Step 1: Happy Path Smoke Test

7. Execute scenario Q1 from the plan:
   - Navigate to the feature's primary route
   - `browser_snapshot` — record initial state
   - Execute the primary user action sequence (from the plan)
   - After each significant action: `browser_snapshot` to verify state change
   - `browser_console_messages` — check for errors (apply noise filter)
   - If DB tables identified: `execute_sql` to verify the write

8. **Score Functionality** (initial — refined in later steps):
   - Core flow completes? +40 points
   - No console errors? +20 points
   - DB state correct? +20 points
   - UI reflects action result? +20 points

#### Step 2: Edge Cases & Resilience (Full only)

9. Execute scenarios Q2–Q6 from the plan:
   - For each scenario:
     a. Set up the precondition (navigate to starting state)
     b. Execute the test action (double-click, refresh, back, boundary input)
     c. `browser_snapshot` — check for unexpected state
     d. `browser_console_messages` — check for errors
     e. If applicable: `execute_sql` to check for duplicate/corrupt data
     f. Record: PASS (handled gracefully), FAIL (bug found), or WARNING (degraded but functional)

10. For each failure, capture:
    - Steps to reproduce
    - Expected vs actual behavior
    - `browser_take_screenshot` as evidence
    - Severity: High (data corruption, broken flow), Med (bad UX, workaround exists), Low (cosmetic)

#### Step 3: Error Handling (Full only)

11. Test error scenarios:
    - Invalid form input → submit → check for inline validation
    - Navigate to non-existent sub-route → check for 404 page
    - Note: Network failure simulation may require `browser_evaluate` to intercept fetch. If not feasible, note as "skipped — requires manual testing"

12. Evaluate error messages:
    - Are they specific? ("Email is required" > "Something went wrong")
    - Can the user recover without refreshing?
    - Is the error visually distinct?

#### Step 4: Visual / UX Validation

13. Test across three viewports — for each viewport:
    a. `browser_resize` to viewport dimensions
    b. `browser_navigate` to the feature (or refresh)
    c. `browser_snapshot` — evaluate the UX checklist:
       - Loading states present?
       - No layout shift?
       - Visual hierarchy correct?
       - Touch targets adequate? (mobile only)
       - Text readable?
       - Spacing consistent?
    d. `browser_take_screenshot` — visual evidence for the report
    e. Check hover/focus states (desktop only): `browser_hover` on interactive elements, `browser_snapshot`

14. **Viewports:**
    | Name | Size | Focus |
    |------|------|-------|
    | Mobile (iPhone 14) | 390x844 | Touch targets, text size, horizontal scroll |
    | Tablet (iPad) | 768x1024 | Layout adaptation, gap handling |
    | Desktop | 1440x900 | Content width, visual hierarchy |

15. Score UX Quality and Accessibility based on checklist results.

#### Step 5: Product Completeness

16. Execute Product scenarios P1–P6:
    - **P1 (Empty state):** Navigate to the feature with no data (new user or clear data). `browser_snapshot` — is there a helpful empty state, or just a blank page?
    - **P2 (CRUD coverage):** For each function in the feature map's service layer, check if there's a UI trigger. Navigate the feature and look for create/edit/delete affordances.
    - **P3 (Destructive guards):** If delete or destructive actions exist, trigger them. Is there a confirmation dialog?
    - **P4 (Action feedback):** Perform each user action. After each, `browser_snapshot` — is there a toast, state change, or animation confirming the action?
    - **P5 (Error recovery):** After encountering an error (from Step 3, or simulate one), can the user retry without a full page refresh?
    - **P6 (Feature-specific):** Execute any custom product scenarios from the plan

17. For each missing flow or safeguard:
    - Describe what's missing
    - Reference the code evidence (e.g., "deleteProject() in service.ts line 45 has no UI trigger")
    - Assess priority: Should build / Could build / Nice to have
    - Estimate effort: Small (< 1hr) / Medium (1-4hr) / Large (4hr+)

#### Step 6: Data Integrity

18. For each write action performed during the audit:
    - `execute_sql` to verify the row exists with correct data
    - Check timestamps are reasonable
    - Check FK relationships are intact
    - If deletion was tested: verify cascade behavior and no orphaned records

19. If RLS is relevant (Supabase projects):
    - `execute_sql` to check if cross-user data is accessible
    - Verify the test user can only see their own data

20. If Supabase MCP is not available: note as "skipped — no DB MCP server" and trust UI state with lower confidence.

#### Step 7: Performance & Monitoring (Full only)

21. **Performance:**
    - `browser_network_requests` — compile API response times
    - Flag any request >1s as slow, >2s as critical
    - `browser_evaluate` with `JSON.stringify(performance.getEntriesByType('navigation'))` for page load timing

22. **Console errors (session aggregate):**
    - `browser_console_messages` — compile all errors from entire session
    - Apply noise filter
    - Categorize: application errors, failed API calls, framework warnings

23. **Sentry (if available):**
    - `list_issues` filtered by timeframe of this audit session
    - Check for new errors not present before the audit started
    - Note any existing unresolved errors affecting this feature

### Phase 3: Score and Report

24. **Calculate Excellence Score:**

    For each dimension, start at 0 and add points based on findings:

    **Functionality (0–100, weight 30%):**
    - Happy path completes: +40
    - No console errors: +15
    - DB state correct: +15
    - Edge cases handled (or no edge case bugs): +15
    - Error handling graceful: +15
    - Deduct 10 per High bug, 5 per Med bug

    **Completeness (0–100, weight 25%):**
    - Has empty state: +15
    - Full CRUD coverage: +20
    - Destructive actions guarded: +15
    - Action feedback present: +15
    - Error recovery possible: +10
    - First-time experience: +10
    - Search/filter for lists: +10
    - Keyboard shortcuts: +5
    - Deduct 10 per High missing flow, 5 per Med

    **UX Quality (0–100, weight 20%):**
    - Loading states: +15
    - No layout shift: +15
    - Visual hierarchy clear: +15
    - Hover/active states: +10
    - Transitions smooth: +10
    - Spacing consistent: +10
    - Text readable: +10
    - Responsive (no breakage across viewports): +15
    - Deduct 10 per High UX issue, 5 per Med

    **Accessibility (0–100, weight 10%):**
    - Focus indicators visible: +25
    - Form labels present: +25
    - Touch targets ≥44px: +25
    - Color contrast sufficient: +25
    - Deduct 15 per missing item

    **Resilience (0–100, weight 15%):**
    - Handles network errors: +20
    - Handles invalid input: +20
    - State survives refresh: +20
    - Back button works: +20
    - No data corruption from edge cases: +20
    - Deduct 15 per resilience failure

    **Overall** = (Functionality × 0.30) + (Completeness × 0.25) + (UX × 0.20) + (Accessibility × 0.10) + (Resilience × 0.15)

    **Grade:** A: 90+ | B: 75–89 | C: 60–74 | D: 40–59 | F: <40

25. **Generate the report** using the format defined in the SKILL.md:
    - Feature identification
    - Excellence score with dimension breakdown
    - Feature map summary
    - What works (acknowledge good implementations)
    - Bugs found (with reproduction steps, severity, evidence)
    - Missing flows (with code evidence, priority, effort)
    - UX recommendations (with viewport, current vs better)
    - Step results summary
    - Scenario counts
    - Prioritized next actions

26. **Write the report:**
    - Save to `qa-reports/[feature]/qa-audit-[date].md`
    - Print the summary (score + grade + top 3 findings) to the console
    - If a previous audit exists for this feature, note the score change: "[Feature]: 68 → 75 (+7)"

27. **Record to Forge:**
    - Call `record_audit` with:
      - agent_name: "feature-audit"
      - project_slug: [project slug from CLAUDE.md or ask user]
      - flow_name: [feature/flow name]
      - stage: "qa-audit"
      - score: [overall score]
      - grade: [letter grade]
      - findings: [array of all findings with type, severity, title, description, status, code_ref]
      - skill_usage: [array of skills used during the audit]
      - report_content: [full report markdown]
      - metadata: { scenarios_total, scenarios_passed, scenarios_deferred, mode }
    - If `record_audit` is not available (MCP not configured), warn the user: "Forge MCP not configured — audit results not recorded. Add rtg-forge to .mcp.json to enable tracking."
    - This is NOT optional. Audit results must be tracked for score progression and finding resolution.

### Phase 4: Wrap-Up & Suggest Next Step

28. `browser_close` — close the browser session
29. Remind the user: "Report saved to `qa-reports/[feature]/qa-audit-[date].md`"
30. **Suggest next step based on findings:**

    Choose the most appropriate recommendation:

    a. **If blocking bugs found:**
       "I found [N] blocking bugs. These need fixing before deeper analysis. Want me to generate a remediation plan for just the blockers?"

    b. **If clean or only non-blocking issues:**
       "QA audit passed clean. Before fixing anything, I'd recommend running `/product-audit [feature]` — it evaluates whether the flow is efficient, not just functional. If the flow needs restructuring, fixing UX bugs now would be wasted work."

    c. **If Product audit already done:**
       "QA and Product audits complete. Run `/ux-audit [feature]` to evaluate interaction consistency and generate a design guide. Then we'll have the full picture for remediation."

    d. **If all three audits complete:**
       "All three audits done. Want me to generate a consolidated remediation plan? I'll prioritize across all findings — QA, Product, and UX — so you fix once, fix right."

    e. **If deferred scenarios exist:**
       "I deferred [N] edge case scenarios ([list]). Want me to run those specifically? The double-click and close-during-build scenarios are where real bugs tend to hide."

    f. **If this is a re-audit with score improvements and all stages have been re-run:**
       "All stages re-audited with improvements. Want me to generate an engagement summary? It'll consolidate everything — score progression, what was fixed, what remains, and context for the next audit run."

    Always end with: "What would you like to do next?"

## Key Principles

- **Never proceed with a broken browser or failed login** — Stop and tell the user. A broken session produces garbage data.
- **Snapshot for assertions, screenshot for evidence** — Never rely solely on screenshots to determine pass/fail.
- **Score conservatively** — When in doubt, give the lower score. Inflated scores erode trust.
- **Acknowledge good work** — The "What Works" section is mandatory. An all-negative report gets ignored.
- **Evidence everything** — Every bug gets reproduction steps. Every missing flow gets a code reference. Every UX issue gets a viewport.
- **Prioritize the next actions** — The report should end with "here's what to fix first." Not just findings, but a plan.
- **Track improvement** — If prior audit exists, show the delta. This motivates continued investment.
- **Always suggest next step** — Never end with just a report. Recommend what comes next and why. The consultant always has an opinion.
