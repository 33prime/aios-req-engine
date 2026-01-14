"""Chat assistant API endpoints."""

import json
from typing import Any, AsyncGenerator, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.chains.chat_context import build_smart_context
from app.chains.chat_tools import execute_tool, get_tool_definitions
from app.context.conversation_compressor import compress_conversation
from app.context.dynamic_prompt_builder import build_dynamic_prompt
from app.context.intent_classifier import classify_intent
from app.context.models import ChatMessage as ContextChatMessage
from app.context.state_frame import generate_state_frame
from app.context.token_budget import get_budget_manager
from app.context.tool_truncator import truncate_tool_result
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
    conversation_id: str
    conversation_history: List[ChatMessage] = []
    context: Dict[str, Any] | None = None


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

        # Build smart context
        context = await build_smart_context(project_id, request)

        # Generate state frame for goal-based context
        state_frame = await generate_state_frame(project_id, context)

        # Classify user intent for dynamic prompt building
        intent = await classify_intent(request.message, context)
        logger.info(f"Intent: {intent.primary} (confidence: {intent.confidence:.2f})")

        # Generate streaming response
        async def generate() -> AsyncGenerator[str, None]:
            """Generate streaming chat responses."""
            assistant_content = ""  # Track assistant response for persistence
            tool_calls_data = []  # Track tool executions

            try:
                # Persist user message
                user_msg_data = {
                    "conversation_id": str(conversation_id),
                    "role": "user",
                    "content": request.message,
                }
                user_msg_response = supabase.table("messages").insert(user_msg_data).execute()
                user_message_id = user_msg_response.data[0]["id"] if user_msg_response.data else None

                # Send conversation ID to client (for subsequent requests)
                yield f"data: {json.dumps({'type': 'conversation_id', 'conversation_id': str(conversation_id)})}\n\n"

                # Import here to avoid loading if API key not set
                from anthropic import AsyncAnthropic

                client = AsyncAnthropic(api_key=anthropic_api_key)

                # Compress conversation history
                history_messages = [
                    ContextChatMessage(role=msg.role, content=msg.content)
                    for msg in request.conversation_history
                    if msg.content and msg.content.strip()
                ]
                compressed = await compress_conversation(
                    messages=history_messages,
                    recent_count=settings.CHAT_RECENT_MESSAGES,
                    max_summary_tokens=settings.CHAT_MAX_SUMMARY_TOKENS,
                )

                # Build messages for Claude
                messages = compressed.to_messages()
                messages.append({"role": "user", "content": request.message})

                # Build dynamic system prompt with state frame
                budget_manager = get_budget_manager()
                system_prompt = build_dynamic_prompt(
                    context=context,
                    state_frame=state_frame,
                    intent=intent,
                    budget_manager=budget_manager,
                )

                # Log context stats
                logger.info(
                    f"Context: phase={state_frame.current_phase.value}, "
                    f"progress={state_frame.phase_progress:.0%}, "
                    f"blockers={len(state_frame.blockers)}, "
                    f"history_summarized={compressed.total_messages_summarized}"
                )

                # Tool use loop - handle multi-turn conversation with tools
                max_turns = 5  # Prevent infinite loops
                for turn in range(max_turns):
                    # Stream response from Claude using configured model
                    async with client.messages.stream(
                        model=settings.CHAT_MODEL,  # Configurable (default: Haiku 3.5)
                        max_tokens=settings.CHAT_RESPONSE_BUFFER,
                        messages=messages,
                        system=system_prompt,
                        tools=get_tool_definitions(),
                    ) as stream:
                        # Collect the final message
                        async for event in stream:
                            if hasattr(event, "type"):
                                if event.type == "content_block_delta":
                                    if hasattr(event, "delta") and hasattr(event.delta, "text"):
                                        # Accumulate content for persistence
                                        assistant_content += event.delta.text

                                        # Send text chunk
                                        yield f"data: {json.dumps({'type': 'text', 'content': event.delta.text})}\n\n"

                        # Get the final message to check for tool use
                        final_message = await stream.get_final_message()

                        # Check if Claude wants to use tools
                        tool_use_blocks = [block for block in final_message.content if block.type == "tool_use"]

                        if not tool_use_blocks:
                            # No tool use - conversation is complete
                            break

                        # Execute all requested tools
                        tool_results = []
                        for tool_block in tool_use_blocks:
                            logger.info(f"Executing tool: {tool_block.name}")
                            tool_result = await execute_tool(
                                project_id=project_id,
                                tool_name=tool_block.name,
                                tool_input=tool_block.input,
                            )

                            # Truncate tool result for context window efficiency
                            truncated_result = truncate_tool_result(
                                tool_name=tool_block.name,
                                result=tool_result,
                            )

                            # Track tool call for persistence (use original result)
                            tool_calls_data.append({
                                "tool_name": tool_block.name,
                                "status": "complete",
                                "result": tool_result,
                            })

                            # Build tool result for next turn (use truncated result)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_block.id,
                                "content": json.dumps(truncated_result),
                            })

                            # Send tool result notification to frontend (use original)
                            yield f"data: {json.dumps({'type': 'tool_result', 'tool_name': tool_block.name, 'result': tool_result})}\n\n"

                        # Add assistant message with tool use to conversation
                        messages.append({
                            "role": "assistant",
                            "content": final_message.content,
                        })

                        # Add tool results to conversation
                        messages.append({
                            "role": "user",
                            "content": tool_results,
                        })

                        # Clear assistant_content for next turn
                        assistant_content = ""

                        # Continue loop to get Claude's response to the tool results

                # Persist assistant message
                if assistant_content or tool_calls_data:
                    assistant_msg_data = {
                        "conversation_id": str(conversation_id),
                        "role": "assistant",
                        "content": assistant_content,
                    }

                    if tool_calls_data:
                        assistant_msg_data["tool_calls"] = tool_calls_data

                    supabase.table("messages").insert(assistant_msg_data).execute()

                # Send completion event
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                logger.error(f"Error in chat stream: {e}", exc_info=True)
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
    semantic_search_research directly for the Research tab.

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


def build_system_prompt(context: Dict[str, Any]) -> str:
    """
    Build the system prompt with project context.

    Args:
        context: Project context dictionary

    Returns:
        System prompt string
    """
    project = context.get("project", {})
    summary = context.get("summary", {})
    focused_entity = context.get("focused_entity")

    mode_description = (
        "Maintenance Mode (surgical updates via patches)"
        if project.get("prd_mode") == "maintenance"
        else "Initial Mode (generative baseline building)"
    )

    baseline_status = (
        "✓ Finalized - research available"
        if project.get("baseline_ready")
        else "⏳ In progress - research not yet available"
    )

    # Build focused entity section if present
    focused_section = ""
    if focused_entity:
        entity_type = focused_entity.get("type", "entity")
        entity_data = focused_entity.get("data", {})
        entity_title = entity_data.get("title") or entity_data.get("name") or entity_data.get("question", "Untitled")

        focused_section = f"""

# Currently Viewing
The consultant is currently viewing: **{entity_type}** - "{entity_title}"

When answering questions, prioritize information relevant to this focused entity.
You can reference specific details from this entity in your responses.
"""

    # Get intent data and suggestions if available
    intent_data = context.get("intent", {})
    suggestions = context.get("suggestions", [])

    # Build suggestions section
    suggestions_section = ""
    if suggestions:
        suggestions_section = "\n\n# Proactive Suggestions\n"
        suggestions_section += "Consider mentioning these suggestions in your response when appropriate:\n"
        for suggestion in suggestions:
            suggestions_section += f"- {suggestion}\n"

    return f"""You are a **Project Command Center** - an AI helping consultants manage client-approved data and project evolution.

# Your Philosophy
- **Signal-driven updates** - Client signals (transcripts, emails, documents) are the source of truth
- **Proposals, not patches** - Changes come as reviewable proposals for bulk apply/discard
- **Client-approved data** - Focus on capturing what clients say, not generating content
- **Command center** - Help navigate project state and pending decisions

# Project Context
Project: {project.get('name', 'Unknown')}
Mode: {mode_description}
Baseline: {baseline_status}

# Current State
- Features: {summary.get('features', 0)}
- Personas: {summary.get('personas', 0)}
- Value Path Steps: {summary.get('vp_steps', 0)}
- Open Confirmations: {summary.get('confirmations_open', 0)}

# Your Primary Capabilities

## 1. Add Client Signals (PRIMARY WORKFLOW)
Use `add_signal` when the user shares client data:
- **signal_type**: "transcript", "email", "document", "note"
- Automatically extracts: stakeholders, creative brief info, features, personas
- Creates a **proposal** for review if significant changes detected
- User reviews proposals in the Overview tab

Example user input: "Here's the transcript from our discovery call..."
→ Use `add_signal` with signal_type="transcript"

## 2. Review Proposals
Use `preview_proposal` and `apply_proposal` to manage pending changes:
- `preview_proposal`: Show detailed before/after for a proposal
- `apply_proposal`: Apply changes after user confirms
- Proposals appear in the Overview tab's "Pending Proposals" section

## 3. Project Status
Use `get_project_status` to understand current state:
- Shows counts for all entities
- Highlights items needing attention

## 4. Research & Evidence
- `search_research`: Find evidence from ingested research
- `semantic_search_research`: AI-powered concept search

## 5. Client Communication
- `list_pending_confirmations`: Questions needing client input
- `generate_client_email`: Draft client outreach emails
- `generate_meeting_agenda`: Structure client meetings

# How to Help Effectively

## When user shares client data (transcript, email, etc.):
1. Use `add_signal` with appropriate signal_type
2. Report what was extracted (stakeholders, features, etc.)
3. If a proposal was created, mention it's in Overview tab for review
4. NEVER use old tools like list_insights or bulk_apply_patches

## When user asks about project state:
1. Use `get_project_status` for current counts
2. Point them to specific tabs for details
3. Highlight any pending proposals or confirmations

## When user wants to make changes:
1. If they have new client data → `add_signal`
2. If they want to propose features → `propose_features`
3. If they want to apply a proposal → `apply_proposal`

# Guidelines
1. **Signal-first** - Client data via `add_signal` is the primary workflow
2. **Proposals over patches** - Use proposal system, not old patch system
3. **Be concise** - Use markdown for clarity
4. **Point to UI** - Tell users where to find things (Overview tab for proposals)

# Important
- **DO NOT use**: list_insights, bulk_apply_patches, assess_readiness, apply_patch
- **DO use**: add_signal, preview_proposal, apply_proposal, get_project_status
- Changes from signals appear as proposals in the Overview tab
- Value Path = user journey steps (not "value proposition")

When the user asks about current state, use tools to get fresh data rather than relying on the context above (which may be stale).
{suggestions_section}{focused_section}
"""
