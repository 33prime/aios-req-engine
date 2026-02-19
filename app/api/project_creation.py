"""Project creation chat API with SSE streaming.

Provides a conversational interface for creating new projects using Claude Haiku 4.5.
"""

import json
import re
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.chains.project_creation_chat import (
    PROJECT_CREATION_SYSTEM_PROMPT,
    get_initial_greeting,
    parse_conversation_state,
    strip_markers_from_response,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.company_info import upsert_company_info
from app.db.projects import create_project

logger = get_logger(__name__)

router = APIRouter()

# Claude Haiku 4.5 model ID for fast responses
HAIKU_MODEL = "claude-haiku-4-5-20251001"


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str  # 'user' or 'assistant'
    content: str


class ProjectCreationChatRequest(BaseModel):
    """Request for project creation chat."""

    messages: list[ChatMessage] = []


class InitResponse(BaseModel):
    """Response for chat initialization."""

    greeting: str


@router.get("/project-creation/init")
async def init_project_creation_chat() -> InitResponse:
    """
    Initialize a new project creation chat.

    Returns the initial AI greeting message.

    Returns:
        InitResponse with greeting message
    """
    return InitResponse(greeting=get_initial_greeting())


@router.post("/project-creation/chat")
async def project_creation_chat(request: ProjectCreationChatRequest) -> StreamingResponse:
    """
    Chat endpoint for project creation using Haiku 4.5.

    Streams AI responses and handles project creation when ready.

    SSE Event Types:
    - type: 'text' - Streaming text content
    - type: 'project_created' - Project was created, includes project data
    - type: 'done' - Stream complete
    - type: 'error' - An error occurred

    Args:
        request: Chat request with message history

    Returns:
        StreamingResponse with Server-Sent Events
    """
    settings = get_settings()

    # Check if Anthropic API key is configured
    anthropic_api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
    if not anthropic_api_key:
        raise HTTPException(
            status_code=500,
            detail="Anthropic API key not configured. Please set ANTHROPIC_API_KEY in environment.",
        )

    async def generate() -> AsyncGenerator[str, None]:
        """Generate streaming chat responses."""
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=anthropic_api_key)

            # Build messages for Claude
            messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

            # Stream response from Haiku 3.5
            full_response = ""
            last_sent_length = 0

            async with client.messages.stream(
                model=HAIKU_MODEL,
                max_tokens=800,  # Allow for longer responses with formatting
                messages=messages,
                system=PROJECT_CREATION_SYSTEM_PROMPT,
            ) as stream:
                async for event in stream:
                    if hasattr(event, "type"):
                        if event.type == "content_block_delta":
                            if hasattr(event, "delta") and hasattr(event.delta, "text"):
                                chunk = event.delta.text
                                full_response += chunk

                                # Strip markers from the FULL accumulated response
                                clean_response = strip_markers_from_response(full_response)

                                # Only send the new part that hasn't been sent yet
                                if len(clean_response) > last_sent_length:
                                    new_content = clean_response[last_sent_length:]
                                    last_sent_length = len(clean_response)
                                    yield f"data: {json.dumps({'type': 'text', 'content': new_content})}\n\n"

            # Parse conversation state from full response
            messages_dict = [{"role": m.role, "content": m.content} for m in request.messages]

            # Debug: log the raw response to see if markers are present
            logger.info(f"Raw LLM response (last 300 chars): ...{full_response[-300:]}")

            state = parse_conversation_state(messages_dict, full_response)

            # Include full messages in state for storing complete conversation
            state["_full_messages"] = messages_dict

            logger.info(f"Conversation state: {state}")

            # Check if summary is ready (new flow — chat collects, frontend launches)
            if state.get("summary_ready") and state["project_name"]:
                summary_data = {
                    "name": state["project_name"],
                    "problem": state.get("problem", ""),
                    "users": state.get("users", ""),
                    "features": state.get("features", ""),
                    "org_fit": state.get("org_fit", ""),
                }
                yield f"data: {json.dumps({'type': 'summary_ready', 'summary': summary_data})}\n\n"

            # Legacy: check if ready to create project (backwards compatible)
            elif state["ready_to_create"] and state["project_name"]:
                try:
                    project_data = await _create_project_from_state(state)
                    yield f"data: {json.dumps({'type': 'project_created', 'project': project_data})}\n\n"
                except Exception as e:
                    logger.error(f"Failed to create project: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to create project: {str(e)}'})}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Error in project creation chat stream: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


def _parse_client_details(client_info: str | None) -> tuple[str | None, str | None]:
    """
    Parse client name and website from the client_info description.

    Expected formats:
    - "Client: Acme Motors (acmemotors.com)"
    - "Client: Acme Motors (https://acmemotors.com)"

    Args:
        client_info: Description text that may contain client details

    Returns:
        Tuple of (client_name, website) - either may be None
    """
    if not client_info:
        return None, None

    client_name = None
    website = None

    # Try to match "Client: Name (website)" pattern
    match = re.search(r"Client:\s*([^(]+?)\s*\(([^)]+)\)", client_info, re.IGNORECASE)
    if match:
        client_name = match.group(1).strip()
        website_raw = match.group(2).strip()
        # Ensure website has protocol
        if website_raw and not website_raw.startswith("http"):
            website = f"https://{website_raw}"
        else:
            website = website_raw
    else:
        # Try just "Client: Name" without website
        match = re.search(r"Client:\s*([^.]+)", client_info, re.IGNORECASE)
        if match:
            client_name = match.group(1).strip()

    return client_name, website


async def _create_project_from_state(state: dict[str, Any]) -> dict[str, Any]:
    """
    Create a project from the conversation state.

    Args:
        state: Parsed conversation state with project_name, client_info, etc.

    Returns:
        Project data dict with id, name, and optional onboarding_job_id
    """
    project_name = state["project_name"]
    client_info = state.get("client_info")

    logger.info(f"Creating project: {project_name}")

    # Create project with optional description from client info
    project = create_project(
        name=project_name,
        description=client_info,  # Use client info as initial description
        created_by=None,
        tags=[],
    )

    project_id = project["id"]
    result = {
        "id": project_id,
        "name": project_name,
    }

    # Create company_info record from parsed client details
    client_name, website = _parse_client_details(client_info)
    company_name = client_name or project_name  # Fall back to project name

    try:
        company_info_record = upsert_company_info(
            project_id=uuid.UUID(project_id),
            name=company_name,
            website=website,
            description=client_info,
        )
        logger.info(
            f"Created company_info for project {project_id}: {company_name}",
            extra={"company_info_id": company_info_record.get("id")},
        )
    except Exception as e:
        logger.warning(f"Failed to create company_info: {e}")
        # Don't fail project creation if company_info fails

    # If we have client info, ingest it as a signal and run onboarding
    if client_info:
        try:
            from app.core.chunking import chunk_text
            from app.core.embeddings import embed_texts
            from app.db.jobs import complete_job, create_job, fail_job, start_job
            from app.db.phase0 import insert_signal, insert_signal_chunks

            run_id = uuid.uuid4()

            # Build full conversation text to store (not just the brief summary)
            # This preserves all the detailed information the user provided
            conversation_messages = state.get("_full_messages", [])
            if conversation_messages:
                # Format the full conversation as the signal content
                full_conversation_parts = []
                for msg in conversation_messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        full_conversation_parts.append(f"User: {content}")
                    # Skip assistant messages to keep just the user input

                # Combine user messages with the summary
                full_text = "\n\n".join(full_conversation_parts)
                if full_text:
                    full_text += f"\n\n---\n\nSummary: {client_info}"
                else:
                    full_text = client_info
            else:
                full_text = client_info

            # Insert signal (authority=client since this is client information)
            signal = insert_signal(
                project_id=uuid.UUID(project_id),
                signal_type="note",
                source="project_creation_chat",
                raw_text=full_text,
                metadata={"authority": "client", "auto_ingested": True, "summary": client_info},
                run_id=run_id,
                source_label=f"Project Intake: {project_name}",
            )
            signal_id = uuid.UUID(signal["id"])

            logger.info(
                f"Auto-ingested client info as signal {signal_id}",
                extra={"project_id": project_id, "signal_id": str(signal_id)},
            )

            # Chunk and embed the full conversation text
            chunks = chunk_text(full_text, metadata={"authority": "client"})
            if chunks:
                chunk_texts = [chunk["content"] for chunk in chunks]
                embeddings = embed_texts(chunk_texts)
                insert_signal_chunks(
                    signal_id=signal_id,
                    chunks=chunks,
                    embeddings=embeddings,
                    run_id=run_id,
                )

                logger.info(
                    f"Created {len(chunks)} chunks for client info signal",
                    extra={"signal_id": str(signal_id)},
                )

            # Create onboarding job and run in background
            import threading

            onboarding_job_id = create_job(
                project_id=uuid.UUID(project_id),
                job_type="onboarding",
                input_json={"signal_id": str(signal_id)},
                run_id=run_id,
            )

            logger.info(
                f"Created onboarding job {onboarding_job_id}",
                extra={"project_id": project_id, "job_id": str(onboarding_job_id)},
            )

            # Run onboarding in background thread
            def run_onboarding_background():
                try:
                    start_job(onboarding_job_id)
                    from app.graphs.onboarding_graph import run_onboarding

                    onboarding_result = run_onboarding(
                        project_id=uuid.UUID(project_id),
                        signal_id=signal_id,
                        job_id=onboarding_job_id,
                        run_id=run_id,
                    )
                    complete_job(onboarding_job_id, output_json=onboarding_result)
                    logger.info(
                        f"Onboarding job {onboarding_job_id} completed",
                        extra={"result": onboarding_result},
                    )
                except Exception as e:
                    logger.error(f"Onboarding job {onboarding_job_id} failed: {e}")
                    fail_job(onboarding_job_id, error_message=str(e))

            thread = threading.Thread(target=run_onboarding_background, daemon=True)
            thread.start()

            result["onboarding_job_id"] = str(onboarding_job_id)
            result["signal_id"] = str(signal_id)

        except Exception as e:
            logger.error(f"Failed to process client info: {e}")
            # Don't fail project creation if info processing fails

    return result
