"""Client Portal API endpoints."""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.auth_middleware import AuthContext, require_auth, require_project_access
from app.core.schemas_portal import (
    ClientDocument,
    ClientDocumentCreate,
    ContextSource,
    DashboardProgress,
    DashboardResponse,
    DocumentCategory,
    InfoRequest,
    InfoRequestAnswer,
    InfoRequestPhase,
    InfoRequestStatus,
    PortalPhase,
    PortalProject,
    PortalProjectList,
    ProjectContext,
    ProjectContextSectionUpdate,
)
from app.db.client_documents import (
    can_user_delete_document,
    create_client_document,
    delete_client_document,
    get_document_counts,
    list_client_documents,
)
from app.db.info_requests import (
    get_info_request,
    get_info_request_progress,
    list_info_requests,
    submit_info_request_answer,
    update_info_request_status,
)
from app.db.project_context import (
    add_competitor,
    add_key_user,
    add_tribal_knowledge,
    get_or_create_project_context,
    get_project_context,
    lock_context_section,
    update_context_section,
    update_project_context,
)
from app.db.project_members import list_user_projects
from app.db.supabase_client import get_supabase as get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["portal"])


# ============================================================================
# Project Access
# ============================================================================


@router.get("/projects", response_model=PortalProjectList)
async def list_portal_projects(auth: AuthContext = Depends(require_auth)):
    """List all projects the client has access to."""
    project_ids = await list_user_projects(auth.user_id)

    client = get_client()
    projects = []

    for pid in project_ids:
        result = (
            client.table("projects")
            .select("*")
            .eq("id", str(pid))
            .eq("portal_enabled", True)
            .execute()
        )
        if result.data:
            projects.append(PortalProject(**result.data[0]))

    return PortalProjectList(projects=projects)


@router.get("/projects/{project_id}", response_model=PortalProject)
async def get_portal_project(
    project_id: UUID,
    auth: AuthContext = Depends(require_project_access),
):
    """Get project details for the portal."""
    client = get_client()
    result = (
        client.table("projects")
        .select("*")
        .eq("id", str(project_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    project = result.data[0]
    if not project.get("portal_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portal not enabled for this project",
        )

    return PortalProject(**project)


# ============================================================================
# Dashboard
# ============================================================================


@router.get("/projects/{project_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    project_id: UUID,
    auth: AuthContext = Depends(require_project_access),
):
    """Get dashboard data (phase-aware)."""
    # Get project
    client = get_client()
    project_result = (
        client.table("projects")
        .select("*")
        .eq("id", str(project_id))
        .execute()
    )

    if not project_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    project = project_result.data[0]
    phase = PortalPhase(project.get("portal_phase", "pre_call"))

    # Get info requests for current phase
    info_phase = InfoRequestPhase.PRE_CALL if phase == PortalPhase.PRE_CALL else InfoRequestPhase.POST_CALL
    info_requests = await list_info_requests(project_id, phase=info_phase)

    # Calculate progress
    progress_data = await get_info_request_progress(project_id, info_phase)
    progress = DashboardProgress(**progress_data)

    # Build call info
    call_info = None
    if project.get("discovery_call_date"):
        call_info = {
            "consultant_name": "Matt Edmund",  # TODO: Get from project consultant
            "scheduled_date": project.get("discovery_call_date"),
            "completed_date": project.get("call_completed_at"),
            "duration_minutes": 60,
        }

    return DashboardResponse(
        project_id=project_id,
        project_name=project.get("client_display_name") or project["name"],
        phase=phase,
        call_info=call_info,
        progress=progress,
        info_requests=info_requests,
        due_date=project.get("prototype_expected_date"),
    )


# ============================================================================
# Info Requests (Questions/Actions)
# ============================================================================


@router.get("/projects/{project_id}/info-requests", response_model=list[InfoRequest])
async def list_portal_info_requests(
    project_id: UUID,
    phase: Optional[InfoRequestPhase] = None,
    auth: AuthContext = Depends(require_project_access),
):
    """List info requests for the client."""
    return await list_info_requests(project_id, phase=phase)


@router.patch("/info-requests/{request_id}", response_model=InfoRequest)
async def answer_info_request(
    request_id: UUID,
    data: InfoRequestAnswer,
    auth: AuthContext = Depends(require_auth),
):
    """Submit an answer to an info request."""
    # Get the request to verify access
    request = await get_info_request(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Info request not found",
        )

    # Submit the answer
    updated = await submit_info_request_answer(
        request_id=request_id,
        user_id=auth.user_id,
        answer_data=data.answer_data,
        status=data.status,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save answer",
        )

    # Flow answer to project context if configured
    if updated.auto_populates_to and updated.status == InfoRequestStatus.COMPLETE:
        await _flow_answer_to_context(updated)

    # Create authoritative signal from portal response
    if updated.status == InfoRequestStatus.COMPLETE and updated.answer_data:
        await _create_portal_response_signal(updated, auth.user_id)

    return updated


@router.patch("/info-requests/{request_id}/status", response_model=InfoRequest)
async def update_request_status(
    request_id: UUID,
    status: InfoRequestStatus,
    auth: AuthContext = Depends(require_auth),
):
    """Update the status of an info request (e.g., mark as skipped)."""
    updated = await update_info_request_status(request_id, status)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Info request not found",
        )
    return updated


# ============================================================================
# Project Context
# ============================================================================


@router.get("/projects/{project_id}/context", response_model=ProjectContext)
async def get_portal_context(
    project_id: UUID,
    auth: AuthContext = Depends(require_project_access),
):
    """Get the project context."""
    context = await get_or_create_project_context(project_id)

    # Calculate and update completion scores
    scores = await _calculate_completion_scores(context, project_id)
    context.completion_scores = scores
    context.overall_completion = scores.get("overall", 0)

    return context


@router.patch("/projects/{project_id}/context/{section}", response_model=ProjectContext)
async def update_portal_context_section(
    project_id: UUID,
    section: str,
    data: dict[str, Any],
    auth: AuthContext = Depends(require_project_access),
):
    """Update a specific section of project context."""
    valid_sections = ["problem", "success", "users", "design", "competitors", "tribal"]
    if section not in valid_sections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid section. Must be one of: {valid_sections}",
        )

    # Update with manual source (client edit)
    updated = await update_context_section(
        project_id=project_id,
        section=section,
        data=data,
        source=ContextSource.MANUAL,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update context",
        )

    # Lock the section since client manually edited it
    await lock_context_section(project_id, section)

    return updated


@router.post("/projects/{project_id}/context/lock")
async def lock_portal_context_section(
    project_id: UUID,
    section: str,
    field: Optional[str] = None,
    auth: AuthContext = Depends(require_project_access),
):
    """Lock a context section to prevent auto-updates."""
    await lock_context_section(project_id, section, field)
    return {"message": f"Section '{section}' locked"}


# ============================================================================
# Files
# ============================================================================


@router.get("/projects/{project_id}/files", response_model=list[ClientDocument])
async def list_portal_files(
    project_id: UUID,
    category: Optional[DocumentCategory] = None,
    auth: AuthContext = Depends(require_project_access),
):
    """List all files for a project."""
    return await list_client_documents(project_id, category=category)


@router.post("/projects/{project_id}/files", response_model=ClientDocument)
async def upload_portal_file(
    project_id: UUID,
    file: UploadFile = File(...),
    description: Optional[str] = None,
    info_request_id: Optional[UUID] = None,
    auth: AuthContext = Depends(require_project_access),
):
    """Upload a file to the project."""
    # Validate file size (10MB max)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10MB.",
        )

    # Upload to Supabase Storage
    client = get_client()
    file_path = f"projects/{project_id}/client/{auth.user_id}/{file.filename}"

    try:
        client.storage.from_("client-documents").upload(
            file_path,
            content,
            {"content-type": file.content_type or "application/octet-stream"},
        )
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file",
        )

    # Create document record
    doc = await create_client_document(
        project_id=project_id,
        uploaded_by=auth.user_id,
        data=ClientDocumentCreate(
            file_name=file.filename,
            file_path=file_path,
            file_size=len(content),
            file_type=file.filename.split(".")[-1] if "." in file.filename else "unknown",
            mime_type=file.content_type,
            category=DocumentCategory.CLIENT_UPLOADED,
            description=description,
            info_request_id=info_request_id,
        ),
    )

    # If uploaded for an info request, update its status
    if info_request_id:
        await submit_info_request_answer(
            request_id=info_request_id,
            user_id=auth.user_id,
            answer_data={"file_ids": [str(doc.id)]},
            status=InfoRequestStatus.COMPLETE,
        )

    return doc


@router.delete("/files/{document_id}")
async def delete_portal_file(
    document_id: UUID,
    auth: AuthContext = Depends(require_auth),
):
    """Delete a file (only uploader can delete)."""
    can_delete = await can_user_delete_document(document_id, auth.user_id)
    if not can_delete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete files you uploaded",
        )

    success = await delete_client_document(document_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return {"message": "Document deleted"}


# ============================================================================
# Chat (extends existing chat with client context)
# ============================================================================


from pydantic import BaseModel as PydanticBaseModel


class PortalChatRequest(PydanticBaseModel):
    """Request body for portal chat."""

    message: str
    conversation_id: Optional[UUID] = None
    conversation_history: list[dict] = []


@router.post("/projects/{project_id}/chat")
async def portal_chat(
    project_id: UUID,
    request: PortalChatRequest,
    auth: AuthContext = Depends(require_project_access),
):
    """
    Chat with the AI assistant in the client portal.

    The assistant can help clients:
    - Complete action items
    - Add information to project context
    - Answer questions about the project

    Returns a streaming response with Server-Sent Events.
    """
    import json
    from typing import AsyncGenerator

    from anthropic import AsyncAnthropic
    from fastapi.responses import StreamingResponse

    from app.chains.client_chat_tools import (
        build_client_system_prompt,
        execute_client_tool,
        get_client_tool_definitions,
    )
    from app.core.config import get_settings

    settings = get_settings()
    anthropic_api_key = getattr(settings, "ANTHROPIC_API_KEY", None)

    if not anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Chat service not configured",
        )

    # Get project info for context
    client = get_client()
    project_result = (
        client.table("projects")
        .select("name, client_display_name")
        .eq("id", str(project_id))
        .single()
        .execute()
    )
    project_name = project_result.data.get("client_display_name") or project_result.data.get("name", "Project")

    # Get user info for personalization
    user_result = (
        client.table("users")
        .select("first_name")
        .eq("id", str(auth.user_id))
        .single()
        .execute()
    )
    client_name = user_result.data.get("first_name") if user_result.data else None

    # Get or create conversation
    conversation_id = request.conversation_id
    if conversation_id:
        conv_response = (
            client.table("conversations")
            .select("*")
            .eq("id", str(conversation_id))
            .single()
            .execute()
        )
        if not conv_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
    else:
        conv_data = {
            "project_id": str(project_id),
            "conversation_type": "client_portal",
            "started_by": str(auth.user_id),
        }
        conv_response = client.table("conversations").insert(conv_data).execute()
        if conv_response.data:
            conversation_id = UUID(conv_response.data[0]["id"])
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create conversation",
            )

    async def generate() -> AsyncGenerator[str, None]:
        """Generate streaming chat responses."""
        assistant_content = ""
        tool_calls_data = []

        try:
            # Persist user message
            user_msg_data = {
                "conversation_id": str(conversation_id),
                "role": "user",
                "content": request.message,
            }
            user_msg_response = client.table("messages").insert(user_msg_data).execute()

            # Send conversation ID to client
            yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': str(conversation_id)})}\n\n"

            anthropic = AsyncAnthropic(api_key=anthropic_api_key)

            # Build messages
            messages = []
            for msg in request.conversation_history:
                if msg.get("content"):
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                    })
            messages.append({"role": "user", "content": request.message})

            # Build system prompt
            system_prompt = build_client_system_prompt(project_name, client_name)

            # Tool use loop
            max_turns = 5
            for turn in range(max_turns):
                async with anthropic.messages.stream(
                    model=getattr(settings, "CHAT_MODEL", "claude-3-5-haiku-latest"),
                    max_tokens=2048,
                    messages=messages,
                    system=system_prompt,
                    tools=get_client_tool_definitions(),
                ) as stream:
                    async for event in stream:
                        if hasattr(event, "type"):
                            if event.type == "content_block_delta":
                                if hasattr(event, "delta") and hasattr(event.delta, "text"):
                                    assistant_content += event.delta.text
                                    yield f"data: {json.dumps({'type': 'text', 'content': event.delta.text})}\n\n"

                    final_message = await stream.get_final_message()
                    tool_use_blocks = [
                        block for block in final_message.content if block.type == "tool_use"
                    ]

                    if not tool_use_blocks:
                        break

                    # Execute tools
                    tool_results = []
                    for tool_block in tool_use_blocks:
                        logger.info(f"Client executing tool: {tool_block.name}")
                        tool_result = await execute_client_tool(
                            project_id=project_id,
                            user_id=auth.user_id,
                            tool_name=tool_block.name,
                            tool_input=tool_block.input,
                        )

                        tool_calls_data.append({
                            "tool_name": tool_block.name,
                            "status": "complete",
                            "result": tool_result,
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_block.id,
                            "content": json.dumps(tool_result),
                        })

                        yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': tool_block.name, 'result': tool_result})}\n\n"

                    # Add to conversation for next turn
                    messages.append({
                        "role": "assistant",
                        "content": final_message.content,
                    })
                    messages.append({
                        "role": "user",
                        "content": tool_results,
                    })

                    assistant_content = ""

            # Persist assistant message
            if assistant_content or tool_calls_data:
                assistant_msg_data = {
                    "conversation_id": str(conversation_id),
                    "role": "assistant",
                    "content": assistant_content,
                }
                if tool_calls_data:
                    assistant_msg_data["tool_calls"] = tool_calls_data
                client.table("messages").insert(assistant_msg_data).execute()

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Error in client chat stream: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Helper Functions
# ============================================================================


async def _create_portal_response_signal(info_request: InfoRequest, user_id: UUID) -> None:
    """Create an authoritative signal from a client portal response."""
    from datetime import datetime
    from uuid import uuid4

    # Get answer text
    answer_text = info_request.answer_data.get("text", "")
    if not answer_text:
        # For file uploads, create a note about the upload
        file_ids = info_request.answer_data.get("file_ids", [])
        if file_ids:
            answer_text = f"Client uploaded {len(file_ids)} file(s) for: {info_request.title}"
        else:
            return  # No content to create signal from

    try:
        client = get_client()
        # Insert signal with source_type for evidence display
        client.table("signals").insert({
            "project_id": str(info_request.project_id),
            "signal_type": "portal_response",
            "source": "client_portal",
            "source_type": "portal_response",
            "source_label": f"Client Answer: {info_request.title[:50]}",
            "source_timestamp": datetime.utcnow().isoformat(),
            "raw_text": f"Q: {info_request.title}\n\nA: {answer_text}",
            "metadata": {
                "info_request_id": str(info_request.id),
                "request_type": info_request.request_type.value if info_request.request_type else "question",
                "authority": "client",
                "answered_by": str(user_id),
                "best_answered_by": info_request.best_answered_by,
            },
            "run_id": str(uuid4()),
        }).execute()
        logger.info(f"Created portal_response signal for info_request {info_request.id}")

        # Invalidate DI cache - new signal to analyze
        try:
            from app.db.di_cache import invalidate_cache
            invalidate_cache(info_request.project_id, "new portal_response signal")
        except Exception as cache_err:
            logger.warning(f"Failed to invalidate DI cache: {cache_err}")
    except Exception as e:
        logger.error(f"Failed to create portal_response signal: {e}")
        # Don't fail the request if signal creation fails


async def _flow_answer_to_context(info_request: InfoRequest) -> None:
    """Flow an info request answer to project context sections."""
    if not info_request.auto_populates_to or not info_request.answer_data:
        return

    answer_text = info_request.answer_data.get("text", "")
    if not answer_text:
        return

    for section in info_request.auto_populates_to:
        if section == "problem":
            await update_context_section(
                project_id=info_request.project_id,
                section="problem",
                data={"main": answer_text},
                source=ContextSource.DASHBOARD,
            )
        elif section == "users":
            # Parse user info from answer if structured
            pass
        elif section == "metrics":
            # Parse metrics if structured
            pass
        elif section == "tribal":
            await add_tribal_knowledge(
                project_id=info_request.project_id,
                knowledge=answer_text,
                source=ContextSource.DASHBOARD,
            )


async def _calculate_completion_scores(
    context: ProjectContext,
    project_id: UUID,
) -> dict[str, int]:
    """Calculate completion scores for each section."""
    scores = {}

    # Problem section (problem_main + problem_why_now + metrics)
    problem_score = 0
    if context.problem_main:
        problem_score += 50
    if context.problem_why_now:
        problem_score += 30
    if context.metrics:
        problem_score += 20
    scores["problem"] = min(problem_score, 100)

    # Success section
    success_score = 0
    if context.success_future:
        success_score += 60
    if context.success_wow:
        success_score += 40
    scores["success"] = min(success_score, 100)

    # Users section
    if context.key_users:
        # Score based on completeness of user details
        user_scores = []
        for user in context.key_users:
            user_score = 25  # Base for having name
            if user.role:
                user_score += 25
            if user.frustrations:
                user_score += 25
            if user.helps:
                user_score += 25
            user_scores.append(user_score)
        scores["users"] = int(sum(user_scores) / len(user_scores)) if user_scores else 0
    else:
        scores["users"] = 0

    # Design section
    design_score = 0
    if context.design_love:
        design_score += 60
    if context.design_avoid:
        design_score += 40
    scores["design"] = min(design_score, 100)

    # Competitors section
    if context.competitors:
        comp_scores = []
        for comp in context.competitors:
            comp_score = 25  # Base for having name
            if comp.worked:
                comp_score += 25
            if comp.didnt_work:
                comp_score += 25
            if comp.why_left:
                comp_score += 25
            comp_scores.append(comp_score)
        scores["competitors"] = int(sum(comp_scores) / len(comp_scores)) if comp_scores else 0
    else:
        scores["competitors"] = 0

    # Tribal knowledge section
    if context.tribal_knowledge:
        # Score based on number of items (up to 5)
        scores["tribal"] = min(len(context.tribal_knowledge) * 20, 100)
    else:
        scores["tribal"] = 0

    # Files section
    doc_counts = await get_document_counts(project_id)
    # Score based on having at least 2 files
    file_count = doc_counts.get("total", 0)
    scores["files"] = min(file_count * 50, 100)

    # Overall score (weighted average)
    weights = {
        "problem": 0.20,
        "success": 0.15,
        "users": 0.15,
        "design": 0.10,
        "competitors": 0.15,
        "tribal": 0.10,
        "files": 0.15,
    }
    overall = sum(scores.get(k, 0) * v for k, v in weights.items())
    scores["overall"] = int(overall)

    return scores
