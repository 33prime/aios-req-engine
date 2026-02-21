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
            "name": "list_entities",
            "description": "List all entities of a given type from the BRD. Returns names, key fields, and status. Use this when the user asks to see, review, consolidate, or compare features, personas, workflows, constraints, stakeholders, data entities, business drivers (goals/pains/KPIs), or open questions. ALWAYS use this before analyzing or consolidating entities — never say you can't see the data.",
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
                            "constraint",
                            "data_entity",
                            "question",
                            "workflow",
                            "business_driver",
                        ],
                        "description": "Type of entities to list. Use 'business_driver' for goals, pain points, and KPIs.",
                    },
                    "filter": {
                        "type": "string",
                        "enum": ["all", "mvp", "confirmed", "draft"],
                        "description": "Optional filter. 'mvp' for features only. 'confirmed' = client/consultant confirmed. 'draft' = ai_generated.",
                        "default": "all",
                    },
                    "driver_type": {
                        "type": "string",
                        "enum": ["goal", "pain", "kpi"],
                        "description": "For business_driver only: filter by driver type (goal, pain, kpi).",
                    },
                },
                "required": ["entity_type"],
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
            "name": "schedule_meeting",
            "description": "Schedule a meeting with stakeholders. Use this when the user wants to book, create, or schedule a client meeting with a specific date and time. Creates the meeting in the system and optionally links to Google Calendar.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Meeting title (e.g. 'Requirements Kickoff with Acme Corp')",
                    },
                    "meeting_date": {
                        "type": "string",
                        "description": "Meeting date in YYYY-MM-DD format",
                    },
                    "meeting_time": {
                        "type": "string",
                        "description": "Meeting start time in HH:MM format (24-hour, e.g. '14:30')",
                    },
                    "meeting_type": {
                        "type": "string",
                        "enum": ["discovery", "validation", "review", "other"],
                        "description": "Type of meeting (default: 'other')",
                        "default": "other",
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "Meeting duration in minutes (default: 60)",
                        "default": 60,
                    },
                    "description": {
                        "type": "string",
                        "description": "Meeting purpose and context (optional)",
                    },
                    "timezone": {
                        "type": "string",
                        "description": "IANA timezone (default: 'America/New_York')",
                        "default": "America/New_York",
                    },
                    "create_calendar_event": {
                        "type": "boolean",
                        "description": "If true, also creates a Google Calendar event with auto-generated Meet link. Only works if the user has Google connected.",
                        "default": False,
                    },
                    "attendee_emails": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Email addresses to add as calendar event attendees (optional)",
                    },
                },
                "required": ["title", "meeting_date", "meeting_time"],
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
            "description": "Create a new entity in the project. Supports features, personas, workflow steps, stakeholders, data entities, workflows, and business drivers (goals, pain points, KPIs). Use when the user asks to add/create something. Always confirm what was created.",
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
                            "business_driver",
                        ],
                        "description": "Type of entity to create",
                    },
                    "name": {
                        "type": "string",
                        "description": "Name/title/description of the entity",
                    },
                    "fields": {
                        "type": "object",
                        "description": "Additional fields. Feature: category, is_mvp, overview, priority_group. Persona: role, goals(array), pain_points(array). VP Step: workflow_id, step_number, actor, pain_description, benefit_description, time_minutes, automation_level. Stakeholder: stakeholder_type(champion/sponsor/blocker/influencer/end_user), email, role, organization, influence_level. Data Entity: entity_type, fields(array of {name,type,description}). Workflow: workflow_type(current/future), description. Business Driver: driver_type(goal/pain/kpi), measurement, timeframe, priority(1-5).",
                    },
                },
                "required": ["entity_type", "name"],
            },
        },
        {
            "name": "update_entity",
            "description": "Update an existing entity by ID. Supports all entity types including business drivers (goals, pain points, KPIs). Use when the user asks to change, modify, rename, or update something specific. Always confirm what was changed.",
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
                            "business_driver",
                        ],
                        "description": "Type of entity to update",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "UUID of the entity to update",
                    },
                    "fields": {
                        "type": "object",
                        "description": "Fields to update. Feature: name, category, overview, priority_group, is_mvp. Persona: name, role, goals, pain_points. VP Step: name, actor, pain_description, benefit_description, time_minutes. Stakeholder: name, stakeholder_type, email, role, influence_level. Data Entity: name, entity_type, fields. Workflow: name, description. Business Driver: description, measurement, timeframe, priority, driver_type.",
                    },
                },
                "required": ["entity_type", "entity_id", "fields"],
            },
        },
        {
            "name": "delete_entity",
            "description": "Delete an entity by ID. Supports features, personas, workflow steps, stakeholders, data entities, workflows, and business drivers (goals, pain points, KPIs). Use when the user asks to remove/delete something. Always confirm what was deleted by name.",
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
                            "business_driver",
                        ],
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "UUID of the entity to delete",
                    },
                },
                "required": ["entity_type", "entity_id"],
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
        # Knowledge & References
        {
            "name": "add_belief",
            "description": "Record a belief or knowledge — 'remember that...', 'note that the client prefers...', 'keep in mind...'. Saves to the project knowledge graph for future reference.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The belief or knowledge to remember",
                    },
                    "domain": {
                        "type": "string",
                        "enum": [
                            "client_priority",
                            "technical",
                            "market",
                            "user_need",
                            "constraint",
                        ],
                        "description": "Optional domain category for the belief",
                    },
                    "linked_entity_type": {
                        "type": "string",
                        "enum": ["feature", "persona", "vp_step", "stakeholder", "business_driver", "competitor"],
                        "description": "Optional entity type this belief is about",
                    },
                    "linked_entity_id": {
                        "type": "string",
                        "description": "Optional UUID of the linked entity",
                    },
                },
                "required": ["content"],
            },
        },
        {
            "name": "add_company_reference",
            "description": "Add a competitor or design/feature inspiration — 'add X as a competitor', 'look at Y for design inspiration'. Tracks companies and products relevant to the project.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the company or product",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to the company or product",
                    },
                    "reference_type": {
                        "type": "string",
                        "enum": ["competitor", "design_inspiration", "feature_inspiration"],
                        "description": "Type of reference (default: competitor)",
                        "default": "competitor",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about why this reference is relevant",
                    },
                },
                "required": ["name", "url"],
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
        # =================================================================
        # Solution Flow Tools
        # =================================================================
        {
            "name": "update_solution_flow_step",
            "description": "Update any field on a solution flow step (goal, information fields, questions, pattern, actors, etc.).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "string", "description": "UUID of the step to update"},
                    "title": {"type": "string"},
                    "goal": {"type": "string"},
                    "phase": {"type": "string", "enum": ["entry", "core_experience", "output", "admin"]},
                    "actors": {"type": "array", "items": {"type": "string"}},
                    "information_fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string", "enum": ["captured", "displayed", "computed"]},
                                "mock_value": {"type": "string"},
                                "confidence": {"type": "string", "enum": ["known", "inferred", "guess", "unknown"]},
                            },
                            "required": ["name", "type", "mock_value", "confidence"],
                        },
                    },
                    "mock_data_narrative": {"type": "string"},
                    "open_questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question": {"type": "string"},
                                "context": {"type": "string"},
                                "status": {"type": "string", "enum": ["open", "resolved", "escalated"]},
                                "resolved_answer": {"type": "string"},
                                "escalated_to": {"type": "string"},
                            },
                            "required": ["question"],
                        },
                    },
                    "implied_pattern": {"type": "string"},
                    "confirmation_status": {"type": "string", "enum": ["ai_generated", "confirmed_consultant", "needs_client", "confirmed_client"]},
                    "success_criteria": {"type": "array", "items": {"type": "string"}, "description": "What makes this step successful (measurable outcomes)"},
                    "pain_points_addressed": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "persona": {"type": "string"},
                            },
                            "required": ["text"],
                        },
                        "description": "Pain points this step solves, with optional persona attribution",
                    },
                    "goals_addressed": {"type": "array", "items": {"type": "string"}, "description": "Business goals this step contributes to"},
                    "ai_config": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "behaviors": {"type": "array", "items": {"type": "string"}},
                            "guardrails": {"type": "array", "items": {"type": "string"}},
                        },
                        "description": "AI behavior configuration for this step",
                    },
                },
                "required": ["step_id"],
            },
        },
        {
            "name": "add_solution_flow_step",
            "description": "Add a new step to the solution flow at a given position.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Step name"},
                    "goal": {"type": "string", "description": "What must be achieved"},
                    "phase": {"type": "string", "enum": ["entry", "core_experience", "output", "admin"]},
                    "actors": {"type": "array", "items": {"type": "string"}},
                    "step_index": {"type": "integer", "description": "Position in the flow (0-based). Omit to append."},
                    "implied_pattern": {"type": "string"},
                },
                "required": ["title", "goal", "phase"],
            },
        },
        {
            "name": "remove_solution_flow_step",
            "description": "Remove a step from the solution flow.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "string", "description": "UUID of the step to remove"},
                },
                "required": ["step_id"],
            },
        },
        {
            "name": "reorder_solution_flow_steps",
            "description": "Reorder all steps in the solution flow. Provide step IDs in the desired order.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Step UUIDs in the desired order",
                    },
                },
                "required": ["step_ids"],
            },
        },
        {
            "name": "resolve_solution_flow_question",
            "description": "Mark an open question on a solution flow step as resolved.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "string", "description": "UUID of the step"},
                    "question_text": {"type": "string", "description": "The question to resolve (exact match)"},
                    "answer": {"type": "string", "description": "The resolution answer"},
                },
                "required": ["step_id", "question_text", "answer"],
            },
        },
        {
            "name": "escalate_to_client",
            "description": "Escalate an open question from a solution flow step to the client. Creates a pending item so it appears in the client's queue. Use when the question requires client input.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "string", "description": "UUID of the solution flow step"},
                    "question_text": {"type": "string", "description": "The question to escalate (exact match)"},
                    "suggested_stakeholder": {"type": "string", "description": "Name or role of who should answer (optional)"},
                    "reason": {"type": "string", "description": "Why this needs client input (optional)"},
                },
                "required": ["step_id", "question_text"],
            },
        },
        {
            "name": "refine_solution_flow_step",
            "description": "Use AI to refine a solution flow step based on an instruction. The AI analyzes the step's context (linked entities, information fields, questions) and applies targeted changes. Only ai_generated fields will be modified; confirmed fields are preserved.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "string", "description": "UUID of the step to refine"},
                    "instruction": {"type": "string", "description": "What to refine or change about this step"},
                },
                "required": ["step_id", "instruction"],
            },
        },
        {
            "name": "get_recent_documents",
            "description": "Get recently uploaded documents for this project with their processing status. Use this when the user asks about uploads, document processing, or says 'any update'. Returns filenames, upload times, processing status (pending/processing/completed/failed), and extracted entity counts.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum documents to return (default 5)",
                        "default": 5,
                    },
                },
            },
        },
    ]


# =============================================================================
# Page-Context Tool Filtering
# =============================================================================

# Tools sent on every request regardless of page
CORE_TOOLS = {
    "get_project_status",
    "list_entities",
    "search",
    "create_entity",
    "update_entity",
    "delete_entity",
    "create_task",
    "suggest_actions",
    "add_signal",
    "create_confirmation",
    "add_belief",
    "add_company_reference",
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
    "brd:questions": {"list_pending_confirmations", "generate_client_email"},
    "overview": {
        "generate_strategic_context",
        "update_strategic_context",
        "update_project_type",
        "identify_stakeholders",
        "list_pending_confirmations",
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
    "schedule_meeting",
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
    "schedule_meeting",
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
    "create_entity", "update_entity", "delete_entity", "add_signal", "create_task",
    "create_confirmation", "attach_evidence", "generate_strategic_context",
    "update_strategic_context", "update_project_type", "identify_stakeholders",
    "respond_to_document_clarification", "add_belief", "add_company_reference",
    "update_solution_flow_step", "add_solution_flow_step",
    "remove_solution_flow_step", "reorder_solution_flow_steps",
    "resolve_solution_flow_question", "escalate_to_client",
    "refine_solution_flow_step", "schedule_meeting",
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
        elif tool_name == "list_entities":
            return await _list_entities(project_id, tool_input)
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
        elif tool_name == "schedule_meeting":
            return await _schedule_meeting(project_id, tool_input)
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
        # Document Tools
        elif tool_name == "get_recent_documents":
            return await _get_recent_documents(project_id, tool_input)
        elif tool_name == "check_document_clarifications":
            return await _check_document_clarifications(project_id, tool_input)
        elif tool_name == "respond_to_document_clarification":
            return await _respond_to_document_clarification(project_id, tool_input)
        # Unified Entity CRUD Tools (v3)
        elif tool_name == "create_entity":
            return await _create_entity(project_id, tool_input)
        elif tool_name == "update_entity":
            return await _update_entity(project_id, tool_input)
        elif tool_name == "delete_entity":
            return await _delete_entity(project_id, tool_input)
        # Research / Evolution Tools
        elif tool_name == "query_entity_history":
            return await _query_entity_history(project_id, tool_input)
        elif tool_name == "query_knowledge_graph":
            return await _query_knowledge_graph(project_id, tool_input)
        # Task Creation
        elif tool_name == "create_task":
            return await _create_task(project_id, tool_input)
        # Knowledge & References
        elif tool_name == "add_belief":
            return await _add_belief(project_id, tool_input)
        elif tool_name == "add_company_reference":
            return await _add_company_reference(project_id, tool_input)
        # Interactive Action Cards — pass-through (frontend renders)
        elif tool_name == "suggest_actions":
            return tool_input
        # Solution Flow Tools
        elif tool_name == "update_solution_flow_step":
            return await _update_solution_flow_step(project_id, tool_input)
        elif tool_name == "add_solution_flow_step":
            return await _add_solution_flow_step(project_id, tool_input)
        elif tool_name == "remove_solution_flow_step":
            return await _remove_solution_flow_step(project_id, tool_input)
        elif tool_name == "reorder_solution_flow_steps":
            return await _reorder_solution_flow_steps(project_id, tool_input)
        elif tool_name == "resolve_solution_flow_question":
            return await _resolve_solution_flow_question(project_id, tool_input)
        elif tool_name == "escalate_to_client":
            return await _escalate_to_client(project_id, tool_input)
        elif tool_name == "refine_solution_flow_step":
            return await _refine_solution_flow_step(project_id, tool_input)
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


async def _list_entities(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """List entities of a given type with key fields for chat reasoning."""
    entity_type = params.get("entity_type")
    filter_mode = params.get("filter", "all")

    if not entity_type:
        return {"error": "entity_type is required"}

    supabase = get_supabase()
    pid = str(project_id)

    try:
        if entity_type == "feature":
            rows = supabase.table("features").select(
                "id, name, overview, category, is_mvp, confirmation_status, priority_group"
            ).eq("project_id", pid).order("created_at", desc=True).execute().data or []
            if filter_mode == "mvp":
                rows = [r for r in rows if r.get("is_mvp")]
            elif filter_mode == "confirmed":
                rows = [r for r in rows if r.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")]
            elif filter_mode == "draft":
                rows = [r for r in rows if r.get("confirmation_status") == "ai_generated"]
            items = []
            for r in rows:
                overview = (r.get("overview") or "")[:150]
                items.append({
                    "id": r["id"], "name": r.get("name", "?"),
                    "overview": overview + ("..." if len(r.get("overview") or "") > 150 else ""),
                    "category": r.get("category"), "is_mvp": r.get("is_mvp"),
                    "status": r.get("confirmation_status"), "priority": r.get("priority_group"),
                })

        elif entity_type == "persona":
            rows = supabase.table("personas").select(
                "id, name, role, goals, pain_points, confirmation_status"
            ).eq("project_id", pid).order("created_at").execute().data or []
            items = []
            for r in rows:
                items.append({
                    "id": r["id"], "name": r.get("name", "?"), "role": r.get("role"),
                    "goals": (r.get("goals") or [])[:3],
                    "pain_points": (r.get("pain_points") or [])[:3],
                    "status": r.get("confirmation_status"),
                })

        elif entity_type == "vp_step":
            rows = supabase.table("vp_steps").select(
                "id, label, description, workflow_id, actor_persona_name, step_number, confirmation_status, time_minutes"
            ).eq("project_id", pid).order("step_number").execute().data or []
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:120]
                items.append({
                    "id": r["id"], "name": r.get("label", "?"),
                    "description": desc + ("..." if len(r.get("description") or "") > 120 else ""),
                    "workflow_id": r.get("workflow_id"), "actor": r.get("actor_persona_name"),
                    "step_number": r.get("step_number"), "time_min": r.get("time_minutes"),
                    "status": r.get("confirmation_status"),
                })

        elif entity_type == "stakeholder":
            rows = supabase.table("stakeholders").select(
                "id, name, stakeholder_type, role, organization, influence_level, confirmation_status, email"
            ).eq("project_id", pid).order("created_at").execute().data or []
            items = []
            for r in rows:
                items.append({
                    "id": r["id"], "name": r.get("name", "?"),
                    "type": r.get("stakeholder_type"), "role": r.get("role"),
                    "org": r.get("organization"), "influence": r.get("influence_level"),
                    "email": r.get("email"), "status": r.get("confirmation_status"),
                })

        elif entity_type == "constraint":
            rows = supabase.table("constraints").select(
                "id, title, constraint_type, severity, description, confirmation_status"
            ).eq("project_id", pid).order("created_at", desc=True).execute().data or []
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:120]
                items.append({
                    "id": r["id"], "name": r.get("title", "?"),
                    "type": r.get("constraint_type"), "severity": r.get("severity"),
                    "description": desc + ("..." if len(r.get("description") or "") > 120 else ""),
                    "status": r.get("confirmation_status"),
                })

        elif entity_type == "data_entity":
            rows = supabase.table("data_entities").select(
                "id, name, description, entity_category, confirmation_status"
            ).eq("project_id", pid).order("created_at").execute().data or []
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:120]
                items.append({
                    "id": r["id"], "name": r.get("name", "?"),
                    "category": r.get("entity_category"),
                    "description": desc + ("..." if len(r.get("description") or "") > 120 else ""),
                    "status": r.get("confirmation_status"),
                })

        elif entity_type == "question":
            rows = supabase.table("project_open_questions").select(
                "id, question, status, priority, category, suggested_owner"
            ).eq("project_id", pid).order("created_at", desc=True).execute().data or []
            items = []
            for r in rows:
                items.append({
                    "id": r["id"], "question": r.get("question", "?"),
                    "status": r.get("status"), "priority": r.get("priority"),
                    "category": r.get("category"), "owner": r.get("suggested_owner"),
                })

        elif entity_type == "workflow":
            rows = supabase.table("workflows").select(
                "id, name, workflow_type, description"
            ).eq("project_id", pid).order("created_at").execute().data or []
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:150]
                items.append({
                    "id": r["id"], "name": r.get("name", "?"),
                    "type": r.get("workflow_type"),
                    "description": desc + ("..." if len(r.get("description") or "") > 150 else ""),
                })

        elif entity_type == "business_driver":
            from app.db.business_drivers import list_business_drivers
            driver_type_filter = params.get("driver_type")  # optional: "goal", "pain", "kpi"
            rows = list_business_drivers(project_id, driver_type=driver_type_filter)
            if filter_mode == "confirmed":
                rows = [r for r in rows if r.get("confirmation_status") in ("confirmed_client", "confirmed_consultant")]
            elif filter_mode == "draft":
                rows = [r for r in rows if r.get("confirmation_status") == "ai_generated"]
            items = []
            for r in rows:
                desc = (r.get("description") or "")[:150]
                items.append({
                    "id": r["id"],
                    "description": desc + ("..." if len(r.get("description") or "") > 150 else ""),
                    "driver_type": r.get("driver_type"),
                    "priority": r.get("priority"),
                    "measurement": r.get("measurement"),
                    "timeframe": r.get("timeframe"),
                    "status": r.get("confirmation_status"),
                })

        else:
            return {"error": f"Unknown entity_type: {entity_type}"}

        return {
            "entity_type": entity_type,
            "count": len(items),
            "filter": filter_mode,
            "items": items[:50],  # Hard cap at 50
            "truncated": len(items) > 50,
        }

    except Exception as e:
        logger.error(f"list_entities error: {e}", exc_info=True)
        return {"error": str(e)}


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


async def _schedule_meeting(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Schedule a new meeting for the project, optionally creating a Google Calendar event.

    Args:
        project_id: Project UUID
        params: title, meeting_date, meeting_time, meeting_type, duration_minutes,
                description, timezone, create_calendar_event, attendee_emails
    """
    try:
        from datetime import datetime, timedelta

        from app.db.meetings import create_meeting, update_meeting

        title = params.get("title", "").strip()
        meeting_date = params.get("meeting_date", "").strip()
        meeting_time = params.get("meeting_time", "").strip()

        if not title:
            return {"success": False, "error": "Title is required", "message": "Please provide a meeting title."}
        if not meeting_date:
            return {"success": False, "error": "Date is required", "message": "Please provide a meeting date (YYYY-MM-DD)."}
        if not meeting_time:
            return {"success": False, "error": "Time is required", "message": "Please provide a meeting time (HH:MM)."}

        timezone = params.get("timezone", "America/New_York")
        duration_minutes = params.get("duration_minutes", 60)
        description = params.get("description")

        meeting = create_meeting(
            project_id=str(project_id),
            title=title,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            meeting_type=params.get("meeting_type", "other"),
            duration_minutes=duration_minutes,
            description=description,
            timezone=timezone,
        )

        if not meeting:
            return {"success": False, "error": "Failed to create meeting", "message": "Meeting creation failed."}

        meeting_id = meeting.get("id", "")
        calendar_info = ""

        # Optionally create Google Calendar event
        if params.get("create_calendar_event"):
            try:
                from app.core.google_calendar_service import create_calendar_event
                from app.db.supabase_client import get_supabase

                # Look up project owner to get their Google credentials
                supabase = get_supabase()
                project = supabase.table("projects").select("created_by").eq("id", str(project_id)).single().execute()
                user_id = project.data.get("created_by") if project.data else None

                if user_id:
                    start_dt = datetime.fromisoformat(f"{meeting_date}T{meeting_time}")
                    end_dt = start_dt + timedelta(minutes=duration_minutes)

                    cal_result = await create_calendar_event(
                        user_id=user_id,
                        title=title,
                        start_datetime=start_dt.isoformat(),
                        end_datetime=end_dt.isoformat(),
                        timezone=timezone,
                        description=description,
                        attendee_emails=params.get("attendee_emails"),
                    )

                    # Update meeting with calendar data
                    update_meeting(
                        UUID(meeting_id),
                        {
                            "google_calendar_event_id": cal_result["event_id"],
                            "google_meet_link": cal_result.get("meet_link"),
                        },
                    )
                    meet_link = cal_result.get("meet_link", "")
                    calendar_info = f" Google Calendar event created{' with Meet link' if meet_link else ''}."
                else:
                    calendar_info = " (No project owner found — calendar event skipped.)"
            except ValueError:
                calendar_info = " (Google not connected — calendar event skipped.)"
            except Exception as e:
                logger.warning(f"Calendar event creation failed: {e}")
                calendar_info = " (Calendar event creation failed — meeting still saved.)"

        return {
            "success": True,
            "meeting_id": meeting_id,
            "title": title,
            "meeting_date": meeting_date,
            "meeting_time": meeting_time,
            "google_meet_link": meeting.get("google_meet_link"),
            "message": f"Meeting scheduled: **{title}** on {meeting_date} at {meeting_time}.{calendar_info}",
        }

    except Exception as e:
        logger.error(f"Error scheduling meeting: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to schedule meeting: {str(e)}",
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


async def _get_recent_documents(
    project_id: UUID, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Get recently uploaded documents with processing status."""
    try:
        supabase = get_supabase()
        limit = params.get("limit", 5)

        # Query recent documents for this project
        response = (
            supabase.table("documents")
            .select("id, original_filename, document_class, processing_status, signal_id, created_at, metadata")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        docs = response.data or []
        results = []

        for doc in docs:
            doc_info: Dict[str, Any] = {
                "filename": doc.get("original_filename", "unknown"),
                "uploaded_at": doc.get("created_at", ""),
                "document_type": doc.get("document_class") or "pending classification",
                "processing_status": doc.get("processing_status", "unknown"),
            }

            # If document extraction is done and has a signal, check entity extraction
            if doc.get("processing_status") == "completed" and doc.get("signal_id"):
                try:
                    sig_resp = (
                        supabase.table("signals")
                        .select("processing_status, patch_summary")
                        .eq("id", doc["signal_id"])
                        .single()
                        .execute()
                    )
                    if sig_resp.data:
                        sig_status = sig_resp.data.get("processing_status", "")
                        if sig_status in ("completed", "processed"):
                            doc_info["entity_extraction"] = "completed"
                            # Parse patch summary for entity counts
                            patch = sig_resp.data.get("patch_summary") or {}
                            if isinstance(patch, str):
                                import json as _json
                                try:
                                    patch = _json.loads(patch)
                                except Exception:
                                    patch = {}
                            if patch:
                                doc_info["entities_extracted"] = patch
                        elif sig_status in ("processing", "pending"):
                            doc_info["entity_extraction"] = "processing"
                        else:
                            doc_info["entity_extraction"] = sig_status or "unknown"
                except Exception:
                    doc_info["entity_extraction"] = "unknown"
            elif doc.get("processing_status") == "completed":
                doc_info["entity_extraction"] = "not started"
            elif doc.get("processing_status") in ("pending", "processing"):
                doc_info["entity_extraction"] = "waiting for document extraction"

            results.append(doc_info)

        return {
            "documents": results,
            "total": len(results),
            "summary": (
                f"{len(results)} recent document(s). "
                + ", ".join(
                    f"{d['filename']}: {d['processing_status']}"
                    + (f" → entities {d.get('entity_extraction', 'n/a')}" if d.get("entity_extraction") else "")
                    for d in results
                )
                if results
                else "No documents uploaded yet."
            ),
        }

    except Exception as e:
        logger.error(f"Error getting recent documents: {e}", exc_info=True)
        return {"error": str(e)}


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
        elif entity_type == "business_driver":
            return await _create_business_driver_entity(project_id, name, fields)
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
        elif entity_type == "business_driver":
            return await _update_business_driver_entity(eid, project_id, fields)
        else:
            return {"success": False, "error": f"Unsupported entity type: {entity_type}"}

    except Exception as e:
        logger.error(f"Error updating {entity_type} {entity_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _delete_entity(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete any entity type by ID.

    Supports: feature, persona, vp_step, stakeholder, data_entity, workflow.
    Uses cascade delete for features and personas to clean up references.
    """
    entity_type = params.get("entity_type")
    entity_id = params.get("entity_id")

    if not entity_type or not entity_id:
        return {
            "success": False,
            "error": "entity_type and entity_id are required",
        }

    try:
        eid = UUID(entity_id)
    except (ValueError, TypeError):
        return {"success": False, "error": f"Invalid entity_id: {entity_id}"}

    try:
        supabase = get_supabase()

        if entity_type == "feature":
            from app.db.cascade import delete_feature_with_cascade
            result = delete_feature_with_cascade(eid)
            entity_name = result.get("feature_name", "Unknown")
            return {
                "success": True,
                "message": f"Deleted feature: {entity_name}",
                "entity_type": "feature",
                "entity_name": entity_name,
            }

        elif entity_type == "persona":
            from app.db.cascade import delete_persona_with_cascade
            result = delete_persona_with_cascade(eid)
            entity_name = result.get("persona_name", "Unknown")
            return {
                "success": True,
                "message": f"Deleted persona: {entity_name}",
                "entity_type": "persona",
                "entity_name": entity_name,
            }

        elif entity_type == "business_driver":
            from app.db.business_drivers import get_business_driver, delete_business_driver

            driver = get_business_driver(eid)
            if not driver:
                return {"success": False, "error": f"Business driver not found: {entity_id}"}

            entity_name = driver.get("description", "Unknown")[:80]
            driver_type = driver.get("driver_type", "driver")
            delete_business_driver(eid, project_id)

            return {
                "success": True,
                "message": f"Deleted {driver_type}: {entity_name}",
                "entity_type": "business_driver",
                "entity_name": entity_name,
            }

        elif entity_type in ("vp_step", "stakeholder", "data_entity", "workflow"):
            table_map = {
                "vp_step": ("vp_steps", "label"),
                "stakeholder": ("stakeholders", "name"),
                "data_entity": ("data_entities", "name"),
                "workflow": ("workflows", "name"),
            }
            table, name_col = table_map[entity_type]

            # Fetch name before deleting
            fetch = (
                supabase.table(table)
                .select(f"id, {name_col}")
                .eq("id", str(eid))
                .maybe_single()
                .execute()
            )
            if not fetch.data:
                return {"success": False, "error": f"{entity_type} not found: {entity_id}"}

            entity_name = fetch.data.get(name_col, "Unknown")

            supabase.table(table).delete().eq("id", str(eid)).execute()

            return {
                "success": True,
                "message": f"Deleted {entity_type}: {entity_name}",
                "entity_type": entity_type,
                "entity_name": entity_name,
            }

        else:
            return {"success": False, "error": f"Unsupported entity type: {entity_type}"}

    except Exception as e:
        logger.error(f"Error deleting {entity_type} {entity_id}: {e}", exc_info=True)
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


# --- Business Driver ---


async def _create_business_driver_entity(project_id: UUID, description: str, fields: dict) -> Dict[str, Any]:
    """Create a business driver (goal, pain point, or KPI)."""
    from app.db.business_drivers import create_business_driver

    driver_type = fields.get("driver_type", "goal")
    if driver_type not in ("goal", "pain", "kpi"):
        return {"success": False, "error": f"Invalid driver_type: {driver_type}. Must be goal, pain, or kpi."}

    driver = create_business_driver(
        project_id=project_id,
        driver_type=driver_type,
        description=description,
        measurement=fields.get("measurement"),
        timeframe=fields.get("timeframe"),
        priority=fields.get("priority", 3),
    )

    type_label = {"goal": "goal", "pain": "pain point", "kpi": "KPI"}.get(driver_type, driver_type)
    return {
        "success": True,
        "entity_type": "business_driver",
        "entity_id": driver["id"],
        "message": f"Created {type_label}: **{description[:80]}**",
    }


async def _update_business_driver_entity(entity_id: UUID, project_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a business driver (goal, pain point, or KPI)."""
    from app.db.business_drivers import update_business_driver, get_business_driver

    ALLOWED = {"description", "measurement", "timeframe", "priority", "driver_type",
               "severity", "frequency", "affected_users", "business_impact", "current_workaround",
               "goal_timeframe", "success_criteria", "dependencies", "owner",
               "baseline_value", "target_value", "measurement_method", "tracking_frequency",
               "data_source", "responsible_team"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(sorted(ALLOWED))}"}

    driver = update_business_driver(entity_id, project_id, **updates)
    if not driver:
        return {"success": False, "error": f"Business driver not found: {entity_id}"}

    changed = ", ".join(updates.keys())
    desc = driver.get("description", "")[:60]
    return {
        "success": True,
        "entity_type": "business_driver",
        "entity_id": str(entity_id),
        "message": f"Updated {driver.get('driver_type', 'driver')} **{desc}**: {changed}",
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


# =============================================================================
# Knowledge & Reference Handlers
# =============================================================================


async def _add_belief(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Record a belief/knowledge in the project knowledge graph."""
    from app.db.memory_graph import create_node

    content = params.get("content", "").strip()
    if not content:
        return {"error": "content is required"}

    domain = params.get("domain")
    linked_entity_type = params.get("linked_entity_type")
    linked_entity_id = params.get("linked_entity_id")

    summary = content[:100] + ("..." if len(content) > 100 else "")

    try:
        node = create_node(
            project_id=project_id,
            node_type="belief",
            content=content,
            summary=summary,
            confidence=0.8,
            source_type="user",
            belief_domain=domain,
            linked_entity_type=linked_entity_type,
            linked_entity_id=UUID(linked_entity_id) if linked_entity_id else None,
        )
        return {
            "success": True,
            "node_id": node.get("id"),
            "message": f"Got it, I'll remember: {summary}",
        }
    except Exception as e:
        logger.error(f"Failed to add belief: {e}", exc_info=True)
        return {"error": f"Failed to record belief: {str(e)}"}


async def _add_company_reference(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a competitor or design/feature inspiration."""
    from app.db.competitor_refs import create_competitor_ref

    name = params.get("name", "").strip()
    url = params.get("url", "").strip()
    if not name:
        return {"error": "name is required"}
    if not url:
        return {"error": "url is required"}

    reference_type = params.get("reference_type", "competitor")
    notes = params.get("notes")

    try:
        ref = create_competitor_ref(
            project_id=project_id,
            reference_type=reference_type,
            name=name,
            url=url,
            research_notes=notes,
        )
        type_labels = {
            "competitor": "competitor",
            "design_inspiration": "design inspiration",
            "feature_inspiration": "feature inspiration",
        }
        label = type_labels.get(reference_type, reference_type)
        return {
            "success": True,
            "ref_id": ref.get("id"),
            "message": f"Added {name} as a {label}.",
            "name": name,
            "url": url,
            "reference_type": reference_type,
        }
    except Exception as e:
        logger.error(f"Failed to add company reference: {e}", exc_info=True)
        return {"error": f"Failed to add reference: {str(e)}"}


# =============================================================================
# Solution Flow Tool Implementations
# =============================================================================


async def _update_solution_flow_step(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Update fields on a solution flow step."""
    from app.db.solution_flow import get_flow_step, update_flow_step

    step_id = params.pop("step_id", None)
    if not step_id:
        return {"error": "step_id is required"}
    try:
        # Capture before-state for diff
        before = get_flow_step(UUID(step_id))
        result = update_flow_step(UUID(step_id), params)

        # Build field-level diff
        changes = {}
        if before:
            for field in params:
                old_val = before.get(field)
                new_val = result.get(field)
                if old_val != new_val:
                    changes[field] = {"old": old_val, "new": new_val}

        # Record revision
        try:
            from app.db.revisions_enrichment import insert_enrichment_revision
            insert_enrichment_revision(
                project_id=project_id,
                entity_type="solution_flow_step",
                entity_id=UUID(step_id),
                entity_label=result.get("title", ""),
                revision_type="updated",
                trigger_event="chat_tool",
                changes=changes,
                diff_summary=f"Updated {', '.join(params.keys())}",
                created_by="chat_assistant",
            )
        except Exception:
            pass  # Don't fail the update if revision recording fails

        # Cross-step cascade: if substantial fields changed, flag other steps
        # that share linked entities with this step
        substantial_fields = {"goal", "information_fields", "actors"}
        if substantial_fields & set(params.keys()):
            try:
                linked_ids = []
                for key in ("linked_feature_ids", "linked_workflow_ids", "linked_data_entity_ids"):
                    linked_ids.extend(result.get(key) or [])
                if linked_ids:
                    from app.db.solution_flow import flag_steps_with_updates
                    flag_steps_with_updates(project_id, linked_ids)
            except Exception:
                pass  # Don't fail the update

        # Re-fetch full step data for optimistic update
        step_data = get_flow_step(UUID(step_id))
        return {
            "success": True,
            "step_id": step_id,
            "message": f"Updated step '{result.get('title', '')}'.",
            "updated_fields": list(params.keys()),
            "step_data": step_data,
        }
    except Exception as e:
        return {"error": str(e)}


async def _add_solution_flow_step(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a new step to the solution flow."""
    from app.db.solution_flow import create_flow_step, get_or_create_flow

    try:
        flow = get_or_create_flow(project_id)
        result = create_flow_step(UUID(flow["id"]), project_id, params)
        return {
            "success": True,
            "step_id": result["id"],
            "message": f"Added step '{result.get('title', '')}' at index {result.get('step_index', '?')}.",
            "title": result.get("title"),
            "step_index": result.get("step_index"),
        }
    except Exception as e:
        return {"error": str(e)}


async def _remove_solution_flow_step(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Remove a step from the solution flow."""
    from app.db.solution_flow import delete_flow_step, get_flow_step

    step_id = params.get("step_id")
    if not step_id:
        return {"error": "step_id is required"}
    try:
        step = get_flow_step(UUID(step_id))
        title = step.get("title", "") if step else ""
        delete_flow_step(UUID(step_id))
        return {
            "success": True,
            "message": f"Removed step '{title}'. Remaining steps reindexed.",
        }
    except Exception as e:
        return {"error": str(e)}


async def _reorder_solution_flow_steps(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Reorder steps in the solution flow."""
    from app.db.solution_flow import get_or_create_flow, reorder_flow_steps

    step_ids = params.get("step_ids", [])
    if not step_ids:
        return {"error": "step_ids is required"}
    try:
        flow = get_or_create_flow(project_id)
        result = reorder_flow_steps(UUID(flow["id"]), step_ids)
        return {
            "success": True,
            "message": f"Reordered {len(step_ids)} steps.",
            "step_count": len(result),
        }
    except Exception as e:
        return {"error": str(e)}


async def _resolve_solution_flow_question(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve an open question on a solution flow step."""
    from app.db.solution_flow import get_flow_step, update_flow_step

    step_id = params.get("step_id")
    question_text = params.get("question_text", "")
    answer = params.get("answer", "")

    if not step_id or not question_text or not answer:
        return {"error": "step_id, question_text, and answer are required"}

    try:
        step = get_flow_step(UUID(step_id))
        if not step:
            return {"error": "Step not found"}

        questions = step.get("open_questions") or []
        resolved = False
        for q in questions:
            if isinstance(q, dict) and q.get("question") == question_text:
                q["status"] = "resolved"
                q["resolved_answer"] = answer
                resolved = True
                break

        if not resolved:
            return {"error": f"Question not found: '{question_text}'"}

        update_flow_step(UUID(step_id), {"open_questions": questions})

        # Record revision
        try:
            from app.db.revisions_enrichment import insert_enrichment_revision
            insert_enrichment_revision(
                project_id=project_id,
                entity_type="solution_flow_step",
                entity_id=UUID(step_id),
                entity_label=step.get("title", ""),
                revision_type="updated",
                trigger_event="question_resolved",
                changes={"question_resolved": {"question": question_text, "answer": answer}},
                diff_summary=f"Resolved: {question_text[:80]}",
                created_by="chat_assistant",
            )
        except Exception:
            pass

        # Re-fetch full step data for optimistic update
        step_data = get_flow_step(UUID(step_id))
        return {
            "success": True,
            "message": f"Resolved question: '{question_text[:60]}...'",
            "answer": answer,
            "question_text": question_text,
            "step_data": step_data,
        }
    except Exception as e:
        return {"error": str(e)}


async def _escalate_to_client(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Escalate an open question to the client by creating a pending item."""
    from app.db.solution_flow import get_flow_step, update_flow_step

    step_id = params.get("step_id")
    question_text = params.get("question_text", "")
    suggested_stakeholder = params.get("suggested_stakeholder")
    reason = params.get("reason")

    if not step_id or not question_text:
        return {"error": "step_id and question_text are required"}

    try:
        step = get_flow_step(UUID(step_id))
        if not step:
            return {"error": "Step not found"}

        # Find and update the question status to escalated
        questions = step.get("open_questions") or []
        escalated = False
        for q in questions:
            if isinstance(q, dict) and q.get("question") == question_text:
                q["status"] = "escalated"
                q["escalated_to"] = suggested_stakeholder or "client"
                escalated = True
                break

        if not escalated:
            return {"error": f"Question not found: '{question_text}'"}

        update_flow_step(UUID(step_id), {"open_questions": questions})

        # Create pending item
        supabase = get_supabase()
        pending_row = {
            "project_id": str(project_id),
            "item_type": "open_question",
            "source": "solution_flow",
            "entity_id": step_id,
            "title": question_text,
            "why_needed": reason or f"Escalated from solution flow step: {step.get('title', '')}",
            "priority": "high",
        }
        result = supabase.table("pending_items").insert(pending_row).execute()
        pending_item_id = result.data[0]["id"] if result.data else None

        # Record revision
        try:
            from app.db.revisions_enrichment import insert_enrichment_revision
            insert_enrichment_revision(
                project_id=project_id,
                entity_type="solution_flow_step",
                entity_id=UUID(step_id),
                entity_label=step.get("title", ""),
                revision_type="updated",
                trigger_event="question_escalated",
                changes={"question_escalated": {"question": question_text, "escalated_to": suggested_stakeholder or "client"}},
                diff_summary=f"Escalated to {suggested_stakeholder or 'client'}: {question_text[:60]}",
                created_by="chat_assistant",
            )
        except Exception:
            pass

        # Re-fetch full step data for optimistic update
        step_data = get_flow_step(UUID(step_id))
        return {
            "success": True,
            "question": question_text,
            "escalated_to": suggested_stakeholder or "client",
            "pending_item_id": pending_item_id,
            "message": f"Escalated to {suggested_stakeholder or 'client'}: '{question_text[:50]}...'",
            "step_data": step_data,
        }
    except Exception as e:
        return {"error": str(e)}


async def _refine_solution_flow_step(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Refine a solution flow step using AI."""
    from app.chains.refine_solution_flow_step import refine_solution_flow_step

    step_id = params.get("step_id")
    instruction = params.get("instruction", "")

    if not step_id or not instruction:
        return {"error": "step_id and instruction are required"}

    return await refine_solution_flow_step(str(project_id), step_id, instruction)
