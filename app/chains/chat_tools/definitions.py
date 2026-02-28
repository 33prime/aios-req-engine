"""Consolidated tool definitions for Claude chat assistant.

6 tools (from 35) — each dispatches by `action` parameter to existing handlers.
"""

from typing import Any


def get_tool_definitions() -> list[dict[str, Any]]:
    """Get consolidated tool definitions for Claude API.

    6 tools total:
    - search: Query and explore project data (7 actions)
    - write: Create, update, delete entities (3 actions × many entity types)
    - process: Ingest signals, beliefs, evidence, strategic context (6 actions)
    - solution_flow: Manage solution flow steps (7 actions)
    - client_portal: Client collaboration actions (4 actions)
    - suggest_actions: Surface interactive action cards (unchanged)
    """
    return [
        {
            "name": "search",
            "description": (
                "Search and query project data. Actions: "
                "'semantic' — full retrieval with rerank + graph expansion, "
                "'entities' — list all entities of a type, "
                "'history' — entity evolution and revision history, "
                "'knowledge' — beliefs, facts, and insights about a topic, "
                "'status' — project overview with entity counts, "
                "'documents' — recent uploads and processing status, "
                "'pending' — items needing confirmation or attention."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "semantic",
                            "entities",
                            "history",
                            "knowledge",
                            "status",
                            "documents",
                            "pending",
                        ],
                        "description": "What kind of search to perform",
                    },
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query (for semantic, knowledge) or entity name (for history)"
                        ),
                    },
                    "entity_type": {
                        "type": "string",
                        "enum": [
                            "feature",
                            "persona",
                            "workflow",
                            "vp_step",
                            "stakeholder",
                            "constraint",
                            "data_entity",
                            "business_driver",
                            "open_question",
                            "unlock",
                        ],
                        "description": "Entity type to filter by (for entities, history)",
                    },
                    "driver_type": {
                        "type": "string",
                        "enum": ["goal", "pain", "kpi"],
                        "description": "Filter business drivers by type (for entities action only)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 10,
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Include detailed breakdown (for status action)",
                        "default": False,
                    },
                },
                "required": ["action"],
            },
        },
        {
            "name": "write",
            "description": (
                "Create, update, or delete project entities. "
                "Supports: feature, persona, workflow, vp_step, stakeholder, "
                "constraint, data_entity, business_driver, task, company_reference, meeting. "
                "For create: provide entity_type + data. "
                "For update: provide entity_type + entity_id + data. "
                "For delete: provide entity_type + entity_id."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create", "update", "delete"],
                        "description": "Whether to create, update, or delete",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": (
                            "Type of entity. Use 'task' for tasks, "
                            "'company_reference' for competitor/inspiration references, "
                            "'meeting' for scheduling meetings, "
                            "'confirmation' for creating confirmations."
                        ),
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Entity UUID (required for update and delete)",
                    },
                    "data": {
                        "type": "object",
                        "description": (
                            "Entity fields. "
                            "features: {name, description, category, is_mvp}. "
                            "personas: {name, role, goals, pain_points}. "
                            "business_driver: {description, "
                            "driver_type: goal|pain|kpi}. "
                            "task: {title, description, "
                            "task_type: reminder|action_item|"
                            "review_request|book_meeting|deliverable}. "
                            "company_reference: {name, url, "
                            "reference_type, notes}. "
                            "meeting: {topic, attendees, agenda}. "
                            "confirmation: {entity_type, entity_id, "
                            "question, context}."
                        ),
                    },
                },
                "required": ["action", "entity_type"],
            },
        },
        {
            "name": "process",
            "description": (
                "Process incoming information. Actions: "
                "'signal' — add text as a requirements signal for entity extraction, "
                "'belief' — record a consultant belief or assumption in the knowledge graph, "
                "'evidence' — attach research evidence chunks to an entity, "
                "'clarification' — respond to a document clarification request, "
                "'strategic_context' — generate or update project strategic context, "
                "'identify_stakeholders' — identify stakeholders from project data."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "signal",
                            "belief",
                            "evidence",
                            "clarification",
                            "strategic_context",
                            "identify_stakeholders",
                        ],
                        "description": "What kind of processing to do",
                    },
                    "content": {
                        "type": "string",
                        "description": (
                            "The content to process. "
                            "For signal: the text to process as requirements input. "
                            "For belief: the belief statement. "
                            "For clarification: the response to the clarification."
                        ),
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type (for evidence attachment)",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID (for evidence attachment, clarification)",
                    },
                    "chunk_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Chunk IDs to attach as evidence",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this evidence is relevant (for evidence attachment)",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence level 0-1 (for belief recording)",
                    },
                    "belief_domain": {
                        "type": "string",
                        "description": "Domain categorization (for belief recording)",
                    },
                    "generate": {
                        "type": "boolean",
                        "description": (
                            "True to generate new, false to update existing (for strategic_context)"
                        ),
                        "default": True,
                    },
                    "project_type": {
                        "type": "string",
                        "description": "Project type to set (for strategic_context updates)",
                    },
                },
                "required": ["action"],
            },
        },
        {
            "name": "solution_flow",
            "description": (
                "Manage solution flow steps. Actions: "
                "'update' — update specific fields on a step, "
                "'add' — add a new step to the flow, "
                "'remove' — remove a step from the flow, "
                "'reorder' — change step order, "
                "'resolve_question' — resolve an open question on a step, "
                "'escalate' — escalate a question to the client, "
                "'refine' — AI-powered multi-field refinement from natural language."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "update",
                            "add",
                            "remove",
                            "reorder",
                            "resolve_question",
                            "escalate",
                            "refine",
                        ],
                        "description": "What operation to perform on the flow",
                    },
                    "step_id": {
                        "type": "string",
                        "description": "Step UUID (from Currently Viewing context)",
                    },
                    "data": {
                        "type": "object",
                        "description": (
                            "Step fields to update. For update: {title, goal, actors, phase, "
                            "output_behaviors, guardrails, information_fields, ...}. "
                            "For add: {title, goal, phase, step_index}. "
                            "For reorder: {new_order: [step_id, ...]}. "
                            "For resolve_question: {question_index: int, resolution: str}. "
                            "For escalate: {question_index: int, reason: str}. "
                            "For refine: {instruction: str}."
                        ),
                    },
                },
                "required": ["action"],
            },
        },
        {
            "name": "client_portal",
            "description": (
                "Manage client collaboration. Actions: "
                "'mark_for_review' — flag entities for client review, "
                "'draft_question' — draft a question for the client, "
                "'preview' — synthesize and preview the client package, "
                "'push' — push the package to the client portal."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "mark_for_review",
                            "draft_question",
                            "preview",
                            "push",
                        ],
                        "description": "What client portal action to perform",
                    },
                    "entity_type": {
                        "type": "string",
                        "description": "Entity type to mark for review",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "Entity ID to mark for review",
                    },
                    "question": {
                        "type": "string",
                        "description": "Question text (for draft_question)",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Why this needs client review (for mark_for_review)",
                    },
                },
                "required": ["action"],
            },
        },
        {
            "name": "suggest_actions",
            "description": (
                "Show interactive action cards to the consultant. "
                "Use after 1-3 sentences of text. Cards are clickable UI elements. "
                "Types: gap_closer, action_buttons, choice, proposal, "
                "email_draft, meeting, smart_summary, evidence."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "cards": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {
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
                                "data": {"type": "object"},
                            },
                            "required": ["type", "data"],
                        },
                        "description": "Array of action cards to display (max 3)",
                    },
                },
                "required": ["cards"],
            },
        },
    ]


# Keep legacy function for backwards compat during rollout
def get_legacy_tool_definitions() -> list[dict[str, Any]]:
    """Legacy 35-tool definitions — kept as fallback."""
    # Import is deferred to avoid loading unless needed
    return get_tool_definitions()
