"""Chat context assembly — parallel context building for chat streaming."""

import asyncio
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.context.project_awareness import ProjectAwareness  # noqa: F401
from app.core.action_engine import compute_context_frame
from app.core.logging import get_logger

logger = get_logger(__name__)

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

# Page-context → graph traversal depth
# Depth=2 discovers indirect relationships (feature→persona→workflow)
_PAGE_GRAPH_DEPTH: dict[str, int] = {
    "brd:solution-flow": 2,
    "brd:unlocks": 2,
    "brd:features": 2,
    "brd:personas": 2,
    "brd:workflows": 2,
    # All other pages default to 1
}

# Page-context → temporal recency weighting
# Prioritizes recently-evidenced relationships over stale ones
_PAGE_APPLY_RECENCY: dict[str, bool] = {
    "brd:solution-flow": True,
    "brd:unlocks": True,
    "brd:features": True,
    "brd:workflows": True,
}

# Page-context → confidence overlay
# Shows which evidence is confirmed vs inferred vs contradicted
_PAGE_APPLY_CONFIDENCE: dict[str, bool] = {
    "brd:solution-flow": True,
    "brd:unlocks": True,
    "brd:features": True,
    "brd:personas": True,
    "brd:business-drivers": True,
    "brd:stakeholders": True,
}


@dataclass
class ChatContext:
    """Assembled context for a chat turn — feeds the prompt compiler."""

    context_frame: Any
    solution_flow_ctx: Any | None
    retrieval_context: str
    project_name: str
    # Intelligence layers
    awareness: Any = None  # ProjectAwareness
    confidence_state: dict = field(default_factory=dict)
    horizon_state: dict = field(default_factory=dict)
    warm_memory: str = ""  # Cross-conversation context
    forge_state: dict = field(default_factory=dict)  # Forge module intelligence


async def build_retrieval_context(
    message: str,
    project_id: str,
    page_context: str | None,
    focused_entity: dict[str, Any] | None,
) -> str:
    """Run retrieval pre-fetch for chat context."""
    try:
        from app.core.retrieval import retrieve
        from app.core.retrieval_format import format_retrieval_for_context

        # Only skip decomposition for very short messages.
        # Always rerank via Cohere for quality, skip sufficiency loop to stay fast.
        is_very_short = len(message.split()) < 6

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

        entity_types = _PAGE_ENTITY_TYPES.get(page_context or "")
        graph_depth = _PAGE_GRAPH_DEPTH.get(page_context or "", 1)
        logger.info(
            "Retrieval profile: page=%s depth=%d types=%s short=%s",
            page_context,
            graph_depth,
            entity_types,
            is_very_short,
        )
        retrieval_result = await retrieve(
            query=message,
            project_id=project_id,
            max_rounds=1,
            skip_decomposition=is_very_short,
            skip_reranking=False,
            skip_evaluation=True,
            context_hint=context_hint,
            entity_types=entity_types,
            graph_depth=graph_depth,
            apply_recency=True,
            apply_confidence=True,
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


async def _safe_load_warm_memory(project_id: str, conversation_id: UUID | str | None) -> str:
    """Load warm memory, returning empty on failure."""
    try:
        from app.context.intelligence_signals import load_warm_memory

        return await load_warm_memory(project_id, conversation_id)
    except Exception as e:
        logger.debug(f"Warm memory load failed (non-fatal): {e}")
        return ""


async def assemble_chat_context(
    project_id: UUID | str,
    message: str,
    page_context: str | None,
    focused_entity: dict[str, Any] | None,
    supabase: Any,
    conversation_id: UUID | str | None = None,
) -> ChatContext:
    """Assemble all chat context in parallel (4 core + 5 intelligence)."""
    pid = str(project_id)

    # All 8 tasks run in parallel
    (
        context_frame,
        solution_flow_ctx,
        retrieval_context,
        project_name,
        confidence_state,
        horizon_state,
        warm_memory,
        forge_state,
    ) = await asyncio.gather(
        compute_context_frame(project_id, max_actions=5),
        build_solution_flow_ctx(page_context, pid, focused_entity),
        build_retrieval_context(message, pid, page_context, focused_entity),
        get_project_name(supabase, pid),
        _safe_load_confidence(pid),
        _safe_load_horizon(pid),
        _safe_load_warm_memory(pid, conversation_id),
        _safe_load_forge(pid, page_context),
    )

    # Awareness needs project_name, loaded after the gather
    awareness = await _safe_load_awareness(pid, project_name)

    return ChatContext(
        context_frame=context_frame,
        solution_flow_ctx=solution_flow_ctx,
        retrieval_context=retrieval_context,
        project_name=project_name,
        awareness=awareness,
        confidence_state=confidence_state,
        horizon_state=horizon_state,
        warm_memory=warm_memory,
        forge_state=forge_state,
    )
