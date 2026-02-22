"""Chat streaming engine — Anthropic streaming with multi-turn tool loop."""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List
from uuid import UUID

from app.chains.chat_tools import execute_tool, get_tools_for_context
from app.context.dynamic_prompt_builder import build_smart_chat_prompt
from app.context.tool_truncator import truncate_tool_result
from app.core.chat_context import assemble_chat_context
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_TOOL_TURNS = 5


@dataclass
class ChatStreamConfig:
    """Explicit inputs for a chat streaming session."""

    project_id: UUID
    conversation_id: UUID
    message: str
    conversation_history: List[Dict[str, str]]
    page_context: str | None = None
    focused_entity: Dict[str, Any] | None = None
    conversation_context: str | None = None
    anthropic_api_key: str = ""
    chat_model: str = "claude-3-5-haiku-20241022"
    chat_response_buffer: int = 4096


def _sse_event(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


async def generate_chat_stream(
    config: ChatStreamConfig,
    supabase: Any,
) -> AsyncGenerator[str, None]:
    """Generate streaming chat responses with tool loop.

    Yields SSE events: conversation_id → text → tool_result → done/error.
    """
    assistant_content = ""
    tool_calls_data: list[dict] = []

    try:
        # Send conversation ID immediately so client can track
        yield _sse_event({"type": "conversation_id", "conversation_id": str(config.conversation_id)})

        # Import here to avoid loading if API key not set
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=config.anthropic_api_key)

        # Build messages from recent history (no compression LLM call needed)
        # Keep last 10 messages — fits well within 80K token budget
        recent_history = [
            {"role": msg["role"], "content": msg["content"]}
            for msg in config.conversation_history[-10:]
            if msg.get("content", "").strip()
        ]
        messages = recent_history + [{"role": "user", "content": config.message}]

        # ── Parallel context assembly ────────────────────────────────
        # Context building + user message persistence run concurrently
        # to cut ~2-4s off response time.

        async def _persist_user_msg():
            user_msg_data = {
                "conversation_id": str(config.conversation_id),
                "role": "user",
                "content": config.message,
            }
            return supabase.table("messages").insert(user_msg_data).execute()

        chat_ctx, _user_msg_resp = await asyncio.gather(
            assemble_chat_context(
                project_id=config.project_id,
                message=config.message,
                page_context=config.page_context,
                focused_entity=config.focused_entity,
                supabase=supabase,
            ),
            _persist_user_msg(),
        )

        logger.info(
            f"Context frame: phase={chat_ctx.context_frame.phase.value}, "
            f"progress={chat_ctx.context_frame.phase_progress:.0%}, "
            f"gaps={chat_ctx.context_frame.total_gap_count}"
        )

        # Build v3 smart chat prompt from context frame
        system_prompt = build_smart_chat_prompt(
            context_frame=chat_ctx.context_frame,
            project_name=chat_ctx.project_name,
            page_context=config.page_context,
            focused_entity=config.focused_entity,
            conversation_context=config.conversation_context,
            retrieval_context=chat_ctx.retrieval_context,
            solution_flow_context=chat_ctx.solution_flow_ctx,
        )

        # Log context stats
        logger.info(
            f"Chat prompt: phase={chat_ctx.context_frame.phase.value}, "
            f"page={config.page_context or 'none'}, "
            f"history_msgs={len(recent_history)}"
        )

        # Token tracking for cost logging
        total_input = 0
        total_output = 0

        # Build filtered tool set once (reused across turns)
        chat_tools = get_tools_for_context(config.page_context)
        logger.info(f"Chat tools: {len(chat_tools)} tools for page={config.page_context or 'none'}")

        # Tool use loop - handle multi-turn conversation with tools
        for turn in range(MAX_TOOL_TURNS):
            # Stream response from Claude using configured model
            async with client.messages.stream(
                model=config.chat_model,
                max_tokens=config.chat_response_buffer,
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
                                yield _sse_event({"type": "text", "content": event.delta.text})

                # Get the final message to check for tool use
                final_message = await stream.get_final_message()

                # Log LLM usage
                if hasattr(final_message, "usage"):
                    total_input += getattr(final_message.usage, "input_tokens", 0)
                    total_output += getattr(final_message.usage, "output_tokens", 0)

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
                        project_id=config.project_id,
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
                    yield _sse_event({"type": "tool_result", "tool_name": tool_block.name, "result": tool_result})

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
                    model=config.chat_model,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    operation="chat",
                    project_id=str(config.project_id),
                    metadata={"conversation_id": str(config.conversation_id)},
                )
            except Exception:
                pass  # Fire-and-forget

        # Persist assistant message
        if assistant_content or tool_calls_data:
            assistant_msg_data = {
                "conversation_id": str(config.conversation_id),
                "role": "assistant",
                "content": assistant_content,
                "metadata": {
                    "model": config.chat_model,
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                },
            }

            if tool_calls_data:
                assistant_msg_data["tool_calls"] = tool_calls_data

            supabase.table("messages").insert(assistant_msg_data).execute()

        # Send completion event
        yield _sse_event({"type": "done"})

    except Exception as e:
        logger.error(f"Error in chat stream: {e}", exc_info=True)
        yield _sse_event({"type": "error", "message": str(e)})
