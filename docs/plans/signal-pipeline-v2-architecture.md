# Signal Pipeline v2 — Architecture & Design Reference

**Date**: 2026-02-18
**Status**: Approved design — ready for implementation
**Authors**: Matt + Claude (design session)

---

## Executive Summary

The signal pipeline v2 replaces the old lightweight/heavyweight split with a single intelligent pipeline powered by the context engine and memory graph working as one brain. Every signal — regardless of source type or size — goes through the same pipeline with full BRD entity coverage. The system auto-applies high-confidence changes, proposes ambiguous ones in chat, and continuously learns through the memory graph.

**Core principles:**
1. One pipeline, not two — effort scales by content richness, not file size
2. Context + Memory = Intelligence — extraction is never blind
3. Surgical patches, not bulk replace — EntityPatch CRUD with confidence scoring
4. Chat is the confirmation interface — no "confirm 20 things" grid
5. Every modality is a signal — docs, chat, transcripts, images, prototype reviews

---

## 1. Pipeline Architecture

```
Signal arrives (any source type)
    │
    ▼
┌──────────────────────────────────────┐
│ PHASE 1: PREPROCESS (<2s, no LLM)    │
│                                       │
│ • Text extraction (PDF/PPTX/DOCX)    │
│ • Quick fingerprint: word count,      │
│   file type, first 500 chars          │
│ • Image extraction + storage          │
│ • Return immediately to user          │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ PHASE 2: TRIAGE + Q&A (<3s, Haiku)   │
│                                       │
│ • Source type classification          │
│ • Optional consultant Q&A:            │
│   "Who is this from? What context?"   │
│ • Assign extraction strategy          │
│ • Priority: "Does this resolve        │
│   anything in Hot context?"           │
│ • Skippable — "Process all" button    │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ PHASE 3: CHUNK + EMBED (<3s, async)   │
│                                       │
│ • Semantic chunking with context      │
│   prefixes (section path, doc type)   │
│ • Batch OpenAI text-embedding-3-small │
│ • Signal now searchable immediately   │
│ • Parallel per document               │
└──────────────┬───────────────────────┘
               │ event: "signal_ready"
               ▼
┌──────────────────────────────────────┐
│ PHASE 4: EXTRACT (Sonnet, 10-30s)    │
│                                       │
│ Dynamic prompt with 3 layers:         │
│                                       │
│ LAYER 1 — Context Graph:             │
│ • Full entity inventory with IDs      │
│ • Gaps & completeness scores          │
│ • Confirmation statuses               │
│                                       │
│ LAYER 2 — Memory Graph:              │
│ • Active beliefs + confidence         │
│ • Open questions (unresolved)         │
│ • Recent insights & contradictions    │
│                                       │
│ LAYER 3 — Extraction Rules:          │
│ • Strategy-specific per source type   │
│ • Source authority mapping             │
│ • Entity reference instructions       │
│                                       │
│ Output: EntityPatch[]                 │
│   covering ALL 11 BRD entity types    │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ PHASE 5: MEMORY SCORE (Haiku, <1s)   │
│                                       │
│ For each patch:                       │
│ • Belief alignment → confidence adj   │
│ • Mention count → confidence adj      │
│ • Source authority → confirmation lvl  │
│ • Final confidence tier assignment    │
│                                       │
│ Tiers:                                │
│ • very_high → auto-apply              │
│ • high → auto-apply + summarize       │
│ • medium → apply + highlight in chat  │
│ • low → propose in chat, wait         │
│ • conflict → always ask               │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ PHASE 6: RESOLVE + APPLY              │
│                                       │
│ • Merge patches across docs (dedup)   │
│ • Apply atomically per confidence     │
│ • Record evidence links               │
│ • Create state revision               │
│                                       │
│ Simultaneously:                       │
│ • MemoryWatcher → facts → Synthesizer │
│ • Invalidate context frame cache      │
│ • Generate chat summary               │
│ • Cascade staleness propagation       │
└──────────────────────────────────────┘
```

---

## 2. Full BRD Entity Extraction Map

Every extraction run targets ALL entity types the BRD canvas displays:

| Entity Type | Key Fields to Extract | Notes |
|---|---|---|
| **Features** | name, overview, priority_group (MoSCoW), category, is_mvp | priority_group is NEW for extraction |
| **Actors** (personas) | name, role, goals, pain_points, demographics | Rename to "actors" conceptually |
| **Stakeholders** | name, title, stakeholder_type, influence_level, domain_expertise | Full structured extraction |
| **Workflows** | name, state_type (current/future), frequency_per_week, pairing | First-class entity, not just vp_steps |
| **Workflow Steps** | label, description, time_minutes, pain_description, benefit_description, automation_level, operation_type | ALL rich fields extracted |
| **Data Entities** | name, entity_category, fields[] (name/type/required/desc), evidence | Field-level schema extraction |
| **Business Drivers (Pains)** | title, business_impact, affected_users, current_workaround, frequency | Full structured sub-fields |
| **Business Drivers (Goals)** | title, success_criteria, owner, goal_timeframe, dependencies | Full structured sub-fields |
| **Business Drivers (KPIs)** | title, baseline_value, target_value, measurement_method, tracking_frequency | Full structured sub-fields |
| **Constraints** | title, constraint_type, linked_feature_ids, linked_entity_ids | With cross-entity linking |
| **Competitors** | name, is_design_reference, relevance_description | Distinguish competitor vs inspiration |
| **Vision** | statement (full text) | Extracted and set on project |

---

## 3. EntityPatch Schema

```python
class EvidenceRef(BaseModel):
    chunk_id: str
    quote: str  # Exact text from source
    page_or_section: str | None

class BeliefImpact(BaseModel):
    belief_summary: str
    impact: Literal["supports", "contradicts", "refines"]
    new_evidence: str

class EntityPatch(BaseModel):
    operation: Literal["create", "merge", "update", "stale", "delete"]
    entity_type: Literal[
        "feature", "persona", "stakeholder", "workflow",
        "workflow_step", "data_entity", "business_driver",
        "constraint", "competitor", "vision"
    ]
    target_entity_id: str | None  # None for create, required for others

    payload: dict  # Full entity for create, field patches for update/merge
    evidence: list[EvidenceRef]  # Source chunks with quotes

    confidence: Literal["very_high", "high", "medium", "low"]
    confidence_reasoning: str

    # Memory integration
    belief_impact: list[BeliefImpact] | None
    answers_question: str | None  # Open question ID this resolves

    # Extraction metadata
    source_authority: Literal["client", "consultant", "research", "prototype"]
    mention_count: int  # How many times mentioned in signal
```

### EntityPatch Operations

| Operation | When | How | Confirmation |
|---|---|---|---|
| **CREATE** | New entity not matching any existing | Insert with ai_generated status + full evidence | Per confidence tier |
| **MERGE** | New evidence for existing entity | Append evidence, update confidence if higher | Auto if high+ |
| **UPDATE** | Contradicts/enriches specific fields | Patch only changed fields, preserve confirmation, bump updated_at | Per confidence tier |
| **STALE** | New signal contradicts confirmed entity | Mark is_stale=true, add stale_reason, keep entity intact | Always chat |
| **DELETE** | Signal explicitly says "X is no longer needed" | Soft delete if ai_generated, stale if confirmed | Always chat |

### Confirmation Hierarchy (never downgrade)

```
confirmed_client > confirmed_consultant > ai_generated
```

- confirmed_client: only modified by another client signal
- confirmed_consultant: modified by consultant or client signals
- ai_generated: modified by any signal

### Confidence Scoring Matrix

| Signal Evidence | Belief Alignment | Mention Count | → Confidence |
|---|---|---|---|
| Explicit requirement | Supports high belief | 4+ | very_high |
| Explicit requirement | No related belief | 2-3 | high |
| Explicit requirement | Contradicts belief | any | low (conflict) |
| Implied/inferred | Supports high belief | 2+ | high |
| Implied/inferred | No related belief | 1 | medium |
| Implied/inferred | Contradicts belief | any | low (conflict) |

### Auto-Apply Rules

| Confidence | Action | Chat Behavior |
|---|---|---|
| very_high | Auto-apply immediately | Mention in summary |
| high | Auto-apply immediately | Summarize with detail |
| medium | Apply but flag | Highlight, easy to undo |
| low | Do NOT apply | Propose in chat, wait for response |
| conflict | Do NOT apply | Show both sides, ask explicitly |

---

## 4. Context + Memory Integration

### How Context Engine and Memory Graph Work Together

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│    CONTEXT ENGINE            │     │    MEMORY GRAPH              │
│    (what exists NOW)         │     │    (what we BELIEVE)         │
│                              │     │                              │
│ • Entity inventory + IDs     │     │ • Facts (immutable, 1.0)    │
│ • Counts per type            │     │ • Beliefs (evolving, 0-1.0) │
│ • Confirmation statuses      │     │ • Insights (patterns)        │
│ • Completeness score         │     │ • Decisions (episodic)       │
│ • Top gaps                   │     │ • Learnings (procedural)     │
│ • Staleness indicators       │     │ • Open questions             │
│ • TerseActions (next steps)  │     │ • Contradictions             │
│                              │     │                              │
│ Refresh: SWR 30s + on-write  │     │ Refresh: on signal + events  │
└──────────────┬──────────────┘     └──────────────┬──────────────┘
               │                                    │
               └──────────────┬─────────────────────┘
                              │
                   ┌──────────▼──────────┐
                   │  UNIFIED PROMPT      │
                   │  CONTEXT SNAPSHOT    │
                   │                      │
                   │  Fed to every:       │
                   │  • Extraction run    │
                   │  • Chat response     │
                   │  • DI Agent call     │
                   │  • Memory scoring    │
                   └─────────────────────┘
```

### Memory Agent Integration Points

**MemoryWatcher** (Haiku, ~$0.001/call) — runs AFTER patches are applied:
- Extracts immutable facts from the signal processing event
- Scores importance (0.0-1.0)
- Detects contradictions with existing beliefs
- If importance >= 0.7 OR contradictions → triggers MemorySynthesizer

**MemorySynthesizer** (Sonnet, ~$0.02/call) — runs when triggered:
- Receives new facts + active beliefs + edges
- Creates/updates beliefs, adjusts confidence scores
- Creates supporting/contradicting edges
- Marks synthesis cache stale

**MemoryReflector** (Sonnet, ~$0.03/call) — runs periodically:
- Scans all beliefs, facts, insights
- Generates insights: behavioral, contradiction, evolution, risk, opportunity
- Archives old insights (>60 days, no usage)
- Archives low-confidence beliefs (<0.3, >7 days)

### Memory in the Extraction Prompt

The extraction LLM receives memory as structured context:

```
## Project Beliefs (from memory graph)
• [0.85] "Client prioritizes real-time features" — 4 supporting facts
• [0.60] "Budget constraint ~$200K" — 1 supporting fact
• [0.45] "CTO prefers async architecture" — CONTRADICTED by 1 fact

## Open Questions
• Authentication method? (SSO/OAuth/SAML — unresolved)
• Mobile native vs PWA? (no evidence either way)
• Data residency requirements? (mentioned but unclear)

## Recent Insights
• PATTERN: Scope expanding with each signal
• RISK: No compliance stakeholder identified yet
• EVOLUTION: Project framing shifted from B2B to B2B2C
```

The extraction prompt then instructs:
1. For each EntityPatch, note if it supports or contradicts a belief
2. Flag any answers to open questions
3. Prioritize extraction of entities that fill top gaps
4. Reference existing entity IDs for merge/update operations

---

## 5. Tiered Memory Storage

```
┌────────────────────────────────────────────────────┐
│  HOT: Working Context (always fresh, <30s old)      │
│                                                      │
│  • Context frame (Haiku, auto-refresh 30s)           │
│  • Entity inventory (counts, gaps, completeness)     │
│  • Active beliefs (confidence > 0.3)                 │
│  • Open questions (unresolved)                       │
│  • Recent insights (< 30 days)                       │
│  • TerseActions (what to do next)                    │
│                                                      │
│  Forcing functions:                                  │
│  • SWR refresh every 30s on frontend                 │
│  • Cache invalidation on any entity write            │
│  • Beliefs < 0.3 confidence → archived               │
│  • Insights > 60 days unused → archived              │
│  • Loaded into EVERY extraction/chat prompt           │
├──────────────────────────────────────────────────────┤
│  WARM: Project Memory (synthesized, ~minutes)        │
│                                                      │
│  • Unified memory synthesis (Sonnet, cached)         │
│  • Decision history (with landmarks preserved)       │
│  • Learning journal (patterns, mistakes)             │
│  • Belief evolution trajectories                     │
│  • Archived beliefs (still queryable)                │
│                                                      │
│  Forcing functions:                                  │
│  • Compaction at 2000 tokens → 800 target            │
│  • Landmark decisions never compacted                │
│  • Dedup repeated decision titles                    │
│  • Low-confidence beliefs archived after 7 days      │
│  • Queried for: chat context, DI Agent, "why" Qs     │
├──────────────────────────────────────────────────────┤
│  COLD: Long-Term Evidence (full history, immutable)  │
│                                                      │
│  • All facts (immutable, append-only)                │
│  • All signal chunks + embeddings                    │
│  • Belief history (full audit trail)                 │
│  • State revisions (entity snapshots)                │
│  • Archived insights and beliefs                     │
│                                                      │
│  Forcing functions:                                  │
│  • Read-only (append-only)                           │
│  • Never loaded into extraction prompts              │
│  • Queried for: evidence drill-down, audit trail,    │
│    "why did we believe X 3 weeks ago?"               │
└──────────────────────────────────────────────────────┘
```

---

## 6. Source-Specific Extraction Strategies

Same pipeline, different prompts and post-processing per source type:

| Source Type | Triage Hint | Extraction Focus | Special Handling |
|---|---|---|---|
| **Requirements Doc** (PDF/DOCX) | Formal structure, >5 pages | Full entity sweep, all 11 types | High entity volume, cross-reference dedup |
| **Presentation** (PPTX) | Slide structure, image-heavy | Slide-by-slide + image analysis | Vision model for wireframes, exec narrative |
| **Meeting Transcript** | Speaker labels, conversational | Speaker→stakeholder mapping, decisions, actions | Diarization preprocessing, "who said what" evidence |
| **Meeting Notes** | Informal, short, bullet points | Quick facts, action items, decisions | Lightweight, high consultant authority |
| **Chat Messages** | Already structured, incremental | Micro-extraction, entity detection | Batched (every N messages or on entity trigger) |
| **Email Thread** | Sender/recipients + body | Stakeholder identification, decisions, actions | Parse email metadata for authority |
| **Prototype Review** | Verdicts + ratings + chat | Feature confirmation/rejection, UI requirements | Dual output: entity patches + code changes |
| **Research/Discovery** | AI-generated, structured | Competitor intel, market data, industry context | High confidence ai_generated, never client-confirmed |
| **Images** (standalone) | Screenshots, wireframes | Vision model: implied requirements, UI patterns | Creates features/data_entities from visual content |
| **AI-Generated Doc** (external) | Structured, from another tool | Schema mapping to our entity types | Parse their structure → our EntityPatch format |

### Chat as Continuous Signal

Instead of manual `/add-signal`:
- Every N messages (e.g., 5) or when entity detection fires → auto-create micro-signal
- Micro-signals go through same pipeline (lightweight extraction, same context)
- Chat context is ALWAYS part of the project knowledge base
- Consultant doesn't need to do anything — it just works

### Prototype Review as Signal

During prototype review sessions:
- Consultant verdicts + client ratings + chat = accumulated signal
- End of session (or every N messages) → synthesize → EntityPatch[]
- Dual output:
  - Entity patches → update BRD (feature confirmations, new requirements, stale features)
  - Code change requirements → prototype update pipeline (Opus plan → Sonnet exec)
- Client explicit feedback → `confirmed_client` authority (strongest)

---

## 7. Consultant Upload Q&A

When documents arrive, optional quick-context gathering:

```
📄 requirements-v3.pdf (42 pages, formal structure)
   Looks like a requirements doc.
   [From Client] [Internal Draft] [External/Other]

📝 meeting-notes-feb.docx (3 pages, informal)
   Meeting notes — who was in this meeting?
   [CTO + Engineering] [Product Team] [Client Stakeholders] [Skip]

🎨 wireframes.pptx (12 slides, image-heavy)
   Presentation with visuals. Analyze wireframes for UI requirements?
   [Yes] [No, just text]
```

**Always skippable** — "Process All" button uses heuristics. The Q&A is an optimization:
- Source authority → confirmation_status derivation
- Stakeholder context → speaker attribution
- Processing hints → skip unnecessary analysis

---

## 8. Chat as Confirmation Interface

Instead of a grid of checkboxes, the chat presents intelligent summaries:

```
Processed requirements-v3.pdf. Key findings:

 🆕 3 new features (auto-applied, high confidence):
    • Real-time collaboration — aligns with strong pattern (4 prior signals)
    • SSO integration — explicit requirement with deadline
    • Audit trail export — mentioned in compliance section

 🔄 2 existing features enriched:
    • 'User dashboard' — added 3 acceptance criteria from Section 4.2
    • 'Notification system' — now includes SMS (scope change)

 ⚠️ 1 conflict needs your input:
    'Async-first architecture' was high-confidence (0.85) based on CTO's
    initial meeting. This doc explicitly calls for real-time sync.
    Should I update the architecture direction? [Update] [Keep both] [Ignore]

 ❓ 1 open question answered:
    Auth method → "SAML SSO required for enterprise tier" (Section 4.3)
    Applied as confirmed_client.

 💡 Memory insight: This is the 3rd signal expanding scope.
    Consider discussing scope boundaries with the client.
```

---

## 9. Deprecated Code (to be replaced)

### Signal Classification System
| File | Status | Replacement |
|---|---|---|
| `app/core/signal_classifier.py` | **DEPRECATED** | Heuristic fingerprint in triage phase |
| Classification LLM call | **REMOVED** | No LLM classification — pure heuristic |

### Lightweight/Heavyweight Split
| File | Status | Replacement |
|---|---|---|
| `app/graphs/build_state_graph.py` | **DEPRECATED** | Unified extraction pipeline |
| `app/chains/build_state.py` | **DEPRECATED** | New extraction prompt (all 11 entity types) |
| `app/graphs/bulk_signal_graph.py` | **DEPRECATED** | Unified extraction pipeline |

### Bulk Replace Persistence
| File / Function | Status | Replacement |
|---|---|---|
| `app/db/features.py: bulk_replace_features()` | **DEPRECATED** | EntityPatch applicator (surgical CRUD) |
| `app/db/vp.py: upsert by step_index` | **DEPRECATED** | EntityPatch applicator |
| `app/db/personas.py: upsert by slug` | **DEPRECATED** | EntityPatch applicator |

### Old Extraction Chains
| File | Status | Replacement |
|---|---|---|
| `app/chains/extract_facts.py` | **REWRITE** | New extraction prompt with 3-layer context |
| `app/graphs/extract_facts_graph.py` | **REWRITE** | New extraction graph with memory scoring |
| Consolidation functions in bulk_signal_graph | **DEPRECATED** | EntityPatch resolver |

### Old Proposal System
| Component | Status | Replacement |
|---|---|---|
| `generate_proposal` node | **DEPRECATED** | Chat-based confirmation interface |
| `save_proposal` node | **DEPRECATED** | EntityPatch applicator |
| Proposal review UI | **DEPRECATED** | Chat summary with inline actions |

---

## 10. Performance Targets

| Phase | Target | Current |
|---|---|---|
| Document preprocessing | <2s | 10-60s (includes LLM classification) |
| Triage + Q&A | <3s | N/A (new) |
| Chunk + embed | <3s | 2-3s (already OK) |
| Signal searchable | <8s total | 30-90s |
| Entity extraction | 10-30s | 15s (light) / 1-5min (heavy) |
| Memory scoring | <1s | N/A (new) |
| Patch application | <1s | <1s (already fast) |
| Full pipeline end-to-end | <35s | 30s-6min |
| Chat summary delivery | <40s from upload | Never (manual review) |

---

## 11. Open Design Questions

1. **Batch vs per-doc extraction**: When 5 docs uploaded simultaneously, extract per-doc in parallel then merge? Or concatenate chunks and extract once? (Lean: parallel per-doc, merge at resolve phase)
2. **Chat auto-signal threshold**: Every 5 messages? On entity detection? On explicit requirement mention? (Lean: entity detection trigger + 10-message floor)
3. **Image analysis model**: Claude Sonnet vision for wireframe analysis? Cost vs value?
4. **Prototype feedback granularity**: Process per-verdict or per-session? (Lean: per-session with mid-session extraction if >10 interactions)
5. **Cross-project learning**: Should beliefs/patterns from Project A inform Project B for same client? (Lean: yes, via client intelligence agent)
6. **Rollback strategy**: If a batch of patches is bad, undo via state revisions? Or patch reversal? (Lean: state revisions + "undo last signal" command)

---

*This document is the canonical reference for Signal Pipeline v2 architecture. Implementation plan is in `docs/plans/signal-pipeline-v2-implementation.md`.*
