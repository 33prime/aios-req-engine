"""Chat context assembly — parallel context building for chat streaming."""

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import UUID

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


@dataclass
class ChatContext:
    """Assembled context for a chat turn."""

    context_frame: Any
    solution_flow_ctx: Any | None
    retrieval_context: str
    project_name: str


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

        # Solution flow step chat already has rich context —
        # always use simple (fast) retrieval: skip decomposition,
        # reranking, and sufficiency loops.
        is_flow = page_context == "brd:solution-flow"
        is_simple = is_flow or (len(message.split()) < 8 and "?" not in message)

        # Build context hint from focused entity
        context_hint = None
        if focused_entity:
            fe = focused_entity
            edata = fe.get("data", {})
            ename = edata.get("title") or edata.get("name") or ""
            egoal = edata.get("goal") or ""
            if ename:
                parts = [f"User is viewing {fe.get('type', 'entity')}: \"{ename}\"."]
                if egoal:
                    parts.append(f"Goal: {egoal}.")
                context_hint = " ".join(parts)

        entity_types = _PAGE_ENTITY_TYPES.get(page_context or "")
        retrieval_result = await retrieve(
            query=message,
            project_id=project_id,
            max_rounds=1,
            skip_decomposition=is_simple,
            skip_reranking=is_simple,
            evaluation_criteria="Enough context to answer the user's question",
            context_hint=context_hint,
            entity_types=entity_types,
        )
        return format_retrieval_for_context(
            retrieval_result, style="chat", max_tokens=2000
        )
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
    project_row = (
        supabase.table("projects")
        .select("name")
        .eq("id", project_id)
        .single()
        .execute()
    )
    return project_row.data.get("name", "Unknown") if project_row.data else "Unknown"


async def assemble_chat_context(
    project_id: UUID | str,
    message: str,
    page_context: str | None,
    focused_entity: dict[str, Any] | None,
    supabase: Any,
) -> ChatContext:
    """Assemble all chat context in parallel."""
    pid = str(project_id)

    context_frame, solution_flow_ctx, retrieval_context, project_name = await asyncio.gather(
        compute_context_frame(project_id, max_actions=5),
        build_solution_flow_ctx(page_context, pid, focused_entity),
        build_retrieval_context(message, pid, page_context, focused_entity),
        get_project_name(supabase, pid),
    )

    return ChatContext(
        context_frame=context_frame,
        solution_flow_ctx=solution_flow_ctx,
        retrieval_context=retrieval_context,
        project_name=project_name,
    )
