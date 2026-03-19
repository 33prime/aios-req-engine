"""Chat context assembly — parallel context building for chat streaming."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.context.intent_classifier import ChatIntent
from app.context.project_awareness import ProjectAwareness  # noqa: F401
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChatContext:
    """Assembled context for a chat turn — feeds the prompt compiler."""

    solution_flow_ctx: Any | None
    retrieval_context: str
    project_name: str
    # Intelligence layers
    awareness: Any = None  # ProjectAwareness
    confidence_state: dict = field(default_factory=dict)
    horizon_state: dict = field(default_factory=dict)
    warm_memory: str = ""  # Cross-conversation context
    forge_state: dict = field(default_factory=dict)  # Forge module intelligence
    next_actions: list[str] = field(default_factory=list)  # TerseAction sentences


# ── Retrieval cache (per-conversation topic dedup) ────────────────
_retrieval_cache: dict[str, tuple[float, str]] = {}
_RETRIEVAL_CACHE_TTL = 60  # seconds


def _check_retrieval_cache(project_id: str, topics: list[str]) -> str | None:
    """Check retrieval cache. Returns cached result or None."""
    key = f"{project_id}:{','.join(sorted(topics))}"
    if key in _retrieval_cache:
        ts, result = _retrieval_cache[key]
        if time.time() - ts < _RETRIEVAL_CACHE_TTL:
            return result
        _retrieval_cache.pop(key, None)
    return None


def _store_retrieval_cache(project_id: str, topics: list[str], result: str) -> None:
    """Store retrieval result in cache."""
    key = f"{project_id}:{','.join(sorted(topics))}"
    _retrieval_cache[key] = (time.time(), result)


def invalidate_retrieval_cache(project_id: str) -> None:
    """Invalidate all cached retrieval for a project."""
    keys = [k for k in _retrieval_cache if k.startswith(f"{project_id}:")]
    for k in keys:
        _retrieval_cache.pop(k, None)


async def build_retrieval_context(
    message: str,
    project_id: str,
    page_context: str | None,
    focused_entity: dict[str, Any] | None,
    retrieval_plan: dict | None = None,
    skip_reranking: bool = False,
    skip_decomposition: bool = False,
) -> str:
    """Run retrieval pre-fetch for chat context.

    If retrieval_plan is provided (from prompt compiler), uses plan-driven params.
    Otherwise falls back to defaults.
    """
    try:
        from app.core.retrieval import retrieve
        from app.core.retrieval_format import format_retrieval_for_context

        # Skip decomposition for messages under 15 words or without a question mark
        is_short = len(message.split()) < 15 or "?" not in message
        should_skip_decomp = skip_decomposition or is_short

        # Build context hint from focused entity
        context_hint = None
        if focused_entity:
            fe = focused_entity
            edata = fe.get("data", {})
            ename = edata.get("title") or edata.get("name") or ""
            egoal = edata.get("goal") or ""
            if ename:
                parts = [f'User is viewing {fe.get("type", "entity")}: "{ename}".']
                if egoal:
                    parts.append(f"Goal: {egoal}.")
                context_hint = " ".join(parts)

        # Use retrieval plan if available, otherwise fall back to defaults
        if retrieval_plan:
            entity_types = retrieval_plan.get("entity_types")
            graph_depth = retrieval_plan.get("graph_depth", 1)
            apply_recency = retrieval_plan.get("apply_recency", True)
            apply_confidence = retrieval_plan.get("apply_confidence", True)
        else:
            entity_types = None
            graph_depth = 1
            apply_recency = True
            apply_confidence = True

        logger.info(
            "Retrieval profile: page=%s depth=%d types=%s skip_decomp=%s skip_rerank=%s plan=%s",
            page_context,
            graph_depth,
            entity_types,
            should_skip_decomp,
            skip_reranking,
            "yes" if retrieval_plan else "no",
        )
        retrieval_result = await retrieve(
            query=message,
            project_id=project_id,
            max_rounds=1,
            skip_decomposition=should_skip_decomp,
            skip_reranking=skip_reranking,
            skip_evaluation=True,
            context_hint=context_hint,
            entity_types=entity_types,
            graph_depth=graph_depth,
            apply_recency=apply_recency,
            apply_confidence=apply_confidence,
        )
        return format_retrieval_for_context(retrieval_result, style="chat", max_tokens=2000)
    except Exception as e:
        logger.debug(f"Retrieval pre-fetch failed (non-fatal): {e}")
        return ""


async def build_solution_flow_ctx(
    page_context: str | None,
    project_id: str,
    focused_entity: dict[str, Any] | None,
) -> Any | None:
    """Build solution flow context if on a solution-flow page."""
    if page_context != "brd:solution-flow":
        return None
    try:
        from app.core.solution_flow_context import build_solution_flow_context

        focused_step_id = None
        if focused_entity:
            fe_data = focused_entity.get("data", {})
            focused_step_id = fe_data.get("id")
        return await build_solution_flow_context(
            project_id=project_id,
            focused_step_id=focused_step_id,
        )
    except Exception as e:
        logger.debug(f"Solution flow context build failed (non-fatal): {e}")
        return None


async def get_project_name(supabase: Any, project_id: str) -> str:
    """Fetch the project name from the database."""
    project_row = supabase.table("projects").select("name").eq("id", project_id).single().execute()
    return project_row.data.get("name", "Unknown") if project_row.data else "Unknown"


async def _safe_load_awareness(project_id: str, project_name: str) -> Any:
    """Load project awareness, returning empty on failure."""
    try:
        from app.context.project_awareness import load_project_awareness

        return await load_project_awareness(project_id, project_name)
    except Exception as e:
        logger.debug(f"Awareness load failed (non-fatal): {e}")
        from app.context.project_awareness import ProjectAwareness

        return ProjectAwareness(project_name=project_name)


async def _safe_load_confidence(project_id: str) -> dict:
    """Load confidence state, returning empty on failure."""
    try:
        from app.context.intelligence_signals import load_confidence_state

        return await load_confidence_state(project_id)
    except Exception as e:
        logger.debug(f"Confidence state load failed (non-fatal): {e}")
        return {}


async def _safe_load_horizon(project_id: str) -> dict:
    """Load horizon state, returning empty on failure."""
    try:
        from app.context.intelligence_signals import load_horizon_state

        return await load_horizon_state(project_id)
    except Exception as e:
        logger.debug(f"Horizon state load failed (non-fatal): {e}")
        return {}


async def _safe_load_forge(project_id: str, page_context: str | None) -> dict:
    """Load Forge intelligence, returning empty on failure."""
    try:
        from app.context.forge_intelligence import load_forge_intelligence

        return await load_forge_intelligence(project_id, page_context or "")
    except Exception as e:
        logger.debug(f"Forge intelligence load failed (non-fatal): {e}")
        return {}


async def _safe_load_next_actions(project_id: str) -> list[str]:
    """Load top TerseAction sentences from the context frame (cached)."""
    try:
        from app.core.action_engine import compute_context_frame

        frame = await compute_context_frame(UUID(project_id), max_actions=5)
        return [a.sentence for a in (frame.actions or [])[:5]]
    except Exception as e:
        logger.debug(f"Next actions load failed (non-fatal): {e}")
        return []


async def _safe_load_warm_memory(project_id: str, conversation_id: UUID | str | None) -> str:
    """Load warm memory, returning empty on failure."""
    try:
        from app.context.intelligence_signals import load_warm_memory

        return await load_warm_memory(project_id, conversation_id)
    except Exception as e:
        logger.debug(f"Warm memory load failed (non-fatal): {e}")
        return ""


async def _noop_dict() -> dict:
    return {}


async def _noop_str() -> str:
    return ""


async def _noop_list() -> list[str]:
    return []


async def assemble_chat_context(
    project_id: UUID | str,
    message: str,
    page_context: str | None,
    focused_entity: dict[str, Any] | None,
    supabase: Any,
    conversation_id: UUID | str | None = None,
    intent: ChatIntent | None = None,
) -> ChatContext:
    """Assemble all chat context with intent-gated loading.

    Phase A (parallel): Load awareness, project_name, and intelligence layers
    gated by intent.retrieval_strategy.
    Phase B (sequential): Build retrieval (if needed) with plan-driven params.
    """
    pid = str(project_id)
    strategy = intent.retrieval_strategy if intent else "full"
    intent_type = intent.type if intent else "discuss"
    is_mutation = intent_type in ("create", "update", "delete")

    # Check FORGE_API_URL to skip forge loading
    forge_enabled = False
    try:
        from app.core.config import get_settings
        forge_enabled = bool(get_settings().FORGE_API_URL)
    except Exception:
        pass

    # Determine if warm memory is useful (skip on first message)
    has_history = bool(conversation_id)

    # Phase A: Parallel loading, gated by intent
    tasks = [
        build_solution_flow_ctx(page_context, pid, focused_entity),
        get_project_name(supabase, pid),
        # Confidence: skip for mutations
        _safe_load_confidence(pid) if not is_mutation else _noop_dict(),
        # Horizon: skip for mutations
        _safe_load_horizon(pid) if not is_mutation else _noop_dict(),
        # Warm memory: skip on first message
        _safe_load_warm_memory(pid, conversation_id) if has_history else _noop_str(),
        # Forge: skip if URL not configured
        _safe_load_forge(pid, page_context) if forge_enabled else _noop_dict(),
        # Next actions: skip for search intent
        _safe_load_next_actions(pid) if intent_type != "search" else _noop_list(),
    ]

    (
        solution_flow_ctx,
        project_name,
        confidence_state,
        horizon_state,
        warm_memory,
        forge_state,
        next_actions,
    ) = await asyncio.gather(*tasks)

    # Load awareness (needs project_name)
    awareness = await _safe_load_awareness(pid, project_name)

    # Phase B: Retrieval, gated by strategy
    retrieval_context = ""
    if strategy == "none":
        logger.info("Retrieval skipped: strategy=none (intent=%s)", intent_type)
    else:
        # Check retrieval cache first
        topics = intent.topics if intent else []
        cached = _check_retrieval_cache(pid, topics)
        if cached is not None:
            retrieval_context = cached
            logger.info("Retrieval cache hit: topics=%s", topics)
        else:
            # Build retrieval plan from cognitive frame
            retrieval_plan = None
            try:
                from app.context.prompt_compiler import compile_cognitive_frame

                frame = compile_cognitive_frame(
                    intent_type=intent_type,
                    awareness=awareness,
                    page_context=page_context,
                    focused_entity=focused_entity,
                    horizon_state=horizon_state,
                )
                if hasattr(frame, "retrieval_plan") and frame.retrieval_plan:
                    retrieval_plan = frame.retrieval_plan
            except Exception as e:
                logger.debug(f"Retrieval plan compilation failed (non-fatal): {e}")

            retrieval_context = await build_retrieval_context(
                message,
                pid,
                page_context,
                focused_entity,
                retrieval_plan,
                skip_reranking=(strategy == "light"),
                skip_decomposition=(strategy == "light"),
            )

            # Cache successful retrieval
            if retrieval_context and topics:
                _store_retrieval_cache(pid, topics, retrieval_context)

    return ChatContext(
        solution_flow_ctx=solution_flow_ctx,
        retrieval_context=retrieval_context,
        project_name=project_name,
        awareness=awareness,
        confidence_state=confidence_state,
        horizon_state=horizon_state,
        warm_memory=warm_memory,
        forge_state=forge_state,
        next_actions=next_actions,
    )
