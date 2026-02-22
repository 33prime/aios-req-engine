"""Tool definition dicts for Claude chat assistant."""

from typing import Any, Dict, List


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
