"""Chat streaming engine — Anthropic streaming with multi-turn tool loop."""

import asyncio
import json
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.chains.chat_tools import execute_tool, get_tools_for_context
from app.context.dynamic_prompt_builder import build_smart_chat_prompt
from app.context.intent_classifier import classify_intent_async
from app.context.prompt_compiler import compile_cognitive_frame, compile_prompt
from app.context.tool_truncator import truncate_tool_result
from app.core.chat_context import assemble_chat_context, invalidate_retrieval_cache
from app.core.chat_fast_path import try_fast_path
from app.core.chat_routing_log import (
    RoutingTimer,
    compute_tier,
    estimate_cost,
    log_chat_routing,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_TOOL_TURNS = 5


@dataclass
class ChatStreamConfig:
    """Explicit inputs for a chat streaming session."""

    project_id: UUID
    conversation_id: UUID
    message: str
    conversation_history: list[dict[str, str]]
    page_context: str | None = None
    focused_entity: dict[str, Any] | None = None
    conversation_context: str | None = None
    anthropic_api_key: str = ""
    chat_model: str = "claude-3-5-haiku-20241022"
    chat_response_buffer: int = 1500


def _sse_event(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data)}\n\n"


def _template_summarize(messages: list[dict]) -> tuple[str, int, int]:
    """Template-based summary of older messages — no LLM call.

    Returns (summary, original_token_est, compressed_token_est).
    """
    entity_pattern = re.compile(
        r'\b(?:feature|persona|workflow|stakeholder|constraint|driver|step)'
        r'\s*[:\-]?\s*["\']?([^"\',.]{3,40})',
        re.I,
    )
    action_pattern = re.compile(
        r'\b(created|updated|deleted|confirmed|added|removed'
        r'|changed|resolved|generated)\b',
        re.I,
    )

    entities: set[str] = set()
    actions: set[str] = set()
    last_user_msg = ""
    original_chars = 0

    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            continue
        original_chars += len(content)
        for match in entity_pattern.finditer(content):
            entities.add(match.group(1).strip()[:30])
        for match in action_pattern.finditer(content):
            actions.add(match.group(1).lower())
        if msg.get("role") == "user":
            last_user_msg = content[:100]

    parts: list[str] = []
    if entities:
        parts.append(
            f"Entities discussed: {', '.join(list(entities)[:8])}"
        )
    if actions:
        parts.append(
            f"Actions taken: {', '.join(list(actions)[:5])}"
        )
    if last_user_msg:
        parts.append(f"Last topic: {last_user_msg}")

    summary = "; ".join(parts) if parts else "Earlier conversation context"

    # Rough token estimates (~4 chars per token)
    original_tokens = original_chars // 4
    compressed_tokens = len(summary) // 4

    return summary, original_tokens, compressed_tokens


def should_retry_higher_tier(
    response: str, current_tier: int,
) -> bool:
    """Placeholder: detect if response quality warrants a tier upgrade.

    Future implementation: returns True if response is suspiciously short
    (<30 tokens) or contains hedging phrases, triggering a retry at
    current_tier + 1. Currently always returns False.
    """
    return False


async def generate_chat_stream(
    config: ChatStreamConfig,
    supabase: Any,
) -> AsyncGenerator[str, None]:
    """Generate streaming chat responses with tool loop.

    Yields SSE events: conversation_id → text → tool_result → done/error.
    """
    assistant_content = ""
    tool_calls_data: list[dict] = []

    # Routing telemetry
    timer = RoutingTimer()
    compressed_token_count: int | None = None
    original_token_count: int | None = None

    try:
        # Send conversation ID immediately so client can track
        cid = str(config.conversation_id)
        yield _sse_event({"type": "conversation_id", "conversation_id": cid})

        with timer:
            # ── Fast path: bypass LLM for simple patterns ─────────
            fast = await try_fast_path(
                config.message, config.page_context, config.project_id,
            )
            if fast:
                # Persist user message
                supabase.table("messages").insert({
                    "conversation_id": cid,
                    "role": "user",
                    "content": config.message,
                }).execute()

                if fast.tool_calls:
                    for tc in fast.tool_calls:
                        yield _sse_event({
                            "type": "tool_start",
                            "tool_name": tc["tool_name"],
                            "tool_input": {
                                "action": tc["tool_input"].get("action"),
                            },
                        })
                        result = await execute_tool(
                            project_id=config.project_id,
                            tool_name=tc["tool_name"],
                            tool_input=tc["tool_input"],
                        )
                        yield _sse_event({
                            "type": "tool_result",
                            "tool_name": tc["tool_name"],
                            "result": result,
                        })

                yield _sse_event({"type": "text", "content": fast.text})

                if fast.cards:
                    yield _sse_event({
                        "type": "tool_result",
                        "tool_name": "suggest_actions",
                        "result": {"cards": fast.cards},
                    })

                supabase.table("messages").insert({
                    "conversation_id": cid,
                    "role": "assistant",
                    "content": fast.text,
                    "metadata": {"fast_path": True},
                }).execute()

                yield _sse_event({"type": "done"})

                # Log fast path routing (async, non-blocking)
                asyncio.ensure_future(log_chat_routing(
                    supabase=supabase,
                    project_id=str(config.project_id),
                    conversation_id=cid,
                    raw_message=config.message,
                    classified_tier=1,
                    retrieval_strategy="none",
                    classifier_source="regex",
                    intent_type="fast_path",
                    latency_ms=timer.latency_ms,
                ))
                return

            # ── Normal path: classify → assemble → LLM ───────────
            # Hybrid classification: regex first, Haiku for ambiguous
            intent = await classify_intent_async(
                config.message, config.page_context,
            )
            logger.info(
                "Intent: type=%s strategy=%s complexity=%s "
                "source=%s topics=%s",
                intent.type, intent.retrieval_strategy,
                intent.complexity, intent.classifier_source,
                intent.topics,
            )

            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=config.anthropic_api_key)

            # Build messages with conversation compression
            if len(config.conversation_history) > 6:
                old = config.conversation_history[:-4]
                summary, orig_t, comp_t = _template_summarize(old)
                original_token_count = orig_t
                compressed_token_count = comp_t

                # Warn if compression is too aggressive (>70% loss)
                if orig_t > 0 and comp_t < orig_t * 0.3:
                    logger.warning(
                        "Aggressive compression: %d→%d tokens (%.0f%% loss)",
                        orig_t, comp_t,
                        (1 - comp_t / orig_t) * 100,
                    )

                recent_history = [
                    {
                        "role": "user",
                        "content": f"[Prior context: {summary}]",
                    }
                ] + [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in config.conversation_history[-4:]
                    if msg.get("content", "").strip()
                ]
            else:
                recent_history = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in config.conversation_history[-10:]
                    if msg.get("content", "").strip()
                ]

            # Inject step context on solution flow page
            user_content = config.message
            if (
                config.page_context == "brd:solution-flow"
                and config.focused_entity
            ):
                fe_data = config.focused_entity.get("data", {})
                step_title = fe_data.get("title", "")
                if step_title:
                    user_content = (
                        f"[Viewing step: {step_title}]\n"
                        f"{config.message}"
                    )

            messages = recent_history + [
                {"role": "user", "content": user_content}
            ]

            # ── Parallel context assembly ─────────────────────────
            async def _persist_user_msg():
                user_msg_data = {
                    "conversation_id": str(config.conversation_id),
                    "role": "user",
                    "content": config.message,
                }
                return (
                    supabase.table("messages")
                    .insert(user_msg_data)
                    .execute()
                )

            chat_ctx, _user_msg_resp = await asyncio.gather(
                assemble_chat_context(
                    project_id=config.project_id,
                    message=config.message,
                    page_context=config.page_context,
                    focused_entity=config.focused_entity,
                    supabase=supabase,
                    conversation_id=config.conversation_id,
                    intent=intent,
                ),
                _persist_user_msg(),
            )

            if chat_ctx.awareness:
                logger.info(
                    "Awareness: phase=%s, flows=%d, next=%s",
                    chat_ctx.awareness.active_phase,
                    len(chat_ctx.awareness.flows),
                    (
                        chat_ctx.awareness.whats_next[:2]
                        if chat_ctx.awareness.whats_next
                        else "[]"
                    ),
                )

            # Build prompt via dimensional compiler
            try:
                frame = compile_cognitive_frame(
                    intent_type=intent.type,
                    awareness=chat_ctx.awareness,
                    page_context=config.page_context,
                    focused_entity=config.focused_entity,
                    horizon_state=chat_ctx.horizon_state,
                )
                compiled = compile_prompt(
                    frame=frame,
                    awareness=chat_ctx.awareness,
                    page_context=config.page_context,
                    focused_entity=config.focused_entity,
                    retrieval_context=chat_ctx.retrieval_context,
                    solution_flow_ctx=chat_ctx.solution_flow_ctx,
                    confidence_state=chat_ctx.confidence_state,
                    horizon_state=chat_ctx.horizon_state,
                    conversation_context=config.conversation_context,
                    warm_memory=chat_ctx.warm_memory,
                    forge_state=chat_ctx.forge_state,
                    next_actions=chat_ctx.next_actions,
                )
                system_blocks = [
                    {
                        "type": "text",
                        "text": compiled.cached_block,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": compiled.awareness_block,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": compiled.dynamic_block,
                    },
                ]
                logger.info(
                    "Compiler: frame=%s, intent=%s, "
                    "strategy=%s, page=%s, history=%d",
                    compiled.active_frame, intent.type,
                    intent.retrieval_strategy,
                    config.page_context or "none",
                    len(recent_history),
                )
            except Exception as e:
                logger.warning(
                    f"Compiler failed, falling back to legacy: {e}"
                )
                system_blocks = build_smart_chat_prompt(
                    context_frame=None,
                    project_name=chat_ctx.project_name,
                    page_context=config.page_context,
                    focused_entity=config.focused_entity,
                    conversation_context=config.conversation_context,
                    retrieval_context=chat_ctx.retrieval_context,
                    solution_flow_context=chat_ctx.solution_flow_ctx,
                )

            # Token tracking
            total_input = 0
            total_output = 0
            total_cache_read = 0

            # Build filtered tool set once
            chat_tools = get_tools_for_context(config.page_context)
            if chat_tools:
                for t in chat_tools:
                    t.pop("cache_control", None)
                chat_tools[-1]["cache_control"] = {"type": "ephemeral"}

            max_tokens = config.chat_response_buffer

            # Extended thinking for strategic queries
            extra_params: dict[str, Any] = {}
            has_thinking = False
            if (
                intent.type in ("plan", "review")
                and intent.complexity == "strategic"
            ):
                extra_params["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": 1024,
                }
                max_tokens = max(max_tokens, 2500)
                has_thinking = True

            # Tool use loop
            for turn in range(MAX_TOOL_TURNS):
                stream_kwargs: dict[str, Any] = {
                    "model": config.chat_model,
                    "max_tokens": max_tokens,
                    "messages": messages,
                    "system": system_blocks,
                    "tools": chat_tools,
                    **extra_params,
                }

                async with client.messages.stream(
                    **stream_kwargs
                ) as stream:
                    async for event in stream:
                        if hasattr(event, "type"):
                            if event.type == "content_block_delta":
                                delta = getattr(event, "delta", None)
                                if delta and hasattr(delta, "text"):
                                    assistant_content += delta.text
                                    yield _sse_event({
                                        "type": "text",
                                        "content": delta.text,
                                    })

                    final_message = await stream.get_final_message()

                    if hasattr(final_message, "usage"):
                        total_input += getattr(
                            final_message.usage, "input_tokens", 0,
                        )
                        total_output += getattr(
                            final_message.usage, "output_tokens", 0,
                        )
                        cache_read = getattr(
                            final_message.usage,
                            "cache_read_input_tokens", 0,
                        )
                        total_cache_read += cache_read
                        cache_create = getattr(
                            final_message.usage,
                            "cache_creation_input_tokens", 0,
                        )
                        if cache_read or cache_create:
                            logger.info(
                                "Cache: read=%d, created=%d (turn %d)",
                                cache_read, cache_create, turn + 1,
                            )

                    tool_use_blocks = [
                        b for b in final_message.content
                        if b.type == "tool_use"
                    ]

                    if not tool_use_blocks:
                        break

                    # Emit tool_start BEFORE execution so frontend
                    # can suppress narration and show activity indicator
                    for tb in tool_use_blocks:
                        yield _sse_event({
                            "type": "tool_start",
                            "tool_name": tb.name,
                            "tool_input": {
                                "action": (tb.input or {}).get("action"),
                            },
                        })

                    # Execute tools in parallel
                    async def _exec_tool(tool_block):
                        result = await execute_tool(
                            project_id=config.project_id,
                            tool_name=tool_block.name,
                            tool_input=tool_block.input,
                        )
                        truncated = truncate_tool_result(
                            tool_name=tool_block.name,
                            result=result,
                        )
                        return tool_block, result, truncated

                    exec_results = await asyncio.gather(
                        *[_exec_tool(tb) for tb in tool_use_blocks]
                    )

                    # Invalidate retrieval cache on tool execution
                    invalidate_retrieval_cache(str(config.project_id))

                    tool_results = []
                    for tb, tool_result, truncated_result in exec_results:
                        logger.info(f"Executed tool: {tb.name}")

                        tool_calls_data.append({
                            "tool_name": tb.name,
                            "status": "complete",
                            "result": tool_result,
                        })

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tb.id,
                            "content": json.dumps(truncated_result),
                        })

                        yield _sse_event({
                            "type": "tool_result",
                            "tool_name": tb.name,
                            "result": tool_result,
                        })

                    messages.append({
                        "role": "assistant",
                        "content": final_message.content,
                    })
                    messages.append({
                        "role": "user",
                        "content": tool_results,
                    })

                    # Trim history on tool loop turns
                    if turn > 0 and len(messages) > 8:
                        orig_idx = len(recent_history)
                        tool_ex = messages[orig_idx:]
                        hist = messages[
                            max(0, orig_idx - 4):orig_idx
                        ]
                        messages = hist + tool_ex

                    assistant_content = ""
                    extra_params.pop("thinking", None)
                    max_tokens = config.chat_response_buffer

        # ── Post-response: tier fallback check (placeholder) ──────
        if should_retry_higher_tier(assistant_content, compute_tier(
            intent.retrieval_strategy,
            has_thinking=has_thinking,
        )):
            logger.info("Tier fallback triggered (not yet active)")

        # Log LLM usage
        if total_input or total_output:
            try:
                from app.core.llm_usage import log_llm_usage

                log_llm_usage(
                    model=config.chat_model,
                    input_tokens=total_input,
                    output_tokens=total_output,
                    operation="chat",
                    project_id=str(config.project_id),
                    metadata={
                        "conversation_id": str(config.conversation_id),
                    },
                )
            except Exception:
                pass

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

            supabase.table("messages").insert(
                assistant_msg_data
            ).execute()

        yield _sse_event({"type": "done"})

        # ── Async routing log (fire-and-forget) ───────────────────
        tier = compute_tier(
            intent.retrieval_strategy,
            has_thinking=has_thinking,
        )
        cost = estimate_cost(total_input, total_output, total_cache_read)
        asyncio.ensure_future(log_chat_routing(
            supabase=supabase,
            project_id=str(config.project_id),
            conversation_id=cid,
            raw_message=config.message,
            classified_tier=tier,
            retrieval_strategy=intent.retrieval_strategy,
            classifier_source=intent.classifier_source,
            intent_type=intent.type,
            complexity=intent.complexity,
            latency_ms=timer.latency_ms,
            tokens_in=total_input,
            tokens_out=total_output,
            estimated_cost=cost,
            compressed_token_count=compressed_token_count,
            original_token_count=original_token_count,
        ))

    except Exception as e:
        logger.error(f"Error in chat stream: {e}", exc_info=True)
        yield _sse_event({"type": "error", "message": str(e)})
