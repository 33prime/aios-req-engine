"""Tool dispatch — routes consolidated tool names to handler functions.

6 tools dispatch by `action` parameter to existing handler implementations.
"""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

from .filtering import _MUTATING_TOOLS

logger = get_logger(__name__)

# Lazy-import handler map — populated on first call to avoid circular imports
_HANDLERS_LOADED = False


# ── Individual handler imports (lazy) ──────────────────────────────


def _ensure_handlers():
    global _HANDLERS_LOADED
    if _HANDLERS_LOADED:
        return
    _HANDLERS_LOADED = True


# ── Dispatch functions ─────────────────────────────────────────────


async def _search_dispatch(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Dispatch search actions to existing handlers."""
    action = params.get("action", "semantic")

    if action == "semantic":
        from .tools_search import _search

        return await _search(project_id, params)

    elif action == "entities":
        from .tools_status import _list_entities

        return await _list_entities(project_id, params)

    elif action == "history":
        from .tools_search import _query_entity_history

        # Map consolidated params to legacy format
        legacy_params = {
            "entity_type": params.get("entity_type", "feature"),
            "entity_id_or_name": params.get("query", ""),
        }
        return await _query_entity_history(project_id, legacy_params)

    elif action == "knowledge":
        from .tools_search import _query_knowledge_graph

        legacy_params = {
            "topic": params.get("query", ""),
            "limit": params.get("limit", 5),
        }
        return await _query_knowledge_graph(project_id, legacy_params)

    elif action == "status":
        from .tools_status import _get_project_status

        return await _get_project_status(project_id, params)

    elif action == "documents":
        from .tools_signals import _get_recent_documents

        return await _get_recent_documents(project_id, params)

    elif action == "pending":
        from .tools_communication import _list_pending_confirmations

        return await _list_pending_confirmations(project_id, params)

    else:
        return {"error": f"Unknown search action: {action}"}


async def _write_dispatch(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Dispatch write actions to existing CRUD handlers."""
    action = params.get("action", "create")
    entity_type = params.get("entity_type", "")
    data = params.get("data", {})

    # Special entity types that have dedicated handlers
    if entity_type == "task":
        from .tools_entity_crud import _create_task

        return await _create_task(project_id, data)

    elif entity_type == "company_reference":
        from .tools_entity_crud import _add_company_reference

        return await _add_company_reference(project_id, data)

    elif entity_type == "meeting":
        from .tools_communication import _schedule_meeting

        return await _schedule_meeting(project_id, data)

    elif entity_type == "confirmation":
        from .tools_communication import _create_confirmation

        return await _create_confirmation(project_id, data)

    # Standard entity CRUD
    if action == "create":
        from .tools_entity_crud import _create_entity

        legacy_params = {"entity_type": entity_type, **data}
        return await _create_entity(project_id, legacy_params)

    elif action == "update":
        from .tools_entity_crud import _update_entity

        legacy_params = {
            "entity_type": entity_type,
            "entity_id": params.get("entity_id", ""),
            **data,
        }
        return await _update_entity(project_id, legacy_params)

    elif action == "delete":
        from .tools_entity_crud import _delete_entity

        legacy_params = {
            "entity_type": entity_type,
            "entity_id": params.get("entity_id", ""),
        }
        return await _delete_entity(project_id, legacy_params)

    else:
        return {"error": f"Unknown write action: {action}"}


async def _process_dispatch(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Dispatch process actions to existing handlers."""
    action = params.get("action", "signal")

    if action == "signal":
        from .tools_signals import _add_signal

        legacy_params = {"content": params.get("content", "")}
        return await _add_signal(project_id, legacy_params)

    elif action == "belief":
        from .tools_entity_crud import _add_belief

        legacy_params = {
            "statement": params.get("content", ""),
            "confidence": params.get("confidence", 0.7),
            "belief_domain": params.get("belief_domain"),
        }
        return await _add_belief(project_id, legacy_params)

    elif action == "evidence":
        from .tools_search import _attach_evidence

        legacy_params = {
            "entity_type": params.get("entity_type", ""),
            "entity_id": params.get("entity_id", ""),
            "chunk_ids": params.get("chunk_ids", []),
            "rationale": params.get("rationale", ""),
        }
        return await _attach_evidence(project_id, legacy_params)

    elif action == "clarification":
        from .tools_signals import _respond_to_document_clarification

        legacy_params = {
            "clarification_id": params.get("entity_id", ""),
            "response": params.get("content", ""),
        }
        return await _respond_to_document_clarification(project_id, legacy_params)

    elif action == "strategic_context":
        if params.get("project_type"):
            from .tools_strategic import _update_project_type

            return await _update_project_type(project_id, {"project_type": params["project_type"]})
        elif params.get("generate", True):
            from .tools_strategic import _generate_strategic_context

            return await _generate_strategic_context(project_id, params)
        else:
            from .tools_strategic import _update_strategic_context

            return await _update_strategic_context(project_id, params)

    elif action == "identify_stakeholders":
        from .tools_strategic import _identify_stakeholders

        return await _identify_stakeholders(project_id, params)

    else:
        return {"error": f"Unknown process action: {action}"}


async def _solution_flow_dispatch(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Dispatch solution flow actions to existing handlers."""
    action = params.get("action", "update")
    data = params.get("data", {})
    step_id = params.get("step_id", "")

    if action == "update":
        from .tools_solution_flow import _update_solution_flow_step

        legacy_params = {"step_id": step_id, **data}
        return await _update_solution_flow_step(project_id, legacy_params)

    elif action == "add":
        from .tools_solution_flow import _add_solution_flow_step

        return await _add_solution_flow_step(project_id, data)

    elif action == "remove":
        from .tools_solution_flow import _remove_solution_flow_step

        legacy_params = {"step_id": step_id}
        return await _remove_solution_flow_step(project_id, legacy_params)

    elif action == "reorder":
        from .tools_solution_flow import _reorder_solution_flow_steps

        return await _reorder_solution_flow_steps(project_id, data)

    elif action == "resolve_question":
        from .tools_solution_flow import _resolve_solution_flow_question

        legacy_params = {"step_id": step_id, **data}
        return await _resolve_solution_flow_question(project_id, legacy_params)

    elif action == "escalate":
        from .tools_solution_flow import _escalate_to_client

        legacy_params = {"step_id": step_id, **data}
        return await _escalate_to_client(project_id, legacy_params)

    elif action == "refine":
        from .tools_solution_flow import _refine_solution_flow_step

        legacy_params = {"step_id": step_id, **data}
        return await _refine_solution_flow_step(project_id, legacy_params)

    else:
        return {"error": f"Unknown solution_flow action: {action}"}


async def _client_portal_dispatch(project_id: UUID, params: dict[str, Any]) -> dict[str, Any]:
    """Dispatch client portal actions to existing handlers."""
    action = params.get("action", "mark_for_review")

    if action == "mark_for_review":
        from .tools_collaboration import _mark_for_client_review

        return await _mark_for_client_review(project_id, params)

    elif action == "draft_question":
        from .tools_collaboration import _draft_client_question

        return await _draft_client_question(project_id, params)

    elif action == "preview":
        from .tools_collaboration import _synthesize_and_preview

        return await _synthesize_and_preview(project_id, params)

    elif action == "push":
        from .tools_collaboration import _push_to_portal

        return await _push_to_portal(project_id, params)

    else:
        return {"error": f"Unknown client_portal action: {action}"}


# ── Dispatch Map ───────────────────────────────────────────────────

_DISPATCH_MAP: dict[str, Callable] = {
    "search": _search_dispatch,
    "write": _write_dispatch,
    "process": _process_dispatch,
    "solution_flow": _solution_flow_dispatch,
    "client_portal": _client_portal_dispatch,
}


async def execute_tool(
    project_id: UUID, tool_name: str, tool_input: dict[str, Any]
) -> dict[str, Any]:
    """Execute a tool and return results.

    Routes consolidated tool names to dispatch functions, which then
    route by `action` parameter to existing handler implementations.
    """
    try:
        logger.info(f"Executing tool {tool_name} for project {project_id}")

        # suggest_actions is a pass-through — frontend renders the cards
        if tool_name == "suggest_actions":
            return tool_input

        dispatcher = _DISPATCH_MAP.get(tool_name)
        if dispatcher is None:
            return {"error": f"Unknown tool: {tool_name}"}

        return await dispatcher(project_id, tool_input)

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        # Invalidate context frame cache after mutating tools
        if tool_name in _MUTATING_TOOLS:
            try:
                from app.core.action_engine import invalidate_context_frame

                invalidate_context_frame(project_id)
            except Exception:
                pass  # Best-effort
            try:
                from app.context.project_awareness import invalidate_awareness

                invalidate_awareness(project_id)
            except Exception:
                pass  # Best-effort
