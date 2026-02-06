# Signal Ingestion Evolution

## Current State

Signals are the raw inputs that feed AIOS:
- Emails, transcripts, notes, documents, research
- Processed via `document_processing_graph`
- Chunked, embedded, stored with metadata
- Used for extraction, enrichment, evidence

Ingestion methods:
1. **Chat drop**: Drag file into WorkspaceChat
2. **API ingest**: `POST /ingest` or `/research/ingest`
3. **Email capture**: Forward to routing address
4. **Meeting recording**: Auto-transcribe via bot

## Original Assumptions

1. Consultants have many scattered signals (emails, transcripts, notes)
2. Manual organization is the bottleneck
3. AI can extract structure from unstructured text
4. Evidence tracing requires chunk-level granularity
5. Authority matters: client signals vs consultant observations

## Evolution Timeline

### 2026-01-XX - Communication Integrations

**Trigger**: Manual upload is friction; consultants want auto-capture

**Before**: Manual file upload only

**After**:
- Gmail OAuth integration
- Email routing tokens (forward to AIOS)
- Meeting bot deployment (Recall.ai)
- Calendar sync for automatic recording

**Learning**:
- Auto-capture dramatically increases signal volume
- Need to handle duplicates and noise
- Privacy controls essential

### 2026-01-XX - Research Signal Type

**Trigger**: Research reports have different structure than emails

**Before**: All signals treated the same

**After**:
- `source_type` field: transcript, email, doc, note, research
- Research-specific chunking (preserves section structure)
- n8n webhook for automated research ingestion

**Learning**:
- Different signal types need different processing
- Research signals often higher quality than emails

### 2026-01-XX - Signal Classification

**Trigger**: Need to route signals to appropriate pipeline

**Before**: All signals go through full extraction

**After**:
- Lightweight vs heavyweight classification
- Lightweight: Quick update, merge into existing entities
- Heavyweight: Full extraction, fact clustering, state build

**Learning**:
- Most signals are lightweight (incremental info)
- Heavy extraction only needed for substantial new content

### Initial - Basic Ingestion

**Trigger**: Need a way to get data into the system

**Before**: N/A

**After**:
- `POST /ingest` endpoint
- Chunking (1200 chars, 120 overlap)
- pgvector embeddings for search
- `signal_chunks` table

**Learning**:
- Chunk size affects extraction quality
- Overlap prevents losing context at boundaries
- Vector search is powerful for evidence retrieval

---

## Open Questions

1. Optimal chunk size for different signal types?
2. Should we auto-dedupe similar signals?
3. How to handle conflicting info from different signals?
4. When to re-process old signals with new extraction?

## Related Features

- CL-002 (File Drop Upload)
- EV-001 (Evidence Panel)
- Backend: `/ingest`, `/research/ingest`, `document_processing_graph`
