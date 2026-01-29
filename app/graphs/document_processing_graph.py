"""Document Processing Graph.

LangGraph workflow for processing uploaded documents:
1. Download file from storage
2. Extract content (PDF, image, etc.)
3. Classify the document
4. Chunk with contextual prefixes
5. Create signal and embed chunks
6. Update document status
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.core.config import get_settings
from app.core.document_processing import (
    ClassificationResult,
    ChunkWithContext,
    ExtractionResult,
    classify_document,
    chunk_document,
    get_extractor,
)
from app.core.logging import get_logger
from app.db.document_uploads import (
    get_document_upload,
    update_document_processing,
)
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

MAX_STEPS = 10

# Thread pool for running async code from sync context
_executor = ThreadPoolExecutor(max_workers=4)


def _run_async(coro):
    """Run an async coroutine from sync context safely.

    Works whether or not there's already an event loop running.
    """
    try:
        # Try to get existing loop
        loop = asyncio.get_running_loop()
        # If we're in an async context, run in thread pool
        import concurrent.futures
        future = _executor.submit(asyncio.run, coro)
        return future.result(timeout=300)  # 5 min timeout
    except RuntimeError:
        # No loop running - safe to use asyncio.run directly
        return asyncio.run(coro)


@dataclass
class DocumentProcessingState:
    """State for document processing graph."""

    # Input
    document_id: UUID
    run_id: UUID

    # Document info (loaded from DB)
    project_id: UUID | None = None
    original_filename: str = ""
    storage_path: str = ""
    file_type: str = ""
    mime_type: str = ""
    authority: str = "consultant"

    # Processing state
    step_count: int = 0
    started_at: str = ""
    start_time_ms: int = 0

    # Downloaded file
    file_bytes: bytes = b""

    # Extraction result
    extraction_result: ExtractionResult | None = None

    # Classification result
    classification: ClassificationResult | None = None

    # Chunks
    chunks: list[ChunkWithContext] = field(default_factory=list)

    # Output
    signal_id: UUID | None = None
    chunk_ids: list[str] = field(default_factory=list)

    # Error tracking
    error: str | None = None


def _check_max_steps(state: DocumentProcessingState) -> DocumentProcessingState:
    """Check and increment step count."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Exceeded max steps ({MAX_STEPS})")
    return state


def load_document(state: DocumentProcessingState) -> dict[str, Any]:
    """Load document info from database."""
    state = _check_max_steps(state)
    state.started_at = datetime.now(timezone.utc).isoformat()
    state.start_time_ms = int(time.time() * 1000)

    logger.info(f"Loading document {state.document_id}")

    doc = get_document_upload(state.document_id)
    if not doc:
        state.error = f"Document {state.document_id} not found"
        return {"error": state.error}

    return {
        "project_id": UUID(doc["project_id"]),
        "original_filename": doc["original_filename"],
        "storage_path": doc["storage_path"],
        "file_type": doc["file_type"],
        "mime_type": doc["mime_type"],
        "authority": doc.get("authority", "consultant"),
    }


def download_file(state: DocumentProcessingState) -> dict[str, Any]:
    """Download file from Supabase Storage."""
    state = _check_max_steps(state)

    if state.error:
        return {}

    logger.info(f"Downloading file from {state.storage_path}")

    try:
        supabase = get_supabase()
        response = supabase.storage.from_("project-files").download(state.storage_path)

        if not response:
            state.error = "Failed to download file from storage"
            return {"error": state.error}

        return {"file_bytes": response}

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return {"error": f"Download failed: {e}"}


def extract_content(state: DocumentProcessingState) -> dict[str, Any]:
    """Extract content from document."""
    state = _check_max_steps(state)

    if state.error:
        return {}

    logger.info(f"Extracting content from {state.original_filename} ({len(state.file_bytes)} bytes)")
    extract_start = time.time()

    # Get appropriate extractor
    extractor = get_extractor(
        mime_type=state.mime_type,
        file_extension=f".{state.file_type}",
    )

    if not extractor:
        return {"error": f"No extractor for {state.file_type}"}

    try:
        # Run extraction (async operation)
        result = _run_async(
            extractor.extract(
                file_bytes=state.file_bytes,
                filename=state.original_filename,
                mime_type=state.mime_type,
            )
        )

        extract_time = time.time() - extract_start
        logger.info(
            f"Extracted {len(result.sections)} sections, "
            f"{result.word_count} words from {state.original_filename} "
            f"in {extract_time:.1f}s"
        )

        return {"extraction_result": result}

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {"error": f"Extraction failed: {e}"}


def classify_content(state: DocumentProcessingState) -> dict[str, Any]:
    """Classify the document."""
    state = _check_max_steps(state)

    if state.error or not state.extraction_result:
        return {}

    logger.info(f"Classifying {state.original_filename}")
    classify_start = time.time()

    try:
        # Run classification (async operation)
        result = _run_async(
            classify_document(
                content_preview=state.extraction_result.get_first_n_chars(2000),
                filename=state.original_filename,
                file_type=state.file_type,
                full_content=state.extraction_result.raw_text[:4000]
                if len(state.extraction_result.raw_text) > 2000
                else None,
            )
        )

        classify_time = time.time() - classify_start
        logger.info(
            f"Classified as {result.document_class} "
            f"(quality={result.quality_score:.2f}) in {classify_time:.1f}s"
        )

        return {"classification": result}

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        # Classification failure is not fatal - use defaults
        return {
            "classification": ClassificationResult(
                document_class="generic",
                quality_score=0.5,
                relevance_score=0.5,
                information_density=0.5,
                content_summary="Classification failed - treating as generic document.",
                keyword_tags=[],
                key_topics=[],
                processing_priority=30,
                confidence=0.1,
            )
        }


def create_chunks(state: DocumentProcessingState) -> dict[str, Any]:
    """Create chunks with contextual prefixes."""
    state = _check_max_steps(state)

    if state.error or not state.extraction_result:
        return {}

    logger.info(f"Creating chunks for {state.original_filename}")

    try:
        chunks = chunk_document(
            extraction_result=state.extraction_result,
            document_title=state.original_filename,
            document_type=state.classification.document_class
            if state.classification
            else state.file_type,
            document_summary=state.classification.content_summary
            if state.classification
            else None,
            authority=state.authority,
        )

        logger.info(f"Created {len(chunks)} chunks")

        return {"chunks": chunks}

    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        return {"error": f"Chunking failed: {e}"}


def create_signal_and_embed(state: DocumentProcessingState) -> dict[str, Any]:
    """Create signal and embed chunks."""
    state = _check_max_steps(state)

    if state.error or not state.chunks:
        return {}

    logger.info(f"Creating signal for {state.original_filename} ({len(state.chunks)} chunks)")
    embed_start = time.time()

    settings = get_settings()
    supabase = get_supabase()

    try:
        # Create signal record
        signal_data = {
            "project_id": str(state.project_id),
            "signal_type": "document",
            "raw_text": state.extraction_result.raw_text[:50000]  # Limit content
            if state.extraction_result
            else "",
            "source_type": "upload",
            "source": state.original_filename,
            "run_id": str(state.run_id),
            "metadata": {
                "document_class": state.classification.document_class
                if state.classification
                else "generic",
                "quality_score": state.classification.quality_score
                if state.classification
                else 0.5,
                "page_count": state.extraction_result.page_count
                if state.extraction_result
                else 1,
                "word_count": state.extraction_result.word_count
                if state.extraction_result
                else 0,
                "extraction_method": state.extraction_result.extraction_method
                if state.extraction_result
                else "unknown",
                "authority": state.authority,
            },
        }

        signal_response = supabase.table("signals").insert(signal_data).execute()

        if not signal_response.data:
            return {"error": "Failed to create signal"}

        signal_id = UUID(signal_response.data[0]["id"])

        # Embed chunks in batch (much faster than one-by-one)
        from openai import OpenAI

        openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Batch embed all chunks at once
        chunk_texts = [chunk.content_with_context for chunk in state.chunks]
        embedding_response = openai_client.embeddings.create(
            model=settings.EMBEDDING_MODEL,
            input=chunk_texts,
        )
        embeddings = [e.embedding for e in embedding_response.data]

        # Insert all chunks with their embeddings
        chunk_ids = []
        for i, chunk in enumerate(state.chunks):
            chunk_data = {
                "signal_id": str(signal_id),
                "chunk_index": chunk.chunk_index,
                "content": chunk.original_content,
                "start_char": 0,  # Not tracked in chunker, placeholder
                "end_char": len(chunk.original_content),
                "embedding": embeddings[i],
                "metadata": chunk.metadata,
                "run_id": str(state.run_id),
                "document_upload_id": str(state.document_id),
                "page_number": chunk.page_number,
                "section_path": chunk.section_path,
            }

            chunk_response = supabase.table("signal_chunks").insert(chunk_data).execute()

            if chunk_response.data:
                chunk_ids.append(chunk_response.data[0]["id"])

        embed_time = time.time() - embed_start
        logger.info(f"Created signal {signal_id} with {len(chunk_ids)} chunks in {embed_time:.1f}s")

        return {
            "signal_id": signal_id,
            "chunk_ids": chunk_ids,
        }

    except Exception as e:
        logger.error(f"Signal creation failed: {e}")
        return {"error": f"Signal creation failed: {e}"}


def finalize(state: DocumentProcessingState) -> dict[str, Any]:
    """Finalize processing and update document status."""
    state = _check_max_steps(state)

    # Calculate duration safely (avoid overflow if start_time_ms wasn't set)
    if state.start_time_ms > 0:
        duration_ms = int(time.time() * 1000) - state.start_time_ms
        # Sanity check - duration should be reasonable (< 1 hour)
        if duration_ms < 0 or duration_ms > 3600000:
            duration_ms = 0
    else:
        duration_ms = 0

    if state.error:
        logger.error(f"Document processing failed: {state.error}")
        update_document_processing(
            document_id=state.document_id,
            status="failed",
            error=state.error,
            processing_duration_ms=duration_ms,
        )
        return {}

    logger.info(
        f"Document processing complete for {state.original_filename} "
        f"in {duration_ms}ms"
    )

    # Update document with results
    update_document_processing(
        document_id=state.document_id,
        status="completed",
        page_count=state.extraction_result.page_count
        if state.extraction_result
        else None,
        word_count=state.extraction_result.word_count
        if state.extraction_result
        else None,
        total_chunks=len(state.chunks),
        content_summary=state.classification.content_summary
        if state.classification
        else None,
        keyword_tags=state.classification.keyword_tags
        if state.classification
        else None,
        key_topics=state.classification.key_topics
        if state.classification
        else None,
        extraction_method=state.extraction_result.extraction_method
        if state.extraction_result
        else None,
        document_class=state.classification.document_class
        if state.classification
        else None,
        quality_score=state.classification.quality_score
        if state.classification
        else None,
        relevance_score=state.classification.relevance_score
        if state.classification
        else None,
        information_density=state.classification.information_density
        if state.classification
        else None,
        signal_id=state.signal_id,
        processing_duration_ms=duration_ms,
    )

    # Trigger signal pipeline to extract features/personas/etc. in background
    if state.signal_id and state.project_id:
        _trigger_signal_pipeline(
            project_id=state.project_id,
            signal_id=state.signal_id,
            signal_content=state.extraction_result.raw_text[:50000] if state.extraction_result else "",
            signal_type="document",
        )

    return {}


def _trigger_signal_pipeline(
    project_id: UUID,
    signal_id: UUID,
    signal_content: str,
    signal_type: str,
) -> None:
    """Trigger signal pipeline in background to extract features/personas/etc.

    Uses the full process_signal function to ensure documents go through the
    complete pipeline including memory agent integration.
    """
    import threading
    from uuid import uuid4

    def run_pipeline():
        try:
            import asyncio
            from app.core.signal_pipeline import process_signal

            run_id = uuid4()
            logger.info(
                f"Starting signal pipeline for document signal {signal_id}",
                extra={"project_id": str(project_id), "run_id": str(run_id)},
            )

            # Run full signal pipeline (includes build state + memory agent)
            result = asyncio.run(
                process_signal(
                    project_id=project_id,
                    signal_id=signal_id,
                    run_id=run_id,
                    signal_content=signal_content,
                    signal_type=signal_type,
                )
            )

            logger.info(
                f"Signal pipeline completed for document: "
                f"success={result.get('success')}, "
                f"pipeline={result.get('pipeline')}, "
                f"features={result.get('features_created', 0)}",
                extra={"project_id": str(project_id), "signal_id": str(signal_id)},
            )

        except Exception as e:
            logger.exception(f"Signal pipeline failed for document: {e}")

    # Run in background thread
    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()


def should_continue(state: DocumentProcessingState) -> str:
    """Determine if processing should continue."""
    if state.error:
        return "finalize"
    return "continue"


def build_document_processing_graph() -> StateGraph:
    """Build the document processing graph."""
    workflow = StateGraph(DocumentProcessingState)

    # Add nodes
    workflow.add_node("load_document", load_document)
    workflow.add_node("download_file", download_file)
    workflow.add_node("extract_content", extract_content)
    workflow.add_node("classify_content", classify_content)
    workflow.add_node("create_chunks", create_chunks)
    workflow.add_node("create_signal_and_embed", create_signal_and_embed)
    workflow.add_node("finalize", finalize)

    # Add edges
    workflow.set_entry_point("load_document")
    workflow.add_edge("load_document", "download_file")
    workflow.add_conditional_edges(
        "download_file",
        should_continue,
        {"continue": "extract_content", "finalize": "finalize"},
    )
    workflow.add_conditional_edges(
        "extract_content",
        should_continue,
        {"continue": "classify_content", "finalize": "finalize"},
    )
    workflow.add_edge("classify_content", "create_chunks")
    workflow.add_conditional_edges(
        "create_chunks",
        should_continue,
        {"continue": "create_signal_and_embed", "finalize": "finalize"},
    )
    workflow.add_edge("create_signal_and_embed", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile()


# Pre-compiled graph instance
document_processing_graph = build_document_processing_graph()


async def process_document(
    document_id: UUID,
    run_id: UUID | None = None,
) -> dict[str, Any]:
    """Process a document through the graph.

    Args:
        document_id: Document UUID to process
        run_id: Optional run ID for tracking

    Returns:
        Dict with processing results
    """
    from uuid import uuid4

    run_id = run_id or uuid4()

    initial_state = DocumentProcessingState(
        document_id=document_id,
        run_id=run_id,
    )

    try:
        # Run the graph
        final_state = document_processing_graph.invoke(initial_state)

        return {
            "success": not final_state.error,
            "document_id": str(document_id),
            "run_id": str(run_id),
            "signal_id": str(final_state.signal_id) if final_state.signal_id else None,
            "chunks_created": len(final_state.chunk_ids),
            "document_class": final_state.classification.document_class
            if final_state.classification
            else None,
            "error": final_state.error,
        }

    except Exception as e:
        logger.exception(f"Document processing graph failed: {e}")
        return {
            "success": False,
            "document_id": str(document_id),
            "run_id": str(run_id),
            "error": str(e),
        }
