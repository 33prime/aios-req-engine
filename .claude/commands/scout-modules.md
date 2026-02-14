# Scout Modules in Codebase

Scan the current codebase and identify features that could be extracted as RTG Forge modules. This is the "what should we extract?" step — run it before `/prepare-module`.

## Steps

1. **Scan the project structure.** Map out the codebase to understand how it's organized:
   - Look at the top-level directory structure
   - Identify the API layer (routers, endpoints, route handlers)
   - Identify the service/business logic layer
   - Identify database schemas, migrations, models
   - Identify AI/ML pipelines (LangGraph, LangChain, etc.)
   - Note the frontend structure if it exists

2. **Identify module candidates.** A good module candidate is a self-contained feature that:
   - Has its own API endpoints (at least one route prefix like `/api/v1/something`)
   - Has business logic that could work independently of the rest of the app
   - Has its own database tables or could have them
   - Solves a problem that other projects would also need to solve
   - Could be described in one sentence ("enriches stakeholder profiles from public data sources")

   Look for these patterns:
   - Route files organized by domain (e.g., `enrichment.py`, `invoices.py`, `notifications.py`)
   - Service classes or modules with clear boundaries
   - Groups of related database tables
   - AI pipelines/graphs that serve a specific purpose
   - Features with their own config/env vars

3. **Score each candidate.** For every potential module, assess:

   | Factor | Score | Criteria |
   |--------|-------|----------|
   | **Reusability** | 1-5 | Would other projects need this exact feature? |
   | **Isolation** | 1-5 | How cleanly can this be separated from the rest of the codebase? |
   | **Complexity** | low/med/high | How much logic does it contain? (Higher = more valuable to extract) |
   | **Forge-readiness** | 1-5 | How close is the code to the six-file structure already? |

4. **Present the Module Scout Report:**

   ```
   MODULE SCOUT REPORT
   Project: {project_name}
   Scanned: {date}
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   Found {N} module candidates:

   1. STAKEHOLDER ENRICHMENT          Score: 18/20
      "Multi-source profile enrichment with AI synthesis"
      Reusability: 5 | Isolation: 5 | Complexity: high | Forge-ready: 3
      Key files: app/services/enrichment.py, app/api/enrichment.py
      Tables: enrichment_profiles, enrichment_sources
      Missing: dedicated config.py, MODULE.md
      → Ready for /prepare-module

   2. MAGIC LINK AUTH                  Score: 15/20
      "Passwordless authentication via email magic links"
      Reusability: 5 | Isolation: 4 | Complexity: medium | Forge-ready: 2
      Key files: app/auth/magic_link.py, app/api/auth.py
      Tables: magic_links, sessions
      Missing: service.py separation, models.py
      → Needs refactoring before extraction

   3. NOTIFICATION ENGINE              Score: 12/20
      "Multi-channel notifications (email, Slack, in-app)"
      Reusability: 4 | Isolation: 3 | Complexity: medium | Forge-ready: 1
      Key files: app/services/notifications.py (tightly coupled)
      Tables: notifications, notification_preferences
      Missing: router separation, config isolation
      → Significant refactoring needed

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   RECOMMENDATION: Start with #1 (Stakeholder Enrichment).
   Highest score, most isolated, most reusable.
   Run: /prepare-module stakeholder enrichment pipeline
   ```

5. **For each candidate, note:**
   - Which files map to which forge contract files (router.py, service.py, models.py, etc.)
   - What's missing and would need to be created
   - What refactoring would be needed to isolate the module
   - Whether a `frontend/` directory makes sense (does it have UI components?)

6. **Ask the user which modules they want to pursue.** They may want to extract the top scorer immediately, or flag several for future extraction.

## What Makes a BAD Module Candidate

Skip features that are:
- **Too small** — A single utility function is a skill, not a module
- **Too coupled** — If extracting it would require pulling half the app, it's not isolated enough yet
- **Too generic** — CRUD wrappers around a single table with no business logic aren't worth the contract overhead
- **Too project-specific** — If only this exact project would ever need it, it's not reusable

## Arguments
Project description (optional): $ARGUMENTS
