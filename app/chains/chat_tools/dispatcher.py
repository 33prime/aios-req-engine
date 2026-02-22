"""Tool dispatch — routes tool_name to handler function."""

from typing import Any, Callable, Coroutine, Dict
from uuid import UUID

from app.core.logging import get_logger

from .filtering import _MUTATING_TOOLS

logger = get_logger(__name__)

# Lazy-import handler map — populated on first call to avoid circular imports
_HANDLER_MAP: Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]] | None = None


def _build_handler_map() -> Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]]:
    from .tools_status import _get_project_status, _list_entities
    from .tools_search import _search, _attach_evidence, _query_entity_history, _query_knowledge_graph
    from .tools_signals import _add_signal, _get_recent_documents, _check_document_clarifications, _respond_to_document_clarification
    from .tools_communication import _create_confirmation, _schedule_meeting, _list_pending_confirmations
    from .tools_strategic import _generate_strategic_context, _update_project_type, _identify_stakeholders, _update_strategic_context
    from .tools_entity_crud import _create_entity, _update_entity, _delete_entity, _create_task, _add_belief, _add_company_reference
    from .tools_solution_flow import (
        _update_solution_flow_step, _add_solution_flow_step, _remove_solution_flow_step,
        _reorder_solution_flow_steps, _resolve_solution_flow_question, _escalate_to_client,
        _refine_solution_flow_step,
    )
    from .tools_collaboration import (
        _mark_for_client_review, _draft_client_question,
        _synthesize_and_preview, _push_to_portal,
    )

    return {
        "get_project_status": _get_project_status,
        "list_entities": _list_entities,
        "create_confirmation": _create_confirmation,
        "search": _search,
        "attach_evidence": _attach_evidence,
        "add_signal": _add_signal,
        "schedule_meeting": _schedule_meeting,
        "list_pending_confirmations": _list_pending_confirmations,
        "generate_strategic_context": _generate_strategic_context,
        "update_project_type": _update_project_type,
        "identify_stakeholders": _identify_stakeholders,
        "update_strategic_context": _update_strategic_context,
        "get_recent_documents": _get_recent_documents,
        "check_document_clarifications": _check_document_clarifications,
        "respond_to_document_clarification": _respond_to_document_clarification,
        "create_entity": _create_entity,
        "update_entity": _update_entity,
        "delete_entity": _delete_entity,
        "query_entity_history": _query_entity_history,
        "query_knowledge_graph": _query_knowledge_graph,
        "create_task": _create_task,
        "add_belief": _add_belief,
        "add_company_reference": _add_company_reference,
        "update_solution_flow_step": _update_solution_flow_step,
        "add_solution_flow_step": _add_solution_flow_step,
        "remove_solution_flow_step": _remove_solution_flow_step,
        "reorder_solution_flow_steps": _reorder_solution_flow_steps,
        "resolve_solution_flow_question": _resolve_solution_flow_question,
        "escalate_to_client": _escalate_to_client,
        "refine_solution_flow_step": _refine_solution_flow_step,
        "mark_for_client_review": _mark_for_client_review,
        "draft_client_question": _draft_client_question,
        "synthesize_and_preview": _synthesize_and_preview,
        "push_to_portal": _push_to_portal,
    }


async def execute_tool(project_id: UUID, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool and return results.

    Args:
        project_id: Project UUID
        tool_name: Name of tool to execute
        tool_input: Tool input parameters

    Returns:
        Tool execution results
    """
    global _HANDLER_MAP
    if _HANDLER_MAP is None:
        _HANDLER_MAP = _build_handler_map()

    try:
        logger.info(f"Executing tool {tool_name} for project {project_id}")

        # suggest_actions is a pass-through — frontend renders the cards
        if tool_name == "suggest_actions":
            return tool_input

        handler = _HANDLER_MAP.get(tool_name)
        if handler is None:
            return {"error": f"Unknown tool: {tool_name}"}

        return await handler(project_id, tool_input)

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
