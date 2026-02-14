# Prepare Module for RTG Forge

Discover and map files in the current codebase that should become a forge module. This is the discovery step before `/add-module`.

## Steps

1. Ask the user to describe what the module should do in plain language. Example: "stakeholder enrichment — takes a LinkedIn URL or company website and produces an enriched profile with AI synthesis and confidence scores"

2. Based on the description, search the entire codebase for relevant files:
   - Search for related route handlers / API endpoints (FastAPI routers, Next.js API routes, etc.)
   - Search for service/business logic files
   - Search for Pydantic/data models related to the domain
   - Search for LangGraph/LangChain graphs or pipelines
   - Search for database migrations, SQL files, or schema definitions related to the domain
   - Search for configuration or env vars related to the domain
   - Search for tests related to the domain

3. For each discovered file, classify it into the forge contract structure:
   - `router.py` — API endpoints
   - `service.py` — Business logic
   - `models.py` — Request/response schemas
   - `config.py` — Configuration/env vars
   - `graph/` — AI pipeline (LangGraph/LangChain)
   - `migrations/` — SQL/database schema
   - `tests/` — Test files

4. Present a **Module Map** to the user:
   ```
   MODULE MAP: {module_name}
   ━━━━━━━━━━━━━━━━━━━━━━━━━━

   Router (API endpoints):
     → app/api/enrichment.py (lines 45-120)
     → app/api/stakeholders.py (lines 10-85)

   Service (business logic):
     → app/services/enrichment_service.py
     → app/core/enrichment.py

   Models (schemas):
     → app/core/schemas_enrichment.py

   Graph (AI pipeline):
     → app/graphs/enrichment_graph.py

   Migrations (database):
     → migrations/042_enrichment_tables.sql

   Config (env vars):
     → ENRICHMENT_API_KEY (found in app/core/config.py)
     → SCRAPING_PROXY_URL (found in .env.example)

   Dependencies:
     → httpx, langchain-anthropic, langgraph (from imports)
     → supabase, anthropic (external services)

   Tests:
     → tests/test_enrichment.py

   NOT FOUND (will need to be created):
     → No dedicated config.py (settings are inline)
     → No MODULE.md documentation
   ```

5. Ask the user to confirm or adjust the map. They may say "also include X" or "skip Y".

6. Save the final module map as a summary the user can pass to `/add-module`.

## Arguments
Describe the module: $ARGUMENTS
