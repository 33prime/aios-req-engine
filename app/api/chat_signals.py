"""Chat-as-signal endpoints: entity detection and signal extraction."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str
    content: str


class DetectEntitiesRequest(BaseModel):
    """Request to detect entity-rich content in chat messages."""

    messages: List[ChatMessage]


class SaveAsSignalRequest(BaseModel):
    """Request to save chat messages as a signal for entity extraction."""

    messages: List[ChatMessage]


@router.post("/detect-entities")
async def detect_entities_in_chat(
    request: DetectEntitiesRequest,
    project_id: UUID = Query(..., description="Project UUID"),
) -> Dict[str, Any]:
    """
    Lightweight Haiku check: do recent chat messages contain extractable requirements?

    Returns entity hints without running full extraction.
    """
    from app.chains.detect_chat_entities import detect_chat_entities

    try:
        msg_dicts = [{"role": m.role, "content": m.content} for m in request.messages]
        result = await detect_chat_entities(msg_dicts, project_id=str(project_id))
        return result
    except Exception as e:
        logger.error(f"Error detecting chat entities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save-as-signal")
async def save_chat_as_signal(
    request: SaveAsSignalRequest,
    project_id: UUID = Query(..., description="Project UUID"),
) -> Dict[str, Any]:
    """
    Convert chat messages into a signal and run through V2 pipeline.

    Pipeline: chat messages → signal record → chunk → process_signal_v2.
    Returns V2 processing summary with patch counts.
    """
    from uuid import uuid4

    from app.graphs.unified_processor import process_signal_v2

    supabase = get_supabase()

    try:
        # Build the chat text from messages
        chat_lines = []
        for msg in request.messages:
            if msg.content.strip():
                chat_lines.append(f"[{msg.role}]: {msg.content}")

        chat_text = "\n\n".join(chat_lines)

        if not chat_text.strip():
            return {"success": False, "error": "No message content to extract"}

        run_id = str(uuid4())

        # 1. Create synthetic signal (V2 pipeline needs this)
        signal_data = {
            "project_id": str(project_id),
            "signal_type": "chat",
            "source_type": "workspace_chat",
            "source": f"chat_extraction_{run_id[:8]}",
            "raw_text": chat_text[:50000],
            "run_id": run_id,
            "metadata": {
                "message_count": len(request.messages),
                "extraction_source": "chat_as_signal",
            },
        }
        signal_response = supabase.table("signals").insert(signal_data).execute()
        if not signal_response.data:
            return {"success": False, "error": "Failed to create signal"}

        signal = signal_response.data[0]
        signal_id = signal["id"]

        # 2. Create a single chunk (V2 pipeline reads from chunks)
        chunk_data = {
            "signal_id": signal_id,
            "chunk_index": 0,
            "content": chat_text[:10000],
            "start_char": 0,
            "end_char": min(len(chat_text), 10000),
            "metadata": {"source": "chat_as_signal"},
            "run_id": run_id,
        }
        supabase.table("signal_chunks").insert(chunk_data).execute()

        # 3. Run V2 pipeline
        result = await process_signal_v2(
            signal_id=signal_id,
            project_id=str(project_id),
            run_id=run_id,
        )

        # 4. Build summary from V2 result
        patches_applied = result.get("patches_applied", 0) if result else 0
        chat_summary = result.get("chat_summary", "") if result else ""
        entity_types = result.get("entity_types_affected", []) if result else []

        type_summary = ", ".join(entity_types) if entity_types else "no entities"

        return {
            "success": True,
            "signal_id": signal_id,
            "patches_applied": patches_applied,
            "type_summary": type_summary,
            "summary": chat_summary or f"Processed {patches_applied} patches from chat conversation.",
        }

    except Exception as e:
        logger.error(f"Error saving chat as signal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
