# AIOS Architecture Questionnaire — Answers from Codebase Audit

---

## Section 1: Tab Architecture & Data Sources

### 1.1 BRD View Tab

**What data does the BRD View tab render? Which tables/RPCs?**

- **Answer**: The BRD View renders data from 13+ tables via `GET /projects/{id}/workspace/brd`. Phase 1 runs 14 parallel DB queries: projects, company_info, business_drivers, personas, vp_steps, features, constraints, data_entities, stakeholders, competitor_references, pending_items, workflow_pairs, solution_flow, signal_impact, gap_clusters. Phase 2 resolves data_entity→workflow links. Phase 3 does in-memory aggregation (MoSCoW grouping, driver type splitting, relatability scoring).
- **Source**: `app/api/workspace_brd.py` — `get_brd_workspace()` endpoint
- **Confidence**: High

**How are entities grouped/organized?**

- **Answer**: Each entity type has its own section with type-specific grouping:
  - **Features**: MoSCoW priority groups (must_have, should_have, could_have, out_of_scope). Drag-drop between groups. Capped at 30 total.
  - **Business Drivers**: Split by driver_type — pain_points, goals, success_metrics. Each capped at 8, sorted by relatability_score descending (confirmed first).
  - **Personas**: Canvas role toggle (Primary/Secondary/None). Shows linked driver count + workflow count.
  - **Workflows**: VP Step Pairs (current → future). ROI summary per pair.
  - **Constraints**: Simple list, no sub-grouping.
  - **Data Entities**: Entity definitions with fields (hidden from BRD view but still fetched).
  - **Stakeholders**: Stakeholder list (hidden from BRD view but still fetched).
- **Source**: `apps/workbench/components/workspace/brd/BRDCanvas.tsx`, `app/api/workspace_brd.py`
- **Confidence**: High

**Is there a narrative or summary view?**

- **Answer**: Yes, multiple:
  - **Vision** — editable narrative field in BusinessContextSection
  - **Background** — editable narrative with problem provenance
  - **Intelligence Section** — score ring (0-100%), stage journey (discovery→validation→prototype→build), synthesized next actions (Haiku-generated narrative via `synthesize_intelligence()`)
  - **Completeness Report** — per-section coverage percentages
  - **No single "BRD narrative document"** — it's section-based, not a single document view
- **Source**: `apps/workbench/components/workspace/brd/sections/BusinessContextSection.tsx`, `apps/workbench/components/workspace/brd/sections/IntelligenceSection.tsx`
- **Confidence**: High

**Where does business_drivers data appear?**

- **Answer**: In the **BusinessContextSection** under three containers: Pain Points, Goals, Success Metrics. Each driver type renders type-specific fields:
  - Pain: severity, business_impact, affected_users, frequency
  - Goal: success_criteria, owner, goal_timeframe, dependencies
  - KPI: baseline_value, target_value, measurement_method, monetary fields
  - All types: associated persona names (explicit links + fallback text-overlap), relatability score (for sorting), confirmation status
- **Source**: `apps/workbench/components/workspace/brd/sections/BusinessContextSection.tsx`
- **Confidence**: High
- **Notes**: Business drivers are significantly richer than other entity types — 50+ columns. They already encode before/after states (baseline→target) and observable criteria.

### 1.2 Solution Flow Tab

**What is the solution_flow_steps table schema?**

- **Answer**: Extensive — ~35 columns across 7 migrations (0144 through 0189). Key columns:
  - **Identity**: id, flow_id (FK→solution_flows), project_id, step_index, phase (entry/core_experience/output/admin)
  - **Content**: title, goal, actors (TEXT[]), story_headline, mock_data_narrative, background_narrative, feel_description
  - **Data**: information_fields (JSONB [{name, type, mock_value, confidence}]), data_model (JSONB)
  - **Outcomes**: success_criteria (JSONB), pain_points_addressed (JSONB [{text, persona}]), goals_addressed (JSONB), user_actions (JSONB), human_value_statement
  - **Questions**: open_questions (JSONB [{question, context, status, resolved_answer, escalated_to}])
  - **UI**: implied_pattern (dashboard/table/form/wizard/card), image_url, image_caption
  - **AI**: ai_config (JSONB {role, agent_name, agent_type, behaviors, guardrails, fallback, automation_estimate, ...})
  - **Entity Links**: linked_workflow_ids (UUID[]), linked_feature_ids (UUID[]), linked_data_entity_ids (UUID[]), evidence_ids (UUID[])
  - **Versioning**: generation_version, preserved_from_version, confirmation_status
  - **Search**: embedding vector(1536)
- **Source**: `migrations/0144_solution_flow.sql` through `migrations/0189_solution_flow_step_ux_fields.sql`
- **Confidence**: High

**How are solution flow steps created?**

- **Answer**: Via the Solution Flow v4 generation pipeline — a 6-phase process:
  1. **Phase 0**: Intelligence Assembly — 17 parallel DB queries (7 BRD + 10 intelligence sources)
  2. **Phase 1**: Insight Synthesis — Sonnet analyzes intelligence, surfaces hidden connections, tensions, missing capabilities
  3. **Phase 2**: Flow Architecture — Sonnet designs 6-16 step skeletons with entity links, horizons, data flow
  4. **Phase 3**: Parallel Step Builders — Haiku ×N fills in information_fields, mock_data_narrative, ai_config, etc.
  5. **Phase 4**: Coherence QA — Sonnet validates data continuity, coverage, consistency
  6. **Phase 5**: Persistence — delete ai_generated steps, preserve confirmed, reindex, embed
  - Total: ~22s, ~$0.30 per generation
- **Source**: `app/chains/solution_flow_v4/__init__.py`, `architecture.py`, `builders.py`, `coherence.py`
- **Confidence**: High

**How are steps linked to entities?**

- **Answer**: **Direct UUID arrays on the step**, NOT junction tables:
  - `linked_workflow_ids UUID[] DEFAULT '{}'`
  - `linked_feature_ids UUID[] DEFAULT '{}'`
  - `linked_data_entity_ids UUID[] DEFAULT '{}'`
  - `evidence_ids UUID[] DEFAULT '{}'`
  - The architecture phase (Sonnet) assigns entity IDs to each step skeleton. Coherence QA validates coverage (every must_have feature in at least one step).
- **Source**: `migrations/0144_solution_flow.sql`, `app/chains/solution_flow_v4/architecture.py`
- **Confidence**: High
- **Notes**: entity_dependencies is NOT used for step-entity linking. It tracks general graph relationships separately.

**What is mock_data_narrative?**

- **Answer**: A 3-5 sentence user story describing what the persona experiences on this screen. Uses specific names, numbers, dates from the project. Generated by Phase 3 (Haiku builders) with focused per-step context.
  - Example: "Sarah opens her morning dashboard. 247 new items. AI pre-classified 89% with confidence above 90%. She reviews 27 exceptions in 4 minutes."
  - Stored on `solution_flow_steps.mock_data_narrative`
  - Separate from `background_narrative` which is a deterministic provenance text (zero LLM cost)
- **Source**: `app/chains/solution_flow_v4/builders.py`
- **Confidence**: High

**Is there a concept of "pages" or "screens" distinct from solution flow steps?**

- **Answer**: **No.** Solution flow steps ARE the screens/surfaces. Each step represents a discrete user interaction point characterized by `implied_pattern` (dashboard, table, form, wizard, card). There is no separate "page" or "screen" entity in the database. The `story_headline` captures the key moment on each screen. The `user_actions` lists what the user can do.
- **Source**: Searched for "surface", "page", "screen" tables — none found. Solution flow steps serve this role.
- **Confidence**: High
- **Notes**: This is critical for the Outcomes system — outcomes will "compile to surfaces" which ARE solution flow steps.

### 1.3 Data & AI Tab (Intelligence Layer)

**What tables power the Intelligence Layer?**

- **Answer**: 5 tables:
  1. `agents` — 47 columns: identity, autonomy, partner, data access, pipeline deps, maturity, technique, rhythm, narratives, chat, sample I/O, processing steps, cascade effects, validation, confidence tiers
  2. `agent_tools` — per-agent tool definitions with reliability scores
  3. `agent_chat_messages` — conversation history (role: user/agent/system)
  4. `agent_executions` — "See in Action" runs with validation verdicts
  5. `intelligence_architecture` — JSONB storing 4 quadrants per project (knowledge_systems, scoring_models, decision_logic, ai_capabilities)
- **Source**: `migrations/0190_intelligence_layer.sql`, `migrations/0191_agent_hierarchy.sql`, `migrations/0192_intelligence_architecture.sql`
- **Confidence**: High

**Where does each quadrant's data come from?**

- **Answer**: The 4 quadrants are stored in `intelligence_architecture.quadrants` as a single JSONB object per project. Each quadrant has `items[]` (name, description, powers, status) and `open_questions[]`. This is generated by `build_intelligence_layer.py` — Sonnet plans the hierarchy from solution_flow_steps with ai_config, then categorizes into quadrants. The items are NOT individual DB rows — they're JSONB arrays within the quadrant object.
  - **Knowledge Systems** = data assets, rule sets
  - **Scoring Models** = metrics, rankings
  - **Decision Logic** = routing, gating
  - **AI Capabilities** = LLM/ML usage
- **Source**: `migrations/0192_intelligence_architecture.sql`, `app/chains/build_intelligence_layer.py`
- **Confidence**: High
- **Notes**: No separate tables for knowledge_systems, scoring_models, or decision_rules. They're all JSONB within intelligence_architecture.

**How is the Intelligence Profile bar computed?**

- **Answer**: Computed at **frontend render time**, not in the API. The backend returns raw quadrant data (item counts per quadrant). The frontend normalizes counts into percentages (e.g., 19% AI / 37% Rules / 44% Data). No backend function computes this.
- **Source**: `app/api/workspace_intel_layer.py` returns `IntelligenceLayerResponse` with counts, not percentages
- **Confidence**: Medium (inferred from API shape — didn't find the exact frontend calculation)

**How are agents derived from solution_flow_steps?**

- **Answer**: Via `build_intelligence_layer.py`:
  1. Load all solution_flow_steps with `ai_config.role` set
  2. Phase 1 (Sonnet): Plans hierarchy — creates orchestrators + sub-agents from AI-capable steps
  3. Phase 2 (Haiku): Fills in tool definitions, data sources, sample I/O per sub-agent
  4. Phase 3: Persists — creates agents with `source_step_id` pointing back to the originating step, sub-agents with `parent_agent_id` to orchestrator
- **Source**: `app/chains/build_intelligence_layer.py`, lines 489-626
- **Confidence**: High

---

## Section 2: Chat Assistant Behavior Per Tab

### 2.1 Chat Modes

**How does chat_modes.py work?**

- **Answer**: Defines 13 `ChatMode` configurations keyed by page_context string. Each mode specifies: tools (list), retrieval_strategy ("none"/"light"/"full"), intelligence loads (forge, horizon, confidence, warm_memory), max_tokens, thinking_eligible, primary_entity_type. Function `get_chat_mode(page_context)` returns the mode from a dict lookup, with a default fallback.
- **Source**: `app/context/chat_modes.py`
- **Confidence**: High

**Per-tab tool availability:**

| Tab | Page Context | Tools | Retrieval | Intelligence Loads |
|-----|-------------|-------|-----------|-------------------|
| BRD View (features) | `brd:features` | search, write, process, suggest_actions, client_portal | light | Forge YES, Confidence YES |
| BRD View (personas) | `brd:personas` | search, write, process, suggest_actions, client_portal | light | Confidence YES |
| BRD View (drivers) | `brd:business-drivers` | search, write, process, suggest_actions, client_portal | light | Confidence YES |
| Solution Flow | `brd:solution-flow` | search, write, solution_flow, suggest_actions | light | Horizon YES, Confidence YES, **Thinking enabled** |
| Data & AI | `data-ai` | suggest_actions | none | Nothing loaded |
| Overview | `overview` | suggest_actions | none | Nothing loaded |

- **Source**: `app/context/chat_modes.py`
- **Confidence**: High
- **Notes**: Data & AI tab is extremely lightweight — suggest_actions only, no retrieval. Solution Flow is the most capable — thinking enabled, horizon intelligence loaded.

**Does chat mode affect retrieval scope?**

- **Answer**: Yes, indirectly. The `primary_entity_type` field on ChatMode filters next actions to that entity type. The retrieval_strategy ("none"/"light"/"full") determines whether retrieval runs at all and with what parameters. The cognitive frame (compiled from page_context) shapes `graph_depth`, `apply_recency`, and `boost_confirmed` via `compile_retrieval_plan()`.
- **Source**: `app/context/prompt_compiler.py` — `compile_retrieval_plan()`
- **Confidence**: High

**Does chat mode affect cognitive frame?**

- **Answer**: Yes. The page_context maps to a phase (brd/solution_flow/prototype) which drives CognitiveMode selection. Solution Flow page → REFINE or EXECUTE mode. BRD page → DISCOVER or SYNTHESIZE mode. The page_context also feeds PAGE_GUIDANCE (specific instruction text per page) into the dynamic block.
- **Source**: `app/context/prompt_compiler.py` — `compile_cognitive_frame()`
- **Confidence**: High

### 2.2 Chat as Signal Source

**Simple operations (e.g., "create a feature called X"):**

- **Answer**: Goes through the **fast path** — `try_fast_path()` in `chat_fast_path.py` matches regex patterns like `^(add|create)\s+(feature|persona|...)\s+called\s+"(.+)"$`. Returns a `FastPathResult` with a tool call dict. The chat handler then executes `execute_tool("write", ...)` which routes to `_create_entity()` — a **direct DB insert**. No signal record, no pipeline, no embeddings, no linking. Confirmation status pre-set to `confirmed_consultant`.
- **Source**: `app/core/chat_fast_path.py` lines 45-117, `app/chains/chat_tools/tools_entity_crud.py`
- **Confidence**: High
- **Notes**: This is a significant gap — fast-path entities don't get embedded, linked, or versioned. They bypass all intelligence.

**Complex operations (save-as-signal):**

- **Answer**: `POST /save-as-signal` creates a synthetic signal record (signal_type="chat", source_type="workspace_chat"), creates one signal_chunk, then calls `process_signal_v2(signal_id, project_id, run_id)` — the **full 8-node pipeline**: load → triage → context → extract → dedup → score → apply → summary → memory. Full cascades fire.
- **Source**: `app/api/chat_signals.py` lines 57-144
- **Confidence**: High

**Boundary between pipeline vs direct:**

- **Answer**: Clear boundary:
  - **Direct** (no pipeline): Fast path regex matches ("add feature called X"), write tool create/update/delete actions, confirmation status changes
  - **Pipeline** (full V2): save-as-signal, document uploads, email ingestion, any signal-based input
  - The write tool's create action does NOT create a signal record — it's a direct insert
- **Source**: `app/core/chat_fast_path.py`, `app/chains/chat_tools/dispatcher.py`
- **Confidence**: High

---

## Section 3: Entity Lifecycle & Cascades

### 3.1 Entity Creation Flow (Full Trace)

**1. Signal arrives → chunked:**
- Character-based sliding window: 1200 chars, 120 char overlap
- Each chunk gets JSONB metadata (confirmation_status, authority, section_type, meta_tags)
- Chunks embedded via OpenAI text-embedding-3-small (1536 dims)
- **Source**: `app/core/chunking.py`

**2. Context snapshot (5 layers):**
- Layer 1: Entity inventory (IDs, names, statuses for 9 entity types, capped 20 per type)
- Layer 2: Memory beliefs + insights + open questions
- Layer 3: Structural gaps (from project phase)
- Layer 4: Extraction briefing (Pulse Engine deterministic rules, Haiku fallback ~$0.002)
- Layer 5: Entity relationship hints (graph neighborhoods of top entities)
- **Source**: `app/core/context_snapshot.py` lines 25-52, 55-136

**3. Extraction prompt structure:**
- 5-layer system prompt: static rules (cached) → strategy block (per signal type, cached) → context template (dynamic) → extraction briefing (cached or dynamic) → chunk-specific rules
- Model: Sonnet 4.6 for single-call (<2 chunks), Haiku 4.5 for parallel (2+ chunks)
- Forced tool_use: `submit_entity_patches`
- Temperature: 0.1, max_tokens: 16000/8000
- **Source**: `app/chains/extract_entity_patches.py` lines 380-482

**4. Dedup tiers:**
- Tier 1: Exact normalized name match (score 1.0)
- Tier 2: Fuzzy token_set_ratio via RapidFuzz (per-type thresholds, e.g., feature: 0.82)
- Tier 2.5: Cohere rerank for ambiguous zone (threshold 0.8)
- Tier 3: Embedding cosine similarity (per-type thresholds, e.g., feature: 0.88)
- **Source**: `app/core/entity_dedup.py` — `DEDUP_CONFIG` lines 36-48

**5. Scoring:**
- Pass 1 (heuristic): mention_count >= 3 → bump confidence one tier
- Pass 2 (Haiku): evaluates belief alignment (supports→bump, contradicts→drop to "conflict", refines→none), question resolution, confidence adjustments
- **Source**: `app/chains/score_entity_patches.py`

**6. Apply sequence in patch_applicator:**
- Check confidence threshold (very_high/high/medium auto-apply; low/conflict escalate)
- Dispatch by operation: create (INSERT), merge (evidence append + version bump), update (field UPDATE + version bump), stale (mark status), delete (safe delete)
- Never downgrade confirmation hierarchy (ai_generated < needs_client < confirmed_consultant < confirmed_client)
- **Source**: `app/db/patch_applicator.py` lines 95-259

### 3.2 Post-Apply Cascades (In Order)

All hooks are **fire-and-forget, non-blocking**. Exceptions logged as warnings, never fail the operation.

| # | Hook | What It Does | Source |
|---|------|-------------|--------|
| 1 | `_embed_modified_entities()` | Batch-fetches entities by table, calls `embed_entity()` per entity. Uses EMBED_TEXT_BUILDERS (e.g., feature → "name: overview") | Line 855-896 |
| 2 | `flag_steps_with_updates()` | Marks solution_flow_steps as having updates when linked entities change | Line 184-191 |
| 3 | `cascade_staleness_to_steps()` | Demotes confirmed solution_flow_steps linked to stale entities. Only fires on "stale" operations. | Line 193-203 |
| 4 | `_record_state_revision()` | Inserts audit trail via `insert_state_revision()` with input_summary + diff | Line 206-210 |
| 5 | `_record_evidence_links()` | Links chunk evidence to entities via `record_chunk_impacts()` | Line 213-217 |
| 6 | `_link_entities_by_cooccurrence()` | Finds entities sharing signal chunks. Cross-type pairs only (feature↔driver, feature↔persona, etc.). Top 5 per entity. Registers with dep_type="co_occurrence", strength=normalized, confidence=0.5 | Line 220-224, 959-1062 |
| 7 | `_resolve_and_create_semantic_links()` | Resolves extraction links (target_name → target_id via fuzzy match, threshold 0.8). Registers with dep_type=link.link_type, strength=0.8, confidence=0.7, source="semantic_extraction" | Line 227-231, 1064-1172 |
| 8 | `_register_fk_dependencies()` | Registers structural FK relationships from entity payloads (e.g., workflow.owner → persona). 9 FK_DEPENDENCY_MAP entries. Strength=1.0, confidence=1.0, source="structural" | Line 234-238, 1407-1544 |
| 9 | `_trigger_forge_matching()` | Async fire-and-forget. Matches new features against Forge modules via `forge.match_features()` | Line 241-252 |

### 3.3 Confirmation Flow

**UI confirmation (batch endpoint):**

- **Answer**: `POST /confirmations/batch` calls `batch_confirm_entities()`. Updates `confirmation_status` field on the entity record. When confirming a `solution_flow_step`, cascades: fetches linked_feature_ids, linked_workflow_ids, linked_data_entity_ids and updates all linked entities to the same confirmation_status. Best-effort cascade (skips errors).
- **Source**: `app/api/confirmations.py` lines 271-404
- **Confidence**: High
- **Notes**: Cascade only fires for solution_flow_step confirmations, NOT for individual entity confirmations. Confirming a feature does NOT cascade.

**Chat confirmation:**

- **Answer**: The write tool handles status updates. Routes through `_update_entity()` which does a direct DB update. No cascade. Same effect as a direct status field change.
- **Source**: `app/chains/chat_tools/tools_entity_crud.py`
- **Confidence**: High

**Client portal confirmation:**

- **Answer**: Sets `confirmation_status = "confirmed_client"` (highest tier). Same endpoint, different status value. Does NOT trigger additional cascades beyond what batch confirm does.
- **Source**: `app/api/confirmations.py`
- **Confidence**: High

---

## Section 4: Entity Relationships & Links

### 4.1 Entity Dependencies Table

**Full schema:**

- **Answer**: `entity_dependencies` has: id, project_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, dependency_type, strength (FLOAT DEFAULT 1.0), confidence (FLOAT), source (TEXT), disputed (BOOLEAN), disputed_at (TIMESTAMPTZ), created_at, updated_at. Has UNIQUE constraint on (project_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, dependency_type).
- **Source**: `migrations/0034_entity_dependencies.sql`
- **Confidence**: High

**CHECK constraints:**

- **Answer**: Source entity types: ('persona', 'feature', 'vp_step', 'strategic_context', 'stakeholder'). Target entity types: ('persona', 'feature', 'vp_step', 'signal', 'research_chunk'). Dependency types: ('uses', 'targets', 'derived_from', 'informed_by', 'actor_of'). **However**, later migrations expanded these via DROP + ADD CONSTRAINT to include: spawns, enables, constrains, co_occurrence, addresses.
- **Source**: `migrations/0034_entity_dependencies.sql`, later migrations expanding CHECK constraints
- **Confidence**: High
- **Notes**: The CHECK constraints are the biggest obstacle to extending the link system. They don't include business_driver, workflow, data_entity, constraint, competitor, or any new entity types.

**Co-occurrence vs explicit links:**

- **Answer**: Co-occurrence links are created by `_link_entities_by_cooccurrence()` — they find entities that share signal chunks. They have dependency_type="co_occurrence", confidence=0.5, source="co_occurrence". Explicit links come from extraction (confidence=0.7, source="semantic_extraction") or FK resolution (confidence=1.0, source="structural"). The `disputed` column allows manual override.
- **Source**: `app/db/patch_applicator.py` lines 959-1062
- **Confidence**: High

### 4.2 Graph Queries

**How does get_entity_neighborhood() work?**

- **Answer**: Takes an entity_id, entity_type, project_id, depth (1 or 2). Queries `signal_impact` for chunk_ids associated with the entity, then finds co-occurring entities in those chunks. Counts shared chunks per entity (weight). For depth-2: walks to neighbors' chunks with 50% weight decay. Returns entity data + related entities with relationship, weight, strength ("strong"≥5, "moderate"≥3, "weak"<3), hop, path, freshness, certainty, belief_confidence.
- **Source**: `app/db/graph_queries.py`
- **Confidence**: High

**Link direction:**

- **Answer**: Links ARE directional (source → target). But `get_entity_neighborhood()` searches BOTH directions — it finds entities where the target entity appears as either source or target in entity_dependencies. The co-occurrence system (signal_impact) is inherently bidirectional.
- **Source**: `app/db/graph_queries.py`, `app/db/entity_dependencies.py`
- **Confidence**: High

---

## Section 5: Existing Proto-Outcome Concepts

### 5.1 Business Drivers

**Schema:**

- **Answer**: 50+ columns across 7 migrations. Key fields:
  - **Core**: driver_type (kpi/pain/goal), description, measurement, timeframe, priority (1-5)
  - **KPI**: baseline_value, target_value, measurement_method, tracking_frequency, data_source, responsible_team
  - **Pain**: severity (critical/high/medium/low), frequency (constant/daily/weekly/monthly/rare), affected_users, business_impact, current_workaround
  - **Goal**: goal_timeframe, success_criteria, dependencies, owner
  - **Financial**: monetary_value_low/high, monetary_type, monetary_confidence, monetary_source
  - **Linking**: linked_persona_ids[], linked_vp_step_ids[], linked_feature_ids[], linked_driver_ids[]
  - **Horizons**: horizon_alignment (JSONB with h1/h2/h3 scores), trajectory (JSONB)
  - **Hierarchy**: parent_driver_id, spawned_from_unlock_id
- **Source**: `migrations/0042_business_drivers.sql` through `migrations/0115_business_driver_links.sql`
- **Confidence**: High
- **Notes**: Business drivers already encode before/after states (baseline→target for KPIs, severity levels for pains) and observable criteria (measurement_method, tracking_frequency). These map directly to outcome concepts.

**Could business drivers evolve into outcomes?**

- **Answer**: Partially. Drivers have state-change semantics (pain severity current→target, KPI baseline→target) but lack:
  - Actor-specific sub-outcomes (per-persona state changes)
  - Strength scoring (4-dimension model)
  - "What Helps" lists
  - "Ways to Achieve" linkage
  - Convergence/surface compilation
  - Before/after narrative transforms

  Drivers are **evidence of outcomes** but are not outcomes themselves. A pain point like "12% error rate" is evidence supporting the outcome "Error rate drops to near-zero." Multiple drivers can point to the same outcome. The relationship is many-to-one, not 1:1.
- **Confidence**: Medium (design judgment)

### 5.2 Unlocks

**Schema:**

- **Answer**: 26 columns. Key fields: title, narrative, impact_type (7 values: operational_scale, talent_leverage, risk_elimination, revenue_expansion, data_intelligence, compliance, speed_to_change), unlock_kind (new_capability/feature_upgrade), tier (implement_now/after_feedback/if_this_works), status (generated/curated/promoted/dismissed), promoted_feature_id (FK→features), provenance JSONB.
- **Source**: `migrations/0140_unlocks.sql`
- **Confidence**: High

**Difference from drivers:**

- **Answer**: Unlocks are forward-looking opportunities that can **promote to features**. Drivers are intrinsic problems/goals. Unlocks have `promoted_feature_id` FK — when promoted, they become real features. Unlocks are generated from the intelligence pipeline, not extracted from signals directly.
- **Source**: `app/db/unlocks.py`
- **Confidence**: High

**Linked to horizons?**

- **Answer**: Not directly via FK. The `tier` field maps conceptually: implement_now ≈ H1, after_feedback ≈ H2, if_this_works ≈ H3. But there's no horizon_id FK on the unlocks table.
- **Source**: `migrations/0140_unlocks.sql`
- **Confidence**: High

### 5.3 Horizon Outcomes

**Schema and usage:**

- **Answer**: Three tables, **actively used**:
  1. `project_horizons` — 3 per project (H1/H2/H3). Fields: horizon_number, title, description, status, readiness_pct, last_readiness_check
  2. `horizon_outcomes` — Links driver to horizon with measurable threshold. Fields: horizon_id FK, driver_id FK, threshold_type (value_target/severity_target/completion/adoption/custom), threshold_value, progress_pct, trend (improving/stable/declining/unknown), status (tracking/at_risk/achieved/abandoned), weight, is_blocking
  3. `outcome_measurements` — Time-series actual values. Fields: outcome_id FK, value, source_type (signal/manual/integration/derived/client_portal), confidence, is_baseline
- **Source**: `migrations/0163_horizons_and_outcomes.sql`
- **Confidence**: High

**Active usage:**

- **Answer**: Yes, actively used in 6+ Python modules:
  - `outcome_tracking.py` — deterministic progress computation (linear interpolation or severity ordinal mapping)
  - `horizon_crystallization.py` — auto-creates horizon_outcomes from business_drivers when first solution flow is generated
  - `driver_evolution.py` — trajectory computation (severity curves, velocity)
  - `horizon_briefing.py` — briefing generation with progress summaries
  - `workspace_horizons.py` — REST API endpoints
  - `project_horizons.py` — CRUD operations
- **Source**: Searched `horizon_outcome` across Python codebase — 6 active modules
- **Confidence**: High
- **Notes**: This is a **metric tracking** system, not a discovery/organizing system. It tracks whether KPIs hit targets. The new Outcomes system is about discovering and organizing what must be true — a fundamentally different concept.

### 5.4 Goals / KPIs

**Answer**: No separate goals, kpi, or objective tables. All three concepts unified under `business_drivers` with `driver_type` discrimination (kpi/pain/goal). The `projects` table has `vision` (TEXT) which is the closest thing to a macro goal.

- **Source**: Searched migrations for "goal", "kpi", "objective" table creation — none found
- **Confidence**: High

---

## Section 6: Embedding & Retrieval Details

### 6.1 Current Embedding Builders

**Per-type text builders** (from `app/db/entity_embeddings.py`):

| Entity Type | Embedded Text | Notes |
|---|---|---|
| feature | `name: overview` | Short — loses category, priority |
| persona | `name - role: description` | Reasonable coverage |
| constraint | `title: description` | Basic |
| stakeholder | `name, role at organization` | Very short |
| business_driver | `description (driver_type)` | Loses baseline/target/severity |
| data_entity | `name: description` | Basic |
| competitor | `name: research_notes[:300]` | Truncated |
| workflow | `name: description` | Basic |
| vp_step | `label: description` | Basic |
| solution_flow_step | `title: goal — mock_data_narrative[:300]` | Richest — includes narrative |
| unlock | `title (impact_type): narrative — why_now \| non_obvious` | Rich |
| prototype_feedback | `[source/feedback_type] content` | Basic |

- **Source**: `app/db/entity_embeddings.py` lines 21-45
- **Confidence**: High
- **Notes**: Each entity is embedded **in isolation** — no linked entity context included. This is a key limitation the multi-vector upgrade addresses.

### 6.2 Match Entities RPC

**Answer**: Literally 12 SELECT statements UNIONed. Each selects: id AS entity_id, literal entity_type, name column (varies: name/label/title/LEFT(content,80)/description), cosine similarity. Filtered by project_id and embedding IS NOT NULL. Optional filter_entity_types array. Returns entity_id, entity_type, entity_name, similarity. Ordered by similarity DESC, LIMIT match_count.

- **Source**: `migrations/0156_embedding_expansion.sql`
- **Confidence**: High
- **Notes**: Adding a new entity type (like outcomes) requires adding another UNION clause to this RPC. The entity_vectors table approach eliminates this — one table, one query.

### 6.3 Retrieval Pipeline

**parallel_retrieve() parameters:**

- chunks: `match_signal_chunks(query_embedding, chunks_per_query, project_id)` — default 5 per sub-query
- entities: `match_entities(query_embedding, 10, project_id, entity_types)` — default 10
- beliefs: `match_memory_nodes(query_embedding, 5, project_id)` — default 5
- Results merged by ID, keeping highest similarity. Deduplication across all 3 sources.

**Graph expansion:**

- Runs when `include_graph_expansion=True` (default) AND entities were returned
- Takes top 3 entities by similarity as seeds
- Depth configurable (1 or 2 hops)
- Max 15 new entities added
- **Source**: `app/core/retrieval.py` lines 311-470
- **Confidence**: High

---

## Section 7: Pulse Engine & Memory

### 7.1 Pulse Engine

**What it computes:**

- **Answer**: A single deterministic `ProjectPulse` per project — zero LLM calls, ~50ms. Includes: stage (discovery/validation/prototype/specification/handoff), entity health scores (per type), ranked actions (top 5), risk assessment (stale clusters, critical questions), forecasts (prototype readiness, spec completeness), extraction directives, auto-confirm candidates.
- **Source**: `app/core/pulse_engine.py`
- **Confidence**: High

**Pulse directives:**

- **Answer**: Per-entity-TYPE (not per individual entity). 5 values:
  - **grow** — coverage thin, need more entities
  - **confirm** — adequate count but confirmation_rate < 0.4
  - **enrich** — adequate count, low quality (confirmation 0.4-0.7, quality < 0.5)
  - **stable** — healthy, no action needed (coverage adequate + confirmation ≥ 0.7)
  - **merge_only** — saturated, only merge/refine

**Retrieval multipliers** (in `_apply_pulse_weights()`):
  - Link density: 0.7x (no links) to 1.3x (fully connected)
  - Directive: grow=1.5x, confirm=1.2x, enrich=1.0x, stable=0.7x, merge_only=0.3x
  - Combined range: 0.21x (merge_only + no links) to 1.95x (grow + high density)
- **Source**: `app/core/retrieval.py` lines 478-534
- **Confidence**: High

### 7.2 Memory & Beliefs

**What's in the memory graph:**

- **Answer**: Three node types in `memory_nodes`:
  - **Facts** — immutable observations, confidence always 1.0, created by MemoryWatcher from signals
  - **Beliefs** — evolving interpretations, confidence 0.0-1.0, created by MemorySynthesizer from fact patterns
  - **Insights** — generated patterns, created by MemoryReflector from belief evolution
  - Connected by `memory_edges` with types: supports, contradicts, caused_by, leads_to, supersedes, related_to

**How beliefs are created:**
  1. MemoryWatcher extracts facts from signals (Haiku, ~$0.001)
  2. If importance ≥ 0.7 or contradictions detected → triggers MemorySynthesizer
  3. Synthesizer (Sonnet) creates beliefs from accumulated facts with confidence based on evidence count
  4. MemoryReflector periodically creates insights from belief evolution

**How beliefs factor into extraction:**
  - Scoring pass 2 (Haiku) evaluates each patch against active beliefs
  - "supports" → bump confidence one tier
  - "contradicts" → drop to "conflict" tier
  - "refines" → no change

**How beliefs factor into retrieval:**
  - `match_memory_nodes()` RPC — vector search on memory_nodes embeddings
  - Returns beliefs with confidence scores, used in formatted context
- **Source**: `app/db/memory_graph.py`, `app/agents/memory_agent.py`, `app/chains/score_entity_patches.py`
- **Confidence**: High

---

## Section 8: Solution Flow Generation

### 8.1 Covered in Section 1.2 above.

Key additions:

**Regeneration behavior:**

- **Answer**: Solution flow can be regenerated multiple times. Confirmed steps are preserved (`preserved_from_version` set, `confirmation_status` checked). Only `ai_generated` and `needs_review` steps are deleted on regeneration. New steps interleave with preserved steps. Version counter increments.
- **Source**: `app/chains/solution_flow_v4/__init__.py` — `_persist_steps()`
- **Confidence**: High

### 8.2 Solution Flow and Prototype

**Answer**: The prototype generation pipeline uses solution flow steps as input — specifically `mock_data_narrative`, `implied_pattern`, `information_fields`, `ai_config`, and `story_headline`. Each step becomes a screen/page in the prototype. There is NO separate concept of "screens" — solution_flow_steps ARE the screens.

- **Source**: `app/chains/solution_flow_v4/builders.py`, prototype pipeline (not deeply audited in this pass)
- **Confidence**: Medium

---

## Section 9: Design Questions for Outcome Decisions

### 9.1 Where should outcomes live?

**Answer**: **New standalone tables, NOT the 12-table entity pattern.**

Reasons:
- Outcomes are a higher-order concept — they organize entities, not sit alongside them
- The match_entities() 12-way UNION should not grow to 13. Outcomes get their own `match_outcomes()` RPC.
- The patch_applicator is designed for signal-extracted entities. Outcomes are derived from entity graphs, not extracted from signals.
- The entity_vectors table (Phase 1) makes entity search independent of table count — outcomes get their own vectors there.

Recommendation: `outcomes` + `outcome_actors` as designed in the v2 implementation guide. Outcomes get embedded in `entity_vectors` with entity_type="outcome" for unified retrieval.

- **Confidence**: High

### 9.2 What should happen to business_drivers?

**Answer**: **Keep business_drivers as-is. Outcomes are net new.**

Business drivers are evidence/inputs that feed into outcomes. A pain ("12% error rate") supports an outcome ("Error rate drops to near-zero"). Multiple drivers can feed one outcome. The relationship is:
- business_driver → evidence for → outcome (many-to-one)
- outcome → measured by → horizon_outcome (progress tracking)

Don't deprecate drivers — they serve a different purpose (granular problem/goal/KPI tracking). Outcomes are the state-change synthesis that sits above them.

Fields that partially overlap: `baseline_value/target_value` (KPI) ≈ `before_state/after_state` (outcome actor). But drivers are per-metric, outcomes are per-persona-experience. Different granularity.

- **Confidence**: Medium (design judgment)

### 9.3 Where do outcomes appear per tab?

**Answer based on chat_modes and current architecture:**

- **BRD View**: Outcomes as a **new header section** above the entity sections. Each entity section shows which outcome(s) it serves (via outcome_entity_links). Drivers get an explicit "Supports Outcome" badge. Features get "Serves Outcome X" tags.
  - Chat mode: Add outcomes to the entity inventory in Layer 1 of context snapshot.

- **Solution Flow**: Outcomes as the **organizing principle** for step architecture. Steps "serve" outcomes via outcome_entity_links with surface_id. The convergence map shows which steps have multiple outcomes converging.
  - Chat mode: The solution_flow tool gets outcome-aware actions (link step to outcome, check outcome coverage).

- **Data & AI**: Outcome_capabilities as "Ways to Achieve" per outcome. Intelligence items tagged to outcomes. Gap analysis shows which outcomes lack intelligence coverage.
  - Chat mode: Currently suggest_actions only — would need enhancement for outcome-intelligence queries.

- **Confidence**: Medium (projection from current patterns)

### 9.4 How should outcome confirmation work?

**Answer based on existing confirmation patterns:**

- **UI**: Same batch_confirm endpoint pattern. `PATCH /outcomes/{id}/confirm` sets confirmation_status.
- **Chat**: The write tool gets outcome-aware actions, or a new `outcome` tool (following the solution_flow tool pattern).
- **Client portal**: Same endpoint, status="confirmed_client".

**Cascade behavior:**
- Confirming a **core outcome** should NOT auto-confirm actor outcomes. Actor outcomes have independent strength scores and may need individual sharpening. The UI shows them as separate items with separate confirm buttons.
- Confirming an **actor outcome** should check if all actor outcomes for a core outcome are confirmed → if yes, auto-confirm the core outcome.
- Outcome confirmation should NOT cascade to linked entities. Entities have their own independent confirmation lifecycle.

- **Confidence**: Medium (design recommendation)

### 9.5 What cascades should outcome creation trigger?

**Answer based on existing cascade patterns:**

1. **Embed the outcome** — fire-and-forget, same pattern as entity embedding
2. **Link to entities** — similarity search against entity_vectors, create outcome_entity_links for similarity > 0.7
3. **Intelligence gap analysis** — check if outcome has Ways to Achieve across all 4 quadrants. Surface gaps as next actions.
4. **Surface coverage check** — check if outcome has any solution_flow_steps serving it. If not, flag as "unserved outcome" (equivalent to ghost card in convergence map playground).
5. **Horizon alignment** — if outcome has horizon set, update project_horizons readiness computation.
6. **Invalidate intelligence cache** — so next chat response reflects new outcome context.

All should be fire-and-forget, matching existing patterns.

- **Confidence**: Medium (design recommendation based on existing patterns)
