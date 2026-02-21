# AIOS Intelligence Architecture

## How It All Comes Together

---

## 1. THE THREE-LAYER STACK

```
SIGNALS (raw input)                    INTELLIGENCE (understanding)               BRD (structured output)
┌─────────────────────┐    ┌───────────────────────────────────────────┐    ┌─────────────────────────┐
│ Transcripts         │    │ Semantic Chunks + Meta-Tags (Haiku)       │    │ Features, Workflows     │
│ Documents (PDF/DOCX)│    │ Vector Embeddings (1536d, text-embed-3)   │    │ Personas, Constraints   │
│ Emails, Chat        │───▶│ Entity Embeddings (12 types, 14 tables)   │───▶│ Stakeholders, Drivers   │
│ Portal Responses    │    │ Memory Graph (facts→beliefs→tensions)     │    │ Data Entities, Comps    │
│ Prototype Feedback  │    │ Knowledge Graph (signal_impact FKs)       │    │ Solution Flow Steps     │
│ Confirmations       │    │ Confirmation Signals (embedded as facts)  │    │ Unlocks                 │
└─────────────────────┘    └───────────────────────────────────────────┘    └─────────────────────────┘
```

The intelligence layer is not a separate database. It's PostgreSQL doing everything — relational, vector (pgvector), JSONB metadata, recursive CTEs for graph traversal, real-time subscriptions. Single operational surface. No Pinecone, no Elasticsearch, no Redis, no Neo4j. One Supabase instance, one deployment, one bill.

### What's embedded and searchable

14 tables carry `embedding vector(1536)` columns, all searched through a single `match_entities()` RPC with 12 UNION ALLs:

| Table | Entity Type | Embedding Source |
|-------|------------|-----------------|
| features | `feature` | name + overview |
| personas | `persona` | name + role + description |
| workflows | `workflow` | name + description |
| vp_steps | `vp_step` | label + description |
| stakeholders | `stakeholder` | name + role + organization |
| business_drivers | `business_driver` | description + driver_type |
| constraints | `constraint` | title + description |
| data_entities | `data_entity` | name + description |
| competitor_references | `competitor` | name + research_notes[:300] |
| solution_flow_steps | `solution_flow_step` | title + goal + mock_data_narrative[:300] |
| unlocks | `unlock` | title + impact_type + narrative + why_now + non_obvious |
| prototype_feedback | `prototype_feedback` | source + feedback_type + content |
| signal_chunks | *(searched separately)* | Raw document/transcript text |
| memory_nodes | *(searched separately)* | Facts, beliefs, insights, confirmation events |

Every entity embedded. Every signal chunk embedded. Every memory observation embedded. Every confirmation event embedded as a fact. One `retrieve()` call searches all of them.

---

## 2. SIGNAL PIPELINE — 8-Node LangGraph

Signals enter as raw text (transcripts, documents, emails, portal responses) and exit as structured entity patches applied to the BRD.

```
┌─────────┐   ┌────────┐   ┌──────────────┐   ┌────────────┐   ┌──────────┐
│ 1.LOAD  │──▶│2.TRIAGE│──▶│ 3.CONTEXT    │──▶│ 4.EXTRACT  │──▶│ 5.SCORE  │
│ Raw text│   │<100ms  │   │ Parallel DB  │   │ N×Haiku    │   │ Haiku    │
│ Classify│   │Fast/   │   │ queries +    │   │ per chunk  │   │ Priority │
│         │   │Slow    │   │ entity inv.  │   │ Cached sys │   │ Conflict │
└─────────┘   └────────┘   └──────────────┘   └────────────┘   └──────────┘
                                                                      │
                                                                      ▼
┌────────────────┐   ┌──────────────────┐   ┌────────────┐   ┌──────────┐
│ 8.MEMORY       │◀──│ 7.SUMMARY        │◀──│ 6.APPLY    │◀──│ DEDUP    │
│ Facts+beliefs  │   │ Diff generation  │   │ Patches to │   │ 3-tier   │
│ Contradiction  │   │ Change tracking  │   │ entities   │   │ gate     │
│ detection      │   │ Revision history │   │ Embed new  │   │ (below)  │
└───────┬────────┘   └──────────────────┘   └──────┬─────┘   └──────────┘
        │                                          │
        ▼                                          ▼
┌───────────────────────┐              ┌──────────────────────────┐
│ 9.QUESTION            │              │ CASCADES (fire-and-forget)│
│ AUTO-RESOLUTION       │              │ • flag_steps_with_updates │
│ Open Q's vs signal    │              │ • staleness_to_steps      │
│ 0.80 confidence gate  │              │ • confirmation_signals    │
│ Project + flow Q's    │              │ • question_auto_resolve   │
└───────────────────────┘              └──────────────────────────┘
```

**Stage 3+4 run in parallel** (meta-tags don't depend on embeddings). Stage 4 fans out N Haiku calls simultaneously with a shared cached system prompt prefix. A 20-page transcript with 15 chunks costs ~$0.015 for extraction (15 Haiku calls) instead of one truncated Sonnet call.

**Stage 9 is new**: after patches are applied and memory is synthesized, the signal content is checked against all open questions — both `project_open_questions` table entries and `solution_flow_steps.open_questions` JSONB fields. Questions that the signal answers (above 0.80 confidence) are auto-resolved. This means a client answering one portal question can silently resolve 3 related open questions across the BRD.

**Six production callers** feed into this pipeline: document upload, client portal responses, email ingestion, manual signal creation, chat-submitted signals, and prototype feedback synthesis.

---

## 3. THE THREE-TIER DEDUP GATE

Between extraction and scoring, every entity patch goes through a dedup gate that prevents duplicate entities from proliferating.

```
Incoming entity patch (create)
    │
    ├──▶ Tier 1: EXACT NORMALIZED NAME                                    ─── $0 cost
    │    • Strip non-alphanumeric, lowercase
    │    • Match? → merge (score=1.0)
    │
    ├──▶ Tier 2: FUZZY TOKEN-SET                                          ─── $0 cost
    │    • RapidFuzz token_set_ratio
    │    • Per-type thresholds: 0.80 (constraints) → 0.90 (business_drivers)
    │    • Generic description guard (<20 chars blocked)
    │    • Score ≥ threshold? → merge
    │
    └──▶ Tier 3: EMBEDDING SIMILARITY (only if ambiguous zone)            ─── ~$0.001
         • Ambiguous: fuzzy score 0.45-0.85 (type-dependent)
         • Cosine similarity on entity embeddings
         • Thresholds: 0.88 (constraints) → 0.92 (business_drivers)
         • Disabled for: competitors, stakeholders, personas (name-only matching)
         • Score ≥ threshold? → merge

Result: 80-90% of dedup resolves at tiers 1-2 (zero cost)
```

The dedup gate runs per-type, meaning a feature named "Scoring Engine" won't accidentally merge with a workflow named "Scoring Engine" — each entity type has its own threshold profile tuned to how that type naturally varies in naming.

---

## 4. UNIFIED RETRIEVAL — The Single Point of Leverage

Every consumer in the system calls the same `retrieve()` function. This is the architectural decision that makes everything compound.

```
User Query / System Query
    │
    ▼
┌──────────────────────────────────────────┐
│ Stage 1: DECOMPOSITION (Haiku)           │  "What are the risks of voice-first?"
│ • Simple queries (<8 words) → skip       │  → ["voice input constraints",
│ • Complex → 2-4 sub-queries              │     "accessibility concerns",
│ • context_hint enriches focus            │     "timeline pressure"]
│ • Page-aware entity type filtering       │
└───────────────┬──────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│ Stage 2: PARALLEL RETRIEVAL (asyncio.gather, ~200ms)     │
│                                                          │
│  2a. Vector Search (signal_chunks)                       │
│      • match_signal_chunks() RPC per sub-query           │
│      • 5 chunks/query, deduped by chunk_id               │
│      • Optional JSONB meta_filters (entity types,        │
│        topics, sentiment, speaker roles)                  │
│                                                          │
│  2b. Entity Graph Neighborhood                           │
│      • match_entities() RPC — 12 UNION ALLs              │
│      • entity_types filter: page-context-aware           │
│        (brd:unlocks → unlock+feature+competitor)         │
│      • Reverse provenance via signal_impact FKs           │
│      • 1-hop neighbors (features↔workflows↔constraints)  │
│      • Pure SQL JOINs, ~50ms                             │
│                                                          │
│  2c. Memory Belief Lookup                                │
│      • match_memory_nodes() RPC (facts+beliefs+insights) │
│      • Includes confirmation events (embedded as facts)  │
│      • Returns beliefs + confidence + supporting facts   │
│      • Keyword fallback if no embeddings                 │
└───────────────┬──────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────┐
│ Stage 3: RERANKING (Haiku)               │  If >10 candidates
│ • Full text comparison vs query          │  Filter topically-adjacent
│ • Precision over recall                  │  but irrelevant chunks
└───────────────┬──────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────┐
│ Stage 4: EVALUATE & LOOP (Haiku)         │  "Are results sufficient?"
│ • Flow-specific evaluation criteria      │  → If not, reformulate + retry
│ • Max 2-3 rounds                         │  → 70% resolve in 1 round
│ • Merges + dedupes across rounds         │
└───────────────┬──────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────┐
│ Stage 5: FORMAT                          │  chat: concise quotes
│ • 3 styles: chat/generation/analysis     │  generation: grouped by type
│ • Token budget truncation                │  analysis: supports vs contradicts
└──────────────────────────────────────────┘
```

### Why this matters

**One improvement benefits everything.** When we added unlock embeddings, every consumer — chat, briefing, gap intel, solution flow, stakeholder intel, prototype updater — gets unlock context for free. No per-flow wiring.

**Page-context entity filtering** focuses each query. On the unlocks page, retrieval searches `unlock + feature + competitor` embeddings. On the solution flow page: `solution_flow_step + feature + workflow + unlock`. On the prototype page: `prototype_feedback + feature`. This means vector search returns focused, high-signal results instead of diluting across all 12 entity types.

**Graceful degradation.** If entity embeddings are missing, it falls back to reverse provenance via FKs. If memory nodes have no embeddings, it falls back to keyword search. No single failure breaks the system.

**Skip flags for performance.** Simple chat queries skip decomposition + reranking. Generation calls skip evaluation. Each consumer optimizes without forking the code.

**7 consumers currently wired:**

| Consumer | Purpose | Retrieval Config |
|----------|---------|-----------------|
| Chat pre-fetch | Evidence for user questions | 2 rounds, page-entity filtering |
| Solution flow generation | Per-phase evidence enrichment | 1 round, phase-specific context_hint |
| Briefing engine | Hypothesis evidence gathering | 2 rounds, analysis format |
| Gap intelligence | Gap validation evidence | 1 round, generation format |
| Stakeholder intel | Person-specific evidence | 2 rounds, entity-filtered |
| Unlocks generation | Opportunity evidence | 1 round, parallel 3-tier |
| Prototype updater | Code change evidence | 1 round, feature-filtered |

---

## 5. CHAT INTELLIGENCE — How Context Gets Built

The chat assistant is not an LLM with a system prompt. It's a 13-section context assembly pipeline that pre-fetches evidence, caches entity state, filters tools by page, and adapts its prompt based on project phase.

```
User Message arrives
    │
    ├──▶ Rate limit check (per-user, per-project)
    │
    ├──▶ Context Frame (cached, fingerprint-based invalidation)
    │    │  • Phase: EMPTY / SEEDING / BUILDING / REFINING
    │    │  • Top 5 gaps (ranked by impact_score × phase multiplier)
    │    │  • State snapshot (entity counts, recent changes)
    │    │  • Workflow context (1-hop names + step labels)
    │    │  • Memory hints (beliefs < 0.6 confidence)
    │    │  • Entity inventory (for tool reference)
    │    └──▶ Cached 2 min, invalidated when mutating tools fire
    │
    ├──▶ Solution Flow Context (if on flow page, zero-LLM)
    │    │  • Layer 1: Flow summary (1 line per step)
    │    │  • Layer 2: Focused step detail (~300 tokens)
    │    │  • Layer 3: Cross-step intelligence (6 checks)
    │    │  • Layer 4: Retrieval hints (goal + questions + actors)
    │    │  • Layer 5: Entity change delta (linked entity revisions)
    │    └──▶ Layer 6: Confirmation history (step's own timeline)
    │
    ├──▶ Vector Pre-Fetch (retrieve() call, ~200ms)
    │    │  • Embeds user message
    │    │  • Page-context entity type filtering
    │    │  • Retrieves chunks + entities + beliefs + confirmations
    │    │  • Formats as chat-style evidence
    │    └──▶ Injected into system prompt (no tool call needed)
    │
    ├──▶ Page-Aware Tool Filtering
    │    │  • 33 total tools filtered to 15-26 per page
    │    │  • Solution flow page: 26 tools (7 flow-specific)
    │    │  • Prototype page: 15 tools
    │    │  • Overview: 18 tools
    │    └──▶ 30-55% token savings on tool definitions
    │
    └──▶ build_smart_chat_prompt()
         │  13-section system prompt:
         │  1. Identity & personality (positive teammate, not doom-and-gloom)
         │  2. Current state (context frame)
         │  3. Phase + progress indicators
         │  4. Active gaps (top 5, framed as opportunities)
         │  5. Workflow context
         │  6. Memory hints (low-confidence beliefs)
         │  7. Page awareness + tool guidance
         │  8. Focused entity OR solution flow context
         │  9. Conversation context + retrieval evidence
         │  10. Action card guidance (8 card types)
         │  11. Capabilities
         │  12. Conversation patterns
         └──▶ 13. Entity counts

~70% of chats are reads → answered in ONE LLM turn (no tools needed)
~30% are writes → multi-turn tool loop (max 5 turns)
```

### Quick Action Cards

The `suggest_actions` tool returns structured cards the UI renders as interactive components:

| Card Type | Purpose | Example |
|-----------|---------|---------|
| `gap_closer` | Proposes action to close a specific gap | "3 features lack success criteria" |
| `action_buttons` | Multiple quick actions | "Confirm / Edit / Escalate" |
| `choice` | Decision point | "Should this be a Phase 1 or Phase 2 feature?" |
| `proposal` | Detailed recommendation | "Based on 4 signals, consider splitting this workflow" |
| `email_draft` | Ready-to-send client email | Pre-populated from context |
| `meeting` | Meeting agenda | Discovery session prep |
| `smart_summary` | Section summary | "Here's what we know about payments" |
| `evidence` | Supporting evidence | Linked quotes from signals |

---

## 6. SOLUTION FLOW — Parallel Generation with Confirmation Preservation

The solution flow is not a one-shot generation. It's a 4-stage parallel pipeline that treats confirmed work as sacred and generates around it.

```
Readiness Gate (5 entity thresholds — min confirmed counts required)
    │
    ▼
Stage 0: SNAPSHOT (~50ms, $0)
    • Bucket existing steps: confirmed / needs_review / ai_generated
    • Collect resolved Q&A as "project knowledge"
    • Load context via 7 parallel DB queries
    • Broad retrieval for evidence enrichment
    │
    ▼
Stage 1: DECOMPOSE (Haiku, ~200 tokens output, ~$0.001)
    • Input: full context + confirmed step positions
    • Output: phases[], target step counts, preserved indices
    • Tells us how many Sonnet calls to make and what each focuses on
    │
    ▼
Stage 2: PARALLEL GENERATE (Sonnet × 3-4, asyncio.gather, ~$0.15)
    • Each phase gets its own Sonnet call:
      - Full project context (same XML tags)
      - Phase-specific retrieval (per-phase context_hint)
      - Confirmed steps as HARD CONSTRAINTS ("preserve exactly")
      - needs_review steps as SOFT CONSTRAINTS ("preserve intent, may modify")
      - Resolved Q&A as project knowledge
    • max_tokens=3000 per call, temperature=0.3
    │
    ▼
Stage 3: STITCH + VALIDATE (Haiku, ~$0.002)
    • Cross-phase data flow resolution
    • Duplicate detection + gap validation
    • Final ordering of steps
    │
    ▼
Non-Destructive Persistence
    • DELETE only ai_generated + needs_review steps
    • PRESERVE confirmed steps (update preserved_from_version)
    • INSERT new steps around confirmed ones
    • Embed all new steps via entity_embeddings (fire-and-forget)
    • Build background narratives from entity provenance
    • Track all changes via enrichment_revisions
```

### Staleness Cascade

When new evidence contradicts existing entities, the cascade flows through to the solution flow:

```
New transcript contradicts Feature X
    │
    ▼
V2 pipeline marks Feature X as stale (is_stale = true)
    │
    ▼
patch_applicator calls flag_steps_with_updates()
    │
    ▼
Solution flow steps linked to Feature X:
    • ai_generated steps → flagged with has_pending_updates
    • confirmed steps → DEMOTED to needs_review (not deleted)
    • confidence_impact score set (0.0-1.0, proportion of links affected)
    │
    ▼
Next regeneration:
    • Demoted steps treated as SOFT CONSTRAINTS
    • Their intent preserved, but details may change
    • Confirmed steps elsewhere remain untouched
```

This is the key insight: **confirmations are durable signals, not brittle labels.** They survive regeneration. They only get demoted when evidence explicitly contradicts them. And even then, the intent is preserved as a soft constraint.

### Background Narratives (Zero-LLM Provenance)

Each step gets a provenance narrative built from pure DB reads:

> "This step was derived from Workflow: Assessment Pipeline (confirmed by consultant, 3 signals) and Feature: Scoring Engine (AI-generated, 2 signals). The step has been revised 4 times."

No LLM call. Just entity name resolution + revision count queries.

---

## 7. CONFIRMATION INTELLIGENCE

Confirmations in AIOS are not just status flags. They're first-class signals that compound through the system.

### Confirmation as Signal

When a consultant or client confirms an entity, four things happen:

```
Entity confirmed (e.g., Feature "Risk Scoring" → confirmed_consultant)
    │
    ├──▶ 1. Status update on entity row
    │
    ├──▶ 2. Enrichment revision created (audit trail with diff)
    │
    ├──▶ 3. Memory fact created + embedded                          ← NEW
    │       "Feature 'Risk Scoring' was confirmed by the consultant"
    │       → Searchable via match_memory_nodes()
    │       → retrieve() can surface "Client confirmed this on Feb 15"
    │
    ├──▶ 4. Question auto-resolution triggered                      ← NEW
    │       Check if this confirmation answers any open questions
    │       0.80 confidence threshold via Haiku
    │
    └──▶ 5. Solution flow cascade
            flag_steps_with_updates() for linked steps
```

### Confirmation Clustering

Unconfirmed entities across types are semantically clustered for bulk action:

```
7 unconfirmed entities (3 features, 2 workflows, 1 data entity, 1 constraint)
    │
    ▼
Greedy cosine clustering (0.78 similarity threshold)
    │
    ▼
Cluster 1: "Payment Processing" (2 features + 1 workflow + 1 data entity)
Cluster 2: "User Authentication" (1 feature + 1 workflow + 1 constraint)
    │
    ▼
Consultant clicks "Confirm All" on Cluster 1
    │
    ├──▶ 4 entities confirmed in one action
    ├──▶ 4 confirmation facts embedded in memory graph
    ├──▶ Solution flow steps flagged for refresh
    └──▶ Open questions checked for auto-resolution
```

This replaces tedious one-by-one confirmation with thematic batch operations. The consultant sees related entities grouped by meaning, not by type.

### Dynamic Question Auto-Resolution

Open questions don't just wait for explicit answers. They're checked against every new piece of information:

```
Three trigger points:
    │
    ├──▶ V2 Signal Pipeline (step 9)
    │    New transcript/document → check against all open questions
    │
    ├──▶ Client Portal Response
    │    Client answers one question → check if it resolves others
    │
    └──▶ Entity Confirmation (cluster or individual)
         Confirming entities → check if that answers pending questions

Each trigger:
    │
    ▼
Load open questions (project_open_questions + flow step open_questions)
    │
    ▼
Parallel Haiku checks (asyncio.gather)
    "Does this new information answer this question?"
    │
    ▼
Questions above 0.80 confidence → auto-resolved
    • project_open_questions: status = 'resolved', resolution_source
    • flow step questions: JSONB updated with resolved=true, resolution
```

---

## 8. PROTOTYPE FEEDBACK LOOP

The prototype refinement system turns interactive prototype sessions into structured intelligence that feeds back into the BRD.

```
AIOS Discovery Data → v0 Prompt (Opus) → v0 API → Prototype
    │
    ▼
Ingestion → Bridge Script Injection → Feature Analysis Pipeline
    │                                      │
    │                    ┌─────────────────────────────────┐
    │                    │ Per-feature overlay analysis:    │
    │                    │ • spec_summary vs prototype_summary │
    │                    │ • delta[] (what's different)     │
    │                    │ • implementation_status          │
    │                    │ • personas_affected              │
    │                    │ • validation gaps[]              │
    │                    │ • suggested_verdict              │
    │                    └─────────────────────────────────┘
    ▼
Consultant Session (iframe + feature overlay panel)
    │
    ├──▶ Navigate prototype in iframe
    ├──▶ Feature radar shows per-page overlays
    ├──▶ Click feature → see spec vs implementation delta
    ├──▶ Submit feedback (observations, concerns, questions, answers)
    ├──▶ Set verdict per feature: aligned / needs_adjustment / off_track
    │
    ▼
Client Review (portal link, separate session)
    │
    ├──▶ Same overlay view, client-specific verdicts
    │
    ▼
Convergence Tracking                                                    ← NEW
    │
    ├──▶ Alignment rate: % of features where consultant & client agree
    ├──▶ Session trend: improving / declining / stable / insufficient_data
    ├──▶ Question coverage: answered / total validation questions
    ├──▶ Feedback resolution rate: concerns addressed / total concerns
    ├──▶ Per-feature convergence detail
    ├──▶ Auto-saved as JSONB snapshot on session completion
    └──▶ Trend computed from historical snapshots (need 2+ sessions)
    │
    ▼
Feedback Synthesis → Code Update Plan (Opus) → Code Execution (Sonnet)
    │
    ▼
All feedback now embedded as vectors                                    ← NEW
    │
    ├──▶ Searchable via match_entities() with type='prototype_feedback'
    ├──▶ retrieve() on prototype pages filters to prototype_feedback + feature
    └──▶ Chat can answer: "What did the client think about the dashboard?"
         by surfacing embedded feedback alongside entity evidence
```

### Prototype Feedback as Embedded Intelligence

Previously, prototype feedback lived in its own table and was only accessible through direct DB queries. Now:

- Every feedback item (observation, concern, requirement, question, answer) is embedded on creation
- Denormalized `project_id` enables the `match_entities()` RPC to include feedback in vector search
- Feedback from prototype sessions surfaces in chat, briefing, and gap intelligence alongside BRD entities
- A client saying "I hate this workflow" during a prototype session can be retrieved when the consultant asks about that workflow in chat

---

## 9. MEMORY GRAPH — Facts, Beliefs, and Tensions

The memory system is not a chat history. It's a structured knowledge graph of organizational understanding.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MEMORY GRAPH                                │
│                                                                     │
│  FACTS (confidence=1.0, immutable)                                 │
│  ├── "Client budget is $500K"                                      │
│  ├── "CTO prefers React over Angular"                              │
│  ├── "Feature 'Risk Scoring' was confirmed by the consultant"  ← NEW│
│  └── Source: signals, portal answers, confirmations                │
│                                                                     │
│  BELIEFS (confidence 0.0-1.0, evolving)                            │
│  ├── "Client likely needs real-time dashboards" (0.7)              │
│  ├── "Timeline is aggressive for Phase 2" (0.4)                    │
│  └── Updated: new signals increase/decrease confidence             │
│                                                                     │
│  INSIGHTS (generated patterns)                                     │
│  ├── "3 stakeholders have conflicting views on data access"        │
│  └── Generated by synthesis agent from fact/belief patterns        │
│                                                                     │
│  EDGES                                                             │
│  ├── supports / contradicts / caused_by / leads_to / supersedes    │
│  └── Enable graph traversal: "What supports this belief?"          │
│                                                                     │
│  CONTRADICTION DETECTION                                           │
│  ├── Cosine similarity between new facts and existing beliefs      │
│  ├── Contradictions trigger belief confidence decrease              │
│  └── Surfaced in briefing as "tensions"                            │
└─────────────────────────────────────────────────────────────────────┘
```

All three node types carry `embedding vector(1536)` and are searched via `match_memory_nodes()`.

### Confirmation events as facts

When entities are confirmed, fact nodes are created:

> "Feature 'Risk Scoring' was confirmed by the consultant"

These facts are embedded and searchable. When the chat assistant or briefing engine asks "what has the client validated?", retrieval surfaces these confirmation facts alongside entity evidence. The system can answer temporal questions: "What was confirmed this week?" — because each fact has a `created_at` timestamp.

---

## 10. META-TAGGING — Per-Chunk Structured Metadata

Every document chunk gets tagged by Haiku in parallel with embedding. Tags are stored in JSONB and indexed via GIN for fast filtering.

```
Chunk: "Sarah mentioned that the scoring algorithm needs to handle
        edge cases where the risk profile changes mid-assessment..."

Tags (Haiku, ~$0.0003 per chunk):
{
  "entities_mentioned": ["Sarah"],
  "entity_types_discussed": ["feature", "workflow"],
  "topics": ["risk_scoring", "edge_case_handling", "assessment_pipeline"],
  "sentiment": "neutral",
  "decision_made": false,
  "speaker_roles": {"Sarah": "Product Manager"},
  "confidence_signals": ["tentative"],
  "temporal": "future_plan"
}
```

**12 entity types in the tagging enum:** feature, persona, workflow, constraint, stakeholder, business_driver, data_entity, competitor, vp_step, solution_flow_step, unlock, prototype_feedback.

Tags enable filtered retrieval: "Find chunks where decisions were made about payment processing" → filter `decision_made=true` + topic contains `payment`.

---

## 11. SPEAKER RESOLUTION — Who Said What

Transcripts contain speaker names that need to match to stakeholders in the BRD.

```
Transcript: "John: I think the timeline is too aggressive"
                │
                ▼
Tier 1: EXACT MATCH
    "John" vs stakeholders.name → no exact match
                │
                ▼
Tier 2: FUZZY MATCH (threshold 0.75)
    "John" vs "John Smith" → token_set_ratio = 0.82 → MATCH
                │
                ▼
Tier 3: INITIAL + LAST NAME
    "J. Smith" vs "John Smith" → initial match → MATCH

Result: Memory nodes get speaker_name="John Smith" (resolved)
        Chunks get speaker attribution
        Beliefs linked to specific stakeholders
```

---

## 12. INTELLIGENCE BRIEFING

The briefing engine synthesizes intelligence from across the system into actionable sections.

```
Briefing Generation (triggered on demand, cached)
    │
    ├──▶ Temporal Diff: What changed since last briefing?
    │    • New entities, updated entities, new confirmations
    │    • Computed from enrichment_revisions timestamps
    │
    ├──▶ Hypothesis Engine: What do we believe and why?
    │    • Low-confidence beliefs surfaced as hypotheses
    │    • Supporting/contradicting evidence via retrieval
    │
    ├──▶ Tension Detector: Where do stakeholders disagree?
    │    • Contradiction edges in memory graph
    │    • Conflicting stakeholder signals
    │
    └──▶ 8 briefing sections assembled (zero additional LLM cost)
         1. Executive summary
         2. Key changes since last session
         3. Confidence shifts (beliefs that moved significantly)
         4. Emerging patterns
         5. Stakeholder alignment/tension
         6. Open questions (prioritized)
         7. Risk signals
         8. Recommended next actions
```

---

## 13. COST ARCHITECTURE

| Operation | Model | Cost per Unit | Notes |
|-----------|-------|--------------|-------|
| Chat message (read) | Haiku 3.5 | ~$0.003 | 1 turn, no tools |
| Chat message (write) | Haiku 3.5 | ~$0.008 | 2-3 tool turns |
| Signal extraction (per chunk) | Haiku 3.5 | ~$0.001 | Cached system prompt |
| Meta-tagging (per chunk) | Haiku 4.5 | ~$0.0003 | 512 max tokens |
| Entity dedup (tier 3) | text-embed-3 | ~$0.001 | Only ambiguous zone |
| Retrieval decomposition | Haiku 3.5 | ~$0.001 | Skipped for simple queries |
| Retrieval reranking | Haiku 3.5 | ~$0.002 | Only if >10 candidates |
| Question auto-resolution | Haiku 3.5 | ~$0.001/q | Parallel, fire-and-forget |
| Solution flow decompose | Haiku 3.5 | ~$0.001 | 200 tokens output |
| Solution flow per-phase | Sonnet | ~$0.045 | 3K tokens output |
| Solution flow stitch | Haiku 3.5 | ~$0.002 | 500 tokens output |
| Confirmation clustering | text-embed-3 | ~$0.000 | Pure cosine, no LLM |
| Convergence tracking | — | $0.000 | Pure data analysis |
| Background narrative | — | $0.000 | Pure DB reads |
| Confirmation signal | text-embed-3 | ~$0.0001 | 1 embedding per event |
| Embedding (per entity) | text-embed-3 | ~$0.0001 | Fire-and-forget |

**Full document processing** (20-page transcript): ~$0.03 total (chunking + meta-tagging + extraction + embedding + memory)

**Solution flow generation**: ~$0.15 total (decompose + 3-4 parallel Sonnet + stitch)

**All tracking costs**: $0.00 (confirmation clustering, convergence tracking, background narratives, staleness cascade — pure data operations)

All LLM costs tracked in `llm_usage_log` table, visible in admin dashboard with per-project and per-operation breakdowns.

---

## 14. THE COMPOUND EFFECT — Why More Intelligence = Simpler LLM Calls

This is the architectural insight that makes AIOS fundamentally different from systems that bolt AI onto a database.

```
Traditional approach:
    User asks question → LLM calls 4-5 tools sequentially to gather context
    Each tool call = another round-trip, more tokens, more cost, more latency

AIOS approach:
    User asks question → retrieve() pre-fetches from ALL embedded types in ONE parallel query
    LLM gets rich context in the system prompt → fewer tool calls, simpler reasoning
```

**Every new embedded type makes every existing consumer smarter.** When we added unlock embeddings, the chat assistant could suddenly answer "What opportunities would voice-first unlock?" without any tool calls — the retrieve() pre-fetch already surfaced relevant unlocks alongside features and competitors.

**When we added prototype feedback embeddings**, the briefing engine could surface prototype validation alongside entity evidence — "The client said the dashboard was too slow during Session 2" shows up next to "Feature: Real-Time Dashboard" automatically.

**When we added confirmation signals as memory facts**, retrieve() started surfacing "Client confirmed Risk Scoring on Feb 15" alongside the entity itself. Temporal context for free.

The pattern:

```
Embed more → retrieve() surfaces richer context → LLM needs fewer tool calls
                                                → simpler prompts
                                                → cheaper per-message
                                                → faster responses
                                                → more accurate answers
```

This is why the entity coverage expansion matters:

| Version | Embedded Types | match_entities UNIONs | Retrieval Surface |
|---------|---------------|----------------------|-------------------|
| v1 (initial) | 9 | 9 | Core BRD entities |
| v2 (+flow) | 10 | 10 | + Solution flow steps |
| v3 (current) | 12 | 12 | + Unlocks + Prototype feedback |
| + memory | — | — | + Confirmation events as facts |

And the meta-tag enum expansion (9 → 12 types) means chunk-level tagging now recognizes solution flow steps, unlocks, and prototype feedback discussions in documents — enabling filtered retrieval like "find chunks where unlock opportunities were discussed."

---

## 15. EVERYTHING IS POSTGRESQL

```
┌─────────────────────────────────────────────────────────────────────┐
│                      ONE SUPABASE INSTANCE                          │
│                                                                     │
│  Relational        │  Vector (pgvector)   │  Document (JSONB)       │
│  ─────────────     │  ────────────────    │  ──────────────         │
│  FK constraints    │  14 embedding cols   │  meta_tags per chunk    │
│  CHECK constraints │  3 match_* RPCs      │  overlay_content        │
│  Cascade deletes   │  ivfflat indexes     │  evidence arrays        │
│  Enrichment revs   │  cosine similarity   │  ai_config per step     │
│                    │                      │  open_questions per step │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Graph (recursive CTE)  │  Real-time       │  Storage               │
│  ─────────────────────  │  ──────────      │  ────────              │
│  Entity neighborhood    │  Live updates    │  Document files        │
│  Path finding (BFS)     │  Subscriptions   │  Prototype assets      │
│  Tension detection      │  Change feeds    │  Brand logos           │
│  Reverse provenance     │                  │                        │
│                                                                     │
│  Auth (GoTrue)          │  Edge Functions   │  Row Level Security    │
│  ──────────────         │  ───────────────  │  ──────────────────   │
│  JWT validation         │  Webhook handlers │  Per-project isolation │
│  Role-based access      │                  │  Client portal scoping │
└─────────────────────────────────────────────────────────────────────┘
```

No Pinecone. No Elasticsearch. No Redis. No Neo4j. No separate vector database.

One database. One deployment. One connection string. One backup strategy. One bill.

---

## THE ELEVATOR PITCH

What makes AIOS genuinely different from "we use AI to write requirements":

1. **Full provenance chain.** Every field in the BRD traces to the exact paragraph, speaker, and timestamp where it was discussed. Click-through from requirement to evidence. This is why consultants trust it — it's defensible.

2. **One retrieval system, every flow.** Retrieval improvements (better embeddings, richer meta-tags, new entity types) automatically benefit chat, briefing, solution flow, gap analysis, unlocks, and prototype feedback. No per-flow maintenance. 7 consumers, 1 pipeline.

3. **Confirmations are compound signals.** When a consultant confirms a requirement, that confirmation becomes an embedded memory fact, triggers question auto-resolution, cascades to the solution flow, and survives regeneration as a hard constraint. When evidence contradicts a confirmed entity, it's demoted to needs_review — not deleted. The system respects human judgment.

4. **Parallel-first, chunk-level processing.** Instead of feeding a truncated document to one expensive model, AIOS fans out cheap Haiku calls per chunk (extraction, meta-tagging, memory observation) and merges results. 100% coverage, 10x cheaper, evidence-linked per paragraph.

5. **Everything compounds.** Adding unlock embeddings made chat, briefing, solution flow, and gap intelligence all smarter in one commit. Adding prototype feedback embeddings closed the validation loop. Adding confirmation signals as memory facts made every retrieval query temporally aware. Each new embedded type multiplies the intelligence of every consumer.

6. **Everything is PostgreSQL.** One Supabase instance handles relational data, vector search (pgvector), JSONB metadata, recursive CTE graph traversal, real-time subscriptions, file storage, auth. One database, one deployment, one bill. Zero infrastructure sprawl.
