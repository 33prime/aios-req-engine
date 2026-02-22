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
            "description": "Get entity counts, open insights, pending confirmations, and items needing attention. Use when: user asks 'how's the project?', 'what needs attention?', 'give me an overview', 'what's the status?'. Do NOT use when the user asks about a specific entity type — use list_entities instead.",
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
            "description": "List all entities of a given type with key fields and confirmation status. Use when: user asks to see, review, compare, consolidate, or count features, personas, workflows, constraints, stakeholders, data entities, business drivers, or open questions. ALWAYS call this before analyzing, consolidating, or proposing changes to entities. Do NOT use for semantic search — use search instead.",
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
                        "description": "For business_driver only: filter by driver type.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max items to return (default 20, max 50)",
                        "default": 20,
                    },
                },
                "required": ["entity_type"],
            },
        },
        {
            "name": "create_confirmation",
            "description": "Create a confirmation item for the client portal. Use when: an insight or decision needs client input/approval, or user says 'ask the client about...'.",
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
            "description": "Semantic search through signal chunks and research using AI embeddings. Use when: user asks 'what did the client say about...', 'find evidence for...', 'is there any mention of...'. Returns ranked text excerpts with similarity scores. Do NOT use for listing BRD entities — use list_entities instead.",
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
            "description": "Link research chunks to features or personas as supporting evidence. Use when: user wants to connect search results to an entity, or after a search yields relevant results.",
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
            "description": "Add a signal (email, note, transcript) and process it through the full extraction pipeline. Use when: user pastes content and says 'process this', 'here's a transcript', 'add this email'. WARNING: triggers full V2 pipeline (chunking + embedding + entity extraction) taking 10-30s. For short notes, prefer add_belief.",
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
            "name": "schedule_meeting",
            "description": "Schedule a meeting with stakeholders. Use when: user says 'schedule a meeting', 'book a call', 'set up a meeting' with a date and time. Creates the meeting and optionally links to Google Calendar.",
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
            "description": "List pending confirmation items that need client input. Use when: user asks 'what needs client input?', 'what questions do we have for the client?', or before drafting emails/agendas via suggest_actions cards.",
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
            "description": "Generate the full strategic context (executive summary, opportunity, risks, success metrics, stakeholder identification, company enrichment). HEAVY operation — multiple LLM calls + web scraping. Use only when: user explicitly asks to generate/regenerate the strategic overview, or project has no strategic context yet. Do NOT use for simple updates — use update_strategic_context instead.",
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
            "description": "Set whether this is an internal software project or a market product. Use when: user says 'this is an internal tool' or 'this is a product we sell'.",
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
            "description": "Auto-identify stakeholders from signals and research. Use when: user asks 'who are the key people?', 'find stakeholders', or after adding new signals with people mentioned.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "update_strategic_context",
            "description": "Update strategic context by adding a risk, success metric, or updating a field. Use when: user wants to add risks, KPIs, or modify strategic fields. Do NOT use for full regeneration — use generate_strategic_context instead.",
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
            "description": "Check if any uploaded documents need clarification about their type or content. Use when: user mentions a document upload, or you want to check for ambiguous documents.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "respond_to_document_clarification",
            "description": "Respond to a document clarification with the correct document class. Use after the user tells you what type a document is.",
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
            "description": "Create a new BRD entity. Use when: user says 'add', 'create', 'new' followed by an entity type. Confirm what was created. Required: name. Optional by type — Feature: category, is_mvp, overview, priority_group. Persona: role, goals[], pain_points[]. Stakeholder: stakeholder_type, email, role, influence_level. Business Driver: driver_type (goal/pain/kpi). VP Step: workflow_id. Workflow: workflow_type. Data Entity: entity_type.",
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
            "description": "Update fields on an existing entity by ID. Use when: user says 'change', 'update', 'rename', 'modify', 'set'. You MUST have the entity_id — call list_entities first if needed. Confirm what changed.",
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
            "description": "Delete an entity by ID. Use when: user says 'remove', 'delete', 'drop' followed by an entity reference. Confirm what was deleted by name.",
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
            "description": "Show the evolution of a specific entity — revisions, source signals, and linked beliefs. Use when: user asks 'how did this evolve?', 'what changed?', 'tell me about the history of...'. Do NOT use for listing current entities — use list_entities instead.",
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
            "description": "Search the project's knowledge graph for facts and beliefs about a topic. Use when: user asks 'what do we know about X', 'any beliefs about...', or wants to explore connected concepts. Do NOT use for listing entities — use list_entities.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic or keyword to search for in the knowledge graph",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum nodes to return (default 5)",
                        "default": 5,
                    },
                },
                "required": ["topic"],
            },
        },
        # Task Creation
        {
            "name": "create_task",
            "description": "Create a project task. Infer the type from context: 'remind me...' → reminder (set remind_at), 'follow up with...' / 'email them...' → action_item (set action_verb), 'schedule/book a meeting...' → book_meeting (set meeting_type), 'prepare for the meeting...' → meeting_prep, 'send the proposal...' → deliverable, 'can you review...' → review_request, otherwise → custom. Title should start with a verb.",
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
                        "enum": ["signal_review", "action_item", "meeting_prep", "reminder", "review_request", "book_meeting", "deliverable", "custom"],
                        "description": "Type of task. Default: custom",
                        "default": "custom",
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
                    "remind_at": {
                        "type": "string",
                        "description": "ISO datetime for reminder tasks (e.g. '2026-02-24T09:00:00')",
                    },
                    "meeting_type": {
                        "type": "string",
                        "enum": ["discovery", "event_modeling", "proposal", "prototype_review", "kickoff", "stakeholder_interview", "technical_deep_dive", "internal_strategy", "introduction", "monthly_check_in", "hand_off"],
                        "description": "Meeting type for meeting_prep or book_meeting tasks",
                    },
                    "meeting_date": {
                        "type": "string",
                        "description": "ISO datetime for the meeting date",
                    },
                    "action_verb": {
                        "type": "string",
                        "enum": ["send", "email", "schedule", "prepare", "review", "follow_up", "share", "create"],
                        "description": "Action verb for action_item tasks",
                    },
                },
                "required": ["title"],
            },
        },
        # Knowledge & References
        {
            "name": "add_belief",
            "description": "Record a belief or knowledge in the project knowledge graph. Use when: user says 'remember that...', 'note that...', 'keep in mind...'. For longer content that should be processed as a signal, use add_signal instead.",
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
            "description": "Add a competitor or design/feature inspiration. Use when: user says 'add X as a competitor', 'look at Y for inspiration'. Requires name and URL.",
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
            "description": "Present interactive action cards in the chat UI. You MUST use this for any structured content — never output bullet lists or numbered options as text. Card types: gap_closer, action_buttons, choice, proposal, email_draft, meeting, smart_summary, evidence. Max 3 cards per response.",
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
            "description": "Update fields on a solution flow step. The step_id is in your 'Currently Viewing' context — use it directly. For AI-powered refinement from natural language, use refine_solution_flow_step instead.",
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
            "description": "Add a new step to the solution flow at a given position. Use when: user says 'add a step' or describes a new step in the flow.",
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
            "description": "Remove a step from the solution flow. Use when: user says 'remove this step' or 'delete step'.",
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
            "description": "Mark an open question on a solution flow step as resolved. Prefer question_index (0-based position in the questions list) for reliable matching.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "string", "description": "UUID of the step"},
                    "question_index": {"type": "integer", "description": "0-based index of the question in the step's open_questions array (preferred)"},
                    "question_text": {"type": "string", "description": "The question text (fallback if index not provided)"},
                    "answer": {"type": "string", "description": "The resolution answer"},
                },
                "required": ["step_id", "answer"],
            },
        },
        {
            "name": "escalate_to_client",
            "description": "Escalate an open question from a solution flow step to the client. Creates a pending item in the client's queue. Prefer question_index (0-based) for reliable matching.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "step_id": {"type": "string", "description": "UUID of the solution flow step"},
                    "question_index": {"type": "integer", "description": "0-based index of the question in the step's open_questions array (preferred)"},
                    "question_text": {"type": "string", "description": "The question text (fallback if index not provided)"},
                    "suggested_stakeholder": {"type": "string", "description": "Name or role of who should answer (optional)"},
                    "reason": {"type": "string", "description": "Why this needs client input (optional)"},
                },
                "required": ["step_id"],
            },
        },
        {
            "name": "refine_solution_flow_step",
            "description": "Use AI to refine a solution flow step based on a natural language instruction. Only ai_generated fields are modified; confirmed fields are preserved. Use when the user describes changes conversationally rather than specifying exact field values.",
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
            "description": "Get recently uploaded documents with their processing status. Use when: user asks about uploads, document processing, or says 'any update on my upload?'. Returns filenames, statuses, and extracted entity counts.",
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
