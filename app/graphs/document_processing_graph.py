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

from langgraph.checkpoint.memory import MemorySaver
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
    extracted_image_ids: list[str] = field(default_factory=list)

    # Clarification
    needs_clarification: bool = False
    clarification_question: str | None = None

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
        # extract_images=True activates embedded image extraction in PDF/PPTX extractors
        result = _run_async(
            extractor.extract(
                file_bytes=state.file_bytes,
                filename=state.original_filename,
                mime_type=state.mime_type,
                extract_images=True,
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


def process_embedded_images(state: DocumentProcessingState) -> dict[str, Any]:
    """Persist embedded images to storage and DB."""
    state = _check_max_steps(state)

    if state.error or not state.extraction_result:
        return {}

    embedded_images = state.extraction_result.embedded_images
    if not embedded_images:
        return {}

    if not state.project_id:
        return {}

    logger.info(
        f"Processing {len(embedded_images)} embedded images from {state.original_filename}"
    )

    from app.db.document_extracted_images import create_extracted_image

    supabase = get_supabase()
    extracted_ids: list[str] = []

    for idx, img_bytes in enumerate(embedded_images):
        try:
            # Detect MIME type from magic bytes
            mime_type = _detect_image_mime(img_bytes)
            ext = {
                "image/png": "png",
                "image/jpeg": "jpg",
                "image/webp": "webp",
                "image/gif": "gif",
            }.get(mime_type, "png")

            # Upload to storage
            storage_path = (
                f"extracted-images/{state.project_id}/"
                f"{state.document_id}/{idx:03d}.{ext}"
            )

            supabase.storage.from_("project-files").upload(
                path=storage_path,
                file=img_bytes,
                file_options={
                    "content-type": mime_type,
                    "upsert": "true",
                },
            )

            # Determine source context from extraction metadata
            source_context = None
            page_number = None
            # Try to map image index to a page/slide
            metadata = state.extraction_result.metadata or {}
            if "filename" in metadata:
                source_context = f"Extracted from {metadata['filename']}"

            # Save to DB
            record = create_extracted_image(
                document_upload_id=state.document_id,
                project_id=state.project_id,
                storage_path=storage_path,
                mime_type=mime_type,
                file_size_bytes=len(img_bytes),
                image_index=idx,
                page_number=page_number,
                source_context=source_context,
            )

            extracted_ids.append(record["id"])

        except Exception as e:
            logger.warning(f"Failed to persist image {idx}: {e}")

    logger.info(f"Persisted {len(extracted_ids)} images for document {state.document_id}")

    return {"extracted_image_ids": extracted_ids}


def _detect_image_mime(img_bytes: bytes) -> str:
    """Detect image MIME type from magic bytes."""
    if img_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    elif img_bytes[:2] == b"\xff\xd8":
        return "image/jpeg"
    elif img_bytes[:4] == b"RIFF" and len(img_bytes) > 12 and img_bytes[8:12] == b"WEBP":
        return "image/webp"
    elif img_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/png"


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
            f"(quality={result.quality_score:.2f}, confidence={result.confidence:.2f}) "
            f"in {classify_time:.1f}s"
        )

        # Check if clarification is needed
        needs_clarification = False
        clarification_question = None

        if result.confidence < 0.6 or result.document_class == "generic":
            needs_clarification = True
            clarification_question = (
                f"I processed **{state.original_filename}** but I'm not confident about "
                f"what type of document this is (classified as '{result.document_class}' "
                f"with {result.confidence:.0%} confidence).\n\n"
                f"Could you tell me what kind of document this is? For example:\n"
                f"- Meeting transcript\n"
                f"- Requirements spec / PRD\n"
                f"- Email thread\n"
                f"- Research report\n"
                f"- Presentation deck\n"
                f"- Process documentation\n\n"
                f"This helps me extract the right types of information from it."
            )
            logger.info(
                f"Document {state.original_filename} needs clarification "
                f"(class={result.document_class}, confidence={result.confidence:.2f})"
            )

        return {
            "classification": result,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
        }

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

    # Persist clarification state if needed
    if state.needs_clarification and state.clarification_question:
        try:
            supabase = get_supabase()
            supabase.table("document_uploads").update({
                "needs_clarification": True,
                "clarification_question": state.clarification_question,
            }).eq("id", str(state.document_id)).execute()
        except Exception as e:
            logger.warning(f"Failed to save clarification state: {e}")

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
    """Trigger V2 signal pipeline in background to extract entities via EntityPatch.

    Uses threading because this is called from a sync LangGraph node.
    V2 reads the signal from DB via signal_id, so signal_content/signal_type
    are only used for logging.
    """
    import threading
    from uuid import uuid4

    def run_pipeline():
        try:
            import asyncio
            from app.graphs.unified_processor import process_signal_v2

            run_id = uuid4()
            logger.info(
                f"Starting V2 signal pipeline for document signal {signal_id}",
                extra={"project_id": str(project_id), "run_id": str(run_id)},
            )

            result = asyncio.run(
                process_signal_v2(
                    signal_id=signal_id,
                    project_id=project_id,
                    run_id=run_id,
                )
            )

            logger.info(
                f"V2 signal pipeline completed for document: "
                f"success={result.success}, "
                f"patches_applied={result.patches_applied}, "
                f"created={result.created_count}",
                extra={"project_id": str(project_id), "signal_id": str(signal_id)},
            )

            # Create notification for the project owner
            _create_document_notification(
                project_id=project_id,
                signal_id=signal_id,
                patches_applied=result.patches_applied,
                created_count=result.created_count,
            )

        except Exception as e:
            logger.exception(f"V2 signal pipeline failed for document: {e}")

    # Run in background thread
    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()


def _create_document_notification(
    project_id: UUID,
    signal_id: UUID,
    patches_applied: int,
    created_count: int,
) -> None:
    """Create a notification for the project owner when document processing completes."""
    try:
        supabase = get_supabase()

        # Get the document filename from the signal's linked document
        doc_resp = (
            supabase.table("document_uploads")
            .select("original_filename")
            .eq("signal_id", str(signal_id))
            .limit(1)
            .execute()
        )
        filename = (
            doc_resp.data[0]["original_filename"]
            if doc_resp.data
            else "document"
        )

        # Get project owner (created_by)
        proj_resp = (
            supabase.table("projects")
            .select("created_by")
            .eq("id", str(project_id))
            .single()
            .execute()
        )
        if not proj_resp.data or not proj_resp.data.get("created_by"):
            return

        user_id = proj_resp.data["created_by"]

        # Build notification
        from app.db.notifications import create_notification

        title = f"Document processed: {filename}"
        body = (
            f"Extracted {created_count} new entities and applied {patches_applied} updates to the BRD."
            if created_count or patches_applied
            else f"Finished analyzing {filename} — no new entities found."
        )

        create_notification(
            user_id=user_id,
            type="document_processed",
            title=title,
            body=body,
            project_id=project_id,
            metadata={
                "signal_id": str(signal_id),
                "patches_applied": patches_applied,
                "created_count": created_count,
                "filename": filename,
            },
        )

    except Exception as e:
        logger.warning(f"Failed to create document notification: {e}")


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
    workflow.add_node("process_embedded_images", process_embedded_images)
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
        {"continue": "process_embedded_images", "finalize": "finalize"},
    )
    workflow.add_edge("process_embedded_images", "classify_content")
    workflow.add_edge("classify_content", "create_chunks")
    workflow.add_conditional_edges(
        "create_chunks",
        should_continue,
        {"continue": "create_signal_and_embed", "finalize": "finalize"},
    )
    workflow.add_edge("create_signal_and_embed", "finalize")
    workflow.add_edge("finalize", END)

    return workflow.compile(checkpointer=MemorySaver())


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
        # Run the graph with checkpointer config
        config = {"configurable": {"thread_id": str(run_id)}}
        result = document_processing_graph.invoke(initial_state, config=config)

        # LangGraph StateGraph.invoke() returns a dict, not the typed state object
        if isinstance(result, dict):
            error = result.get("error")
            signal_id = result.get("signal_id")
            chunk_ids = result.get("chunk_ids", [])
            classification = result.get("classification")
        else:
            error = result.error
            signal_id = result.signal_id
            chunk_ids = result.chunk_ids
            classification = result.classification

        return {
            "success": not error,
            "document_id": str(document_id),
            "run_id": str(run_id),
            "signal_id": str(signal_id) if signal_id else None,
            "chunks_created": len(chunk_ids),
            "document_class": classification.document_class
            if classification and hasattr(classification, "document_class")
            else (classification.get("document_class") if isinstance(classification, dict) else None),
            "error": error,
        }

    except Exception as e:
        logger.exception(f"Document processing graph failed: {e}")
        return {
            "success": False,
            "document_id": str(document_id),
            "run_id": str(run_id),
            "error": str(e),
        }
