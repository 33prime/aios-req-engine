"""Chat assistant tools for Claude."""

from typing import Any, Dict, List
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get tool definitions for Claude API.

    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "name": "get_project_status",
            "description": "Get a comprehensive status summary of the project including counts, recent activity, and items needing attention. Use this when the user asks about project status, overview, or what needs attention.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "include_details": {
                        "type": "boolean",
                        "description": "Include detailed breakdown of critical items",
                        "default": False,
                    }
                },
            },
        },
        {
            "name": "create_confirmation",
            "description": "Create a confirmation item for the client. Use this when an insight or decision needs client input/approval.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask the client",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about why this confirmation is needed",
                    },
                    "related_insight_id": {
                        "type": "string",
                        "description": "Optional UUID of related insight",
                    },
                },
                "required": ["question"],
            },
        },
        {
            "name": "search",
            "description": "Semantic search through research using AI embeddings. Better than keyword search for finding related concepts and contextual matches. Use this when you need intelligent research discovery based on meaning, not just keywords.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query describing what you're looking for",
                    },
                    "chunk_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["competitive", "market", "user_research", "technical", "all"],
                        },
                        "description": "Types of research chunks to search (optional, defaults to all)",
                    },
                    "min_similarity": {
                        "type": "number",
                        "description": "Minimum similarity threshold (0.0-1.0, default 0.7)",
                        "default": 0.7,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
        {
            "name": "attach_evidence",
            "description": "Link research chunks to features or Value Path steps as supporting evidence. Use this to strengthen decisions with research backing and create audit trail.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["feature", "vp_step", "persona"],
                        "description": "Type of entity to attach evidence to",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "UUID of the entity",
                    },
                    "chunk_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Array of research chunk UUIDs to attach",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Brief explanation of how this evidence supports the entity",
                    },
                },
                "required": ["entity_type", "entity_id", "chunk_ids", "rationale"],
            },
        },
        {
            "name": "add_signal",
            "description": "Add a signal (email, note, transcript, document) and process it through the full pipeline (chunking, embedding, fact extraction). Use this when the user wants to add client content directly.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "signal_type": {
                        "type": "string",
                        "enum": ["email", "note", "transcript", "document", "file_text"],
                        "description": "Type of signal content",
                    },
                    "content": {
                        "type": "string",
                        "description": "The signal content (email body, notes, transcript, etc.)",
                    },
                    "source": {
                        "type": "string",
                        "description": "Source of the signal (e.g., 'client@example.com', 'kickoff meeting')",
                    },
                    "process_immediately": {
                        "type": "boolean",
                        "description": "Whether to process through full pipeline immediately",
                        "default": True,
                    },
                },
                "required": ["signal_type", "content"],
            },
        },
        {
            "name": "generate_client_email",
            "description": "Generate a professional email draft for client outreach based on pending confirmation items. Use this when the user wants to draft an email to ask the client questions or gather information. Returns a formatted email with subject line and body.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "confirmation_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific confirmation item IDs to include (optional - if empty, includes all open email-suitable items)",
                    },
                    "client_name": {
                        "type": "string",
                        "description": "Client's name for personalized greeting (optional)",
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Project name for context (optional)",
                    },
                },
            },
        },
        {
            "name": "generate_meeting_agenda",
            "description": "Generate a structured meeting agenda for client discussions based on pending confirmation items. Use this when the user wants to plan a client call or meeting. Returns a formatted agenda with time allocations and pre-read summary.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "confirmation_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific confirmation item IDs to include (optional - if empty, includes all open meeting-suitable items)",
                    },
                    "client_name": {
                        "type": "string",
                        "description": "Client's name for personalized greeting (optional)",
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Project name for context (optional)",
                    },
                    "meeting_duration": {
                        "type": "integer",
                        "description": "Target meeting duration in minutes (default: 30)",
                        "default": 30,
                    },
                },
            },
        },
        {
            "name": "list_pending_confirmations",
            "description": "List pending confirmation items that need client input. Use this to see what questions need to be asked to the client, or before generating emails/meeting agendas.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "method_filter": {
                        "type": "string",
                        "enum": ["email", "meeting", "all"],
                        "description": "Filter by suggested outreach method (optional, default: all)",
                        "default": "all",
                    },
                },
            },
        },
        # Strategic Context Tools
        {
            "name": "generate_strategic_context",
            "description": "Generate or regenerate the strategic context for the project. This analyzes signals to extract: project type (internal vs market), executive summary, opportunity, risks, investment case, success metrics, constraints, and stakeholders. Use this when the user wants to generate the strategic overview, understand the business case, or see the big picture.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "regenerate": {
                        "type": "boolean",
                        "description": "Whether to regenerate existing context (default: false)",
                        "default": False,
                    },
                },
            },
        },
        {
            "name": "update_project_type",
            "description": "Set whether this is an internal software project or a market product. This affects how the investment case is displayed.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "project_type": {
                        "type": "string",
                        "enum": ["internal", "market_product"],
                        "description": "The project type: 'internal' for internal tools, 'market_product' for products sold to customers",
                    },
                },
                "required": ["project_type"],
            },
        },
        {
            "name": "identify_stakeholders",
            "description": "Automatically identify stakeholders from signals and research. Use this to discover who the key people are based on conversation history.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "update_strategic_context",
            "description": "Update the strategic context by adding a risk, success metric, or updating a field. Use this when the user wants to add risks, KPIs, or modify strategic context fields.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add_risk", "add_success_metric", "update_field"],
                        "description": "The type of update to perform",
                    },
                    "data": {
                        "type": "object",
                        "description": "Data for the action. For add_risk: {category(business/technical/compliance/competitive), description, severity(high/medium/low), mitigation(optional)}. For add_success_metric: {name, description, target, category, measurement_approach}. For update_field: {field_name, value}.",
                    },
                },
                "required": ["action", "data"],
            },
        },
        # Document Clarification Tools
        {
            "name": "check_document_clarifications",
            "description": "Check if any uploaded documents need clarification about their type or content. Returns pending clarification questions. Use this when the user mentions a document upload or when you want to check for ambiguous documents.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "respond_to_document_clarification",
            "description": "Respond to a document clarification question. After the user tells you what type a document is, use this to update the classification.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "UUID of the document needing clarification",
                    },
                    "document_class": {
                        "type": "string",
                        "enum": [
                            "prd",
                            "transcript",
                            "spec",
                            "email",
                            "presentation",
                            "spreadsheet",
                            "wireframe",
                            "research",
                            "process_doc",
                            "generic",
                        ],
                        "description": "The correct document class based on user response",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context from the user about the document",
                    },
                },
                "required": ["document_id", "document_class"],
            },
        },
        # =============================================================================
        # Unified Entity CRUD Tools (v3 smart chat)
        # =============================================================================
        {
            "name": "create_entity",
            "description": "Create a new entity in the project. Supports features, personas, workflow steps, stakeholders, data entities, and workflows. Use when the user asks to add/create something. Always confirm what was created.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": [
                            "feature",
                            "persona",
                            "vp_step",
                            "stakeholder",
                            "data_entity",
                            "workflow",
                        ],
                        "description": "Type of entity to create",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name/title of the entity",
                    },
                    "fields": {
                        "type": "object",
                        "description": "Additional fields. Feature: category, is_mvp, overview, priority_group. Persona: role, goals(array), pain_points(array). VP Step: workflow_id, step_number, actor, pain_description, benefit_description, time_minutes, automation_level. Stakeholder: stakeholder_type(champion/sponsor/blocker/influencer/end_user), email, role, organization, influence_level. Data Entity: entity_type, fields(array of {name,type,description}). Workflow: workflow_type(current/future), description.",
                    },
                },
                "required": ["entity_type", "name"],
            },
        },
        {
            "name": "update_entity",
            "description": "Update an existing entity by ID. Supports all entity types. Use when the user asks to change, modify, rename, or update something specific. Always confirm what was changed.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": [
                            "feature",
                            "persona",
                            "vp_step",
                            "stakeholder",
                            "data_entity",
                            "workflow",
                        ],
                        "description": "Type of entity to update",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "UUID of the entity to update",
                    },
                    "fields": {
                        "type": "object",
                        "description": "Fields to update. Feature: name, category, overview, priority_group, is_mvp. Persona: name, role, goals, pain_points. VP Step: name, actor, pain_description, benefit_description, time_minutes. Stakeholder: name, stakeholder_type, email, role, influence_level. Data Entity: name, entity_type, fields. Workflow: name, description.",
                    },
                },
                "required": ["entity_type", "entity_id", "fields"],
            },
        },
        # Research / Evolution Tools
        {
            "name": "query_entity_history",
            "description": "Show the evolution of a specific entity — when it was created, how it changed over time, which signals contributed to it, and linked beliefs. Use this when the user asks 'tell me about the evolution of this feature' or 'how did this persona change'.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["feature", "persona", "vp_step", "stakeholder", "data_entity", "workflow"],
                        "description": "Type of entity to look up",
                    },
                    "entity_id_or_name": {
                        "type": "string",
                        "description": "UUID or name (fuzzy match) of the entity",
                    },
                },
                "required": ["entity_type", "entity_id_or_name"],
            },
        },
        {
            "name": "query_knowledge_graph",
            "description": "Search the project's knowledge graph for facts, beliefs, and relationships about a topic. Use when the user asks 'what do we know about X' or wants to explore connected concepts.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic or keyword to search for in the knowledge graph",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum nodes to return",
                        "default": 10,
                    },
                },
                "required": ["topic"],
            },
        },
        # Task Creation
        {
            "name": "create_task",
            "description": "Create a project task for follow-ups, reviews, or action items. Use when the user says 'create a task', 'remind me to', 'follow up on', or any request to track an action item.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title — clear, actionable, starts with a verb",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional detailed description of the task",
                    },
                    "task_type": {
                        "type": "string",
                        "enum": ["manual", "gap", "enrichment", "validation", "research", "collaboration"],
                        "description": "Type of task. Default: manual",
                        "default": "manual",
                    },
                    "requires_client_input": {
                        "type": "boolean",
                        "description": "Whether the task needs client review or input",
                        "default": False,
                    },
                    "anchored_entity_type": {
                        "type": "string",
                        "enum": ["business_driver", "feature", "persona", "vp_step", "stakeholder"],
                        "description": "Optional entity type this task is anchored to",
                    },
                    "anchored_entity_id": {
                        "type": "string",
                        "description": "Optional UUID of the anchored entity",
                    },
                },
                "required": ["title"],
            },
        },
        # Interactive Action Cards
        {
            "name": "suggest_actions",
            "description": "Present interactive action cards to the consultant. Use this when you can offer specific, one-click actions. Cards render as interactive UI in the chat. Types: gap_closer (close gaps), action_buttons (simple 1-2 buttons), choice (pick from options), proposal (approve/modify/skip), email_draft, meeting, smart_summary (batch save entities), evidence (tag document quotes).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "cards": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "card_type": {
                                    "type": "string",
                                    "enum": [
                                        "gap_closer",
                                        "action_buttons",
                                        "choice",
                                        "proposal",
                                        "email_draft",
                                        "meeting",
                                        "smart_summary",
                                        "evidence",
                                    ],
                                },
                                "id": {"type": "string"},
                                "data": {"type": "object"},
                            },
                            "required": ["card_type", "id", "data"],
                        },
                    }
                },
                "required": ["cards"],
            },
        },
    ]


# =============================================================================
# Page-Context Tool Filtering
# =============================================================================

# Tools sent on every request regardless of page
CORE_TOOLS = {
    "get_project_status",
    "search",
    "create_entity",
    "update_entity",
    "create_task",
    "suggest_actions",
    "add_signal",
    "create_confirmation",
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
    "brd:questions": {"list_pending_confirmations", "generate_client_email"},
    "overview": {
        "generate_strategic_context",
        "update_strategic_context",
        "update_project_type",
        "identify_stakeholders",
        "list_pending_confirmations",
    },
    "prototype": {"attach_evidence", "query_entity_history"},
}

# Tools added when no specific page context (chat opened from sidebar, etc.)
FALLBACK_EXTRAS = {
    "generate_strategic_context",
    "update_strategic_context",
    "update_project_type",
    "identify_stakeholders",
    "list_pending_confirmations",
    "generate_client_email",
    "generate_meeting_agenda",
    "attach_evidence",
    "query_entity_history",
    "query_knowledge_graph",
    "check_document_clarifications",
    "respond_to_document_clarification",
}

# Communication tools — added on any page that involves client interaction
COMMUNICATION_TOOLS = {
    "generate_client_email",
    "generate_meeting_agenda",
    "list_pending_confirmations",
}

# Document tools — added when documents may be discussed
DOCUMENT_TOOLS = {
    "check_document_clarifications",
    "respond_to_document_clarification",
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

        # For any brd: page, include communication and document tools
        if page_context.startswith("brd"):
            page_extras = page_extras | COMMUNICATION_TOOLS | DOCUMENT_TOOLS

        # For the generic "brd" page (all sections), include everything BRD-related
        if page_context == "brd":
            page_extras = set()
            for key, tools in PAGE_TOOLS.items():
                if key.startswith("brd:"):
                    page_extras |= tools
            page_extras |= COMMUNICATION_TOOLS | DOCUMENT_TOOLS

        allowed = CORE_TOOLS | page_extras

    return [t for t in all_tools if t["name"] in allowed]


# Tools that mutate project data — invalidate context frame cache after execution
_MUTATING_TOOLS = {
    "create_entity", "update_entity", "add_signal", "create_task",
    "create_confirmation", "attach_evidence", "generate_strategic_context",
    "update_strategic_context", "update_project_type", "identify_stakeholders",
    "respond_to_document_clarification",
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
    try:
        logger.info(f"Executing tool {tool_name} for project {project_id}")

        if tool_name == "get_project_status":
            return await _get_project_status(project_id, tool_input)
        elif tool_name == "create_confirmation":
            return await _create_confirmation(project_id, tool_input)
        elif tool_name == "search":
            return await _search(project_id, tool_input)
        elif tool_name == "attach_evidence":
            return await _attach_evidence(project_id, tool_input)
        elif tool_name == "add_signal":
            return await _add_signal(project_id, tool_input)
        elif tool_name == "generate_client_email":
            return await _generate_client_email(project_id, tool_input)
        elif tool_name == "generate_meeting_agenda":
            return await _generate_meeting_agenda(project_id, tool_input)
        elif tool_name == "list_pending_confirmations":
            return await _list_pending_confirmations(project_id, tool_input)
        # Strategic Context Tools
        elif tool_name == "generate_strategic_context":
            return await _generate_strategic_context(project_id, tool_input)
        elif tool_name == "update_project_type":
            return await _update_project_type(project_id, tool_input)
        elif tool_name == "identify_stakeholders":
            return await _identify_stakeholders(project_id, tool_input)
        elif tool_name == "update_strategic_context":
            return await _update_strategic_context(project_id, tool_input)
        # Document Clarification Tools
        elif tool_name == "check_document_clarifications":
            return await _check_document_clarifications(project_id, tool_input)
        elif tool_name == "respond_to_document_clarification":
            return await _respond_to_document_clarification(project_id, tool_input)
        # Unified Entity CRUD Tools (v3)
        elif tool_name == "create_entity":
            return await _create_entity(project_id, tool_input)
        elif tool_name == "update_entity":
            return await _update_entity(project_id, tool_input)
        # Research / Evolution Tools
        elif tool_name == "query_entity_history":
            return await _query_entity_history(project_id, tool_input)
        elif tool_name == "query_knowledge_graph":
            return await _query_knowledge_graph(project_id, tool_input)
        # Task Creation
        elif tool_name == "create_task":
            return await _create_task(project_id, tool_input)
        # Interactive Action Cards — pass-through (frontend renders)
        elif tool_name == "suggest_actions":
            return tool_input
        else:
            return {"error": f"Unknown tool: {tool_name}"}

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


async def _get_project_status(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get project status summary.

    Args:
        project_id: Project UUID
        params: Status parameters

    Returns:
        Project status summary
    """
    supabase = get_supabase()
    include_details = params.get("include_details", False)

    # Get counts in parallel
    features_response = supabase.table("features").select("id", count="exact").eq("project_id", str(project_id)).execute()

    personas_response = supabase.table("personas").select("id", count="exact").eq("project_id", str(project_id)).execute()

    vp_response = supabase.table("vp_steps").select("id", count="exact").eq("project_id", str(project_id)).execute()

    insights_response = (
        supabase.table("insights")
        .select("id, severity", count="exact")
        .eq("project_id", str(project_id))
        .eq("insight_type", "general")
        .eq("status", "open")
        .execute()
    )

    patches_queued_response = (
        supabase.table("insights")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("insight_type", "patch")
        .eq("status", "queued")
        .execute()
    )

    patches_applied_response = (
        supabase.table("insights")
        .select("id", count="exact")
        .eq("project_id", str(project_id))
        .eq("insight_type", "patch")
        .eq("status", "applied")
        .execute()
    )

    # Try to get confirmation_items (table may not exist yet)
    confirmations_count = 0
    try:
        confirmations_response = (
            supabase.table("confirmation_items")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .eq("status", "open")
            .execute()
        )
        confirmations_count = confirmations_response.count or 0
    except Exception:
        # Table doesn't exist yet - migrations not run
        pass

    # Count critical insights
    insights_data = insights_response.data or []
    critical_count = sum(1 for insight in insights_data if insight.get("severity") == "critical")

    status = {
        "counts": {
            "features": features_response.count or 0,
            "personas": personas_response.count or 0,
            "vp_steps": vp_response.count or 0,
            "insights_open": insights_response.count or 0,
            "insights_critical": critical_count,
            "patches_queued": patches_queued_response.count or 0,
            "patches_applied": patches_applied_response.count or 0,
            "confirmations_open": confirmations_count,
        }
    }

    # Add detailed breakdown if requested
    if include_details and critical_count > 0:
        critical_insights = [i for i in insights_data if i.get("severity") == "critical"][:5]

        critical_response = (
            supabase.table("insights")
            .select("id, title, severity")
            .in_("id", [i["id"] for i in critical_insights])
            .execute()
        )

        status["critical_insights"] = critical_response.data or []

    # Generate summary message
    summary_parts = []
    if status["counts"]["insights_critical"] > 0:
        summary_parts.append(f"{status['counts']['insights_critical']} critical insights")
    if status["counts"]["patches_queued"] > 0:
        summary_parts.append(f"{status['counts']['patches_queued']} patches ready to apply")
    if status["counts"]["confirmations_open"] > 0:
        summary_parts.append(f"{status['counts']['confirmations_open']} confirmations needed")

    if summary_parts:
        status["needs_attention"] = ", ".join(summary_parts)
    else:
        status["needs_attention"] = "No urgent items"

    status["message"] = f"Project has {status['counts']['features']} features, {status['counts']['personas']} personas, {status['counts']['vp_steps']} VP steps"

    return status


async def _create_confirmation(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a confirmation item for the client.

    Args:
        project_id: Project UUID
        params: Confirmation parameters

    Returns:
        Created confirmation
    """
    supabase = get_supabase()

    question = params.get("question")
    context = params.get("context", "")
    related_insight_id = params.get("related_insight_id")

    if not question:
        return {"error": "question is required"}

    try:
        import time

        # Create confirmation record matching confirmation_items schema
        # Generate unique key from timestamp
        key = f"chat_{int(time.time() * 1000)}"

        confirmation_data = {
            "project_id": str(project_id),
            "kind": "insight" if related_insight_id else "chat",
            "key": key,
            "title": question[:100],  # First 100 chars as title
            "why": context or "Created from chat conversation",
            "ask": question,
            "status": "open",
            "suggested_method": "email",
            "priority": "medium",
            "evidence": [],
            "created_from": {"source": "chat_assistant"},
        }

        if related_insight_id:
            confirmation_data["target_table"] = "insights"
            confirmation_data["target_id"] = related_insight_id

        response = supabase.table("confirmation_items").insert(confirmation_data).execute()

        if response.data:
            confirmation = response.data[0]
            return {
                "success": True,
                "confirmation_id": confirmation["id"],
                "message": f"Created confirmation: {question[:50]}...",
                "confirmation": confirmation,
            }
        else:
            return {"success": False, "error": "Failed to create confirmation"}

    except Exception as e:
        error_msg = str(e)
        # Handle missing confirmations table gracefully
        if "confirmation" in error_msg and "not found" in error_msg.lower():
            return {
                "success": False,
                "error": "Confirmations feature not yet available - database migration needed",
                "message": "⚠️ The confirmation_items table hasn't been created yet. Please run database migrations.",
            }
        return {"success": False, "error": error_msg, "message": f"Failed to create confirmation: {error_msg}"}


async def _search(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Semantic search through research using AI embeddings.

    Args:
        project_id: Project UUID
        params: Tool parameters (query, chunk_types, min_similarity, limit)

    Returns:
        Search results with similarity scores
    """
    try:
        from app.core.embeddings import embed_texts
        from app.db.phase0 import vector_search_with_priority

        query = params["query"]
        chunk_types = params.get("chunk_types", ["all"])
        min_similarity = params.get("min_similarity", 0.7)
        limit = params.get("limit", 10)

        logger.info(f"Semantic search for: {query}")

        # Generate embedding for query
        query_embedding = embed_texts([query])[0]

        # Search with priority boosting
        results = vector_search_with_priority(
            query_embedding=query_embedding,
            match_count=limit * 2,  # Get more, then filter
            project_id=project_id,
            priority_boost=True,
        )

        # Filter by similarity threshold and chunk type
        filtered_results = []
        for result in results:
            similarity = result.get("similarity", 0)
            if similarity < min_similarity:
                continue

            # Filter by chunk type if specified
            if "all" not in chunk_types:
                source_type = result.get("metadata", {}).get("source_type", "")
                if source_type not in chunk_types:
                    continue

            filtered_results.append({
                "chunk_id": result.get("id"),
                "text": result.get("text", "")[:500],  # Limit text preview
                "similarity": round(similarity, 3),
                "source_type": result.get("metadata", {}).get("source_type", "unknown"),
                "metadata": result.get("metadata", {}),
            })

            if len(filtered_results) >= limit:
                break

        return {
            "success": True,
            "results": filtered_results,
            "count": len(filtered_results),
            "query": query,
            "message": f"Found {len(filtered_results)} relevant research chunks",
        }

    except Exception as e:
        logger.error(f"Error in semantic search: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Semantic search failed: {str(e)}",
        }


async def _attach_evidence(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attach research evidence to an entity.

    Args:
        project_id: Project UUID
        params: Tool parameters (entity_type, entity_id, chunk_ids, rationale)

    Returns:
        Success status and updated entity
    """
    try:
        supabase = get_supabase()

        entity_type = params["entity_type"]
        entity_id = params["entity_id"]
        chunk_ids = params["chunk_ids"]
        rationale = params["rationale"]

        # Map entity type to table name
        table_map = {
            "feature": "features",
            "vp_step": "vp_steps",
            "persona": "personas",
        }

        table_name = table_map.get(entity_type)
        if not table_name:
            return {"success": False, "error": f"Invalid entity type: {entity_type}"}

        # Get current entity
        response = supabase.table(table_name).select("*").eq("id", entity_id).single().execute()

        if not response.data:
            return {"success": False, "error": f"Entity not found: {entity_id}"}

        entity = response.data
        current_evidence = entity.get("evidence", [])

        # Build new evidence entries
        new_evidence = []
        for chunk_id in chunk_ids:
            # Fetch chunk to get excerpt
            chunk_response = supabase.table("signal_chunks").select("text").eq("id", chunk_id).single().execute()

            if chunk_response.data:
                new_evidence.append({
                    "chunk_id": chunk_id,
                    "excerpt": chunk_response.data.get("text", "")[:280],
                    "rationale": rationale,
                })

        # Merge with existing evidence (avoid duplicates)
        existing_chunk_ids = {e.get("chunk_id") for e in current_evidence}
        for evidence in new_evidence:
            if evidence["chunk_id"] not in existing_chunk_ids:
                current_evidence.append(evidence)

        # Update entity
        update_response = supabase.table(table_name).update({"evidence": current_evidence}).eq("id", entity_id).execute()

        logger.info(f"Attached {len(new_evidence)} evidence chunks to {entity_type} {entity_id}")

        return {
            "success": True,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "attached_count": len(new_evidence),
            "total_evidence": len(current_evidence),
            "message": f"Attached {len(new_evidence)} evidence chunks to {entity_type}",
        }

    except Exception as e:
        logger.error(f"Error attaching evidence: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to attach evidence: {str(e)}",
        }


def _summarize_change(change: Dict[str, Any]) -> str:
    """
    Create a one-line summary of a change.

    Args:
        change: Change object

    Returns:
        Summary string
    """
    operation = change.get("operation", "unknown")
    entity_type = change.get("entity_type", "unknown")
    after = change.get("after", {})

    if operation == "create":
        name = after.get("name") or after.get("label") or after.get("slug") or "Untitled"
        return f"Create {entity_type}: {name}"
    elif operation == "update":
        name = after.get("name") or after.get("label") or after.get("slug") or "Untitled"
        return f"Update {entity_type}: {name}"
    elif operation == "delete":
        before = change.get("before", {})
        name = before.get("name") or before.get("label") or before.get("slug") or "Untitled"
        return f"Delete {entity_type}: {name}"
    else:
        return f"{operation} {entity_type}"


async def _add_signal(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a signal and process it through the full pipeline.

    Args:
        project_id: Project UUID
        params: Signal parameters (signal_type, content, source, process_immediately)

    Returns:
        Created signal with processing status
    """
    import uuid as uuid_module

    signal_type = params.get("signal_type", "note")
    content = params.get("content")
    source = params.get("source", "chat")
    process_immediately = params.get("process_immediately", True)

    if not content:
        return {"success": False, "error": "content is required"}

    try:
        supabase = get_supabase()
        run_id = str(uuid_module.uuid4())

        # Derive a meaningful title from the content (first line, truncated)
        def derive_title(text: str, max_length: int = 60) -> str:
            """Derive a title from content - first non-empty line, cleaned and truncated."""
            lines = text.strip().split('\n')
            for line in lines:
                cleaned = line.strip()
                # Skip empty lines or lines that look like timestamps/metadata
                if cleaned and not cleaned.startswith('[') and len(cleaned) > 5:
                    # Remove common transcript markers
                    if cleaned.lower().startswith(('speaker', 'transcript', '---')):
                        continue
                    # Truncate and add ellipsis if needed
                    if len(cleaned) > max_length:
                        return cleaned[:max_length].rsplit(' ', 1)[0] + '...'
                    return cleaned
            # Fallback to generic title with timestamp
            from datetime import datetime
            return f"Signal from {datetime.now().strftime('%b %d, %Y')}"

        signal_title = derive_title(content)

        # Create signal record
        signal_data = {
            "project_id": str(project_id),
            "signal_type": signal_type,
            "source": source,
            "raw_text": content,
            "metadata": {
                "source": source,
                "added_via": "chat_assistant",
                "title": signal_title,
            },
            "run_id": run_id,
        }

        response = supabase.table("signals").insert(signal_data).execute()

        if not response.data:
            return {"success": False, "error": "Failed to create signal"}

        signal = response.data[0]
        signal_id = signal["id"]

        # Chunk and embed the signal text
        chunks_created = 0
        try:
            from app.core.chunking import chunk_text
            from app.core.embeddings import embed_texts
            from app.db.phase0 import insert_signal_chunks

            chunks = chunk_text(content)
            if chunks:
                # Extract content strings for embedding
                chunk_texts = [c["content"] for c in chunks]
                embeddings = embed_texts(chunk_texts)
                insert_signal_chunks(
                    signal_id=UUID(signal_id),
                    chunks=chunks,
                    embeddings=embeddings,
                    run_id=UUID(run_id),
                )
                chunks_created = len(chunks)
                logger.info(f"Created {chunks_created} chunks for signal {signal_id}")
        except Exception as chunk_error:
            logger.warning(f"Failed to chunk signal {signal_id}: {chunk_error}")
            # Continue anyway - signal is saved

        # Invalidate DI cache - new signal to analyze
        try:
            from app.db.di_cache import invalidate_cache
            invalidate_cache(project_id, f"new {signal_type} signal from {source}")
        except Exception as cache_err:
            logger.warning(f"Failed to invalidate DI cache: {cache_err}")

        result = {
            "success": True,
            "signal_id": signal_id,
            "signal_type": signal_type,
            "source": source,
            "content_length": len(content),
            "chunks_created": chunks_created,
        }

        # Process through V2 pipeline if requested
        if process_immediately:
            try:
                from app.graphs.unified_processor import process_signal_v2

                logger.info(f"Processing signal {signal_id} through V2 pipeline")

                pipeline_result = await process_signal_v2(
                    signal_id=UUID(signal_id),
                    project_id=project_id,
                    run_id=UUID(run_id),
                )

                if pipeline_result.success:
                    result["processed"] = True
                    result["patches_applied"] = pipeline_result.patches_applied
                    result["created_count"] = pipeline_result.created_count
                    result["merged_count"] = pipeline_result.merged_count
                    result["message"] = pipeline_result.chat_summary or (
                        f"Created {signal_type} signal and processed: "
                        f"{pipeline_result.patches_applied} patches applied, "
                        f"{pipeline_result.created_count} created"
                    )
                else:
                    result["processed"] = False
                    result["pipeline_error"] = pipeline_result.error or "Unknown error"
                    result["message"] = f"Created {signal_type} signal but processing failed: {result['pipeline_error']}"

            except Exception as pipeline_error:
                logger.warning(f"V2 pipeline processing failed: {pipeline_error}")
                result["processed"] = False
                result["pipeline_error"] = str(pipeline_error)
                result["message"] = f"Created {signal_type} signal but processing failed: {str(pipeline_error)}"
        else:
            result["processed"] = False
            result["message"] = f"Created {signal_type} signal. Use signal streaming to process."

        return result

    except Exception as e:
        logger.error(f"Error adding signal: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to add signal: {str(e)}",
        }


# =======================
# Client Communication Tools
# =======================


async def _generate_client_email(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a professional email draft for client outreach.

    Args:
        project_id: Project UUID
        params: Tool parameters (confirmation_ids, client_name, project_name)

    Returns:
        Generated email with subject and body
    """
    try:
        import json
        from openai import OpenAI
        from app.core.config import get_settings
        from app.db.confirmations import list_confirmation_items, get_confirmation_item

        settings = get_settings()
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        confirmation_ids = params.get("confirmation_ids", [])
        client_name = params.get("client_name", "")
        project_name = params.get("project_name", "")

        # Get confirmations to include
        if confirmation_ids:
            confirmations = []
            for cid in confirmation_ids:
                item = get_confirmation_item(UUID(cid))
                if item:
                    confirmations.append(item)
        else:
            # Get all open confirmations suitable for email
            all_confirmations = list_confirmation_items(project_id, status="open")
            confirmations = [
                c for c in all_confirmations
                if c.get("suggested_method") == "email"
            ]

        if not confirmations:
            return {
                "success": False,
                "error": "No suitable confirmations found",
                "message": "There are no pending confirmation items suitable for email. Items may already be resolved or require a meeting instead.",
            }

        # Build questions text
        questions_text = "\n".join([
            f"{i+1}. **{c.get('title', 'Question')}**\n   - Why: {c.get('why', 'N/A')}\n   - Ask: {c.get('ask', 'N/A')}\n   - Priority: {c.get('priority', 'medium')}"
            for i, c in enumerate(confirmations)
        ])

        prompt = f"""You are drafting a professional email to a client to gather information for their software project.

**Project:** {project_name or 'your project'}
**Client:** {client_name or 'there'}

**Questions to include:**
{questions_text}

**Instructions:**
- Write a friendly, professional email
- Be concise - busy clients appreciate brevity
- Frame everything as QUESTIONS to the client, not requests to "review" anything
- The client will NOT see any platform or system - they only receive this email
- Group related questions together
- Number the questions for easy reference
- Make questions clear and answerable via email reply
- Make it easy to respond (e.g., "You can reply inline or schedule a quick call")
- End with a clear call to action

Return JSON with:
- "subject": Email subject line
- "body": Full email body (use \\n for newlines)
"""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_MINI,
            temperature=0.7,
            max_tokens=1500,
            messages=[
                {"role": "system", "content": "You are a professional consultant drafting client communications. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )

        # Log usage
        from app.core.llm_usage import log_llm_usage
        log_llm_usage(
            workflow="chat_assistant", chain="generate_client_email",
            model=response.model, provider="openai",
            tokens_input=response.usage.prompt_tokens, tokens_output=response.usage.completion_tokens,
            project_id=project_id,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        result = json.loads(raw)

        email_body = result.get("body", "").replace("\\n", "\n")
        email_subject = result.get("subject", "Questions for your project")

        return {
            "success": True,
            "subject": email_subject,
            "body": email_body,
            "confirmation_count": len(confirmations),
            "confirmations_included": [c["id"] for c in confirmations],
            "message": f"✉️ Generated email draft with {len(confirmations)} questions\n\n**Subject:** {email_subject}\n\n{email_body}",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse email generation JSON: {e}")
        return {"success": False, "error": "Failed to generate email", "message": "Email generation returned invalid format"}
    except Exception as e:
        logger.error(f"Error generating client email: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate email: {str(e)}",
        }


async def _generate_meeting_agenda(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a structured meeting agenda for client discussions.

    Args:
        project_id: Project UUID
        params: Tool parameters (confirmation_ids, client_name, project_name, meeting_duration)

    Returns:
        Generated meeting agenda with time allocations
    """
    try:
        import json
        from openai import OpenAI
        from app.core.config import get_settings
        from app.db.confirmations import list_confirmation_items, get_confirmation_item

        settings = get_settings()
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        confirmation_ids = params.get("confirmation_ids", [])
        client_name = params.get("client_name", "")
        project_name = params.get("project_name", "")
        meeting_duration = params.get("meeting_duration", 30)

        # Get confirmations to include
        if confirmation_ids:
            confirmations = []
            for cid in confirmation_ids:
                item = get_confirmation_item(UUID(cid))
                if item:
                    confirmations.append(item)
        else:
            # Get all open confirmations suitable for meeting
            all_confirmations = list_confirmation_items(project_id, status="open")
            confirmations = [
                c for c in all_confirmations
                if c.get("suggested_method") == "meeting"
            ]

        if not confirmations:
            return {
                "success": False,
                "error": "No suitable confirmations found",
                "message": "There are no pending confirmation items suitable for a meeting. Items may already be resolved or suitable for email instead.",
            }

        # Build questions text with IDs for reference
        questions_text = "\n".join([
            f"- **{c.get('title', 'Topic')}** (ID: {c['id']})\n  Why: {c.get('why', 'N/A')}\n  Ask: {c.get('ask', 'N/A')}\n  Priority: {c.get('priority', 'medium')}"
            for c in confirmations
        ])

        prompt = f"""You are creating a meeting agenda to discuss open questions with a client about their software project.

**Project:** {project_name or 'the project'}
**Client:** {client_name or 'the client'}
**Target Duration:** {meeting_duration} minutes

**Topics to cover:**
{questions_text}

**Instructions:**
- Create a structured agenda with time allocations
- Frame topics as QUESTIONS or DISCUSSIONS, not requests to "review" anything
- The client will NOT see any platform or system - this is a verbal discussion
- Group related topics together
- Start with quick wins, end with complex discussions
- Include a brief pre-read summary for the client (context only, no platform references)
- Be realistic about time - complex topics need more time

Return JSON with:
- "title": Meeting title
- "duration_estimate": Realistic duration estimate (e.g., "25-30 minutes")
- "agenda": Array of agenda items, each with:
  - "topic": Topic title (phrase as a question or discussion point)
  - "description": Brief description of what to discuss
  - "time_minutes": Allocated minutes
- "pre_read": Brief summary client should read before meeting (2-3 sentences, no platform references)
"""

        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_MINI,
            temperature=0.7,
            max_tokens=2000,
            messages=[
                {"role": "system", "content": "You are a professional consultant creating meeting agendas. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )

        # Log usage
        from app.core.llm_usage import log_llm_usage
        log_llm_usage(
            workflow="chat_assistant", chain="generate_meeting_agenda",
            model=response.model, provider="openai",
            tokens_input=response.usage.prompt_tokens, tokens_output=response.usage.completion_tokens,
            project_id=project_id,
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()

        result = json.loads(raw)

        # Format agenda for display
        agenda_items = result.get("agenda", [])
        agenda_text = "\n".join([
            f"  {i+1}. **{item.get('topic', 'Topic')}** ({item.get('time_minutes', 5)} min)\n     {item.get('description', '')}"
            for i, item in enumerate(agenda_items)
        ])

        return {
            "success": True,
            "title": result.get("title", f"Project Discussion: {project_name}"),
            "duration_estimate": result.get("duration_estimate", f"{meeting_duration} minutes"),
            "agenda": agenda_items,
            "pre_read": result.get("pre_read", ""),
            "confirmation_count": len(confirmations),
            "confirmations_included": [c["id"] for c in confirmations],
            "message": f"📋 Generated meeting agenda with {len(confirmations)} topics\n\n**{result.get('title', 'Meeting Agenda')}**\n*Duration: {result.get('duration_estimate', f'{meeting_duration} min')}*\n\n**Pre-read for client:**\n{result.get('pre_read', '')}\n\n**Agenda:**\n{agenda_text}",
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse meeting agenda JSON: {e}")
        return {"success": False, "error": "Failed to generate agenda", "message": "Agenda generation returned invalid format"}
    except Exception as e:
        logger.error(f"Error generating meeting agenda: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate meeting agenda: {str(e)}",
        }


async def _list_pending_confirmations(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List pending confirmation items that need client input.

    Args:
        project_id: Project UUID
        params: Tool parameters (method_filter)

    Returns:
        List of pending confirmations with summary
    """
    try:
        from app.db.confirmations import list_confirmation_items

        method_filter = params.get("method_filter", "all")

        # Get all open confirmations
        confirmations = list_confirmation_items(project_id, status="open")

        # Apply method filter
        if method_filter == "email":
            confirmations = [c for c in confirmations if c.get("suggested_method") == "email"]
        elif method_filter == "meeting":
            confirmations = [c for c in confirmations if c.get("suggested_method") == "meeting"]

        if not confirmations:
            return {
                "success": True,
                "count": 0,
                "confirmations": [],
                "message": "✅ No pending confirmation items. All questions have been resolved!",
            }

        # Count by method
        email_count = sum(1 for c in confirmations if c.get("suggested_method") == "email")
        meeting_count = sum(1 for c in confirmations if c.get("suggested_method") == "meeting")

        # Count by priority
        high_priority = sum(1 for c in confirmations if c.get("priority") == "high")

        # Format confirmations for display
        formatted = []
        for c in confirmations:
            formatted.append({
                "id": c["id"],
                "title": c.get("title", "Untitled"),
                "ask": c.get("ask", ""),
                "why": c.get("why", ""),
                "priority": c.get("priority", "medium"),
                "suggested_method": c.get("suggested_method", "email"),
                "kind": c.get("kind", "general"),
            })

        # Build summary message
        summary_parts = [f"📋 Found {len(confirmations)} pending confirmation items:"]
        if email_count > 0:
            summary_parts.append(f"  • {email_count} suitable for email")
        if meeting_count > 0:
            summary_parts.append(f"  • {meeting_count} need a meeting")
        if high_priority > 0:
            summary_parts.append(f"  • ⚠️ {high_priority} high priority")

        summary_parts.append("\n**Items:**")
        for i, c in enumerate(formatted[:10], 1):  # Limit to first 10
            method_icon = "📧" if c["suggested_method"] == "email" else "📞"
            priority_marker = "🔴" if c["priority"] == "high" else ""
            summary_parts.append(f"  {i}. {method_icon} {priority_marker} {c['title']}")

        if len(confirmations) > 10:
            summary_parts.append(f"  ... and {len(confirmations) - 10} more")

        return {
            "success": True,
            "count": len(confirmations),
            "email_count": email_count,
            "meeting_count": meeting_count,
            "high_priority_count": high_priority,
            "confirmations": formatted,
            "message": "\n".join(summary_parts),
        }

    except Exception as e:
        logger.error(f"Error listing confirmations: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list confirmations: {str(e)}",
        }


# =============================================================================
# Strategic Context Tools
# =============================================================================


async def _generate_strategic_context(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate or regenerate strategic context.

    This now also:
    - Extracts success_metrics to business_drivers (KPIs)
    - Extracts constraints to constraints table
    - Runs company enrichment (Firecrawl + AI)

    Args:
        project_id: Project UUID
        params: Generation parameters

    Returns:
        Generation results
    """
    try:
        from app.chains.generate_strategic_context import generate_and_save_strategic_context
        from app.chains.enrich_company import enrich_company
        from app.db.company_info import get_company_info
        from app.db.business_drivers import list_business_drivers
        from app.db.constraints import list_constraints

        regenerate = params.get("regenerate", False)

        # Run generation (now also extracts to entity tables)
        result = generate_and_save_strategic_context(
            project_id=project_id,
            regenerate=regenerate,
        )

        project_type = result.get("project_type", "internal")
        risks_count = len(result.get("risks", []))
        metrics_count = len(result.get("success_metrics", []))

        # Also run company enrichment (Firecrawl + AI)
        enrichment_result = None
        company_info = get_company_info(project_id)
        if company_info:
            try:
                logger.info(f"Running company enrichment for project {project_id}")
                enrichment_result = await enrich_company(project_id)
                logger.info(f"Company enrichment complete: {enrichment_result}")
            except Exception as e:
                logger.warning(f"Company enrichment failed (non-fatal): {e}")

        # Get counts of extracted entities
        kpis = list_business_drivers(project_id, driver_type="kpi")
        constraints = list_constraints(project_id)

        # Build success message
        message_parts = ["✅ Generated Strategic Context:"]
        message_parts.append(f"  • Project type: {project_type}")
        if result.get("executive_summary"):
            summary_preview = result["executive_summary"][:100] + "..." if len(result.get("executive_summary", "")) > 100 else result.get("executive_summary", "")
            message_parts.append(f"  • Summary: {summary_preview}")
        message_parts.append(f"  • {risks_count} risks identified")
        message_parts.append(f"  • {metrics_count} success metrics")

        # Report extracted entities
        message_parts.append(f"\n**Entities Created:**")
        message_parts.append(f"  • {len(kpis)} KPIs (in Business Drivers)")
        message_parts.append(f"  • {len(constraints)} constraints")

        # Report enrichment
        if enrichment_result and enrichment_result.get("success"):
            source = enrichment_result.get("enrichment_source", "ai")
            chars = enrichment_result.get("scraped_chars", 0)
            if chars > 0:
                message_parts.append(f"  • Company enriched from website ({chars} chars scraped)")
            else:
                message_parts.append(f"  • Company enriched via AI inference")
        elif company_info:
            if not company_info.get("website"):
                message_parts.append(f"  • Company info exists but no website for enrichment")

        opportunity = result.get("opportunity", {})
        if opportunity.get("problem_statement"):
            message_parts.append(f"\n**Problem**: {opportunity['problem_statement'][:150]}...")

        message_parts.append("\n📋 View full details in the **Strategic Foundation** tab.")

        return {
            "success": True,
            "context": result,
            "message": "\n".join(message_parts),
            "task_complete": True,  # Signal to not chain additional tools
        }

    except Exception as e:
        logger.error(f"Error generating strategic context: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate strategic context: {str(e)}",
        }


async def _update_project_type(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update project type.

    Args:
        project_id: Project UUID
        params: Must contain project_type

    Returns:
        Update result
    """
    try:
        from app.db.strategic_context import update_project_type, get_strategic_context

        project_type = params.get("project_type")
        if not project_type:
            return {
                "success": False,
                "error": "project_type is required",
                "message": "Please specify project_type: 'internal' or 'market_product'",
            }

        # Check if context exists
        context = get_strategic_context(project_id)
        if not context:
            return {
                "success": False,
                "error": "No strategic context found",
                "message": "No strategic context exists. Generate one first with `generate_strategic_context`.",
            }

        # Update
        updated = update_project_type(project_id, project_type)

        type_label = "Internal Software" if project_type == "internal" else "Market Product"
        return {
            "success": True,
            "project_type": project_type,
            "message": f"✅ Updated project type to: {type_label}",
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "message": str(e),
        }
    except Exception as e:
        logger.error(f"Error updating project type: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update project type: {str(e)}",
        }


async def _identify_stakeholders(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify stakeholders from signals.

    Args:
        project_id: Project UUID
        params: Not used

    Returns:
        Identification results
    """
    try:
        from app.chains.generate_strategic_context import identify_stakeholders

        stakeholders = identify_stakeholders(project_id)

        if not stakeholders:
            return {
                "success": True,
                "stakeholders_found": 0,
                "stakeholders": [],
                "message": "No stakeholders identified from signals. Add signals with more context about people involved.",
            }

        # Build message
        message_parts = [f"✅ Identified {len(stakeholders)} stakeholders:"]

        type_groups = {}
        for sh in stakeholders:
            sh_type = sh.get("stakeholder_type", "influencer")
            if sh_type not in type_groups:
                type_groups[sh_type] = []
            type_groups[sh_type].append(sh.get("name", "Unknown"))

        for sh_type, names in type_groups.items():
            message_parts.append(f"\n**{sh_type.title()}s**:")
            for name in names[:5]:
                message_parts.append(f"  • {name}")
            if len(names) > 5:
                message_parts.append(f"  ... and {len(names) - 5} more")

        return {
            "success": True,
            "stakeholders_found": len(stakeholders),
            "stakeholders": stakeholders,
            "message": "\n".join(message_parts),
        }

    except Exception as e:
        logger.error(f"Error identifying stakeholders: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to identify stakeholders: {str(e)}",
        }


async def _update_strategic_context(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update strategic context by adding a risk, success metric, or updating a field.

    Routes to the same DB logic that _add_risk and _add_success_metric used.

    Args:
        project_id: Project UUID
        params: Tool parameters (action, data)

    Returns:
        Update result
    """
    try:
        from app.db.strategic_context import add_risk, add_success_metric, get_strategic_context

        action = params.get("action")
        data = params.get("data", {})

        if not action:
            return {
                "success": False,
                "error": "action is required",
                "message": "Please specify action: add_risk, add_success_metric, or update_field",
            }

        # Check if context exists
        context = get_strategic_context(project_id)
        if not context:
            return {
                "success": False,
                "error": "No strategic context found",
                "message": "No strategic context exists. Generate one first with `generate_strategic_context`.",
            }

        if action == "add_risk":
            category = data.get("category")
            description = data.get("description")
            severity = data.get("severity")

            if not category or not description or not severity:
                return {
                    "success": False,
                    "error": "category, description, and severity are required in data",
                    "message": "Please provide risk category (business/technical/compliance/competitive), description, and severity (high/medium/low)",
                }

            updated = add_risk(
                project_id=project_id,
                category=category,
                description=description,
                severity=severity,
                mitigation=data.get("mitigation"),
            )

            return {
                "success": True,
                "risk_count": len(updated.get("risks", [])),
                "message": f"Added {severity.upper()} {category} risk: {description[:80]}",
            }

        elif action == "add_success_metric":
            metric = data.get("name") or data.get("metric")
            target = data.get("target")

            if not metric or not target:
                return {
                    "success": False,
                    "error": "name/metric and target are required in data",
                    "message": "Please provide metric name and target value",
                }

            updated = add_success_metric(
                project_id=project_id,
                metric=metric,
                target=target,
                current=data.get("current"),
            )

            return {
                "success": True,
                "metric_count": len(updated.get("success_metrics", [])),
                "message": f"Added success metric: {metric} -> Target: {target}",
            }

        elif action == "update_field":
            field_name = data.get("field_name")
            value = data.get("value")

            if not field_name:
                return {
                    "success": False,
                    "error": "field_name is required in data for update_field",
                }

            supabase = get_supabase()
            supabase.table("strategic_context").update(
                {field_name: value, "updated_at": "now()"}
            ).eq("project_id", str(project_id)).execute()

            return {
                "success": True,
                "message": f"Updated strategic context field: {field_name}",
            }

        else:
            return {
                "success": False,
                "error": f"Unknown action: {action}",
                "message": "Valid actions: add_risk, add_success_metric, update_field",
            }

    except Exception as e:
        logger.error(f"Error updating strategic context: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update strategic context: {str(e)}",
        }


async def _check_document_clarifications(
    project_id: UUID, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Check for documents that need clarification about their type."""
    try:
        supabase = get_supabase()

        response = (
            supabase.table("document_uploads")
            .select("id, original_filename, clarification_question, document_class, created_at")
            .eq("project_id", str(project_id))
            .eq("needs_clarification", True)
            .is_("clarification_response", "null")
            .order("created_at", desc=True)
            .execute()
        )

        docs = response.data or []

        if not docs:
            return {
                "success": True,
                "pending_clarifications": [],
                "message": "No documents need clarification.",
            }

        return {
            "success": True,
            "pending_clarifications": docs,
            "message": f"{len(docs)} document(s) need clarification about their type.",
        }

    except Exception as e:
        logger.error(f"Error checking clarifications: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _respond_to_document_clarification(
    project_id: UUID, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Respond to a document clarification with the correct document class."""
    document_id = params.get("document_id")
    document_class = params.get("document_class")
    context = params.get("context", "")

    if not document_id or not document_class:
        return {"success": False, "error": "document_id and document_class are required"}

    try:
        supabase = get_supabase()

        # Update the document with clarification response
        response = (
            supabase.table("document_uploads")
            .update({
                "needs_clarification": False,
                "clarification_response": context or document_class,
                "clarified_document_class": document_class,
                "clarified_at": "now()",
                "document_class": document_class,
            })
            .eq("id", document_id)
            .eq("project_id", str(project_id))
            .execute()
        )

        if not response.data:
            return {"success": False, "error": "Document not found or not in this project"}

        doc = response.data[0]

        return {
            "success": True,
            "message": (
                f"Updated **{doc['original_filename']}** classification to "
                f"'{document_class}'. The document's extracted content is already "
                f"in the system and will be used with this corrected classification."
            ),
        }

    except Exception as e:
        logger.error(f"Error responding to clarification: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# Unified Entity CRUD Tool Handlers (v3 smart chat)
# =============================================================================


async def _create_entity(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create any entity type from a unified interface.

    Supports: feature, persona, vp_step, stakeholder, data_entity, workflow.
    """
    entity_type = params.get("entity_type")
    name = params.get("name")
    fields = params.get("fields", {})

    if not entity_type or not name:
        return {
            "success": False,
            "error": "entity_type and name are required",
        }

    try:
        if entity_type == "feature":
            return await _create_feature_entity(project_id, name, fields)
        elif entity_type == "persona":
            return await _create_persona_entity(project_id, name, fields)
        elif entity_type == "vp_step":
            return await _create_vp_step_entity(project_id, name, fields)
        elif entity_type == "stakeholder":
            return await _create_stakeholder_entity(project_id, name, fields)
        elif entity_type == "data_entity":
            return await _create_data_entity_entity(project_id, name, fields)
        elif entity_type == "workflow":
            return await _create_workflow_entity(project_id, name, fields)
        else:
            return {"success": False, "error": f"Unsupported entity type: {entity_type}"}

    except Exception as e:
        logger.error(f"Error creating {entity_type}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _update_entity(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update any entity type from a unified interface.

    Supports: feature, persona, vp_step, stakeholder, data_entity, workflow.
    """
    entity_type = params.get("entity_type")
    entity_id = params.get("entity_id")
    fields = params.get("fields", {})

    if not entity_type or not entity_id:
        return {
            "success": False,
            "error": "entity_type and entity_id are required",
        }

    if not fields:
        return {
            "success": False,
            "error": "fields must contain at least one field to update",
        }

    try:
        eid = UUID(entity_id)
    except (ValueError, TypeError):
        return {"success": False, "error": f"Invalid entity_id: {entity_id}"}

    try:
        if entity_type == "feature":
            return await _update_feature_entity(eid, fields)
        elif entity_type == "persona":
            return await _update_persona_entity(eid, fields)
        elif entity_type == "vp_step":
            return await _update_vp_step_entity(eid, fields)
        elif entity_type == "stakeholder":
            return await _update_stakeholder_entity(eid, fields)
        elif entity_type == "data_entity":
            return await _update_data_entity_entity(eid, fields)
        elif entity_type == "workflow":
            return await _update_workflow_entity(eid, fields)
        else:
            return {"success": False, "error": f"Unsupported entity type: {entity_type}"}

    except Exception as e:
        logger.error(f"Error updating {entity_type} {entity_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# --- Feature ---

async def _create_feature_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a single feature via direct insert."""
    supabase = get_supabase()

    data = {
        "project_id": str(project_id),
        "name": name,
        "category": fields.get("category", "core"),
        "is_mvp": fields.get("is_mvp", True),
        "confirmation_status": "ai_generated",
        "status": "proposed",
        "confidence": fields.get("confidence", 0.7),
    }
    if fields.get("overview"):
        data["overview"] = fields["overview"]
    if fields.get("priority_group"):
        data["priority_group"] = fields["priority_group"]
    if fields.get("evidence"):
        data["evidence"] = fields["evidence"]

    response = supabase.table("features").insert(data).execute()
    if not response.data:
        return {"success": False, "error": "Failed to insert feature"}

    feature = response.data[0]
    return {
        "success": True,
        "entity_type": "feature",
        "entity_id": feature["id"],
        "message": f"Created feature: **{name}**",
    }


async def _update_feature_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a feature."""
    supabase = get_supabase()

    ALLOWED = {"name", "category", "overview", "priority_group", "is_mvp", "confidence", "status"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields to update. Allowed: {', '.join(ALLOWED)}"}

    updates["updated_at"] = "now()"
    response = supabase.table("features").update(updates).eq("id", str(entity_id)).execute()

    if not response.data:
        return {"success": False, "error": "Feature not found"}

    changed = ", ".join(f"{k}={v}" for k, v in updates.items() if k != "updated_at")
    return {
        "success": True,
        "entity_type": "feature",
        "entity_id": str(entity_id),
        "message": f"Updated feature: {changed}",
    }


# --- Persona ---

async def _create_persona_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a persona."""
    from app.db.personas import create_persona

    slug = name.lower().replace(" ", "_").replace("-", "_")[:50]

    persona = create_persona(
        project_id=project_id,
        slug=slug,
        name=name,
        role=fields.get("role"),
        goals=fields.get("goals"),
        pain_points=fields.get("pain_points"),
        description=fields.get("description"),
        confirmation_status="ai_generated",
    )

    return {
        "success": True,
        "entity_type": "persona",
        "entity_id": persona["id"],
        "message": f"Created persona: **{name}**" + (f" ({fields['role']})" if fields.get("role") else ""),
    }


async def _update_persona_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a persona."""
    from app.db.personas import update_persona

    ALLOWED = {"name", "role", "goals", "pain_points", "description", "demographics", "psychographics"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    persona = update_persona(persona_id=entity_id, updates=updates)
    changed = ", ".join(updates.keys())
    return {
        "success": True,
        "entity_type": "persona",
        "entity_id": str(entity_id),
        "message": f"Updated persona **{persona.get('name', '')}**: {changed}",
    }


# --- VP Step (workflow step) ---

async def _create_vp_step_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a workflow step."""
    from app.db.workflows import create_workflow_step

    workflow_id = fields.get("workflow_id")
    if not workflow_id:
        return {"success": False, "error": "workflow_id is required for vp_step creation"}

    step_data = {
        "name": name,
        "step_number": fields.get("step_number", 99),
        "actor": fields.get("actor"),
        "pain_description": fields.get("pain_description"),
        "benefit_description": fields.get("benefit_description"),
        "time_minutes": fields.get("time_minutes"),
        "automation_level": fields.get("automation_level"),
        "operation_type": fields.get("operation_type"),
        "confirmation_status": "ai_generated",
    }
    # Remove None values
    step_data = {k: v for k, v in step_data.items() if v is not None}

    step = create_workflow_step(
        workflow_id=UUID(workflow_id),
        project_id=project_id,
        data=step_data,
    )

    return {
        "success": True,
        "entity_type": "vp_step",
        "entity_id": step["id"],
        "message": f"Created step: **{name}**" + (f" (actor: {fields['actor']})" if fields.get("actor") else ""),
    }


async def _update_vp_step_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a workflow step."""
    from app.db.workflows import update_workflow_step

    ALLOWED = {
        "name", "step_number", "actor", "pain_description",
        "benefit_description", "time_minutes", "automation_level", "operation_type",
    }
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    step = update_workflow_step(step_id=entity_id, data=updates)
    changed = ", ".join(updates.keys())
    return {
        "success": True,
        "entity_type": "vp_step",
        "entity_id": str(entity_id),
        "message": f"Updated step **{step.get('name', '')}**: {changed}",
    }


# --- Stakeholder ---

async def _create_stakeholder_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a stakeholder."""
    from app.db.stakeholders import create_stakeholder

    stakeholder_type = fields.get("stakeholder_type", "influencer")

    stakeholder = create_stakeholder(
        project_id=project_id,
        name=name,
        stakeholder_type=stakeholder_type,
        email=fields.get("email"),
        role=fields.get("role"),
        organization=fields.get("organization"),
        influence_level=fields.get("influence_level", "medium"),
        priorities=fields.get("priorities", []),
        concerns=fields.get("concerns", []),
        confirmation_status="ai_generated",
    )

    type_labels = {
        "champion": "Champion",
        "sponsor": "Sponsor",
        "blocker": "Blocker",
        "influencer": "Influencer",
        "end_user": "End User",
    }

    return {
        "success": True,
        "entity_type": "stakeholder",
        "entity_id": stakeholder["id"],
        "message": f"Created stakeholder: **{name}** ({type_labels.get(stakeholder_type, stakeholder_type)})",
    }


async def _update_stakeholder_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a stakeholder."""
    from app.db.stakeholders import update_stakeholder

    ALLOWED = {
        "name", "stakeholder_type", "email", "role", "organization",
        "influence_level", "priorities", "concerns", "notes",
    }
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    stakeholder = update_stakeholder(stakeholder_id=entity_id, updates=updates)
    changed = ", ".join(updates.keys())
    return {
        "success": True,
        "entity_type": "stakeholder",
        "entity_id": str(entity_id),
        "message": f"Updated stakeholder **{stakeholder.get('name', '')}**: {changed}",
    }


# --- Data Entity ---

async def _create_data_entity_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a data entity."""
    from app.db.data_entities import create_data_entity

    data = {
        "name": name,
        "entity_type": fields.get("entity_type", "domain_object"),
        "fields": fields.get("fields", []),
        "description": fields.get("description"),
        "confirmation_status": "ai_generated",
    }

    entity = create_data_entity(project_id=project_id, data=data)

    return {
        "success": True,
        "entity_type": "data_entity",
        "entity_id": entity["id"],
        "message": f"Created data entity: **{name}**",
    }


async def _update_data_entity_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a data entity."""
    from app.db.data_entities import update_data_entity

    ALLOWED = {"name", "entity_type", "fields", "description"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    entity = update_data_entity(entity_id=entity_id, data=updates)
    changed = ", ".join(updates.keys())
    return {
        "success": True,
        "entity_type": "data_entity",
        "entity_id": str(entity_id),
        "message": f"Updated data entity **{entity.get('name', '')}**: {changed}",
    }


# --- Workflow ---

async def _create_workflow_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a workflow."""
    from app.db.workflows import create_workflow

    data = {
        "name": name,
        "workflow_type": fields.get("workflow_type", "current"),
        "description": fields.get("description"),
    }

    workflow = create_workflow(project_id=project_id, data=data)

    return {
        "success": True,
        "entity_type": "workflow",
        "entity_id": workflow["id"],
        "message": f"Created workflow: **{name}** ({data['workflow_type']})",
    }


async def _update_workflow_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a workflow."""
    from app.db.workflows import update_workflow

    ALLOWED = {"name", "description", "workflow_type"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    workflow = update_workflow(workflow_id=entity_id, data=updates)
    changed = ", ".join(updates.keys())
    return {
        "success": True,
        "entity_type": "workflow",
        "entity_id": str(entity_id),
        "message": f"Updated workflow **{workflow.get('name', '')}**: {changed}",
    }


# ===========================
# Research / Evolution Tools
# ===========================


async def _query_entity_history(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Query the evolution history of an entity."""
    supabase = get_supabase()
    entity_type = params.get("entity_type", "feature")
    id_or_name = params.get("entity_id_or_name", "")

    # Table mapping
    table_map = {
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
        "stakeholder": "stakeholders",
        "data_entity": "data_entities",
        "workflow": "workflows",
    }
    table = table_map.get(entity_type)
    if not table:
        return {"error": f"Unknown entity type: {entity_type}"}

    # Resolve entity — try UUID first, then fuzzy name match
    entity = None
    entity_id = None
    try:
        UUID(id_or_name)
        resp = supabase.table(table).select("*").eq("id", id_or_name).single().execute()
        entity = resp.data
        entity_id = id_or_name
    except (ValueError, Exception):
        # Fuzzy name match
        resp = (
            supabase.table(table)
            .select("*")
            .eq("project_id", str(project_id))
            .ilike("name", f"%{id_or_name}%")
            .limit(1)
            .execute()
        )
        if resp.data:
            entity = resp.data[0]
            entity_id = entity["id"]

    if not entity:
        return {"error": f"No {entity_type} found matching '{id_or_name}'"}

    result: Dict[str, Any] = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "name": entity.get("name") or entity.get("title", ""),
        "created_at": entity.get("created_at"),
        "confirmation_status": entity.get("confirmation_status"),
    }

    # Load enrichment revisions (chronological field changes)
    try:
        rev_resp = (
            supabase.table("enrichment_revisions")
            .select("field_name, old_value, new_value, source, created_at")
            .eq("entity_type", entity_type)
            .eq("entity_id", entity_id)
            .order("created_at")
            .limit(20)
            .execute()
        )
        result["revisions"] = rev_resp.data or []
    except Exception:
        result["revisions"] = []

    # Load source signals
    source_signal_ids = entity.get("source_signal_ids") or []
    if source_signal_ids:
        try:
            sig_resp = (
                supabase.table("signals")
                .select("id, title, signal_type, created_at")
                .in_("id", source_signal_ids[:10])
                .order("created_at")
                .execute()
            )
            result["source_signals"] = sig_resp.data or []
        except Exception:
            result["source_signals"] = []
    else:
        result["source_signals"] = []

    # Load linked memory nodes
    try:
        mem_resp = (
            supabase.table("memory_nodes")
            .select("id, node_type, summary, confidence, created_at")
            .eq("project_id", str(project_id))
            .eq("linked_entity_type", entity_type)
            .eq("linked_entity_id", entity_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        result["memory_nodes"] = mem_resp.data or []
    except Exception:
        result["memory_nodes"] = []

    rev_count = len(result["revisions"])
    sig_count = len(result["source_signals"])
    mem_count = len(result["memory_nodes"])
    result["message"] = (
        f"**{result['name']}** ({entity_type}): "
        f"{rev_count} revisions, {sig_count} source signals, {mem_count} linked facts"
    )
    return result


async def _query_knowledge_graph(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Search the knowledge graph for facts and beliefs about a topic."""
    supabase = get_supabase()
    topic = params.get("topic", "")
    limit = min(params.get("limit", 10), 20)

    if not topic:
        return {"error": "topic is required"}

    # Search memory nodes by summary
    try:
        nodes_resp = (
            supabase.table("memory_nodes")
            .select("id, node_type, summary, confidence, consultant_status, linked_entity_type, linked_entity_id, created_at")
            .eq("project_id", str(project_id))
            .ilike("summary", f"%{topic}%")
            .order("confidence", desc=True)
            .limit(limit)
            .execute()
        )
        nodes = nodes_resp.data or []
    except Exception as e:
        logger.error(f"Knowledge graph search failed: {e}")
        return {"error": str(e)}

    if not nodes:
        return {
            "nodes": [],
            "edges": [],
            "message": f"No knowledge found about '{topic}'. Try uploading documents or discussing the topic in chat.",
        }

    node_ids = [n["id"] for n in nodes]

    # Load edges for matching nodes
    edges = []
    try:
        edges_resp = (
            supabase.table("memory_edges")
            .select("source_node_id, target_node_id, edge_type, weight")
            .or_(f"source_node_id.in.({','.join(node_ids)}),target_node_id.in.({','.join(node_ids)})")
            .limit(50)
            .execute()
        )
        edges = edges_resp.data or []
    except Exception:
        pass

    # Categorize nodes
    facts = [n for n in nodes if n.get("node_type") == "fact"]
    beliefs = [n for n in nodes if n.get("node_type") == "belief"]
    other = [n for n in nodes if n.get("node_type") not in ("fact", "belief")]

    result = {
        "topic": topic,
        "nodes": nodes,
        "edges": edges,
        "summary": {
            "total_nodes": len(nodes),
            "facts": len(facts),
            "beliefs": len(beliefs),
            "other": len(other),
            "relationships": len(edges),
        },
    }

    # Build message
    parts = []
    if facts:
        parts.append(f"{len(facts)} facts")
    if beliefs:
        parts.append(f"{len(beliefs)} beliefs")
    if edges:
        parts.append(f"{len(edges)} relationships")
    result["message"] = f"Knowledge about '{topic}': {', '.join(parts) if parts else 'no results'}"

    return result


async def _create_task(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a project task from the chat assistant."""
    from app.core.schemas_tasks import TaskCreate, TaskSourceType, TaskType, AnchoredEntityType
    from app.db.tasks import create_task

    title = params.get("title", "").strip()
    if not title:
        return {"error": "title is required"}

    # Map task_type string to enum
    task_type_str = params.get("task_type", "manual")
    task_type_map = {t.value: t for t in TaskType}
    task_type = task_type_map.get(task_type_str, TaskType.MANUAL)

    # Map anchored_entity_type string to enum
    anchored_type = None
    anchored_type_str = params.get("anchored_entity_type")
    if anchored_type_str:
        entity_type_map = {t.value: t for t in AnchoredEntityType}
        anchored_type = entity_type_map.get(anchored_type_str)

    anchored_id = None
    anchored_id_str = params.get("anchored_entity_id")
    if anchored_id_str:
        try:
            anchored_id = UUID(anchored_id_str)
        except (ValueError, TypeError):
            pass

    task_data = TaskCreate(
        title=title,
        description=params.get("description"),
        task_type=task_type,
        requires_client_input=params.get("requires_client_input", False),
        anchored_entity_type=anchored_type,
        anchored_entity_id=anchored_id,
        source_type=TaskSourceType.AI_ASSISTANT,
    )

    try:
        task = await create_task(project_id, task_data)
        return {
            "success": True,
            "task_id": str(task.id),
            "message": f"Task created: \"{title}\"",
        }
    except Exception as e:
        logger.error(f"Failed to create task: {e}", exc_info=True)
        return {"error": f"Failed to create task: {str(e)}"}
