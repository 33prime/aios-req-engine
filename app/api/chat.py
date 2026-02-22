"""Chat assistant API endpoints."""

from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.chains.chat_tools import execute_tool
from app.core.chat_stream import ChatStreamConfig, generate_chat_stream
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.rate_limiter import check_chat_rate_limit, get_chat_rate_limit_stats
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str  # 'user' or 'assistant'
    content: str


class ChatRequest(BaseModel):
    """Request to chat with the AI assistant."""

    message: str
    conversation_id: str | None = None
    conversation_history: List[ChatMessage] = []
    context: Dict[str, Any] | None = None
    page_context: str | None = None  # e.g., "brd:workflows", "canvas", "prototype"
    focused_entity: Dict[str, Any] | None = None  # {type, data: {title/name}}
    conversation_context: str | None = None  # From conversation starter


@router.post("/chat")
async def chat_with_assistant(
    request: ChatRequest,
    project_id: UUID = Query(..., description="Project UUID"),
    conversation_id: UUID | None = Query(None, description="Conversation UUID (optional)"),
) -> StreamingResponse:
    """
    Chat with the AI assistant using streaming responses.

    This endpoint:
    1. Creates/fetches conversation
    2. Builds smart context based on the project and message
    3. Calls Claude API with streaming
    4. Executes tools as needed
    5. Persists messages to database
    6. Returns streaming responses

    Args:
        request: Chat request with message and history
        project_id: Project UUID
        conversation_id: Optional conversation UUID (creates new if not provided)

    Returns:
        StreamingResponse with Server-Sent Events
    """
    # Rate limiting
    check_chat_rate_limit(project_id)

    settings = get_settings()
    supabase = get_supabase()

    # Check if Anthropic API key is configured
    anthropic_api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
    if not anthropic_api_key:
        raise HTTPException(
            status_code=500,
            detail="Anthropic API key not configured. Please set ANTHROPIC_API_KEY in environment.",
        )

    try:
        # Get or create conversation
        if conversation_id:
            # Fetch existing conversation
            conv_response = (
                supabase.table("conversations").select("*").eq("id", str(conversation_id)).single().execute()
            )
            conversation = conv_response.data if conv_response.data else None

            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # Create new conversation
            conv_data = {"project_id": str(project_id)}

            conv_response = supabase.table("conversations").insert(conv_data).execute()

            if conv_response.data:
                conversation = conv_response.data[0]
                conversation_id = UUID(conversation["id"])
            else:
                raise HTTPException(status_code=500, detail="Failed to create conversation")

        config = ChatStreamConfig(
            project_id=project_id,
            conversation_id=conversation_id,
            message=request.message,
            conversation_history=[
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ],
            page_context=request.page_context,
            focused_entity=request.focused_entity,
            conversation_context=request.conversation_context,
            anthropic_api_key=anthropic_api_key,
            chat_model=settings.CHAT_MODEL,
            chat_response_buffer=settings.CHAT_RESPONSE_BUFFER,
        )

        return StreamingResponse(
            generate_chat_stream(config, supabase),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations")
async def list_conversations(
    project_id: UUID = Query(..., description="Project UUID"),
    limit: int = Query(20, description="Maximum number of conversations to return"),
    include_archived: bool = Query(False, description="Include archived conversations"),
) -> Dict[str, Any]:
    """
    List conversations for a project.

    Args:
        project_id: Project UUID
        limit: Maximum number of conversations
        include_archived: Whether to include archived conversations

    Returns:
        List of conversations with metadata
    """
    supabase = get_supabase()

    try:
        query = supabase.table("conversations").select("*").eq("project_id", str(project_id))

        if not include_archived:
            query = query.eq("is_archived", False)

        response = query.order("last_message_at", desc=True).limit(limit).execute()

        conversations = response.data or []

        return {"conversations": conversations, "total": len(conversations)}

    except Exception as e:
        logger.error(f"Error listing conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rate-limit-status")
async def get_rate_limit_status(project_id: UUID = Query(..., description="Project UUID")) -> Dict[str, Any]:
    """
    Get rate limit status for chat endpoint.

    Args:
        project_id: Project UUID

    Returns:
        Rate limit stats
    """
    try:
        stats = get_chat_rate_limit_stats(project_id)
        return {"status": "ok", "rate_limit": stats}

    except Exception as e:
        logger.error(f"Error getting rate limit status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(100, description="Maximum number of messages to return"),
) -> Dict[str, Any]:
    """
    Get messages for a conversation.

    Args:
        conversation_id: Conversation UUID
        limit: Maximum number of messages

    Returns:
        List of messages
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("messages")
            .select("*")
            .eq("conversation_id", str(conversation_id))
            .order("created_at")
            .limit(limit)
            .execute()
        )

        messages = response.data or []

        return {"messages": messages, "total": len(messages)}

    except Exception as e:
        logger.error(f"Error getting messages: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/tools")
async def execute_chat_tool(
    request: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a chat tool directly without going through the full chat flow.

    This endpoint allows the frontend to execute specific tools like
    search directly for the Research tab.

    Args:
        request: Dict with project_id, tool_name, and tool_input

    Returns:
        Tool execution result
    """
    try:
        project_id_str = request.get("project_id")
        tool_name = request.get("tool_name")
        tool_input = request.get("tool_input", {})

        if not project_id_str:
            raise HTTPException(status_code=400, detail="project_id is required")
        if not tool_name:
            raise HTTPException(status_code=400, detail="tool_name is required")

        project_id = UUID(project_id_str)

        logger.info(f"Executing tool {tool_name} directly for project {project_id}")

        # Execute the tool
        result = await execute_tool(project_id, tool_name, tool_input)

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    except Exception as e:
        logger.error(f"Error executing tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
