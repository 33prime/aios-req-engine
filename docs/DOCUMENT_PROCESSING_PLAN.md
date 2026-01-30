# Document Processing System - Implementation Plan

## Overview

A unified document processing system that handles PDF, DOCX, XLSX, PPTX, and images with smart chunking, contextual embedding, and hybrid search. Supports both consultant workbench and client portal uploads.

## Architecture Decision Records

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Memory chunks storage | Reuse `signal_chunks` with `section_type='memory_*'` | Unified search, simpler architecture |
| Chunk strategy | One chunk per semantic section | Matches research approach, better retrieval |
| Hybrid search weights | 0.7 vector / 0.3 keyword | Standard balance, tunable later |
| Processing queue | Database queue (polling) | Simple, sufficient for current scale |
| File storage | Supabase Storage | Already integrated, simple |
| OCR fallback | Tesseract → Claude Vision | Open source first, escalate when needed |

## Size Limits

| Type | Limit | Max Pages/Sheets |
|------|-------|------------------|
| Images (PNG, JPG, WebP) | 5 MB | - |
| PDF | 10 MB | 100 pages |
| DOCX | 10 MB | - |
| XLSX | 5 MB | 20 sheets |
| PPTX | 15 MB | 50 slides |

---

## Phase 1: Foundation (Database + Storage)

### Task 1.1: Document Uploads Migration
**Priority**: Critical | **Estimate**: Small | **Dependencies**: None

Create migration for `document_uploads` table and related indexes.

```sql
-- migrations/0086_document_uploads.sql

-- Document uploads tracking
CREATE TABLE document_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- File info
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'xlsx', 'pptx', 'image')),
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    checksum TEXT,  -- SHA256 for deduplication

    -- Classification (AI-assigned)
    document_class TEXT,  -- 'prd', 'transcript', 'spec', 'email', etc.
    quality_score FLOAT CHECK (quality_score >= 0 AND quality_score <= 1),
    relevance_score FLOAT CHECK (relevance_score >= 0 AND relevance_score <= 1),

    -- Processing status
    processing_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_priority INTEGER DEFAULT 50,
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_error TEXT,
    processing_duration_ms INTEGER,

    -- Extraction metadata
    page_count INTEGER,
    word_count INTEGER,
    total_chunks INTEGER,
    content_summary TEXT,
    keyword_tags TEXT[],
    extraction_method TEXT,  -- 'native', 'ocr', 'vision'

    -- Source tracking
    uploaded_by UUID REFERENCES auth.users(id),
    upload_source TEXT NOT NULL CHECK (upload_source IN ('workbench', 'client_portal', 'api')),
    authority TEXT NOT NULL DEFAULT 'consultant' CHECK (authority IN ('client', 'consultant')),

    -- Link to signal (created after processing)
    signal_id UUID REFERENCES signals(id),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_document_uploads_project ON document_uploads(project_id);
CREATE INDEX idx_document_uploads_status ON document_uploads(processing_status, processing_priority DESC);
CREATE INDEX idx_document_uploads_checksum ON document_uploads(checksum) WHERE checksum IS NOT NULL;

-- Full-text search index on signal_chunks (if not exists)
CREATE INDEX IF NOT EXISTS idx_signal_chunks_fts
ON signal_chunks USING gin(to_tsvector('english', content));

-- Add document_upload_id to signal_chunks
ALTER TABLE signal_chunks ADD COLUMN IF NOT EXISTS document_upload_id UUID REFERENCES document_uploads(id);
ALTER TABLE signal_chunks ADD COLUMN IF NOT EXISTS page_number INTEGER;
ALTER TABLE signal_chunks ADD COLUMN IF NOT EXISTS section_path TEXT;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_document_uploads_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_document_uploads_updated_at
    BEFORE UPDATE ON document_uploads
    FOR EACH ROW
    EXECUTE FUNCTION update_document_uploads_updated_at();

-- RLS policies
ALTER TABLE document_uploads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view document uploads for their projects"
ON document_uploads FOR SELECT
USING (
    project_id IN (
        SELECT pm.project_id FROM project_members pm
        WHERE pm.user_id = auth.uid()
    )
);

CREATE POLICY "Users can insert document uploads for their projects"
ON document_uploads FOR INSERT
WITH CHECK (
    project_id IN (
        SELECT pm.project_id FROM project_members pm
        WHERE pm.user_id = auth.uid()
    )
);
```

**Files to create**:
- `migrations/0086_document_uploads.sql`

---

### Task 1.2: Hybrid Search Function
**Priority**: Critical | **Estimate**: Small | **Dependencies**: 1.1

Add hybrid search (vector + keyword) to database.

```sql
-- Add to migration or separate file

CREATE OR REPLACE FUNCTION hybrid_search_chunks(
    query_text TEXT,
    query_embedding vector(1536),
    p_project_id UUID,
    match_count INTEGER DEFAULT 20,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    filter_document_class TEXT DEFAULT NULL,
    filter_authority TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    signal_id UUID,
    content TEXT,
    metadata JSONB,
    vector_score FLOAT,
    keyword_score FLOAT,
    combined_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        SELECT
            sc.id,
            sc.signal_id,
            sc.content,
            sc.metadata,
            1 - (sc.embedding <=> query_embedding) AS v_score
        FROM signal_chunks sc
        JOIN signals s ON sc.signal_id = s.id
        WHERE s.project_id = p_project_id
        AND (filter_document_class IS NULL OR sc.metadata->>'document_class' = filter_document_class)
        AND (filter_authority IS NULL OR sc.metadata->>'authority' = filter_authority)
        ORDER BY sc.embedding <=> query_embedding
        LIMIT match_count * 3
    ),
    keyword_results AS (
        SELECT
            sc.id,
            ts_rank_cd(to_tsvector('english', sc.content), plainto_tsquery('english', query_text)) AS k_score
        FROM signal_chunks sc
        JOIN signals s ON sc.signal_id = s.id
        WHERE s.project_id = p_project_id
        AND to_tsvector('english', sc.content) @@ plainto_tsquery('english', query_text)
        AND (filter_document_class IS NULL OR sc.metadata->>'document_class' = filter_document_class)
        AND (filter_authority IS NULL OR sc.metadata->>'authority' = filter_authority)
    ),
    combined AS (
        SELECT
            v.id,
            v.signal_id,
            v.content,
            v.metadata,
            v.v_score,
            COALESCE(k.k_score, 0) AS k_score,
            (vector_weight * v.v_score + keyword_weight * COALESCE(k.k_score, 0)) AS c_score
        FROM vector_results v
        LEFT JOIN keyword_results k ON v.id = k.id
    )
    SELECT
        c.id AS chunk_id,
        c.signal_id,
        c.content,
        c.metadata,
        c.v_score AS vector_score,
        c.k_score AS keyword_score,
        c.c_score AS combined_score
    FROM combined c
    ORDER BY c.c_score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

**Files to create/modify**:
- `migrations/0087_hybrid_search.sql`
- `app/db/hybrid_search.py` - Python wrapper

---

### Task 1.3: Database Operations Module
**Priority**: Critical | **Estimate**: Small | **Dependencies**: 1.1

Create CRUD operations for document_uploads table.

**Files to create**:
- `app/db/document_uploads.py`

```python
# Key functions:
- create_document_upload(project_id, filename, storage_path, ...)
- get_document_upload(upload_id)
- update_document_status(upload_id, status, error=None)
- get_pending_uploads(limit=10)  # For queue processing
- check_duplicate_by_checksum(project_id, checksum)
- list_project_uploads(project_id, status=None)
- complete_document_upload(upload_id, signal_id, chunks_count, ...)
```

---

## Phase 2: Extractors (Content Extraction)

### Task 2.1: Base Extractor Interface
**Priority**: High | **Estimate**: Small | **Dependencies**: None

Create base extractor class and registry.

**Files to create**:
- `app/core/document_processing/__init__.py`
- `app/core/document_processing/base.py`

```python
# app/core/document_processing/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class DocumentType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    PPTX = "pptx"
    IMAGE = "image"

@dataclass
class ExtractedSection:
    """A semantic section extracted from a document."""
    section_type: str  # 'heading', 'paragraph', 'table', 'list', 'image_description'
    section_title: Optional[str]
    content: str
    page_number: Optional[int]
    metadata: dict

@dataclass
class ExtractionResult:
    """Result of document extraction."""
    sections: List[ExtractedSection]
    page_count: int
    word_count: int
    extraction_method: str  # 'native', 'ocr', 'vision'
    raw_text: str  # Full text for fallback
    embedded_images: List[bytes]  # For separate vision analysis
    metadata: dict

class BaseExtractor(ABC):
    """Base class for document extractors."""

    @abstractmethod
    def can_handle(self, mime_type: str, file_extension: str) -> bool:
        """Check if this extractor can handle the file type."""
        pass

    @abstractmethod
    async def extract(self, file_bytes: bytes, filename: str) -> ExtractionResult:
        """Extract content from document."""
        pass

    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """Return list of supported MIME types."""
        pass
```

---

### Task 2.2: PDF Extractor
**Priority**: High | **Estimate**: Medium | **Dependencies**: 2.1

Extract content from PDFs using PyMuPDF, with OCR fallback.

**Files to create**:
- `app/core/document_processing/pdf_extractor.py`

```python
# Key capabilities:
- Text extraction with structure preservation (PyMuPDF)
- Page-by-page processing
- Table detection (basic)
- Image extraction for vision analysis
- OCR fallback for scanned PDFs (pytesseract)
- Claude Vision escalation for complex layouts
```

**Dependencies to add**: `PyMuPDF`, `pytesseract`, `pdf2image`

---

### Task 2.3: Image Extractor (Claude Vision)
**Priority**: High | **Estimate**: Medium | **Dependencies**: 2.1

Analyze images using Claude Vision API.

**Files to create**:
- `app/core/document_processing/image_extractor.py`

```python
# Key capabilities:
- Screenshot analysis (UI elements, text, data)
- Diagram interpretation
- Whiteboard/sketch analysis
- Chart/graph data extraction
- Structured output: type, text, elements, entities
```

---

### Task 2.4: DOCX Extractor
**Priority**: Medium | **Estimate**: Small | **Dependencies**: 2.1

Extract content from Word documents.

**Files to create**:
- `app/core/document_processing/docx_extractor.py`

```python
# Key capabilities:
- Heading hierarchy preservation
- List structure preservation
- Table extraction
- Embedded image extraction
- Comments/track changes capture
```

**Dependencies to add**: `python-docx`

---

### Task 2.5: XLSX Extractor
**Priority**: Medium | **Estimate**: Small | **Dependencies**: 2.1

Extract content from Excel spreadsheets.

**Files to create**:
- `app/core/document_processing/xlsx_extractor.py`

```python
# Key capabilities:
- Sheet-by-sheet processing
- Table structure preservation
- Named range detection
- Header row detection
- Summary generation per sheet
```

**Dependencies to add**: `openpyxl`

---

### Task 2.6: PPTX Extractor
**Priority**: Low | **Estimate**: Small | **Dependencies**: 2.1

Extract content from PowerPoint presentations.

**Files to create**:
- `app/core/document_processing/pptx_extractor.py`

```python
# Key capabilities:
- Slide-by-slide extraction
- Speaker notes capture (often high value!)
- Title + content structure
- Embedded image extraction
```

**Dependencies to add**: `python-pptx`

---

## Phase 3: Smart Chunking & Embedding

### Task 3.1: Contextual Prefix Builder
**Priority**: Critical | **Estimate**: Small | **Dependencies**: None

Create universal contextual prefix for all chunks.

**Files to create**:
- `app/core/document_processing/contextual.py`

```python
def build_contextual_prefix(
    document_title: str,
    document_type: str,
    document_summary: str,
    authority: str,
    section_title: str = None,
    quality_score: float = None,
    page_number: int = None,
) -> str:
    """
    Build contextual prefix for embedding.

    This improves retrieval by ~49% (Anthropic research).
    Prepended to every chunk before embedding.
    """
    ...
```

---

### Task 3.2: Document Classifier
**Priority**: High | **Estimate**: Medium | **Dependencies**: 2.1

Claude-powered document classification and quality scoring.

**Files to create**:
- `app/core/document_processing/classifier.py`

```python
# Uses Claude Haiku for speed
# Input: First 2000 tokens + structure metadata
# Output:
@dataclass
class ClassificationResult:
    document_class: str  # 'prd', 'transcript', 'spec', 'email', etc.
    quality_score: float  # 0-1
    relevance_score: float  # 0-1
    information_density: float  # 0-1
    key_topics: List[str]
    summary: str  # 2-3 sentences
    processing_priority: int  # 1-100
```

---

### Task 3.3: Unified Semantic Chunker
**Priority**: Critical | **Estimate**: Medium | **Dependencies**: 3.1, 3.2

Refactor chunking to use semantic sections + contextual prefix.

**Files to modify**:
- `app/core/chunking.py` (refactor)

**Files to create**:
- `app/core/document_processing/chunker.py`

```python
class UnifiedChunker:
    """
    Semantic chunking with contextual embedding.

    Strategy:
    1. Use extracted sections as base chunks
    2. Merge small sections, split large ones
    3. Add contextual prefix to each chunk
    4. Tag with metadata for filtering
    """

    def chunk_document(
        self,
        extraction_result: ExtractionResult,
        classification: ClassificationResult,
        document_metadata: dict,
    ) -> List[ChunkWithContext]:
        ...

    def chunk_by_strategy(
        self,
        sections: List[ExtractedSection],
        strategy: str,  # 'semantic', 'fixed', 'hybrid'
    ) -> List[Chunk]:
        ...
```

---

### Task 3.4: Update Embedding Pipeline
**Priority**: High | **Estimate**: Small | **Dependencies**: 3.3

Ensure embeddings include contextual prefix.

**Files to modify**:
- `app/core/embeddings.py`
- `app/db/phase0.py` (insert_signal_chunks)

```python
# The contextual prefix is already in chunk.content
# Just ensure we're embedding the full content with prefix
# Add batch processing optimization if not present
```

---

## Phase 4: Processing Pipeline

### Task 4.1: Upload API Endpoint
**Priority**: Critical | **Estimate**: Medium | **Dependencies**: 1.3

Create upload endpoint for workbench and client portal.

**Files to create**:
- `app/api/documents.py`

```python
@router.post("/documents/upload")
async def upload_document(
    project_id: UUID,
    file: UploadFile,
    upload_source: str,  # 'workbench' | 'client_portal'
    authority: str = 'consultant',
    background_tasks: BackgroundTasks,
) -> DocumentUploadResponse:
    """
    Upload and queue document for processing.

    1. Validate file type and size
    2. Calculate checksum, check for duplicates
    3. Upload to Supabase Storage
    4. Create document_uploads record (status: pending)
    5. Queue for background processing
    6. Return upload ID for status polling
    """
    ...

@router.get("/documents/{upload_id}/status")
async def get_upload_status(upload_id: UUID) -> DocumentStatusResponse:
    """Poll for processing status."""
    ...

@router.get("/projects/{project_id}/documents")
async def list_project_documents(project_id: UUID) -> List[DocumentSummary]:
    """List all documents for a project."""
    ...
```

---

### Task 4.2: Document Processing Graph
**Priority**: Critical | **Estimate**: Large | **Dependencies**: 2.*, 3.*, 4.1

LangGraph-based async processing pipeline.

**Files to create**:
- `app/graphs/document_processing_graph.py`

```python
"""
Document Processing Pipeline (LangGraph)

States:
    pending → extracting → classifying → chunking → embedding → creating_signal → completed
                                                                              ↘ failed

Nodes:
    1. validate_file: Check file integrity, size limits
    2. extract_content: Run appropriate extractor
    3. classify_document: Get type, quality, priority
    4. chunk_document: Semantic chunking with context
    5. embed_chunks: Generate embeddings
    6. create_signal: Create signal record, link chunks
    7. update_status: Mark completed or failed
"""

@dataclass
class DocumentProcessingState:
    upload_id: UUID
    project_id: UUID
    file_bytes: bytes
    filename: str
    file_type: str
    authority: str

    # Populated during processing
    extraction_result: ExtractionResult = None
    classification: ClassificationResult = None
    chunks: List[ChunkWithContext] = None
    embeddings: List[List[float]] = None
    signal_id: UUID = None
    error: str = None

def build_document_processing_graph() -> StateGraph:
    ...
```

---

### Task 4.3: Background Queue Processor
**Priority**: High | **Estimate**: Small | **Dependencies**: 4.2

Worker that polls and processes pending uploads.

**Files to create**:
- `app/workers/document_processor.py`

```python
async def process_pending_documents(batch_size: int = 5):
    """
    Poll for pending documents and process them.

    Called by:
    - Cron job (every 30 seconds)
    - After upload (immediate processing attempt)
    """
    pending = get_pending_uploads(limit=batch_size)

    for upload in pending:
        try:
            await run_document_processing_graph(upload)
        except Exception as e:
            update_document_status(upload.id, 'failed', str(e))
```

**Files to modify**:
- `app/main.py` - Add startup task or endpoint to trigger processing

---

### Task 4.4: Deduplication Enhancement
**Priority**: Medium | **Estimate**: Small | **Dependencies**: 1.1

Enhance deduplication for document uploads.

**Files to modify**:
- `app/core/chunk_deduplication.py`
- `app/db/document_uploads.py`

```python
# Document-level deduplication (by checksum)
async def check_and_handle_duplicate(project_id, checksum, filename):
    existing = check_duplicate_by_checksum(project_id, checksum)
    if existing:
        # Same file already uploaded
        return {"duplicate": True, "existing_id": existing.id}
    return {"duplicate": False}

# Chunk-level deduplication (existing MMR approach)
# Already implemented, just ensure it's called in pipeline
```

---

## Phase 5: Integration & Polish

### Task 5.1: Workbench UI Integration
**Priority**: High | **Estimate**: Medium | **Dependencies**: 4.1

Add document upload to workbench.

**Files to create/modify**:
- `apps/workbench/components/documents/DocumentUploader.tsx`
- `apps/workbench/components/documents/DocumentList.tsx`
- `apps/workbench/lib/api.ts` - Add upload functions

```typescript
// Drag-and-drop upload component
// Progress indicator
// Status polling
// Document list with status badges
```

---

### Task 5.2: Client Portal Upload
**Priority**: High | **Estimate**: Medium | **Dependencies**: 4.1, 5.1

Add document upload to client portal.

**Files to create/modify**:
- `apps/workbench/app/portal/[token]/components/DocumentUpload.tsx`

```typescript
// Simpler UI than workbench
// Clear size/type limits shown
// Upload status feedback
// List of uploaded documents
```

---

### Task 5.3: Assistant Command Integration
**Priority**: Medium | **Estimate**: Small | **Dependencies**: 4.2

Add `/upload` command to assistant.

**Files to modify**:
- `apps/workbench/lib/assistant/commands.ts`

```typescript
// /upload - Opens file picker, handles upload
// /documents - Lists project documents
// /document-status <id> - Check processing status
```

---

### Task 5.4: Hybrid Search Integration
**Priority**: Medium | **Estimate**: Small | **Dependencies**: 1.2

Wire hybrid search into existing retrieval paths.

**Files to modify**:
- `app/db/phase0.py` - Add `hybrid_search_chunks` wrapper
- `app/core/state_inputs.py` - Use hybrid search in retrieval
- `app/graphs/build_state_graph.py` - Use hybrid search

---

### Task 5.5: Project Memory Vectorization
**Priority**: Low | **Estimate**: Medium | **Dependencies**: 3.3

Add vectorized chunks from project memory for RAG.

**Files to modify**:
- `app/db/project_memory.py`

```python
# When decisions/learnings are added:
# 1. Create chunk with contextual prefix
# 2. Embed and store in signal_chunks
# 3. Tag with section_type='memory_decision' or 'memory_learning'
# 4. Low authority boost (1.0x) but available for context
```

---

## Dependency Graph

```
Phase 1 (Foundation)
├── 1.1 Document Uploads Migration
├── 1.2 Hybrid Search Function ──────────────────────────────┐
└── 1.3 Database Operations ─────────────────────────────────┤
                                                             │
Phase 2 (Extractors)                                         │
├── 2.1 Base Extractor Interface                             │
├── 2.2 PDF Extractor ← 2.1                                  │
├── 2.3 Image Extractor ← 2.1                                │
├── 2.4 DOCX Extractor ← 2.1                                 │
├── 2.5 XLSX Extractor ← 2.1                                 │
└── 2.6 PPTX Extractor ← 2.1                                 │
                                                             │
Phase 3 (Chunking & Embedding)                               │
├── 3.1 Contextual Prefix Builder                            │
├── 3.2 Document Classifier ← 2.1                            │
├── 3.3 Unified Semantic Chunker ← 3.1, 3.2                  │
└── 3.4 Update Embedding Pipeline ← 3.3                      │
                                                             │
Phase 4 (Pipeline)                                           │
├── 4.1 Upload API Endpoint ← 1.3                            │
├── 4.2 Document Processing Graph ← 2.*, 3.*, 4.1            │
├── 4.3 Background Queue Processor ← 4.2                     │
└── 4.4 Deduplication Enhancement ← 1.1                      │
                                                             │
Phase 5 (Integration)                                        │
├── 5.1 Workbench UI ← 4.1                                   │
├── 5.2 Client Portal Upload ← 4.1, 5.1                      │
├── 5.3 Assistant Commands ← 4.2                             │
├── 5.4 Hybrid Search Integration ← 1.2 ─────────────────────┘
└── 5.5 Project Memory Vectorization ← 3.3
```

---

## Implementation Order (Recommended)

### Sprint 1: Core Pipeline (Tasks 1.1 → 4.3)
1. **1.1** Document Uploads Migration
2. **1.3** Database Operations Module
3. **2.1** Base Extractor Interface
4. **2.2** PDF Extractor (most common)
5. **2.3** Image Extractor (critical for screenshots)
6. **3.1** Contextual Prefix Builder
7. **3.2** Document Classifier
8. **3.3** Unified Semantic Chunker
9. **4.1** Upload API Endpoint
10. **4.2** Document Processing Graph
11. **4.3** Background Queue Processor

### Sprint 2: Additional Extractors + Search
1. **2.4** DOCX Extractor
2. **2.5** XLSX Extractor
3. **1.2** Hybrid Search Function
4. **5.4** Hybrid Search Integration
5. **4.4** Deduplication Enhancement
6. **3.4** Update Embedding Pipeline

### Sprint 3: UI + Polish
1. **5.1** Workbench UI Integration
2. **5.2** Client Portal Upload
3. **5.3** Assistant Commands
4. **2.6** PPTX Extractor
5. **5.5** Project Memory Vectorization

---

## Python Dependencies to Add

```toml
# pyproject.toml additions
[project.dependencies]
PyMuPDF = "^1.24.0"      # PDF extraction
python-docx = "^1.1.0"   # DOCX extraction
openpyxl = "^3.1.0"      # XLSX extraction
python-pptx = "^0.6.23"  # PPTX extraction
pytesseract = "^0.3.10"  # OCR fallback
pdf2image = "^1.17.0"    # PDF to image for vision
python-magic = "^0.4.27" # File type detection
Pillow = "^10.0.0"       # Image processing
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Upload → Processing complete | < 30 seconds (small docs) |
| PDF extraction accuracy | > 95% text captured |
| Screenshot analysis quality | Captures all visible text + UI elements |
| Retrieval improvement (hybrid vs vector-only) | > 15% |
| Duplicate detection rate | 100% (by checksum) |
| Processing queue throughput | 10 docs/minute |

---

## Open Items / Future Enhancements

1. **Redis/Celery queue** - When scale demands it
2. **Batch upload** - Multiple files at once
3. **URL ingestion** - Fetch and process from URLs
4. **Version tracking** - Track document versions/updates
5. **OCR language support** - Non-English documents
6. **Audio/video transcription** - Meeting recordings
