"""Signal and document tool implementations."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


async def _add_signal(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a signal and process it through the full pipeline.

    Args:
        project_id: Project UUID
        params: Signal parameters (signal_type, content, source, process_immediately)

    Returns:
        Created signal with processing status
    """
    import uuid as uuid_module

    signal_type = params.get("signal_type", "note")
    content = params.get("content")
    source = params.get("source", "chat")
    process_immediately = params.get("process_immediately", True)

    if not content:
        return {"success": False, "error": "content is required"}

    try:
        supabase = get_supabase()
        run_id = str(uuid_module.uuid4())

        # Derive a meaningful title from the content (first line, truncated)
        def derive_title(text: str, max_length: int = 60) -> str:
            """Derive a title from content - first non-empty line, cleaned and truncated."""
            lines = text.strip().split('\n')
            for line in lines:
                cleaned = line.strip()
                # Skip empty lines or lines that look like timestamps/metadata
                if cleaned and not cleaned.startswith('[') and len(cleaned) > 5:
                    # Remove common transcript markers
                    if cleaned.lower().startswith(('speaker', 'transcript', '---')):
                        continue
                    # Truncate and add ellipsis if needed
                    if len(cleaned) > max_length:
                        return cleaned[:max_length].rsplit(' ', 1)[0] + '...'
                    return cleaned
            # Fallback to generic title with timestamp
            from datetime import datetime
            return f"Signal from {datetime.now().strftime('%b %d, %Y')}"

        signal_title = derive_title(content)

        # Create signal record
        signal_data = {
            "project_id": str(project_id),
            "signal_type": signal_type,
            "source": source,
            "raw_text": content,
            "metadata": {
                "source": source,
                "added_via": "chat_assistant",
                "title": signal_title,
            },
            "run_id": run_id,
        }

        response = supabase.table("signals").insert(signal_data).execute()

        if not response.data:
            return {"success": False, "error": "Failed to create signal"}

        signal = response.data[0]
        signal_id = signal["id"]

        # Chunk and embed the signal text
        chunks_created = 0
        try:
            from app.core.chunking import chunk_text
            from app.core.embeddings import embed_texts
            from app.db.phase0 import insert_signal_chunks

            chunks = chunk_text(content)
            if chunks:
                # Extract content strings for embedding
                chunk_texts = [c["content"] for c in chunks]
                embeddings = embed_texts(chunk_texts)
                insert_signal_chunks(
                    signal_id=UUID(signal_id),
                    chunks=chunks,
                    embeddings=embeddings,
                    run_id=UUID(run_id),
                )
                chunks_created = len(chunks)
                logger.info(f"Created {chunks_created} chunks for signal {signal_id}")
        except Exception as chunk_error:
            logger.warning(f"Failed to chunk signal {signal_id}: {chunk_error}")
            # Continue anyway - signal is saved

        result = {
            "success": True,
            "signal_id": signal_id,
            "signal_type": signal_type,
            "source": source,
            "content_length": len(content),
            "chunks_created": chunks_created,
        }

        # Process through V2 pipeline if requested
        if process_immediately:
            try:
                from app.graphs.unified_processor import process_signal_v2

                logger.info(f"Processing signal {signal_id} through V2 pipeline")

                pipeline_result = await process_signal_v2(
                    signal_id=UUID(signal_id),
                    project_id=project_id,
                    run_id=UUID(run_id),
                )

                if pipeline_result.success:
                    result["processed"] = True
                    result["patches_applied"] = pipeline_result.patches_applied
                    result["created_count"] = pipeline_result.created_count
                    result["merged_count"] = pipeline_result.merged_count
                    result["message"] = pipeline_result.chat_summary or (
                        f"Created {signal_type} signal and processed: "
                        f"{pipeline_result.patches_applied} patches applied, "
                        f"{pipeline_result.created_count} created"
                    )
                else:
                    result["processed"] = False
                    result["pipeline_error"] = pipeline_result.error or "Unknown error"
                    result["message"] = f"Created {signal_type} signal but processing failed: {result['pipeline_error']}"

            except Exception as pipeline_error:
                logger.warning(f"V2 pipeline processing failed: {pipeline_error}")
                result["processed"] = False
                result["pipeline_error"] = str(pipeline_error)
                result["message"] = f"Created {signal_type} signal but processing failed: {str(pipeline_error)}"
        else:
            result["processed"] = False
            result["message"] = f"Created {signal_type} signal. Use signal streaming to process."

        return result

    except Exception as e:
        logger.error(f"Error adding signal: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to add signal: {str(e)}",
        }


async def _get_recent_documents(
    project_id: UUID, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Get recently uploaded documents with processing status."""
    try:
        supabase = get_supabase()
        limit = params.get("limit", 5)

        # Query recent documents for this project
        response = (
            supabase.table("documents")
            .select("id, original_filename, document_class, processing_status, signal_id, created_at, metadata")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        docs = response.data or []

        # Batch-fetch all related signals in one query (replaces N+1 loop)
        signal_ids = [d["signal_id"] for d in docs if d.get("processing_status") == "completed" and d.get("signal_id")]
        signal_map: Dict[str, Any] = {}
        if signal_ids:
            try:
                sig_resp = supabase.table("signals").select("id, processing_status, patch_summary").in_("id", signal_ids).execute()
                signal_map = {s["id"]: s for s in (sig_resp.data or [])}
            except Exception:
                pass

        results = []
        for doc in docs:
            doc_info: Dict[str, Any] = {
                "filename": doc.get("original_filename", "unknown"),
                "uploaded_at": doc.get("created_at", ""),
                "document_type": doc.get("document_class") or "pending classification",
                "processing_status": doc.get("processing_status", "unknown"),
            }

            # If document extraction is done and has a signal, check entity extraction
            if doc.get("processing_status") == "completed" and doc.get("signal_id"):
                sig_data = signal_map.get(doc["signal_id"])
                if sig_data:
                    sig_status = sig_data.get("processing_status", "")
                    if sig_status in ("completed", "processed"):
                        doc_info["entity_extraction"] = "completed"
                        patch = sig_data.get("patch_summary") or {}
                        if isinstance(patch, str):
                            import json as _json
                            try:
                                patch = _json.loads(patch)
                            except Exception:
                                patch = {}
                        if patch:
                            doc_info["entities_extracted"] = patch
                    elif sig_status in ("processing", "pending"):
                        doc_info["entity_extraction"] = "processing"
                    else:
                        doc_info["entity_extraction"] = sig_status or "unknown"
                else:
                    doc_info["entity_extraction"] = "unknown"
            elif doc.get("processing_status") == "completed":
                doc_info["entity_extraction"] = "not started"
            elif doc.get("processing_status") in ("pending", "processing"):
                doc_info["entity_extraction"] = "waiting for document extraction"

            results.append(doc_info)

        return {
            "documents": results,
            "total": len(results),
            "summary": (
                f"{len(results)} recent document(s). "
                + ", ".join(
                    f"{d['filename']}: {d['processing_status']}"
                    + (f" → entities {d.get('entity_extraction', 'n/a')}" if d.get("entity_extraction") else "")
                    for d in results
                )
                if results
                else "No documents uploaded yet."
            ),
        }

    except Exception as e:
        logger.error(f"Error getting recent documents: {e}", exc_info=True)
        return {"error": str(e)}


async def _check_document_clarifications(
    project_id: UUID, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Check for documents that need clarification about their type."""
    try:
        supabase = get_supabase()

        response = (
            supabase.table("document_uploads")
            .select("id, original_filename, clarification_question, document_class, created_at")
            .eq("project_id", str(project_id))
            .eq("needs_clarification", True)
            .is_("clarification_response", "null")
            .order("created_at", desc=True)
            .execute()
        )

        docs = response.data or []

        if not docs:
            return {
                "success": True,
                "pending_clarifications": [],
                "message": "No documents need clarification.",
            }

        return {
            "success": True,
            "pending_clarifications": docs,
            "message": f"{len(docs)} document(s) need clarification about their type.",
        }

    except Exception as e:
        logger.error(f"Error checking clarifications: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _respond_to_document_clarification(
    project_id: UUID, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Respond to a document clarification with the correct document class."""
    document_id = params.get("document_id")
    document_class = params.get("document_class")
    context = params.get("context", "")

    if not document_id or not document_class:
        return {"success": False, "error": "document_id and document_class are required"}

    try:
        supabase = get_supabase()

        # Update the document with clarification response
        response = (
            supabase.table("document_uploads")
            .update({
                "needs_clarification": False,
                "clarification_response": context or document_class,
                "clarified_document_class": document_class,
                "clarified_at": "now()",
                "document_class": document_class,
            })
            .eq("id", document_id)
            .eq("project_id", str(project_id))
            .execute()
        )

        if not response.data:
            return {"success": False, "error": "Document not found or not in this project"}

        doc = response.data[0]

        return {
            "success": True,
            "message": (
                f"Updated **{doc['original_filename']}** classification to "
                f"'{document_class}'. The document's extracted content is already "
                f"in the system and will be used with this corrected classification."
            ),
        }

    except Exception as e:
        logger.error(f"Error responding to clarification: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
