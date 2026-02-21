"""Chat assistant API endpoints."""

import json
from typing import Any, AsyncGenerator, Dict, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.chains.chat_tools import execute_tool, get_tools_for_context
from app.context.dynamic_prompt_builder import build_smart_chat_prompt
from app.context.tool_truncator import truncate_tool_result
from app.core.action_engine import compute_context_frame
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.rate_limiter import check_chat_rate_limit, get_chat_rate_limit_stats
from app.db.supabase_client import get_supabase

# Page-context → entity type filtering for retrieval
# Prioritizes relevant entity types so vector search returns focused results
_PAGE_ENTITY_TYPES: dict[str, list[str]] = {
    "brd:features": ["feature", "unlock"],
    "brd:personas": ["persona"],
    "brd:workflows": ["workflow", "workflow_step"],
    "brd:data-entities": ["data_entity"],
    "brd:stakeholders": ["stakeholder"],
    "brd:constraints": ["constraint"],
    "brd:solution-flow": ["solution_flow_step", "feature", "workflow", "unlock"],
    "brd:business-drivers": ["business_driver"],
    "brd:unlocks": ["unlock", "feature", "competitor"],
    "prototype": ["prototype_feedback", "feature"],
    # Canvas / overview pages get all types (None = no filter)
}

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

        # Compute v3 context frame (single source of truth for chat context)
        context_frame = await compute_context_frame(project_id, max_actions=5)

        # Get project name from Supabase (single fast query)
        project_row = (
            supabase.table("projects")
            .select("name")
            .eq("id", str(project_id))
            .single()
            .execute()
        )
        project_name = project_row.data.get("name", "Unknown") if project_row.data else "Unknown"

        logger.info(
            f"Context frame: phase={context_frame.phase.value}, "
            f"progress={context_frame.phase_progress:.0%}, "
            f"gaps={context_frame.total_gap_count}"
        )

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

                # Build messages from recent history (no compression LLM call needed)
                # Keep last 10 messages — fits well within 80K token budget
                recent_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in request.conversation_history[-10:]
                    if msg.content and msg.content.strip()
                ]
                messages = recent_history + [{"role": "user", "content": request.message}]

                # Build solution flow context if on solution-flow page
                solution_flow_ctx = None
                if request.page_context == "brd:solution-flow":
                    try:
                        from app.core.solution_flow_context import build_solution_flow_context

                        focused_step_id = None
                        if request.focused_entity:
                            fe_data = request.focused_entity.get("data", {})
                            focused_step_id = fe_data.get("id")

                        solution_flow_ctx = await build_solution_flow_context(
                            project_id=str(project_id),
                            focused_step_id=focused_step_id,
                        )
                    except Exception as e:
                        logger.debug(f"Solution flow context build failed (non-fatal): {e}")

                # Pre-fetch relevant evidence via unified retrieval
                retrieval_context = ""
                try:
                    from app.core.retrieval import retrieve
                    from app.core.retrieval_format import format_retrieval_for_context

                    is_simple = len(request.message.split()) < 8 and "?" not in request.message

                    # Build context hint from focused entity (enriches vector search)
                    context_hint = None
                    if solution_flow_ctx and solution_flow_ctx.focused_step_prompt:
                        # Flow-aware retrieval: use step goal + retrieval hints
                        hint_parts = []
                        if request.focused_entity:
                            fe_data = request.focused_entity.get("data", {})
                            step_title = fe_data.get("title", "")
                            step_goal = fe_data.get("goal", "")
                            if step_title:
                                hint_parts.append(f"Solution flow step: {step_title}.")
                            if step_goal:
                                hint_parts.append(f"Goal: {step_goal}.")
                        if solution_flow_ctx.retrieval_hints:
                            hint_parts.append("Related: " + "; ".join(solution_flow_ctx.retrieval_hints[:2]))
                        if hint_parts:
                            context_hint = " ".join(hint_parts)
                    elif request.focused_entity:
                        fe = request.focused_entity
                        etype = fe.get("type", "")
                        edata = fe.get("data", {})
                        ename = edata.get("title") or edata.get("name") or ""
                        if ename:
                            context_hint = f"User is viewing {etype}: \"{ename}\". Prioritize evidence related to this entity."

                    # Page-aware entity type filtering
                    entity_types = _PAGE_ENTITY_TYPES.get(request.page_context or "")

                    retrieval_result = await retrieve(
                        query=request.message,
                        project_id=str(project_id),
                        max_rounds=2 if not is_simple else 1,
                        skip_decomposition=is_simple,
                        skip_reranking=is_simple,
                        evaluation_criteria="Enough context to answer the user's question",
                        context_hint=context_hint,
                        entity_types=entity_types,
                    )
                    retrieval_context = format_retrieval_for_context(
                        retrieval_result, style="chat", max_tokens=2000
                    )
                except Exception as e:
                    logger.debug(f"Retrieval pre-fetch failed (non-fatal): {e}")

                # Build v3 smart chat prompt from context frame
                system_prompt = build_smart_chat_prompt(
                    context_frame=context_frame,
                    project_name=project_name,
                    page_context=request.page_context,
                    focused_entity=request.focused_entity,
                    conversation_context=request.conversation_context,
                    retrieval_context=retrieval_context,
                    solution_flow_context=solution_flow_ctx,
                )

                # Log context stats
                logger.info(
                    f"Chat prompt: phase={context_frame.phase.value}, "
                    f"page={request.page_context or 'none'}, "
                    f"history_msgs={len(recent_history)}"
                )

                # Token tracking for cost logging
                total_input = 0
                total_output = 0

                # Build filtered tool set once (reused across turns)
                chat_tools = get_tools_for_context(request.page_context)
                logger.info(f"Chat tools: {len(chat_tools)} tools for page={request.page_context or 'none'}")

                # Tool use loop - handle multi-turn conversation with tools
                max_turns = 5  # Prevent infinite loops
                for turn in range(max_turns):
                    # Stream response from Claude using configured model
                    async with client.messages.stream(
                        model=settings.CHAT_MODEL,  # Configurable (default: Haiku 3.5)
                        max_tokens=settings.CHAT_RESPONSE_BUFFER,
                        messages=messages,
                        system=system_prompt,
                        tools=chat_tools,
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

                        # Log LLM usage
                        if hasattr(final_message, 'usage'):
                            total_input += getattr(final_message.usage, 'input_tokens', 0)
                            total_output += getattr(final_message.usage, 'output_tokens', 0)

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

                # Log LLM usage for cost tracking
                if total_input or total_output:
                    try:
                        from app.core.llm_usage import log_llm_usage
                        log_llm_usage(
                            model=settings.CHAT_MODEL,
                            input_tokens=total_input,
                            output_tokens=total_output,
                            operation="chat",
                            project_id=str(project_id),
                            metadata={"conversation_id": str(conversation_id)},
                        )
                    except Exception:
                        pass  # Fire-and-forget

                # Persist assistant message
                if assistant_content or tool_calls_data:
                    assistant_msg_data = {
                        "conversation_id": str(conversation_id),
                        "role": "assistant",
                        "content": assistant_content,
                        "metadata": {
                            "model": settings.CHAT_MODEL,
                            "input_tokens": total_input,
                            "output_tokens": total_output,
                        },
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


# =============================================================================
# Chat-as-Signal: Entity Detection + Extraction
# =============================================================================


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


