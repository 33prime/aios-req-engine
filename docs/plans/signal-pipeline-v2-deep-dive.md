# Signal Pipeline v2 — Deep Dive Research & Redesign Notes

**Date**: 2026-02-18
**Status**: Research complete, awaiting design session
**Goal**: Redesign signal processing to be fast, surgical, and context-engine-powered

---

## 1. Current Architecture

### Entry Points
| Source | Format | Current Path |
|--------|--------|-------------|
| Document upload | PDF, PPTX, DOCX | document_processing_graph → signal pipeline |
| Text paste | Raw text | Direct signal creation → pipeline |
| Chat | Conversation | Manual `/add-signal` only — NOT automatic |
| Email | Text + attachments | Signal creation → pipeline |
| Research | AI-generated findings | Signal creation → pipeline |
| Images | PNG, JPEG, WebP, GIF | Extracted but NOT analyzed for requirements |
| Transcripts | Text (from Recall.ai) | Treated as generic text signal |

### Document Processing Graph (LangGraph)
```
load_document → download_file → extract_content → process_embedded_images
  → classify_content → create_chunks → create_signal_and_embed → finalize
```

- **Extractors**: PyPDF2 (PDF), python-pptx (PPTX), standard (DOCX)
- **Classification**: LLM call to determine doc type + quality (2-3s overhead)
- **Chunking**: Semantic split with contextual prefixes (section path, doc type, page)
- **Embedding**: Batch OpenAI `text-embedding-3-small` (~2-3s for 500 chunks)
- **Finalize**: Background thread triggers signal pipeline

### Signal Classification
Heuristic + metadata-based routing:
- **LIGHTWEIGHT** (< 50KB, < 3K words, simple) → `build_state_graph`
- **HEAVYWEIGHT** (>= 50KB, formal spec, BRD) → `bulk_signal_graph`

### Lightweight Path: build_state_graph (~15s)
```
load_inputs → retrieve_chunks (vector search) → call_llm (GPT-4) → persist
```
- Fetches facts digest from last 6 signals
- Vector search with fixed queries (value proposition, workflows, personas, etc.)
- LLM synthesizes VP steps, features, personas
- **Bulk replace**: Preserves confirmed entities, replaces ai_generated ones

### Heavyweight Path: bulk_signal_graph (~1-5 min)
```
extract_facts → extract_stakeholders → extract_creative_brief
  → consolidate → validate → generate_proposal → save_proposal
```
- Uses Claude Sonnet for fact extraction (40-80+ facts per BRD)
- Extracts: features, pains, goals, KPIs, personas, stakeholders, current/future process steps, data entities, constraints, competitors, risks, assumptions
- Also extracts: open questions, contradictions, client info
- Generates batch proposal for consultant review

### Entity Persistence (Smart Merge)
- **Features**: `bulk_replace_features()` — preserves confirmed, replaces ai_generated, similarity matching (Levenshtein + semantic) at 0.70 threshold, conflict detection via cascade_events
- **VP Steps**: Upsert by (project_id, step_index)
- **Personas**: Upsert by (project_id, slug)
- **Confirmation status derived from source authority**: client signal → confirmed_client, consultant → confirmed_consultant, research → ai_generated
- **Signal impacts**: Batch RPC resolves chunk→signal mapping, creates evidence links

---

## 2. What's Broken / Slow

### Multi-Document Upload Failures
- Background thread-based processing (not queue-based) — can lose signals if process crashes
- Concurrent processing may hit race conditions on entity upserts
- Heavyweight path timeout (300s) on large docs
- No retry mechanism if signal pipeline fails mid-stream

### Classification Bottleneck
- LLM call just to decide routing adds 2-3s per document
- Often wrong for edge cases (short BRD classified as lightweight)
- Could be pure heuristic: file size + word count + extension

### No Incremental Processing
- Every signal triggers full state rebuild
- 10th document still does bulk feature replace
- No diffing — can't tell "what changed" from this signal

### Bulk Replace is Destructive
- `bulk_replace_features()` deletes ALL ai_generated features then re-inserts
- If LLM has a bad run, you lose previously good extractions
- No rollback mechanism beyond state revisions (manual recovery)

### Chat-as-Signal Gap
- Chat messages contain valuable requirements info
- Currently requires manual `/add-signal` — consultants never do this
- Entity detection exists but saving is manual (user must click "Save as Requirements")

### Images Are Dead Weight
- Extracted from PPTX/PDF and stored in `extracted_images` table
- Never analyzed for requirements content
- Wireframes, mockups, diagrams — all ignored by extraction

### Transcripts Lack Speaker Intelligence
- Meeting transcripts treated as flat text
- No speaker diarization → stakeholder mapping
- No action item extraction
- No "who said what" evidence linking

---

## 3. The Vision: Context Engine-Powered Pipeline

### Core Principle
The signal pipeline should NOT be a one-shot extraction. It should be a **continuous context accumulation engine** that:

1. **Preprocesses instantly** — text extraction, chunking, embedding in <5s
2. **Extracts surgically** — knows what entities already exist, produces CRUD patches not bulk replacements
3. **Operates on full project context** — not just the new signal, but everything known
4. **Handles all modalities** — text, images, chat, transcripts, presentations
5. **Self-heals** — detects contradictions, staleness, missing evidence, and generates actions

### Proposed Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ PHASE 1: RAPID PREPROCESSING (<5s per doc)                  │
│                                                             │
│ Upload → Extract Text → Chunk → Embed → Signal Created     │
│                                                             │
│ - NO LLM classification (heuristic only)                    │
│ - Synchronous, blocking — user sees "ready" immediately     │
│ - Images extracted + stored for Phase 2 analysis            │
│ - Chunks immediately available for vector search            │
└─────────────────────┬───────────────────────────────────────┘
                      │ (async event: "signal_ready")
                      v
┌─────────────────────────────────────────────────────────────┐
│ PHASE 2: CONTEXT-AWARE EXTRACTION (async, ~10-30s)          │
│                                                             │
│ Load full project context snapshot:                         │
│ - All existing entities (features, personas, vp_steps...)   │
│ - Entity confirmation statuses                              │
│ - Open questions + contradictions                           │
│ - Recent signal summaries                                   │
│                                                             │
│ Extract facts from NEW signal chunks                        │
│                                                             │
│ Generate SURGICAL PATCHES:                                  │
│ - CREATE: Brand new entity not matching anything existing   │
│ - MERGE: New evidence for existing entity → append evidence │
│ - UPDATE: Contradicts or enriches existing → patch fields   │
│ - STALE: Existing entity contradicted → mark stale          │
│ - DELETE: Entity explicitly removed/deprecated in signal    │
│                                                             │
│ Output: EntityPatch[] (not bulk replacement)                │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────────────────────────────────┐
│ PHASE 3: APPLY & CASCADE                                    │
│                                                             │
│ Apply patches atomically:                                   │
│ - Respect confirmation hierarchy (never downgrade)          │
│ - Record evidence links (chunk → entity)                    │
│ - Create state revision for audit trail                     │
│ - Trigger cascading intelligence (staleness propagation)    │
│                                                             │
│ Update context frame:                                       │
│ - Recalculate completeness scores                           │
│ - Generate new TerseActions                                 │
│ - Notify frontend via SWR revalidation                      │
└─────────────────────────────────────────────────────────────┘
```

### EntityPatch Schema (proposed)

```python
class EntityPatch:
    operation: "create" | "merge" | "update" | "stale" | "delete"
    entity_type: "feature" | "persona" | "vp_step" | "stakeholder" | "data_entity"

    # For create: full entity payload
    # For merge/update: entity_id + field patches
    # For stale/delete: entity_id + reason
    target_entity_id: str | None  # None for create

    payload: dict  # Fields to set/merge
    evidence: list[Evidence]  # Source chunks
    confidence: "high" | "medium" | "low"
    reason: str  # Why this operation was chosen
```

### Modality-Specific Intelligence

| Modality | Preprocessing | Extraction Strategy |
|----------|--------------|-------------------|
| **PDF/DOCX** (requirements) | Text extract + chunk | Full fact extraction, heavy |
| **PPTX** (presentations) | Slide text + speaker notes + images | Slide-by-slide extraction, image analysis for wireframes |
| **Images** (screenshots, wireframes) | Store + OCR if text | Vision model analysis: "What requirements does this imply?" |
| **Transcripts** | Text + speaker labels | Speaker→stakeholder mapping, action items, decision points |
| **Chat messages** | Already text | Micro-signal: extract facts incrementally per message batch |
| **Email threads** | Parse sender/recipients + body | Stakeholder identification, decision tracking, action items |
| **Research** | AI-generated text | High-confidence facts, competitor intel, market data |

### Chat as Continuous Signal
Instead of manual `/add-signal`:
- Every N messages (e.g., 5) or when entity detection fires, auto-create micro-signal
- Micro-signals go through lightweight extraction
- Chat context is ALWAYS part of the project knowledge base
- Consultant doesn't need to do anything — it just works

### Image Intelligence
- Vision model (Claude Sonnet) analyzes extracted images
- Outputs: wireframe descriptions, UI requirements, data flow diagrams
- Creates features/vp_steps from visual content
- Links image as evidence (not just text chunks)

### Transcript Intelligence
- Speaker diarization → map speakers to stakeholders
- Extract: decisions, action items, requirements mentioned
- "Who said what" evidence: "John (CTO) said: we need real-time sync"
- Auto-create stakeholder entities from new speakers

---

## 4. Entity CRUD Intelligence

### Current Problem
The current system only does:
- **CREATE**: Bulk insert new entities
- **REPLACE**: Delete ai_generated, insert fresh (destructive)

### What We Need
Full CRUD with intelligence:

| Operation | When | How |
|-----------|------|-----|
| **CREATE** | New entity not matching any existing | Insert with ai_generated status, full evidence |
| **MERGE** | New signal adds evidence to existing entity | Append evidence array, update confidence if higher |
| **UPDATE** | New signal contradicts/enriches specific fields | Patch only changed fields, preserve confirmation, bump updated_at |
| **STALE** | New signal contradicts but existing is confirmed | Mark is_stale=true, add stale_reason, keep entity intact |
| **DELETE** | Signal explicitly says "X is no longer needed" | Soft delete (mark deprecated) if ai_generated, stale if confirmed |

### Confirmation Hierarchy (never downgrade)
```
confirmed_client > confirmed_consultant > ai_generated
```
- A confirmed_client entity can ONLY be modified by another client signal
- A confirmed_consultant entity can be modified by consultant or client signals
- An ai_generated entity can be modified by any signal

### Similarity Matching for Merge/Update
Existing `SimilarityMatcher` uses:
- Exact name match
- Fuzzy string (Levenshtein)
- Semantic (embedding cosine)
- Threshold: 0.70

This should stay but become part of the extraction LLM prompt:
- Give the LLM the existing entity list
- Ask it to reference existing entities by ID when appropriate
- LLM decides: "this is a new feature" vs "this enriches feature X"

---

## 5. Prototype Review Loop Integration

### Current Prototype Pipeline
```
Generate v0 prompt → v0 API → Prototype → Ingest → Bridge → Deploy
  → Feature Analysis → Consultant Review → Client Review
  → Feedback → Code Updates → Repeat
```

### How Signal Pipeline Connects
- **Prototype feedback** (consultant verdicts, client ratings) should be signals
- Each verdict = micro-signal that updates the corresponding feature
- "Feature X works well" → MERGE evidence, boost confidence
- "Feature X is wrong" → UPDATE or STALE the feature
- Client review ratings → confirmation_status upgrade to confirmed_client

### Questions to Resolve
- Should prototype overlay analysis feed back into entity evidence?
- How do we handle "feature exists in prototype but NOT in BRD"?
- Should the review loop create new features discovered during testing?

---

## 6. Performance Targets

| Phase | Target | Current |
|-------|--------|---------|
| Document preprocessing | <5s | 10-60s (includes LLM classification) |
| Signal ready (chunks searchable) | <5s | 30-90s (includes pipeline) |
| Entity extraction | <30s | 15s (light) / 1-5min (heavy) |
| Entity persistence | <1s | <1s (already fast) |
| Full pipeline (upload → entities) | <35s | 30s-6min |

### Key Optimizations
1. Drop LLM classification → pure heuristic (saves 2-3s)
2. Parallelize: preprocessing + embedding (not sequential)
3. Streaming extraction: start extracting while still chunking
4. Incremental processing: only process NEW chunks, not re-process everything

---

## 7. Open Questions for Design Session

1. **Batch vs streaming extraction**: Should we extract facts as chunks are created (streaming) or wait for all chunks (batch)?
2. **Proposal system**: Keep the heavyweight proposal flow for large BRDs, or always do surgical patches?
3. **Chat auto-signal threshold**: How many messages before auto-creating a micro-signal? Or use entity detection as the trigger?
4. **Image analysis model**: Claude Sonnet vision vs GPT-4V vs dedicated model?
5. **Transcript speaker mapping**: How to handle unknown speakers? Ask consultant to map names to stakeholders?
6. **Rollback strategy**: If a batch of patches is bad, how do we undo? State revisions exist but recovery is manual.
7. **Cost management**: More LLM calls (surgical per-signal) vs fewer (batch) — what's the budget?
8. **Prototype feedback loop**: How tightly coupled should review verdicts be to the entity pipeline?
9. **Cross-project learning**: Should extraction improve based on patterns from other projects?
10. **Real-time collaboration**: If two consultants upload simultaneously, how do we merge?

---

## 8. Key Files Reference

| Component | File | Purpose |
|-----------|------|---------|
| Document processing graph | `app/graphs/document_processing_graph.py` | LangGraph: upload → chunks → signal |
| PDF extractor | `app/core/document_processing/pdf_extractor.py` | PDF text + image extraction |
| PPTX extractor | `app/core/document_processing/pptx_extractor.py` | PowerPoint extraction |
| Image extractor | `app/core/document_processing/image_extractor.py` | Embedded image persistence |
| Chunker | `app/core/document_processing/chunker.py` | Semantic chunking |
| Signal classifier | `app/core/signal_classifier.py` | Lightweight vs heavyweight routing |
| Signal pipeline | `app/core/signal_pipeline.py` | Orchestrator: routes signal to graph |
| Extract facts chain | `app/chains/extract_facts.py` | Claude/GPT-4 fact extraction prompt |
| Extract facts graph | `app/graphs/extract_facts_graph.py` | LangGraph for extraction |
| Build state chain | `app/chains/build_state.py` | GPT-4 state synthesis prompt |
| Build state graph | `app/graphs/build_state_graph.py` | LangGraph for state building |
| Bulk signal graph | `app/graphs/bulk_signal_graph.py` | Heavyweight pipeline |
| Feature DB | `app/db/features.py` | bulk_replace_features, similarity matching |
| VP step DB | `app/db/vp.py` | Upsert VP steps |
| Persona DB | `app/db/personas.py` | Upsert personas |
| Signal DB | `app/db/signals.py` | Signal CRUD, impact tracking |
| Chat tools | `app/chains/chat_tools.py` | Tool definitions for chat assistant |
| Chat API | `app/api/chat.py` | Chat endpoint with tool calling |
| Config | `app/core/config.py` | Model settings, limits |
| LLM usage logger | `app/core/llm_usage.py` | Cost tracking |

---

## 9. Models & Costs

| Chain | Model | Est. Cost/Call | Frequency |
|-------|-------|---------------|-----------|
| Classification | LLM (to be removed) | ~$0.01 | Per document |
| Fact extraction | Claude Sonnet | ~$0.05 | Per heavyweight signal |
| State building | GPT-4 | ~$0.10 | Per lightweight signal |
| Feature enrichment | GPT-4-mini | ~$0.02 | Per feature (manual trigger) |
| Persona enrichment | GPT-4-mini | ~$0.02 | Per persona (manual trigger) |
| VP enrichment | GPT-4-mini | ~$0.02 | Per VP step (manual trigger) |
| Embedding | OpenAI small | ~$0.001 | Per batch (500 chunks) |

---

*This document is the foundation for the v2 signal pipeline design session. Next step: design the EntityPatch system, define the context snapshot schema, and map the prototype review feedback loop.*
