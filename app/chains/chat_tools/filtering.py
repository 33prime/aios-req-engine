"""Page-context tool filtering for chat assistant."""

from typing import Any, Dict, List

from .definitions import get_tool_definitions

# Tools sent on every request regardless of page (10 core)
CORE_TOOLS = {
    "get_project_status",
    "list_entities",
    "search",
    "create_entity",
    "update_entity",
    "delete_entity",
    "create_task",
    "suggest_actions",
    "add_belief",
    "get_recent_documents",
}

# Additional tools per page context
PAGE_TOOLS: Dict[str, set] = {
    "brd:features": {"attach_evidence", "query_entity_history"},
    "brd:personas": {"query_entity_history"},
    "brd:workflows": {"query_entity_history"},
    "brd:stakeholders": {"identify_stakeholders", "query_entity_history"},
    "brd:data_entities": {"query_entity_history"},
    "brd:business_context": {
        "generate_strategic_context",
        "update_strategic_context",
        "update_project_type",
    },
    "brd:constraints": {"update_strategic_context"},
    "brd:questions": {"list_pending_confirmations"},
    "overview": {
        "generate_strategic_context",
        "update_strategic_context",
        "update_project_type",
        "identify_stakeholders",
        "list_pending_confirmations",
        "add_company_reference",
    },
    "prototype": {"attach_evidence", "query_entity_history"},
    "brd:solution-flow": {
        "update_solution_flow_step",
        "add_solution_flow_step",
        "remove_solution_flow_step",
        "reorder_solution_flow_steps",
        "resolve_solution_flow_question",
        "escalate_to_client",
        "refine_solution_flow_step",
    },
    "collaborate": {
        "mark_for_client_review",
        "draft_client_question",
        "synthesize_and_preview",
        "push_to_portal",
        "list_pending_confirmations",
        "schedule_meeting",
    },
}

# Tools added when no specific page context (chat opened from sidebar, etc.)
FALLBACK_EXTRAS = {
    "generate_strategic_context",
    "update_strategic_context",
    "update_project_type",
    "identify_stakeholders",
    "list_pending_confirmations",
    "schedule_meeting",
    "attach_evidence",
    "query_entity_history",
    "query_knowledge_graph",
    "check_document_clarifications",
    "respond_to_document_clarification",
    "add_signal",
    "add_company_reference",
    "create_confirmation",
    "mark_for_client_review",
    "draft_client_question",
    "synthesize_and_preview",
    "push_to_portal",
}

# Communication tools — added on any page that involves client interaction
COMMUNICATION_TOOLS = {
    "schedule_meeting",
    "list_pending_confirmations",
    "create_confirmation",
}

# Client portal tools — mark for review, draft questions, synthesize, push
CLIENT_PORTAL_TOOLS = {
    "mark_for_client_review",
    "draft_client_question",
    "synthesize_and_preview",
    "push_to_portal",
}

# Document tools — added when documents may be discussed
DOCUMENT_TOOLS = {
    "check_document_clarifications",
    "respond_to_document_clarification",
    "add_signal",
}

# Tools that mutate project data — invalidate context frame cache after execution
_MUTATING_TOOLS = {
    "create_entity", "update_entity", "delete_entity", "add_signal", "create_task",
    "create_confirmation", "attach_evidence", "generate_strategic_context",
    "update_strategic_context", "update_project_type", "identify_stakeholders",
    "respond_to_document_clarification", "add_belief", "add_company_reference",
    "update_solution_flow_step", "add_solution_flow_step",
    "remove_solution_flow_step", "reorder_solution_flow_steps",
    "resolve_solution_flow_question", "escalate_to_client",
    "refine_solution_flow_step", "schedule_meeting",
    "mark_for_client_review", "draft_client_question",
    "synthesize_and_preview", "push_to_portal",
}


def get_tools_for_context(page_context: str | None = None) -> List[Dict[str, Any]]:
    """Return filtered tool definitions based on current page context.

    Args:
        page_context: Current page (e.g., "brd:features", "overview", None)

    Returns:
        Filtered list of tool definitions
    """
    all_tools = get_tool_definitions()

    if page_context is None:
        # No page context — include core + fallback (all non-niche tools)
        allowed = CORE_TOOLS | FALLBACK_EXTRAS
    else:
        # Core + page-specific + communication on BRD pages + document tools
        page_extras = PAGE_TOOLS.get(page_context, set())

        # For any brd: page, include communication, document, and portal tools
        if page_context.startswith("brd"):
            page_extras = page_extras | COMMUNICATION_TOOLS | DOCUMENT_TOOLS | CLIENT_PORTAL_TOOLS

        # For the generic "brd" page (all sections), include everything BRD-related
        if page_context == "brd":
            page_extras = set()
            for key, tools in PAGE_TOOLS.items():
                if key.startswith("brd:"):
                    page_extras |= tools
            page_extras |= COMMUNICATION_TOOLS | DOCUMENT_TOOLS

        allowed = CORE_TOOLS | page_extras

    return [t for t in all_tools if t["name"] in allowed]
