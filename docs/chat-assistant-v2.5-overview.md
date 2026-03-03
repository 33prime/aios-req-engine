# AIOS Chat Assistant v2.5 — Architecture Overview

## Executive Summary

The AIOS Chat Assistant is a context-aware AI copilot for requirements engineering consultants. Version 2.5 introduces a **dimensional prompt compiler** that dynamically orients the model's thinking based on project state, replacing static if/then block selection with a cognitive frame system that produces ~180 unique behavioral combinations. The system assembles context from 8 parallel data sources in ~100ms, shapes retrieval via a 6-stage pipeline with graph expansion and Cohere reranking, and delivers responses through 6 consolidated tools (down from 35) filtered by page context.

The key insight: **we don't just give the model data — we give it orientation.** The prompt compiler tells the model *how to think*, *what timeframe matters*, *how wide to look*, and *how confident to be* — all computed from live project state.

---

## 1. The Dimensional Prompt Compiler

The compiler selects a **CognitiveFrame** across 4 independent dimensions, each derived from different project signals:

### The Four Dimensions

| Dimension | Values | Selected From |
|-----------|--------|---------------|
| **CognitiveMode** | DISCOVER, SYNTHESIZE, REFINE, EXECUTE, EVOLVE | Project phase + user intent |
| **TemporalEmphasis** | RETROSPECTIVE, PRESENT_STATE, FORWARD_LOOKING | Horizon state + page context |
| **Scope** | ZOOMED_IN, CONTEXTUAL, PANORAMIC | Page type + focused entity |
| **ConfidencePosture** | ASSERTIVE, EXPLORATORY, CONFIRMING, EVOLVING | Flow health status |

Each dimension has natural language instructions that shape behavior:

- **DISCOVER mode**: *"Hunt for gaps in understanding, ask probing questions, help the consultant uncover what they don't yet know."*
- **ASSERTIVE posture**: *"Make confident recommendations. Use language like 'You should...' and 'The evidence supports...'"*
- **PANORAMIC scope**: *"Take the wide view. Cross-entity patterns, project health, strategic positioning."*
- **FORWARD_LOOKING temporal**: *"Think ahead. Consider horizons, dependencies, and what needs to happen next."*

### Frame Selection Rules (~20 rules → hundreds of combinations)

**CognitiveMode** (from phase × intent):
- BRD phase + discuss/plan → DISCOVER
- BRD phase + create/update → SYNTHESIZE
- Solution flow + discuss/review → REFINE
- Solution flow + flow actions → EXECUTE
- Prototype phase → EVOLVE

**TemporalEmphasis** (from project health):
- Prototype phase with discoveries → RETROSPECTIVE
- Blocking horizon outcomes > 0 → FORWARD_LOOKING
- Overview/business context pages → FORWARD_LOOKING
- Default → PRESENT_STATE

**Scope** (from page + intent):
- Overview page or planning intent → PANORAMIC
- Focused entity + update/flow intent → ZOOMED_IN
- Default → CONTEXTUAL

**ConfidencePosture** (from flow health):
- Flow status "confirmed" → ASSERTIVE
- Flow status "ready"/"structured" → CONFIRMING
- Flow status "evolved" → EVOLVING
- Default/no flow → EXPLORATORY

### Two-Block Prompt Architecture

The compiler outputs a `CompiledPrompt` with two distinct blocks:

1. **Cached Block** (~1000-1200 tokens): Identity + cognitive instructions + capabilities + action card patterns + conversation rules. Marked with Anthropic's `cache_control: ephemeral` — cached across multi-turn tool loops within a session.

2. **Dynamic Block** (~1500-2500 tokens): Awareness snapshot + warm memory + page guidance + solution flow context + focused entity + memory/horizon intelligence + retrieved evidence. Rebuilt every request.

This architecture means the stable instruction payload is served from cache on tool-loop turns 2-5, cutting input token costs significantly.

### Retrieval Plan Shaping

The cognitive frame also shapes *how retrieval works*:

```
Scope → graph depth (PANORAMIC=2, CONTEXTUAL=1, ZOOMED_IN=0)
Temporal → recency weighting (RETROSPECTIVE disables recency boost)
Posture → result prioritization (EVOLVING boosts recent signals, ASSERTIVE boosts confirmed)
```

---

## 2. Project Awareness State — "The Patient Chart"

A pre-computed, cached (120s TTL) snapshot of where the project is right now. Built from 5 parallel DB queries in ~50-100ms.

### Phase Detection

The system detects which workspace is the "center of gravity":

```
Has prototype sessions? → "prototype" phase
Has confirmed flow steps or >30% confirmed? → "solution_flow" phase
Otherwise → "brd" phase
```

This maps to the 3-phase project lifecycle: **BRD → Solution Flow → Prototype**. The center of gravity shifts as the project matures.

### Flow Health Assessment

Each solution flow step gets a clinical health status:

| Status | Meaning |
|--------|---------|
| `drafting` | Missing goal and actors |
| `structured` | Has some fields populated |
| `ready` | Goal + actors + ≥2 info fields + 0 open questions |
| `confirmed` | Consultant or client confirmed |
| `evolved` | Has pending updates from new signals/prototype |

Plus: completeness score (0-1), blocking reasons, open question counts.

### Treatment Status

Three lists computed from flow health + project state:

- **What's Working**: Confirmed steps, unlocks discovered
- **What's Next**: Steps ready for confirmation, blocking issues, unresolved questions
- **What's Discovered**: Recent unlocks, horizon shifts from prototype feedback

### Temporal Anchors

Three sentences providing past/present/future context:
- Past: *"12 signals processed, 47 entities extracted"*
- Present: *"Solution flow: 3/8 steps confirmed"*
- Future: *"5 steps to confirm, then prototype generation"*

### Formatted Output

The awareness snapshot renders as ~300-500 tokens with status icons:

```
# Project: ClientCo CRM | Phase: Solution Flow

## Flows
✓ Smart Lead Intake [confirmed] — reduces manual entry
◉ AI Prioritization [ready]
◎ Dashboard View [structured] ⚠ 2 open questions
○ Export Pipeline [drafting] ⚠ needs goal and actors

## Working
- Smart Lead Intake — confirmed, 3 unlocks

## Next
- Confirm AI Prioritization — complete and ready
- Dashboard View: 2 open questions

## Timeline
Past: 8 signals processed, 34 entities extracted
Now: Solution flow: 1/4 steps confirmed
Ahead: 3 steps to confirm, then prototype generation
```

---

## 3. Intelligence Signal Loaders

Three parallel intelligence layers loaded alongside awareness:

### Warm Memory (Cross-Conversation Continuity)

Loads summaries of the last 3 conversations for this project (excluding current). Gives the model awareness of what was discussed in prior sessions without re-processing full message history.

Fallback: if no conversation summaries exist, extracts the last user message from each recent conversation as topic hints.

### Confidence State (Memory Landscape)

Three parallel queries against the `memory_nodes` table:
- **Low-confidence beliefs** (<0.6): Beliefs the model should verify before citing
- **Active domains**: Breadth of knowledge coverage (count of unique belief domains)
- **Recent insights**: Strategic patterns from the reflector

Only surfaced when relevant — low-confidence beliefs appear in all modes; recent insights appear only in SYNTHESIZE and REFINE modes.

### Horizon State (Strategic Intelligence)

- **Horizon summary**: H1/H2/H3 readiness percentages, outcome counts
- **Blocking outcomes**: Outcomes at risk across horizons
- **Compound decisions**: H1→H2/H3 decisions detected via BFS graph traversal

Only included in the prompt when horizons are crystallized (have been computed at least once).

---

## 4. The Retrieval Pipeline (Tier 2.5)

A 6-stage pipeline called by every consumer flow (chat, solution flow, briefing, stakeholder intelligence, unlocks, gap intel, prototype updater):

### Stage 1: Query Decomposition

Complex queries get split into 2-4 targeted sub-queries via Haiku. Short/simple queries (<8 words, no question mark) pass through unchanged. Uses forced tool_choice for structured output.

### Stage 2: Parallel Retrieval

Three strategies fan out simultaneously:

| Strategy | Source | Method |
|----------|--------|--------|
| **Chunks** | `signal_chunks` table | pgvector cosine similarity via `match_signal_chunks` RPC |
| **Entities** | Entity embeddings | pgvector via `match_entities` RPC, with reverse-provenance fallback |
| **Beliefs** | `memory_nodes` table | pgvector via `match_memory_nodes` RPC, with keyword overlap fallback |

Results are deduplicated by ID, keeping highest similarity scores.

### Stage 2.5: Graph Expansion

Takes the top 3 entities by similarity, fetches their neighborhoods in parallel via `get_entity_neighborhood()`:

- **Depth 1**: Direct relationships (feature → persona, workflow → data entity)
- **Depth 2**: Multi-hop relationships (feature → persona → workflow)
- **Temporal weighting**: When enabled, prioritizes recently-evidenced relationships
- **Confidence overlay**: When enabled, includes certainty and belief data on entities

Graph-expanded items are tagged with `source="graph_expansion"` for attribution. Capped at 15 total graph-added entities.

Depth is controlled by page context:
```
Solution flow, Unlocks, Features, Personas, Workflows → depth 2
All other pages → depth 1
```

### Stage 3: Reranking (Cohere → Haiku → Cosine)

Three-tier fallback:

1. **Cohere rerank-v3.5** (primary): Up to 25 chunks, 500 chars each. Fast, high quality.
2. **Haiku listwise ranking** (fallback): Numbered summaries, JSON array output. Used when Cohere unavailable.
3. **Cosine similarity order** (final fallback): Just truncate to top_k by existing similarity scores.

Chat always has reranking enabled (`skip_reranking=False`), sufficiency evaluation disabled for speed (`skip_evaluation=True`).

### Stage 4: Sufficiency Evaluation (Optional)

For multi-round retrieval (max_rounds > 1): Haiku evaluates whether results answer the query. If not, suggests reformulated queries. Re-queries merge and re-rerank. Used by briefing and gap intel flows, skipped for chat (speed priority).

### Page-Aware Retrieval Profiles

Each page gets tailored retrieval parameters:

```
Entity type filtering by page:
  "brd:features"       → ["feature", "unlock"]
  "brd:solution-flow"  → ["solution_flow_step", "feature", "workflow", "unlock"]
  "brd:personas"       → ["persona"]
  "prototype"          → ["prototype_feedback", "feature"]

Graph depth by page:
  "brd:solution-flow"  → depth 2
  "brd:features"       → depth 2
  default              → depth 1

Confidence overlay:
  "brd:solution-flow", "brd:features", "brd:business-drivers" → enabled
```

---

## 5. Solution Flow Context Builder

**Zero LLM cost**, ~100ms. Pure DB reads + string formatting. 4 layers:

| Layer | What | Tokens |
|-------|------|--------|
| **Flow Summary** | All steps: phase, status, actors, field counts, open questions, flags | ~80/step |
| **Focused Step Detail** | Full dump of the selected step: goal, actors, info fields, open questions, linked entities (resolved to names), AI config, success criteria, pain points, provenance | ~300 |
| **Cross-Step Intelligence** | 6 deterministic checks: actor gaps, phase coverage, confidence distribution, explore hotspots, shared data fields, staleness | ~200 |
| **Retrieval Hints** | 2-4 strings derived from step goal + open questions + actor names | ~50 |

Plus two additional context layers:
- **Entity Change Delta**: Recent revisions to linked features/workflows/data entities (batched query)
- **Confirmation History**: Step's own revision timeline with trigger events and diffs

---

## 6. Intent Classification

Two-layer, zero-LLM cost (~0ms):

**Layer 1 — Regex patterns** (~70% coverage):
```
"find", "search", "show me" → search
"create", "add", "generate" → create
"update", "change", "edit"  → update
"delete", "remove", "merge" → delete
"review", "assess", "status"→ review
"plan", "strategy", "next"  → plan
"email", "meeting", "client"→ collaborate
"step", "flow", "goal"      → flow
fallback                     → discuss
```

**Layer 2 — Page context override**:
- On solution-flow page, "discuss" → "flow"
- On collaborate page, "discuss" → "collaborate"

Also extracts: topic keywords (entity nouns), complexity (simple/moderate/strategic based on word count and topic count).

---

## 7. Tool Architecture (6 Consolidated Tools)

Reduced from 35 individual tools to 6 dispatch-based tools:

| Tool | Actions | Purpose |
|------|---------|---------|
| **search** | semantic, entities, history, knowledge, status, documents, pending | Query and explore project data |
| **write** | create, update, delete | CRUD for all entity types |
| **process** | signal, belief, evidence, clarification, strategic_context, identify_stakeholders | Ingest and process information |
| **solution_flow** | update, add, remove, reorder, resolve_question, escalate, refine | Manage solution flow steps |
| **client_portal** | mark_for_review, draft_question, preview, push | Client collaboration |
| **suggest_actions** | gap_closer, action_buttons, choice, proposal, email_draft, meeting, smart_summary, evidence | Interactive UI action cards |

### Page-Context Filtering

```
Always available (4 core):  search, write, process, suggest_actions
+ solution_flow:            on brd:solution-flow page
+ client_portal:            on collaborate page or any brd: page
No page context (sidebar):  all 6 tools
```

Result: 4-6 tools per request. Tool definitions are cached via Anthropic's `cache_control` on the last tool in the array.

---

## 8. Chat Stream Engine

SSE-based streaming with multi-turn tool loop:

### Request Flow

```
1. User message arrives with page_context + focused_entity
2. Parallel: assemble_chat_context() + persist user message to DB
3. Classify intent (regex, ~0ms)
4. Compile cognitive frame (4 dimensions)
5. Compile prompt (cached block + dynamic block)
6. Stream response via Anthropic API with filtered tools
7. If tool_use → execute → feed result back → loop (max 5 turns)
8. Persist assistant message + tool calls to DB
9. Yield SSE done event
```

### Key Design Decisions

- **Model**: Haiku 4.5 — fast, cost-effective for high-frequency chat
- **Max tool turns**: 5 — prevents runaway loops
- **History window**: Last 10 messages — fits within 80K token budget
- **Step context injection**: When on solution-flow page, step title is prepended to user message (`[Viewing step: Smart Lead Intake]`) for highest-attention-zone placement
- **Legacy fallback**: If the prompt compiler fails, falls back to the legacy `dynamic_prompt_builder.py`
- **Tool result truncation**: Large tool results are truncated before being fed back to the model
- **Cache metrics logging**: Logs cache read/creation tokens per turn for cost tracking

---

## 9. Context Assembly Pipeline

8 parallel tasks assembled via `asyncio.gather()`:

```
┌─────────────────────────────────────────────────────────────┐
│                    asyncio.gather()                          │
├─────────────────────────────────────────────────────────────┤
│ 1. compute_context_frame()     — legacy action engine       │
│ 2. build_solution_flow_ctx()   — 4-layer flow context       │
│ 3. build_retrieval_context()   — full 2.5 retrieval pipeline│
│ 4. get_project_name()          — DB lookup                  │
│ 5. load_confidence_state()     — 3 parallel memory queries  │
│ 6. load_horizon_state()        — 2 parallel + BFS compute   │
│ 7. load_warm_memory()          — cross-conversation summaries│
│ 8. load_forge_intelligence()   — module matching            │
├─────────────────────────────────────────────────────────────┤
│ Then: load_project_awareness() — needs project_name         │
└─────────────────────────────────────────────────────────────┘
```

Every loader is wrapped in `_safe_load_*()` that returns empty/default on failure — no single intelligence layer can crash the chat.

Total assembly time: ~100-200ms (dominated by retrieval and DB queries, all parallel).

---

## 10. Architecture Summary

```
User Message + Page Context + Focused Entity
         │
         ▼
┌─ Intent Classifier (regex, ~0ms) ──────────────────────┐
│  intent_type, topics, complexity                        │
└────────────────────────────────────┬────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌─ 8 Parallel Loaders ─┐  ┌─ Project Awareness ─┐  ┌─ Retrieval 2.5 ─────┐
│ confidence_state      │  │ Phase detection     │  │ decompose           │
│ horizon_state         │  │ Flow health         │  │ ↓                   │
│ warm_memory           │  │ Treatment status    │  │ parallel retrieve   │
│ forge_intelligence    │  │ Temporal anchors    │  │ (chunks+entities+   │
│ solution_flow_ctx     │  │ Stakeholders        │  │  beliefs)           │
│ context_frame         │  │ Phase metrics       │  │ ↓                   │
│ project_name          │  │ [120s cache]        │  │ graph expand (d1-2) │
│ ...                   │  │                     │  │ ↓                   │
└───────────┬───────────┘  └──────────┬──────────┘  │ Cohere rerank       │
            │                         │              │ ↓                   │
            └────────────┬────────────┘              │ formatted evidence  │
                         │                           └──────────┬──────────┘
                         ▼                                      │
              ┌─ Prompt Compiler ───────────────────────────────┤
              │                                                 │
              │  Cognitive Frame Selection                      │
              │  ┌──────────────────────────────┐               │
              │  │ CognitiveMode    × intent    │               │
              │  │ TemporalEmphasis × health    │               │
              │  │ Scope            × page      │               │
              │  │ ConfidencePosture× flow      │               │
              │  └──────────────────────────────┘               │
              │                                                 │
              │  Prompt Assembly                                │
              │  ┌──────────────────────────────────────────┐   │
              │  │ CACHED: identity + cognitive instructions│   │
              │  │         + capabilities + patterns        │   │
              │  ├──────────────────────────────────────────┤   │
              │  │ DYNAMIC: awareness + warm memory +       │   │
              │  │          page guidance + flow context +   │   │
              │  │          memory + horizons + forge +     ◄───┘
              │  │          retrieved evidence              │
              │  └──────────────────────────────────────────┘
              └──────────────────────┬──────────────────────
                                     │
                                     ▼
              ┌─ Anthropic Streaming (Haiku 4.5) ──────────┐
              │ system: [cached_block, dynamic_block]       │
              │ tools:  4-6 filtered by page context        │
              │ loop:   up to 5 tool turns                  │
              │ cache:  tool defs + cached_block reused      │
              └─────────────────────────────────────────────┘
```

---

## Key Metrics

| Metric | Value |
|--------|-------|
| Context assembly latency | ~100-200ms (8 parallel tasks) |
| Intent classification | ~0ms (regex, no LLM) |
| Retrieval pipeline stages | 6 (decompose → retrieve → expand → rerank → evaluate → format) |
| Tools (from → to) | 35 → 6 consolidated |
| Tools per request | 4-6 (page-filtered) |
| Cognitive frame combinations | ~180 (5×3×3×4) |
| Prompt cached block | ~1000-1200 tokens |
| Prompt dynamic block | ~1500-2500 tokens |
| Max tool turns | 5 per request |
| Awareness cache TTL | 120 seconds |
| Chat model | Haiku 4.5 |
| Reranker | Cohere rerank-v3.5 → Haiku fallback → cosine |
| Graph expansion seeds | Top 3 entities, max 15 added |
| Solution flow context cost | Zero LLM tokens (pure DB + formatting) |

---

## Source Files

| File | Role |
|------|------|
| `app/context/prompt_compiler.py` | Dimensional model, frame selection, instruction compilation, retrieval plan shaping |
| `app/context/project_awareness.py` | Phase detection, flow health, treatment status, temporal anchors, 120s cache |
| `app/context/intelligence_signals.py` | Warm memory, confidence state, horizon state loaders |
| `app/context/intent_classifier.py` | Regex + page-context intent classification, topic extraction |
| `app/context/prompt_blocks.py` | Identity, capabilities, action cards, conversation patterns, page guidance |
| `app/core/chat_context.py` | 8 parallel context assembly tasks, page-entity type filtering |
| `app/core/chat_stream.py` | SSE streaming, multi-turn tool loop, Anthropic caching, message persistence |
| `app/core/retrieval.py` | 6-stage pipeline, parallel retrieval, graph expansion |
| `app/core/reranker.py` | Cohere rerank-v3.5 primary, Haiku fallback, cosine final fallback |
| `app/core/solution_flow_context.py` | 4-layer zero-LLM context builder |
| `app/chains/chat_tools/definitions.py` | 6 consolidated tools with action dispatch |
| `app/chains/chat_tools/filtering.py` | Page-context tool filtering (4-6 tools per page) |
