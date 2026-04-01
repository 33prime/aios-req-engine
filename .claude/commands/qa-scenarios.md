# QA Scenarios — Feature Excellence Audit Phase 1

Generate a scenario plan for a feature by reading the source code, building a feature map, and applying three lenses (QA Engineer, Product Expert, UX Architect). The output is a structured plan the user reviews before execution.

## Arguments
$ARGUMENTS

If a feature name or route is provided, target that feature.
If no arguments, ask the user which feature to audit.

## Steps

### Phase 0: Prerequisites Check

1. **Check Playwright MCP availability:**
   - Try to determine if `mcp__playwright__browser_navigate` is available
   - If not available, warn the user:
     ```
     Playwright MCP is required for feature audits. To set it up:

     1. Add to your .mcp.json:
        {
          "mcpServers": {
            "playwright": {
              "command": "npx",
              "args": ["@anthropic-ai/mcp-playwright@latest"]
            }
          }
        }

     2. Add permissions to .claude/settings.local.json:
        "mcp__playwright__browser_navigate",
        "mcp__playwright__browser_click",
        "mcp__playwright__browser_snapshot",
        "mcp__playwright__browser_take_screenshot",
        "mcp__playwright__browser_fill_form",
        "mcp__playwright__browser_wait_for",
        "mcp__playwright__browser_resize",
        "mcp__playwright__browser_console_messages",
        "mcp__playwright__browser_network_requests",
        "mcp__playwright__browser_evaluate",
        "mcp__playwright__browser_type",
        "mcp__playwright__browser_press_key"
     ```
   - Do NOT proceed without Playwright MCP. It's the foundation.

2. **Check optional MCP servers:**
   - Supabase MCP → enables DB verification (Step 6)
   - Sentry MCP → enables error monitoring (Step 7)
   - Note which are available. Missing optionals mean those audit steps get marked "skipped — no MCP server"

### Phase 1: Wizard Flow

3. **Feature identification** (from $ARGUMENTS or ask):
   > What feature do you want to audit? (route, feature name, or description)

4. **Audit mode:**
   > Quick audit or full audit?
   > - **Quick**: Happy path + UX + Product completeness + DB verification (~10 min, Steps 1/4/5/6)
   > - **Full**: All 7 steps including edge cases, error handling, and performance (~25 min)

5. **Specific concerns:**
   > Any specific concerns? (e.g., "mobile layout is broken", "users report data loss", "we just refactored the API")
   >
   > These will be weighted in the scenario generation.

### Phase 2: Project Detection

6. **Detect framework and project structure:**
   - Read `package.json`, `pyproject.toml`, or equivalent for framework identification
   - Check for Next.js (`app/` or `pages/`), Vite, SvelteKit, Angular, Django, FastAPI, etc.
   - Identify the route convention, component location, API route location
   - Read `CLAUDE.md` if it exists for project-specific conventions

7. **Detect base URL:**
   - Check `package.json` scripts for dev server port
   - Check `.env` or `.env.local` for `NEXT_PUBLIC_URL`, `VITE_API_URL`, `BASE_URL`, etc.
   - Common defaults: `http://localhost:3000` (Next.js), `http://localhost:5173` (Vite), `http://localhost:8000` (FastAPI/Django)
   - If uncertain, ask: "What's the local dev URL?"

8. **Detect test credentials:**
   - Search `.env`, `.env.local`, `.env.test` for: `QA_TEST_EMAIL`, `TEST_USER_EMAIL`, `QA_TEST_PASSWORD`, `TEST_USER_PASSWORD`
   - Search `CLAUDE.md` or `README.md` for test account references
   - Check for seed scripts that create test users
   - If nothing found, ask: "What test credentials should I use? (email + password)"

### Phase 3: Build Feature Map

9. **Trace the feature through the codebase:**

   a. **Find the route** — Search for the feature's URL path in the routing layer using framework-appropriate patterns
   b. **Read the page/route component** — Identify:
      - Imported components (build dependency tree 1 level deep)
      - Data fetching (API calls, server actions, queries)
      - State management (hooks, stores, context)
   c. **Trace API endpoints** — For each API call found:
      - Find the handler function
      - Identify what service/business logic it calls
      - Identify database operations
   d. **Identify DB tables** — From queries, ORM models, or migration files
   e. **Find orphaned capabilities** — Functions in the service layer with no UI trigger, API endpoints with no frontend consumer, DB columns populated but never displayed

10. **Present the feature map:**
    ```
    FEATURE MAP: [Feature Name]
    ════════════════════════════════

    Routes:
      - /primary/route
      - /primary/route/[id]

    Components (N files):
      - path/to/MainComponent.tsx
      - path/to/SubComponent.tsx
      ...

    API Routes / Server Actions (N endpoints):
      - POST /api/feature/create
      - GET /api/feature/list
      - DELETE /api/feature/[id]

    Service Layer:
      - path/to/service.ts
      - Functions: createThing(), listThings(), deleteThing(), updateThing()

    DB Tables:
      - primary_table (N columns)
      - related_table (FK: primary_table.id)

    Available But Not Surfaced:
      - updateThing() exists in service but no edit UI found
      - "description" column in DB but not displayed
      - DELETE endpoint exists but no delete button in UI
    ```

    Ask the user: "Does this feature map look correct? Anything missing or wrong?"
    Wait for confirmation.

### Phase 4: Generate Scenario Plan

11. **Build the scenario matrix** using the three lenses and the feature map:

For each lens, generate scenarios specific to THIS feature:

#### QA Engineer Scenarios

| # | Scenario | Method | What It Tests | Expected Breakpoints |
|---|----------|--------|---------------|---------------------|
| Q1 | Happy path: [specific flow] | Navigate → interact → verify | Core flow works | None expected |
| Q2 | Double-click [primary action] | Click submit twice rapidly | Race condition / duplicate writes | Duplicate DB rows |
| Q3 | Refresh at [critical state] | F5 after action, before confirmation | State persistence | Lost context |
| Q4 | Back button from [result page] | browser_navigate_back | Navigation state | Stale data |
| Q5 | Empty/boundary input in [form] | Submit with empty, max-length, special chars | Validation | Missing validation |
| Q6 | [Feature-specific edge case from concerns] | ... | ... | ... |

#### Product Expert Scenarios

| # | Scenario | What to Check | Finding Type |
|---|----------|--------------|-------------|
| P1 | Empty state | Navigate with no data — what renders? | Missing flow |
| P2 | CRUD coverage | For each service function: is there a UI trigger? | Missing flow |
| P3 | Destructive action guards | Click delete (if exists) — is there a confirmation? | Missing safeguard |
| P4 | Action feedback | Perform each action — does the user get feedback? | Missing feedback |
| P5 | Error recovery | After an error, can the user try again without refreshing? | Missing flow |
| P6 | [Feature-specific from "Available But Not Surfaced"] | ... | ... |

#### UX Architect Scenarios

| # | Scenario | Viewports | What to Evaluate |
|---|----------|-----------|-----------------|
| U1 | Loading states | All 3 | Are there skeletons/spinners during data fetch? |
| U2 | Visual hierarchy | Desktop + Mobile | Is the primary action the most prominent element? |
| U3 | Responsive layout | 390x844 → 768x1024 → 1440x900 | Does layout adapt without breaking? |
| U4 | Interactive feedback | Desktop | Do buttons have hover/active/focus states? |
| U5 | Transitions | Desktop | Are state changes smooth (not jarring)? |
| U6 | [Feature-specific UX concern from user] | ... | ... |

12. **Present the full scenario plan to the user:**
    ```
    SCENARIO PLAN: [Feature Name]
    ═══════════════════════════════

    Mode:      [Quick / Full]
    Scenarios: [N total] (QA: [n], Product: [n], UX: [n])
    Est. time: [N] minutes

    ── QA Engineer Scenarios ──
    [table from above]

    ── Product Expert Scenarios ──
    [table from above]

    ── UX Architect Scenarios ──
    [table from above]

    ── Execution Order ──
    Step 1 (Happy Path):        Q1
    Step 2 (Edge Cases):        Q2, Q3, Q4, Q5, Q6      [Full only]
    Step 3 (Error Handling):    P5, Q6                    [Full only]
    Step 4 (Visual/UX):         U1, U2, U3, U4, U5, U6
    Step 5 (Completeness):      P1, P2, P3, P4, P6
    Step 6 (Data Integrity):    DB checks after Q1, Q2
    Step 7 (Performance):       Network + Console         [Full only]

    Ready to execute? (y/n/adjust)
    If you want to add, remove, or modify scenarios, tell me now.
    ```

13. **Save the plan:**
    - Create `qa-reports/[feature]/` directory if it doesn't exist (e.g. `qa-reports/project-creation/`)
    - Add `qa-reports/` to `.gitignore` if not already there
    - Write the plan to `qa-reports/[feature]/scenarios-[date].md`
    - Project-wide files (onboard profile, design guide) stay at `qa-reports/` root

14. **Suggest next step:**
    - "Plan saved. Ready to execute? Run `/feature-audit [feature]` to launch the browser and test these scenarios."
    - "Want to adjust anything first? I can add, remove, or modify scenarios."
    - If this is the first audit on the project: "After the QA audit, I'd recommend running `/product-audit` and `/ux-audit` on the same flow to get the full picture before fixing anything."

## CRITICAL: This Command ONLY Plans

**Do NOT execute scenarios. Do NOT launch Playwright. Do NOT drive the browser.**

This command produces a scenario plan document. Execution happens in `/feature-audit`. The separation exists so the user can review, adjust, and approve the plan before any browser automation begins.

If the user says "just run it" or "go ahead and test" — save the plan first, THEN tell them to run `/feature-audit` to execute. Do not combine both phases.

## Key Principles

- **Generate from the feature map, not from templates** — Every scenario should reference specific routes, components, and functions from THIS feature
- **The "Available But Not Surfaced" section is gold** — Functions without UI triggers = missing flows. This is the Product Expert's primary signal.
- **Concerns from the user get priority** — If they said "mobile is broken", weight UX scenarios toward mobile viewport
- **Wait for confirmation** — The feature map and scenario plan are both confirmation gates. Never auto-proceed.
- **Quick mode still covers Product** — Quick isn't just QA. Steps 4 (UX) and 5 (Product) are in Quick because they're the highest-signal, lowest-cost checks.
- **Always suggest the full engagement arc** — After saving the plan, mention that QA → Product → UX → Fix is the recommended sequence.
