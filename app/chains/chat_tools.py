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
        # NOTE: list_insights tool REMOVED - deprecated in favor of proposal system
        {
            "name": "search_research",
            "description": "Search through research data, evidence chunks, and competitive analysis. Use this when the user asks about research, evidence, competitors, market data, or studies.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text",
                    },
                    "chunk_type": {
                        "type": "string",
                        "enum": ["all", "competitive", "market", "user_research", "technical"],
                        "description": "Type of research chunks to search (optional)",
                        "default": "all",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
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
            "name": "list_pending_proposals",
            "description": "List all pending proposals awaiting review. Shows what changes are queued from signal processing. Use this when the user asks about pending changes, proposals, or what needs review.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "include_changes": {
                        "type": "boolean",
                        "description": "Include detailed change list for each proposal",
                        "default": False,
                    },
                },
            },
        },
        # NOTE: apply_patch and dismiss_insight tools REMOVED - deprecated in favor of proposal system
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
        # NOTE: bulk_apply_patches tool REMOVED - deprecated in favor of proposal system
        {
            "name": "request_confirmation",
            "description": "Request user confirmation before performing a destructive or impactful action. Use this to ensure the user wants to proceed with bulk operations, deletions, or major changes.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Brief description of the action requiring confirmation",
                    },
                    "details": {
                        "type": "string",
                        "description": "Detailed explanation of what will happen",
                    },
                    "impact": {
                        "type": "object",
                        "description": "Summary of impact (e.g., number of items affected)",
                    },
                },
                "required": ["action", "details"],
            },
        },
        {
            "name": "create_signal_from_chat",
            "description": "Create a signal (audit record) from this chat conversation. Use this to document important decisions, insights, or context discovered during the conversation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "signal_type": {
                        "type": "string",
                        "enum": ["note", "decision", "insight"],
                        "description": "Type of signal to create",
                    },
                    "title": {
                        "type": "string",
                        "description": "Title for the signal",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content extracted from conversation",
                    },
                    "context": {
                        "type": "string",
                        "description": "Additional context about this signal",
                    },
                },
                "required": ["signal_type", "title", "content"],
            },
        },
        {
            "name": "propose_features",
            "description": "Generate a batch proposal for new or updated features with evidence from research. Returns a proposal ID for preview/apply. Use this when the user wants to add or update features in a batch with intelligent context and evidence.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "What the user wants (e.g., 'add dark mode support', 'update authentication features')",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["new_features", "update_existing", "both"],
                        "description": "Scope of changes to propose",
                        "default": "new_features",
                    },
                    "include_evidence": {
                        "type": "boolean",
                        "description": "Whether to search research for supporting evidence",
                        "default": True,
                    },
                    "count_hint": {
                        "type": "integer",
                        "description": "Approximate number of features to propose (1-10)",
                    },
                },
                "required": ["intent"],
            },
        },
        {
            "name": "preview_proposal",
            "description": "Show a detailed preview of a batch proposal with before/after comparisons and evidence. Use this to let the user review a proposal before applying it.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "proposal_id": {
                        "type": "string",
                        "description": "UUID of the proposal to preview",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["summary", "detailed", "diff"],
                        "description": "Level of detail in the preview",
                        "default": "summary",
                    },
                },
                "required": ["proposal_id"],
            },
        },
        {
            "name": "apply_proposal",
            "description": "Apply a batch proposal atomically, updating all entities as specified. Use this after the user has previewed and approved a proposal. IMPORTANT: For proposals with >3 changes, require confirmation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "proposal_id": {
                        "type": "string",
                        "description": "UUID of the proposal to apply",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "description": "User has confirmed this action (required for >3 changes)",
                        "default": False,
                    },
                },
                "required": ["proposal_id"],
            },
        },
        {
            "name": "analyze_gaps",
            "description": "Analyze the project for gaps in evidence, personas, features, or VP coverage. Use this to identify what's missing or needs attention in the prototype.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "gap_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["evidence", "personas", "features", "vp_steps", "confirmations"],
                        },
                        "description": "Types of gaps to analyze",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["all", "mvp", "critical"],
                        "description": "Scope of analysis",
                        "default": "mvp",
                    },
                },
            },
        },
        # NOTE: assess_readiness tool REMOVED - deprecated in favor of proposal system
        {
            "name": "semantic_search_research",
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
            "description": "Link research chunks to features, PRD sections, or Value Path steps as supporting evidence. Use this to strengthen decisions with research backing and create audit trail.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["feature", "prd_section", "vp_step"],
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
            "name": "find_evidence_gaps",
            "description": "Find entities that lack research evidence backing. Use this to identify decisions that need more research support or validation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["feature", "prd_section", "vp_step"],
                        },
                        "description": "Types of entities to check (defaults to all)",
                    },
                    "mvp_only": {
                        "type": "boolean",
                        "description": "Only check MVP features (default true)",
                        "default": True,
                    },
                    "suggest_queries": {
                        "type": "boolean",
                        "description": "Generate suggested search queries for gaps",
                        "default": True,
                    },
                },
            },
        },
        {
            "name": "orchestrate_agent",
            "description": "Queue an agent to run in the background with optional scope filtering. Returns job ID immediately - use get_agent_status to check progress. Agents: red_team (finds issues), a_team (generates patches), research (gathers data).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "enum": ["red_team", "a_team", "research"],
                        "description": "Type of agent to run",
                    },
                    "scope": {
                        "type": "object",
                        "description": "Optional scope to limit agent execution",
                        "properties": {
                            "feature_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Limit to specific feature UUIDs",
                            },
                            "prd_section_slugs": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Limit to specific PRD section slugs",
                            },
                            "categories": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Limit to feature categories (e.g., 'Core', 'Security')",
                            },
                            "mvp_only": {
                                "type": "boolean",
                                "description": "Only process MVP features",
                            },
                        },
                    },
                    "include_research": {
                        "type": "boolean",
                        "description": "Include research context (for red_team)",
                        "default": True,
                    },
                },
                "required": ["agent_type"],
            },
        },
        {
            "name": "get_agent_status",
            "description": "Check the status of a running or completed agent job. Returns status (queued/processing/completed/failed), output, and progress information.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "UUID of the agent job to check",
                    },
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "get_creative_brief",
            "description": "Get the creative brief status for research. Shows client name, industry, website, competitors, and completeness. Use this to check what info is needed before running research.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "update_creative_brief",
            "description": "Update the creative brief with client information for research. Use this to save client name, industry, website, competitors, focus areas, or custom questions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "client_name": {
                        "type": "string",
                        "description": "Name of the client company",
                    },
                    "industry": {
                        "type": "string",
                        "description": "Industry/vertical of the client",
                    },
                    "website": {
                        "type": "string",
                        "description": "Client website URL",
                    },
                    "competitors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Competitor names to add (appends to existing)",
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Focus areas for research (appends to existing)",
                    },
                    "custom_questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Custom research questions (appends to existing)",
                    },
                },
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
        {
            "name": "enrich_features",
            "description": "Enrich features with detailed mini-spec information. This adds consultant-friendly details: overview, who uses it (target personas), user actions, system behaviors, UI requirements, business rules, and integrations. Use this when the user asks to enrich features, add feature details, or create mini-specs.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "feature_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific feature UUIDs to enrich (optional - if empty, enriches all unenriched features)",
                    },
                    "include_research": {
                        "type": "boolean",
                        "description": "Include research signals in context (default: false)",
                        "default": False,
                    },
                },
            },
        },
        {
            "name": "enrich_personas",
            "description": "Enrich personas with detailed profiles and key workflows. This adds: detailed overview of who the persona is, and key workflows showing how they use features together. Use this when the user asks to enrich personas, add persona details, or create workflow documentation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "persona_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific persona UUIDs to enrich (optional - if empty, enriches all unenriched personas)",
                    },
                },
            },
        },
        {
            "name": "generate_value_path",
            "description": "Generate or regenerate the Value Path - the 'golden path' narrative showing how the product creates value through a sequence of steps. This creates a consultant-friendly demo script with user narratives, system behaviors, evidence, and value created at each step. Use this when the user asks to create the value path, regenerate VP, or wants a demo script.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "preserve_consultant_edits": {
                        "type": "boolean",
                        "description": "Whether to preserve steps that consultants have manually edited (default: true)",
                        "default": True,
                    },
                },
            },
        },
        {
            "name": "process_vp_changes",
            "description": "Process pending changes in the VP change queue. This determines whether to do surgical updates (if <50% of steps affected) or full regeneration (if >=50% affected). Use this after making changes to features/personas to update the Value Path.",
            "input_schema": {
                "type": "object",
                "properties": {},
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
            "name": "get_strategic_context",
            "description": "Get the current strategic context for the project including executive summary, opportunity, risks, investment case, metrics, and constraints. Use this when the user asks about the business case, strategic overview, or project context.",
            "input_schema": {
                "type": "object",
                "properties": {},
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
            "name": "add_stakeholder",
            "description": "Add a stakeholder to the project. IMPORTANT: Before calling this tool, ask the user for any missing required information (name, role/title, and stakeholder type). If the user says 'add John as a stakeholder', ask: 'What is John's role/title, and what type of stakeholder are they (champion, sponsor, blocker, influencer, or end user)?'",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Stakeholder's full name (required)",
                    },
                    "role": {
                        "type": "string",
                        "description": "Job title or role (e.g., 'VP of Engineering', 'Product Manager') - ask if not provided",
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address for the stakeholder",
                    },
                    "organization": {
                        "type": "string",
                        "description": "Company or department",
                    },
                    "stakeholder_type": {
                        "type": "string",
                        "enum": ["champion", "sponsor", "blocker", "influencer", "end_user"],
                        "description": "Type of stakeholder (required): champion (internal advocate pushing for this), sponsor (decision maker with budget), blocker (has concerns/opposition), influencer (opinion leader), end_user (actual user of the software)",
                    },
                    "influence_level": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Level of influence on project decisions",
                        "default": "medium",
                    },
                    "priorities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "What matters to this stakeholder",
                    },
                    "concerns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Their worries or objections",
                    },
                },
                "required": ["name", "stakeholder_type"],
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
            "name": "list_stakeholders",
            "description": "List all stakeholders for the project grouped by type (champions, sponsors, blockers, influencers, end users).",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "add_risk",
            "description": "Add a business, technical, compliance, or competitive risk to the strategic context.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["business", "technical", "compliance", "competitive"],
                        "description": "Risk category",
                    },
                    "description": {
                        "type": "string",
                        "description": "Clear description of the risk",
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Severity level",
                    },
                    "mitigation": {
                        "type": "string",
                        "description": "Suggested mitigation strategy (optional)",
                    },
                },
                "required": ["category", "description", "severity"],
            },
        },
        {
            "name": "add_success_metric",
            "description": "Add a success metric or KPI to the strategic context.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "What to measure",
                    },
                    "target": {
                        "type": "string",
                        "description": "Target value",
                    },
                    "current": {
                        "type": "string",
                        "description": "Current value if known (optional)",
                    },
                },
                "required": ["metric", "target"],
            },
        },
        # Entity Cascade Tools
        {
            "name": "analyze_impact",
            "description": "Before making a change to a persona, feature, or VP step, analyze what other entities would be affected. Shows direct and indirect impacts with recommendations.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["persona", "feature", "vp_step"],
                        "description": "Type of entity to analyze",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "UUID of the entity",
                    },
                    "proposed_change": {
                        "type": "string",
                        "description": "Description of what would change (optional)",
                    },
                },
                "required": ["entity_type", "entity_id"],
            },
        },
        {
            "name": "get_stale_entities",
            "description": "Show all entities that are marked as stale and need review or regeneration. Use when user asks what needs updating or refreshing.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["all", "persona", "feature", "vp_step", "strategic_context"],
                        "description": "Filter by entity type (optional)",
                        "default": "all",
                    },
                },
            },
        },
        {
            "name": "refresh_stale_entity",
            "description": "Regenerate or update a stale entity based on its current dependencies. Use when user wants to refresh or update a specific stale entity.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["persona", "feature", "vp_step", "strategic_context"],
                        "description": "Type of entity to refresh",
                    },
                    "entity_id": {
                        "type": "string",
                        "description": "UUID of the entity to refresh",
                    },
                },
                "required": ["entity_type", "entity_id"],
            },
        },
        {
            "name": "link_strategic_context",
            "description": "Link a strategic context element (risk, success metric) to source entities (features, VP steps, personas). Creates traceability.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["risk", "success_metric", "stakeholder"],
                        "description": "Section of strategic context to link",
                    },
                    "index": {
                        "type": "integer",
                        "description": "Index of the item in the array (0-based)",
                    },
                    "linked_entity_type": {
                        "type": "string",
                        "enum": ["feature", "vp_step", "persona"],
                        "description": "Type of entities to link",
                    },
                    "linked_entity_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "UUIDs of entities to link",
                    },
                },
                "required": ["section", "index", "linked_entity_type", "linked_entity_ids"],
            },
        },
        {
            "name": "rebuild_dependencies",
            "description": "Rebuild the entity dependency graph for the project. Use when relationships seem out of sync or after bulk imports.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "process_cascades",
            "description": "Process pending entity changes and propagate staleness. Usually runs automatically but can be triggered manually.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "auto_only": {
                        "type": "boolean",
                        "description": "Only process auto cascades (default: true)",
                        "default": True,
                    },
                },
            },
        },
    ]


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

        if tool_name == "search_research":
            return await _search_research(project_id, tool_input)
        elif tool_name == "get_project_status":
            return await _get_project_status(project_id, tool_input)
        elif tool_name == "list_pending_proposals":
            return await _list_pending_proposals(project_id, tool_input)
        elif tool_name == "create_confirmation":
            return await _create_confirmation(project_id, tool_input)
        elif tool_name == "request_confirmation":
            return await _request_confirmation(project_id, tool_input)
        elif tool_name == "create_signal_from_chat":
            return await _create_signal_from_chat(project_id, tool_input)
        elif tool_name == "propose_features":
            return await _propose_features(project_id, tool_input)
        elif tool_name == "preview_proposal":
            return await _preview_proposal(project_id, tool_input)
        elif tool_name == "apply_proposal":
            return await _apply_proposal(project_id, tool_input)
        elif tool_name == "analyze_gaps":
            return await _analyze_gaps(project_id, tool_input)
        elif tool_name == "semantic_search_research":
            return await _semantic_search_research(project_id, tool_input)
        elif tool_name == "attach_evidence":
            return await _attach_evidence(project_id, tool_input)
        elif tool_name == "find_evidence_gaps":
            return await _find_evidence_gaps(project_id, tool_input)
        elif tool_name == "orchestrate_agent":
            return await _orchestrate_agent(project_id, tool_input)
        elif tool_name == "get_agent_status":
            return await _get_agent_status(project_id, tool_input)
        elif tool_name == "get_creative_brief":
            return await _get_creative_brief(project_id, tool_input)
        elif tool_name == "update_creative_brief":
            return await _update_creative_brief(project_id, tool_input)
        elif tool_name == "add_signal":
            return await _add_signal(project_id, tool_input)
        elif tool_name == "generate_client_email":
            return await _generate_client_email(project_id, tool_input)
        elif tool_name == "generate_meeting_agenda":
            return await _generate_meeting_agenda(project_id, tool_input)
        elif tool_name == "list_pending_confirmations":
            return await _list_pending_confirmations(project_id, tool_input)
        elif tool_name == "enrich_features":
            return await _enrich_features(project_id, tool_input)
        elif tool_name == "enrich_personas":
            return await _enrich_personas(project_id, tool_input)
        elif tool_name == "generate_value_path":
            return await _generate_value_path(project_id, tool_input)
        elif tool_name == "process_vp_changes":
            return await _process_vp_changes(project_id, tool_input)
        # Strategic Context Tools
        elif tool_name == "generate_strategic_context":
            return await _generate_strategic_context(project_id, tool_input)
        elif tool_name == "get_strategic_context":
            return await _get_strategic_context(project_id, tool_input)
        elif tool_name == "update_project_type":
            return await _update_project_type(project_id, tool_input)
        elif tool_name == "add_stakeholder":
            return await _add_stakeholder(project_id, tool_input)
        elif tool_name == "identify_stakeholders":
            return await _identify_stakeholders(project_id, tool_input)
        elif tool_name == "list_stakeholders":
            return await _list_stakeholders(project_id, tool_input)
        elif tool_name == "add_risk":
            return await _add_risk(project_id, tool_input)
        elif tool_name == "add_success_metric":
            return await _add_success_metric(project_id, tool_input)
        # Entity Cascade Tools
        elif tool_name == "analyze_impact":
            return await _analyze_impact(project_id, tool_input)
        elif tool_name == "get_stale_entities":
            return await _get_stale_entities(project_id, tool_input)
        elif tool_name == "refresh_stale_entity":
            return await _refresh_stale_entity(project_id, tool_input)
        elif tool_name == "link_strategic_context":
            return await _link_strategic_context(project_id, tool_input)
        elif tool_name == "rebuild_dependencies":
            return await _rebuild_dependencies(project_id, tool_input)
        elif tool_name == "process_cascades":
            return await _process_cascades(project_id, tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
        return {"error": str(e)}


async def _search_research(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Search research chunks.

    Args:
        project_id: Project UUID
        params: Search parameters

    Returns:
        Matching research chunks
    """
    supabase = get_supabase()

    query_text = params.get("query", "")
    chunk_type = params.get("chunk_type", "all")
    limit = params.get("limit", 5)

    # First get signals for this project (signal_chunks doesn't have project_id)
    signals_response = supabase.table("signals").select("id").eq("project_id", str(project_id)).execute()
    signal_ids = [s["id"] for s in (signals_response.data or [])]

    if not signal_ids:
        return {
            "count": 0,
            "chunks": [],
            "query": query_text,
            "message": f"No signals found for project",
        }

    # Build query - search in content using ilike for case-insensitive match
    query = supabase.table("signal_chunks").select("*").in_("signal_id", signal_ids)

    # Text search in content field
    query = query.ilike("content", f"%{query_text}%")

    # Execute with limit
    response = query.order("created_at", desc=True).limit(limit).execute()

    chunks = response.data or []

    # Format for readability
    formatted = []
    for chunk in chunks:
        content = chunk.get("content", "")
        formatted.append(
            {
                "id": chunk["id"],
                "type": chunk.get("chunk_type", "unknown"),
                "text": content[:200] + "..." if len(content) > 200 else content,
                "full_text": content,
                "source_url": chunk.get("source_url"),
                "created_at": chunk["created_at"],
            }
        )

    return {
        "count": len(formatted),
        "chunks": formatted,
        "query": query_text,
        "message": f"Found {len(formatted)} research chunks matching '{query_text}'",
    }


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
    prd_response = supabase.table("prd_sections").select("id", count="exact").eq("project_id", str(project_id)).execute()

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
            "prd_sections": prd_response.count or 0,
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

    status["message"] = f"Project has {status['counts']['prd_sections']} PRD sections, {status['counts']['features']} features, {status['counts']['vp_steps']} VP steps"

    return status


async def _list_pending_proposals(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List pending proposals for review.

    Args:
        project_id: Project UUID
        params: Parameters including include_changes

    Returns:
        List of pending proposals with summary
    """
    supabase = get_supabase()
    include_changes = params.get("include_changes", False)

    try:
        # Fetch pending proposals
        query = (
            supabase.table("batch_proposals")
            .select("id, title, description, proposal_type, status, changes, creates_count, updates_count, deletes_count, created_at")
            .eq("project_id", str(project_id))
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(10)
        )
        response = query.execute()

        proposals = response.data or []

        if not proposals:
            return {
                "count": 0,
                "proposals": [],
                "message": "No pending proposals. Add a signal to generate proposals.",
            }

        # Build summary
        summary = {
            "count": len(proposals),
            "proposals": [],
        }

        total_creates = 0
        total_updates = 0

        for p in proposals:
            proposal_summary = {
                "id": p["id"],
                "title": p.get("title", "Untitled"),
                "type": p.get("proposal_type", "mixed"),
                "creates": p.get("creates_count", 0),
                "updates": p.get("updates_count", 0),
                "created_at": p.get("created_at"),
            }

            total_creates += p.get("creates_count", 0)
            total_updates += p.get("updates_count", 0)

            # Include detailed changes if requested
            if include_changes and p.get("changes"):
                changes = p["changes"] if isinstance(p["changes"], list) else []
                proposal_summary["changes"] = [
                    {
                        "entity_type": c.get("entity_type"),
                        "operation": c.get("operation"),
                        "name": c.get("entity_name") or c.get("after", {}).get("name") or c.get("after", {}).get("title"),
                    }
                    for c in changes[:10]  # Limit to first 10 changes
                ]

            summary["proposals"].append(proposal_summary)

        summary["total_creates"] = total_creates
        summary["total_updates"] = total_updates
        summary["message"] = f"Found {len(proposals)} pending proposal(s) with {total_creates} new items and {total_updates} updates. Say 'show proposal <id>' to review details or 'apply proposal <id>' to apply."

        return summary

    except Exception as e:
        logger.error(f"Failed to list pending proposals: {e}", exc_info=True)
        return {
            "count": 0,
            "proposals": [],
            "message": f"Error fetching proposals: {str(e)}",
            "error": str(e),
        }


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


async def _request_confirmation(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Request user confirmation for an action.

    This is a meta-tool that returns a structured confirmation request
    for the LLM to present to the user.

    Args:
        project_id: Project UUID
        params: Confirmation parameters

    Returns:
        Confirmation request structure
    """
    action = params.get("action")
    details = params.get("details")
    impact = params.get("impact", {})

    return {
        "requires_confirmation": True,
        "action": action,
        "details": details,
        "impact": impact,
        "message": f"⚠️ Confirmation required for: {action}",
        "instruction": "Please respond with 'yes' or 'confirm' to proceed, or 'no' or 'cancel' to abort.",
    }


async def _create_signal_from_chat(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a signal (audit record) from chat conversation.

    Args:
        project_id: Project UUID
        params: Signal parameters

    Returns:
        Created signal
    """
    import uuid as uuid_module
    supabase = get_supabase()

    signal_type = params.get("signal_type", "note")
    title = params.get("title", "Chat Note")
    content = params.get("content")
    context = params.get("context", "")

    if not content:
        return {"error": "content is required"}

    try:
        # Create signal record using correct column names
        # Format: title + content as raw_text since signals table uses raw_text
        raw_text = f"# {title}\n\n{content}"
        run_id = str(uuid_module.uuid4())

        signal_data = {
            "project_id": str(project_id),
            "signal_type": signal_type,
            "source": "chat_assistant",
            "raw_text": raw_text,
            "metadata": {"title": title, "source": "chat_assistant", "context": context},
            "run_id": run_id,
        }

        response = supabase.table("signals").insert(signal_data).execute()

        if response.data:
            signal = response.data[0]
            return {
                "success": True,
                "signal_id": signal["id"],
                "message": f"Created {signal_type} signal: {title}",
                "signal": signal,
            }
        else:
            return {"success": False, "error": "Failed to create signal"}

    except Exception as e:
        return {"success": False, "error": str(e), "message": f"Failed to create signal: {str(e)}"}


# =======================
# Batch Proposal Tools
# =======================


async def _propose_features(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a batch proposal for features with evidence.

    Args:
        project_id: Project UUID
        params: Proposal parameters

    Returns:
        Created proposal with summary and complexity assessment
    """
    from app.chains.proposal_generator import generate_feature_proposal, assess_proposal_complexity

    intent = params.get("intent")
    scope = params.get("scope", "new_features")
    include_evidence = params.get("include_evidence", True)
    count_hint = params.get("count_hint")

    if not intent:
        return {"error": "intent is required"}

    try:
        # Generate proposal
        proposal = await generate_feature_proposal(
            project_id=project_id,
            intent=intent,
            scope=scope,
            include_evidence=include_evidence,
            count_hint=count_hint,
        )

        # Build response
        changes_count = len(proposal.get("changes", []))

        # Assess complexity for smart auto-apply logic
        complexity = assess_proposal_complexity(proposal)

        response = {
            "success": True,
            "proposal_id": proposal["id"],
            "title": proposal["title"],
            "description": proposal.get("description"),
            "proposal_type": proposal["proposal_type"],
            "creates_count": proposal.get("creates_count", 0),
            "updates_count": proposal.get("updates_count", 0),
            "deletes_count": proposal.get("deletes_count", 0),
            "total_changes": changes_count,
            "complexity": complexity,
            "message": f"✅ Generated proposal: {proposal['title']} ({changes_count} changes)",
        }

        # Always require user to review and apply from the UI
        # Never auto-apply - proposals stay pending for user review
        response["next_step"] = f"Proposal staged for review. User can apply from the Patches tab in the UI."
        response["auto_apply_recommended"] = False

        return response

    except Exception as e:
        logger.error(f"Error generating proposal: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"Failed to generate proposal: {str(e)}"}


async def _preview_proposal(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Preview a batch proposal with detailed changes.

    Args:
        project_id: Project UUID
        params: Preview parameters

    Returns:
        Proposal preview with formatted changes
    """
    from app.db.proposals import get_proposal

    proposal_id = params.get("proposal_id")
    format_type = params.get("format", "summary")

    if not proposal_id:
        return {"error": "proposal_id is required"}

    try:
        # Get proposal
        proposal = get_proposal(UUID(proposal_id))

        if not proposal:
            return {"error": f"Proposal {proposal_id} not found"}

        # Build preview based on format
        if format_type == "summary":
            # High-level summary
            preview = {
                "proposal_id": proposal["id"],
                "title": proposal["title"],
                "description": proposal.get("description"),
                "status": proposal["status"],
                "creates": proposal.get("creates_count", 0),
                "updates": proposal.get("updates_count", 0),
                "deletes": proposal.get("deletes_count", 0),
                "total_changes": len(proposal.get("changes", [])),
            }

            # Group changes by type
            changes_by_type = {}
            for change in proposal.get("changes", []):
                entity_type = change.get("entity_type", "unknown")
                if entity_type not in changes_by_type:
                    changes_by_type[entity_type] = []
                changes_by_type[entity_type].append({
                    "operation": change.get("operation"),
                    "summary": _summarize_change(change),
                    "has_evidence": len(change.get("evidence", [])) > 0,
                })

            preview["changes_by_type"] = changes_by_type

            return {
                "success": True,
                "preview": preview,
                "message": f"Proposal: {proposal['title']} ({len(proposal.get('changes', []))} changes)",
                "next_step": f"Use apply_proposal with proposal_id={proposal_id} to apply",
            }

        elif format_type == "detailed":
            # Detailed view with all changes
            changes_detailed = []
            for i, change in enumerate(proposal.get("changes", []), 1):
                changes_detailed.append({
                    "index": i,
                    "entity_type": change.get("entity_type"),
                    "operation": change.get("operation"),
                    "entity_id": change.get("entity_id"),
                    "before": change.get("before"),
                    "after": change.get("after"),
                    "evidence_count": len(change.get("evidence", [])),
                    "rationale": change.get("rationale"),
                })

            return {
                "success": True,
                "proposal_id": proposal["id"],
                "title": proposal["title"],
                "changes": changes_detailed,
                "message": f"Detailed view: {len(changes_detailed)} changes",
            }

        elif format_type == "diff":
            # Diff view focusing on before/after
            diffs = []
            for i, change in enumerate(proposal.get("changes", []), 1):
                diff_entry = {
                    "index": i,
                    "operation": change.get("operation"),
                    "entity_type": change.get("entity_type"),
                }

                if change.get("operation") == "create":
                    diff_entry["after"] = change.get("after")
                elif change.get("operation") == "update":
                    diff_entry["before"] = change.get("before")
                    diff_entry["after"] = change.get("after")
                    # Calculate what changed
                    before = change.get("before", {})
                    after = change.get("after", {})
                    changed_fields = []
                    for key in after.keys():
                        if before.get(key) != after.get(key):
                            changed_fields.append(key)
                    diff_entry["changed_fields"] = changed_fields
                elif change.get("operation") == "delete":
                    diff_entry["before"] = change.get("before")

                diffs.append(diff_entry)

            return {
                "success": True,
                "proposal_id": proposal["id"],
                "diffs": diffs,
                "message": f"Diff view: {len(diffs)} changes",
            }

        else:
            return {"error": f"Invalid format: {format_type}"}

    except Exception as e:
        logger.error(f"Error previewing proposal: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"Failed to preview proposal: {str(e)}"}


async def _apply_proposal(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a batch proposal atomically.

    Args:
        project_id: Project UUID
        params: Apply parameters

    Returns:
        Application result
    """
    from app.db.proposals import apply_proposal, get_proposal, mark_previewed

    proposal_id = params.get("proposal_id")
    confirmed = params.get("confirmed", False)

    if not proposal_id:
        return {"error": "proposal_id is required"}

    try:
        # Get proposal
        proposal = get_proposal(UUID(proposal_id))

        if not proposal:
            return {"error": f"Proposal {proposal_id} not found"}

        # Check if confirmation is needed
        changes_count = len(proposal.get("changes", []))
        if changes_count > 3 and not confirmed:
            return {
                "success": False,
                "error": "Confirmation required",
                "message": f"This proposal has {changes_count} changes. Please confirm before applying.",
                "requires_confirmation": True,
                "changes_count": changes_count,
            }

        # Mark as previewed if not already
        if proposal["status"] == "pending":
            mark_previewed(UUID(proposal_id))

        # Apply proposal
        updated_proposal = apply_proposal(UUID(proposal_id), applied_by="chat_assistant")

        return {
            "success": True,
            "proposal_id": updated_proposal["id"],
            "status": updated_proposal["status"],
            "applied_at": updated_proposal.get("applied_at"),
            "message": f"✅ Applied proposal: {updated_proposal['title']} ({changes_count} changes)",
            "creates": updated_proposal.get("creates_count", 0),
            "updates": updated_proposal.get("updates_count", 0),
            "deletes": updated_proposal.get("deletes_count", 0),
        }

    except ValueError as e:
        # Validation error
        return {"success": False, "error": str(e), "message": f"Cannot apply proposal: {str(e)}"}
    except Exception as e:
        logger.error(f"Error applying proposal: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"Failed to apply proposal: {str(e)}"}


async def _analyze_gaps(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze project for gaps in evidence, personas, features, or VP coverage.

    Args:
        project_id: Project UUID
        params: Gap analysis parameters

    Returns:
        Gap analysis results
    """
    from app.db.features import list_features
    from app.db.personas import list_personas
    from app.db.prd import list_prd_sections
    from app.db.vp import list_vp_steps

    gap_types = params.get("gap_types", ["evidence", "personas", "features", "vp_steps"])
    scope = params.get("scope", "mvp")

    try:
        gaps = {}

        # Analyze evidence gaps
        if "evidence" in gap_types:
            features = list_features(project_id)
            prd_sections = list_prd_sections(project_id)
            vp_steps = list_vp_steps(project_id)

            # Filter by scope
            if scope == "mvp":
                features = [f for f in features if f.get("is_mvp")]

            # Count entities without evidence
            features_without_evidence = [
                f["name"] for f in features if not f.get("evidence") or len(f["evidence"]) == 0
            ]
            prd_without_evidence = [
                s["label"] for s in prd_sections if not s.get("evidence") or len(s["evidence"]) == 0
            ]
            vp_without_evidence = [
                f"Step {s['step_index']}" for s in vp_steps if not s.get("evidence") or len(s["evidence"]) == 0
            ]

            gaps["evidence"] = {
                "features_count": len(features_without_evidence),
                "features": features_without_evidence[:5],  # Show first 5
                "prd_sections_count": len(prd_without_evidence),
                "prd_sections": prd_without_evidence[:5],
                "vp_steps_count": len(vp_without_evidence),
                "vp_steps": vp_without_evidence[:5],
                "message": f"{len(features_without_evidence)} features, {len(prd_without_evidence)} PRD sections, and {len(vp_without_evidence)} VP steps lack evidence",
            }

        # Analyze persona gaps
        if "personas" in gap_types:
            personas = list_personas(project_id)

            if len(personas) == 0:
                gaps["personas"] = {
                    "count": 0,
                    "message": "No personas defined - critical gap for understanding users",
                    "severity": "critical",
                }
            elif len(personas) < 2:
                gaps["personas"] = {
                    "count": len(personas),
                    "message": "Only 1 persona defined - consider adding more for comprehensive coverage",
                    "severity": "important",
                }
            else:
                # Check for incomplete personas
                incomplete = []
                for persona in personas:
                    missing_fields = []
                    if not persona.get("demographics"):
                        missing_fields.append("demographics")
                    if not persona.get("psychographics"):
                        missing_fields.append("psychographics")
                    if not persona.get("goals") or len(persona["goals"]) == 0:
                        missing_fields.append("goals")
                    if not persona.get("pain_points") or len(persona["pain_points"]) == 0:
                        missing_fields.append("pain_points")

                    if missing_fields:
                        incomplete.append({
                            "name": persona["name"],
                            "missing": missing_fields,
                        })

                gaps["personas"] = {
                    "total_count": len(personas),
                    "incomplete_count": len(incomplete),
                    "incomplete": incomplete[:5],
                    "message": f"{len(incomplete)} personas have missing details" if incomplete else "All personas are complete",
                    "severity": "minor" if incomplete else "ok",
                }

        # Analyze feature gaps
        if "features" in gap_types:
            features = list_features(project_id)
            mvp_features = [f for f in features if f.get("is_mvp")]

            if len(features) == 0:
                gaps["features"] = {
                    "count": 0,
                    "message": "No features defined - critical gap",
                    "severity": "critical",
                }
            elif len(mvp_features) == 0:
                gaps["features"] = {
                    "total_count": len(features),
                    "mvp_count": 0,
                    "message": "Features exist but none marked as MVP",
                    "severity": "important",
                }
            else:
                # Check confidence distribution
                low_confidence = [f for f in mvp_features if f.get("confidence") == "low"]

                gaps["features"] = {
                    "total_count": len(features),
                    "mvp_count": len(mvp_features),
                    "low_confidence_count": len(low_confidence),
                    "low_confidence": [f["name"] for f in low_confidence[:5]],
                    "message": f"{len(low_confidence)} MVP features have low confidence" if low_confidence else "All MVP features have medium-high confidence",
                    "severity": "minor" if low_confidence else "ok",
                }

        # Analyze VP step gaps
        if "vp_steps" in gap_types:
            vp_steps = list_vp_steps(project_id)

            if len(vp_steps) == 0:
                gaps["vp_steps"] = {
                    "count": 0,
                    "message": "No Value Path steps defined - critical gap",
                    "severity": "critical",
                }
            elif len(vp_steps) < 3:
                gaps["vp_steps"] = {
                    "count": len(vp_steps),
                    "message": f"Only {len(vp_steps)} VP steps - workflows typically need 3-7 steps",
                    "severity": "important",
                }
            else:
                # Check for incomplete steps
                incomplete = []
                for step in vp_steps:
                    missing_fields = []
                    if not step.get("description"):
                        missing_fields.append("description")
                    if not step.get("user_benefit_pain"):
                        missing_fields.append("user_benefit_pain")
                    if not step.get("value_created"):
                        missing_fields.append("value_created")

                    if missing_fields:
                        incomplete.append({
                            "label": step["label"],
                            "missing": missing_fields,
                        })

                gaps["vp_steps"] = {
                    "total_count": len(vp_steps),
                    "incomplete_count": len(incomplete),
                    "incomplete": incomplete[:5],
                    "message": f"{len(incomplete)} VP steps have missing details" if incomplete else "All VP steps are complete",
                    "severity": "minor" if incomplete else "ok",
                }

        # Analyze confirmation gaps
        if "confirmations" in gap_types:
            supabase = get_supabase()
            response = (
                supabase.table("confirmation_items")
                .select("id, ask, status")
                .eq("project_id", str(project_id))
                .eq("status", "open")
                .execute()
            )

            open_confirmations = response.data or []

            gaps["confirmations"] = {
                "open_count": len(open_confirmations),
                "confirmations": [c.get("ask") for c in open_confirmations[:5]],
                "message": f"{len(open_confirmations)} open confirmations need client input" if open_confirmations else "No pending confirmations",
                "severity": "important" if len(open_confirmations) > 5 else "minor" if open_confirmations else "ok",
            }

        # Calculate overall severity
        severities = [gap.get("severity", "ok") for gap in gaps.values()]
        overall_severity = "ok"
        if "critical" in severities:
            overall_severity = "critical"
        elif "important" in severities:
            overall_severity = "important"
        elif "minor" in severities:
            overall_severity = "minor"

        return {
            "success": True,
            "gaps": gaps,
            "overall_severity": overall_severity,
            "message": f"Gap analysis complete: {len(gaps)} categories analyzed",
            "scope": scope,
        }

    except Exception as e:
        logger.error(f"Error analyzing gaps: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"Failed to analyze gaps: {str(e)}"}


async def _semantic_search_research(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
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
            "prd_section": "prd_sections",
            "vp_step": "vp_steps",
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


async def _find_evidence_gaps(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find entities lacking research evidence.

    Args:
        project_id: Project UUID
        params: Tool parameters (entity_types, mvp_only, suggest_queries)

    Returns:
        Entities with missing evidence and suggested queries
    """
    try:
        supabase = get_supabase()

        entity_types = params.get("entity_types", ["feature", "prd_section", "vp_step"])
        mvp_only = params.get("mvp_only", True)
        suggest_queries = params.get("suggest_queries", True)

        gaps = {}

        # Check features
        if "feature" in entity_types:
            query = supabase.table("features").select("*").eq("project_id", str(project_id))
            if mvp_only:
                query = query.eq("is_mvp", True)

            features_response = query.execute()
            features = features_response.data or []

            features_without_evidence = []
            for feature in features:
                evidence = feature.get("evidence", [])
                if not evidence or len(evidence) == 0:
                    features_without_evidence.append({
                        "id": feature["id"],
                        "name": feature.get("name", "Untitled"),
                        "category": feature.get("category", "Unknown"),
                        "suggested_query": f"{feature.get('name', '')} {feature.get('category', '')}" if suggest_queries else None,
                    })

            gaps["features"] = {
                "count": len(features_without_evidence),
                "items": features_without_evidence[:10],  # Limit to 10
                "message": f"{len(features_without_evidence)} features lack evidence",
            }

        # Check PRD sections
        if "prd_section" in entity_types:
            prd_response = supabase.table("prd_sections").select("*").eq("project_id", str(project_id)).execute()
            prd_sections = prd_response.data or []

            prd_without_evidence = []
            for section in prd_sections:
                evidence = section.get("evidence", [])
                if not evidence or len(evidence) == 0:
                    prd_without_evidence.append({
                        "id": section["id"],
                        "label": section.get("label", "Untitled"),
                        "slug": section.get("slug", ""),
                        "suggested_query": f"{section.get('label', '')} requirements" if suggest_queries else None,
                    })

            gaps["prd_sections"] = {
                "count": len(prd_without_evidence),
                "items": prd_without_evidence[:10],
                "message": f"{len(prd_without_evidence)} PRD sections lack evidence",
            }

        # Check VP steps
        if "vp_step" in entity_types:
            vp_response = supabase.table("vp_steps").select("*").eq("project_id", str(project_id)).execute()
            vp_steps = vp_response.data or []

            vp_without_evidence = []
            for step in vp_steps:
                evidence = step.get("evidence", [])
                if not evidence or len(evidence) == 0:
                    vp_without_evidence.append({
                        "id": step["id"],
                        "label": step.get("label", "Untitled"),
                        "step_index": step.get("step_index", 0),
                        "suggested_query": f"{step.get('label', '')} user flow" if suggest_queries else None,
                    })

            gaps["vp_steps"] = {
                "count": len(vp_without_evidence),
                "items": vp_without_evidence[:10],
                "message": f"{len(vp_without_evidence)} Value Path steps lack evidence",
            }

        # Calculate totals
        total_gaps = sum(gap["count"] for gap in gaps.values())

        return {
            "success": True,
            "total_gaps": total_gaps,
            "gaps": gaps,
            "message": f"Found {total_gaps} entities without research evidence",
            "mvp_only": mvp_only,
        }

    except Exception as e:
        logger.error(f"Error finding evidence gaps: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to find evidence gaps: {str(e)}",
        }


async def _orchestrate_agent(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Queue an agent to run in background with optional scope.

    Args:
        project_id: Project UUID
        params: Tool parameters (agent_type, scope, include_research)

    Returns:
        Job information with job_id for tracking
    """
    try:
        import uuid
        from app.db.jobs import create_job, start_job

        agent_type = params["agent_type"]
        scope = params.get("scope")
        include_research = params.get("include_research", True)

        run_id = uuid.uuid4()

        # Create job input
        job_input = {"include_research": include_research}
        if scope:
            job_input["scope"] = scope

        # Create and start job
        job_id = create_job(
            project_id=project_id,
            job_type=agent_type,
            input_json=job_input,
            run_id=run_id,
        )
        start_job(job_id)

        # Queue the background task
        # Note: red_team and a_team agents have been removed
        # Research and other agents can be added here as needed
        if agent_type in ["red_team", "a_team"]:
            return {
                "success": False,
                "error": f"{agent_type} agent has been removed",
                "message": "Use add_signal for processing client data instead",
            }
        elif agent_type == "research":
            # Research agent not implemented yet
            return {
                "success": False,
                "error": "Research agent not yet implemented",
            }

        logger.info(f"Queued {agent_type} agent: job_id={job_id}")

        return {
            "success": True,
            "agent_type": agent_type,
            "job_id": str(job_id),
            "run_id": str(run_id),
            "status": "queued",
            "message": f"{agent_type.replace('_', ' ').title()} agent queued - use get_agent_status to check progress",
            "scope": scope if scope else "full project",
        }

    except Exception as e:
        logger.error(f"Error orchestrating agent: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to queue agent: {str(e)}",
        }


async def _get_agent_status(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get status of a running or completed agent job.

    Args:
        project_id: Project UUID
        params: Tool parameters (job_id)

    Returns:
        Job status, output, and progress information
    """
    try:
        from app.db.jobs import get_job

        job_id_str = params["job_id"]
        job_id = UUID(job_id_str)

        job = get_job(job_id)

        if not job:
            return {
                "success": False,
                "error": "Job not found",
                "message": f"No job found with ID: {job_id_str}",
            }

        # Format response
        response = {
            "success": True,
            "job_id": str(job["id"]),
            "agent_type": job.get("job_type", "unknown"),
            "status": job.get("status", "unknown"),
            "created_at": job.get("created_at"),
            "started_at": job.get("started_at"),
            "completed_at": job.get("completed_at"),
        }

        # Add output if completed
        if job.get("status") == "completed":
            output = job.get("output_json", {})
            response["output"] = output
            response["message"] = "Agent completed successfully"

            # Format specific outputs
            if job.get("job_type") == "red_team":
                response["insights_count"] = output.get("insights_count", 0)
                response["by_severity"] = output.get("by_severity", {})
            elif job.get("job_type") == "a_team":
                response["patches_count"] = output.get("patches_count", 0)

        elif job.get("status") == "failed":
            response["error"] = job.get("error")
            response["message"] = f"Agent failed: {job.get('error', 'Unknown error')}"

        elif job.get("status") == "processing":
            response["message"] = "Agent is currently running..."

        else:  # queued
            response["message"] = "Agent is queued and will start soon"

        return response

    except ValueError as e:
        return {
            "success": False,
            "error": "Invalid job ID format",
            "message": f"Job ID must be a valid UUID: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Error getting agent status: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get agent status: {str(e)}",
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


# =======================
# Creative Brief Tools
# =======================


async def _get_creative_brief(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the creative brief status for research.

    Args:
        project_id: Project UUID
        params: Tool parameters (none required)

    Returns:
        Creative brief with completeness status
    """
    try:
        from app.db.creative_briefs import get_creative_brief, is_brief_complete

        brief = get_creative_brief(project_id)

        if not brief:
            return {
                "success": True,
                "exists": False,
                "is_complete": False,
                "missing_fields": ["client_name", "industry"],
                "completeness_score": 0.0,
                "message": "No creative brief yet. To run research, I need the client name and industry.",
            }

        is_complete, missing = is_brief_complete(project_id)

        response = {
            "success": True,
            "exists": True,
            "is_complete": is_complete,
            "missing_fields": missing,
            "completeness_score": brief.get("completeness_score", 0.0),
            "client_name": brief.get("client_name"),
            "industry": brief.get("industry"),
            "website": brief.get("website"),
            "competitors": brief.get("competitors", []),
            "focus_areas": brief.get("focus_areas", []),
            "custom_questions": brief.get("custom_questions", []),
        }

        if is_complete:
            response["message"] = "Creative brief is complete. Ready for research!"
        else:
            response["message"] = f"Creative brief needs: {', '.join(missing)}"

        return response

    except Exception as e:
        logger.error(f"Error getting creative brief: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get creative brief: {str(e)}",
        }


async def _update_creative_brief(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update the creative brief with client information.

    Args:
        project_id: Project UUID
        params: Fields to update (client_name, industry, website, competitors, etc.)

    Returns:
        Updated creative brief with completeness status
    """
    try:
        from app.db.creative_briefs import upsert_creative_brief, is_brief_complete

        # Build update data from provided params
        update_data = {}
        updated_fields = []

        if "client_name" in params and params["client_name"]:
            update_data["client_name"] = params["client_name"]
            updated_fields.append("client_name")

        if "industry" in params and params["industry"]:
            update_data["industry"] = params["industry"]
            updated_fields.append("industry")

        if "website" in params and params["website"]:
            update_data["website"] = params["website"]
            updated_fields.append("website")

        if "competitors" in params and params["competitors"]:
            update_data["competitors"] = params["competitors"]
            updated_fields.append("competitors")

        if "focus_areas" in params and params["focus_areas"]:
            update_data["focus_areas"] = params["focus_areas"]
            updated_fields.append("focus_areas")

        if "custom_questions" in params and params["custom_questions"]:
            update_data["custom_questions"] = params["custom_questions"]
            updated_fields.append("custom_questions")

        if not update_data:
            return {
                "success": False,
                "error": "No fields to update",
                "message": "Please provide at least one field to update (client_name, industry, website, competitors, focus_areas, or custom_questions)",
            }

        # Upsert the brief
        updated_brief = upsert_creative_brief(
            project_id=project_id,
            data=update_data,
            source="user",
        )

        # Check completeness
        is_complete, missing = is_brief_complete(project_id)

        response = {
            "success": True,
            "updated_fields": updated_fields,
            "is_complete": is_complete,
            "missing_fields": missing,
            "completeness_score": updated_brief.get("completeness_score", 0.0),
            "client_name": updated_brief.get("client_name"),
            "industry": updated_brief.get("industry"),
            "website": updated_brief.get("website"),
        }

        if is_complete:
            response["message"] = f"Updated {', '.join(updated_fields)}. Creative brief is now complete - ready for research!"
        else:
            response["message"] = f"Updated {', '.join(updated_fields)}. Still need: {', '.join(missing)}"

        return response

    except Exception as e:
        logger.error(f"Error updating creative brief: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to update creative brief: {str(e)}",
        }


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

        # Create signal record
        signal_data = {
            "project_id": str(project_id),
            "signal_type": signal_type,
            "source": source,
            "raw_text": content,
            "metadata": {
                "source": source,
                "added_via": "chat_assistant",
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

        # Process through the new unified pipeline if requested
        if process_immediately:
            try:
                from app.core.signal_pipeline import process_signal

                logger.info(f"Processing signal {signal_id} through new unified pipeline")

                # Run the new unified pipeline
                pipeline_result = await process_signal(
                    project_id=project_id,
                    signal_id=UUID(signal_id),
                    run_id=UUID(run_id),
                    signal_content=content,
                    signal_type=signal_type,
                    signal_metadata={"source": source, "added_via": "chat_assistant"},
                )

                if pipeline_result.get("success"):
                    result["processed"] = True
                    result["pipeline"] = pipeline_result.get("pipeline", "standard")

                    # Build result message based on pipeline type
                    if result["pipeline"] == "bulk":
                        proposal_id = pipeline_result.get("proposal_id")
                        total_changes = pipeline_result.get("total_changes", 0)
                        if proposal_id:
                            result["proposal_id"] = proposal_id
                            result["total_changes"] = total_changes
                            result["message"] = f"Heavyweight signal processed. Created bulk proposal with {total_changes} changes for review."
                        else:
                            result["message"] = f"Heavyweight signal processed but no changes detected."
                    else:
                        # Standard pipeline results
                        features = pipeline_result.get("features_created", 0)
                        personas = pipeline_result.get("personas_created", 0)
                        vp_steps = pipeline_result.get("vp_steps_created", 0)
                        result["features_created"] = features
                        result["personas_created"] = personas
                        result["vp_steps_created"] = vp_steps
                        result["message"] = f"Created {signal_type} signal and processed: {features} features, {personas} personas, {vp_steps} VP steps"

                    # Include classification info
                    if pipeline_result.get("classification"):
                        result["classification"] = pipeline_result["classification"]

                else:
                    result["processed"] = False
                    result["pipeline_error"] = pipeline_result.get("error", "Unknown error")
                    result["message"] = f"Created {signal_type} signal but processing failed: {result['pipeline_error']}"

            except Exception as pipeline_error:
                logger.warning(f"Pipeline processing failed: {pipeline_error}")
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


async def _enrich_features(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich features with consultant-friendly mini-spec details.

    Args:
        project_id: Project UUID
        params: Enrichment parameters

    Returns:
        Enrichment results
    """
    try:
        from app.chains.enrich_features_v2 import enrich_and_save_features

        feature_ids_raw = params.get("feature_ids", [])
        include_research = params.get("include_research", False)

        # Convert string IDs to UUIDs
        feature_ids = [UUID(fid) for fid in feature_ids_raw] if feature_ids_raw else None

        # Run enrichment
        result = enrich_and_save_features(
            project_id=project_id,
            feature_ids=feature_ids,
            include_research=include_research,
        )

        enriched_count = result.get("enriched_count", 0)
        enriched_names = result.get("enriched_features", [])

        if enriched_count == 0:
            return {
                "success": True,
                "enriched_count": 0,
                "message": "✅ All features are already enriched! No features needed enrichment.",
            }

        # Build success message
        message_parts = [f"✅ Successfully enriched {enriched_count} feature(s):"]
        for name in enriched_names[:10]:
            message_parts.append(f"  • {name}")
        if len(enriched_names) > 10:
            message_parts.append(f"  ... and {len(enriched_names) - 10} more")

        message_parts.append("\nEach feature now has:")
        message_parts.append("  • Overview (business description)")
        message_parts.append("  • Target personas")
        message_parts.append("  • User actions")
        message_parts.append("  • System behaviors")
        message_parts.append("  • UI requirements")
        message_parts.append("  • Business rules")
        message_parts.append("  • Integrations")

        return {
            "success": True,
            "enriched_count": enriched_count,
            "enriched_features": enriched_names,
            "message": "\n".join(message_parts),
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"No features to enrich: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Error enriching features: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to enrich features: {str(e)}",
        }


async def _enrich_personas(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enrich personas with detailed profiles and key workflows.

    Args:
        project_id: Project UUID
        params: Enrichment parameters

    Returns:
        Enrichment results
    """
    try:
        from app.chains.enrich_personas_v2 import enrich_and_save_personas

        persona_ids_raw = params.get("persona_ids", [])

        # Convert string IDs to UUIDs
        persona_ids = [UUID(pid) for pid in persona_ids_raw] if persona_ids_raw else None

        # Run enrichment
        result = enrich_and_save_personas(
            project_id=project_id,
            persona_ids=persona_ids,
        )

        enriched_count = result.get("enriched_count", 0)
        enriched_names = result.get("enriched_personas", [])

        if enriched_count == 0:
            return {
                "success": True,
                "enriched_count": 0,
                "message": "✅ All personas are already enriched! No personas needed enrichment.",
            }

        # Build success message
        message_parts = [f"✅ Successfully enriched {enriched_count} persona(s):"]
        for name in enriched_names[:10]:
            message_parts.append(f"  • {name}")
        if len(enriched_names) > 10:
            message_parts.append(f"  ... and {len(enriched_names) - 10} more")

        message_parts.append("\nEach persona now has:")
        message_parts.append("  • Detailed overview")
        message_parts.append("  • Key workflows with steps and features used")

        return {
            "success": True,
            "enriched_count": enriched_count,
            "enriched_personas": enriched_names,
            "message": "\n".join(message_parts),
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"No personas to enrich: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Error enriching personas: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to enrich personas: {str(e)}",
        }


async def _generate_value_path(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate or regenerate the Value Path.

    Args:
        project_id: Project UUID
        params: Generation parameters

    Returns:
        Generation results
    """
    try:
        from app.chains.generate_value_path_v2 import generate_and_save_value_path

        preserve_consultant_edits = params.get("preserve_consultant_edits", True)

        # Run generation
        result = generate_and_save_value_path(
            project_id=project_id,
            preserve_consultant_edited=preserve_consultant_edits,
        )

        steps_generated = result.get("steps_generated", 0)
        steps_created = result.get("steps_created", 0)
        steps_updated = result.get("steps_updated", 0)
        steps_preserved = result.get("steps_preserved", 0)
        gaps = result.get("gaps_identified", [])
        summary = result.get("generation_summary", "")

        # Build success message
        message_parts = [f"✅ Generated Value Path with {steps_generated} steps:"]
        message_parts.append(f"  • {steps_created} new steps created")
        message_parts.append(f"  • {steps_updated} existing steps updated")
        if steps_preserved > 0:
            message_parts.append(f"  • {steps_preserved} consultant-edited steps preserved")

        if summary:
            message_parts.append(f"\n**Summary**: {summary}")

        if gaps:
            message_parts.append("\n**Gaps identified**:")
            for gap in gaps[:5]:
                message_parts.append(f"  ⚠️ {gap}")
            if len(gaps) > 5:
                message_parts.append(f"  ... and {len(gaps) - 5} more")

        return {
            "success": True,
            "steps_generated": steps_generated,
            "steps_created": steps_created,
            "steps_updated": steps_updated,
            "steps_preserved": steps_preserved,
            "gaps_identified": gaps,
            "message": "\n".join(message_parts),
        }

    except ValueError as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Cannot generate Value Path: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Error generating value path: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to generate Value Path: {str(e)}",
        }


async def _process_vp_changes(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process pending VP changes (surgical updates or full regeneration).

    Args:
        project_id: Project UUID
        params: Processing parameters

    Returns:
        Processing results
    """
    try:
        from app.chains.update_vp_step import process_change_queue

        # Process changes
        result = process_change_queue(project_id)

        if result.get("message") == "No pending changes":
            return {
                "success": True,
                "action": "none",
                "message": "✅ No pending changes to process. Value Path is up to date.",
            }

        action = result.get("action", "unknown")
        changes_processed = result.get("changes_processed", 0)
        affected_steps = result.get("affected_steps", 0)
        impact_ratio = result.get("impact_ratio", 0)

        # Build success message
        message_parts = [f"✅ Processed {changes_processed} change(s):"]
        message_parts.append(f"  • {affected_steps} VP steps affected ({impact_ratio:.0%} of total)")

        if action == "surgical_update":
            steps_updated = result.get("steps_updated", 0)
            message_parts.append(f"  • Performed surgical updates on {steps_updated} steps")
            message_parts.append("  • Other steps preserved unchanged")
        elif action == "full_regeneration":
            gen_result = result.get("generation_result", {})
            message_parts.append(f"  • Impact >= 50%, triggered full regeneration")
            message_parts.append(f"  • {gen_result.get('steps_generated', 0)} steps generated")

        return {
            "success": True,
            "action": action,
            "changes_processed": changes_processed,
            "affected_steps": affected_steps,
            "impact_ratio": impact_ratio,
            "message": "\n".join(message_parts),
        }

    except Exception as e:
        logger.error(f"Error processing VP changes: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to process VP changes: {str(e)}",
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


async def _get_strategic_context(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get current strategic context.

    Args:
        project_id: Project UUID
        params: Not used

    Returns:
        Strategic context data
    """
    try:
        from app.db.strategic_context import get_strategic_context
        from app.db.stakeholders import list_stakeholders

        context = get_strategic_context(project_id)
        stakeholders = list_stakeholders(project_id)

        if not context:
            return {
                "success": True,
                "exists": False,
                "context": None,
                "stakeholders": [],
                "message": "No strategic context found. Use `generate_strategic_context` to create one.",
            }

        # Build display message
        message_parts = ["**Strategic Context**"]

        if context.get("executive_summary"):
            message_parts.append(f"\n**Executive Summary**: {context['executive_summary']}")

        message_parts.append(f"\n**Project Type**: {context.get('project_type', 'internal')}")

        opportunity = context.get("opportunity", {})
        if opportunity:
            message_parts.append("\n**Opportunity**:")
            if opportunity.get("problem_statement"):
                message_parts.append(f"  • Problem: {opportunity['problem_statement']}")
            if opportunity.get("business_opportunity"):
                message_parts.append(f"  • Opportunity: {opportunity['business_opportunity']}")

        risks = context.get("risks", [])
        if risks:
            message_parts.append(f"\n**Risks** ({len(risks)}):")
            for risk in risks[:3]:
                severity = risk.get("severity", "medium")
                message_parts.append(f"  • [{severity.upper()}] {risk.get('description', '')[:80]}")
            if len(risks) > 3:
                message_parts.append(f"  ... and {len(risks) - 3} more")

        metrics = context.get("success_metrics", [])
        if metrics:
            message_parts.append(f"\n**Success Metrics** ({len(metrics)}):")
            for metric in metrics[:3]:
                message_parts.append(f"  • {metric.get('metric', '')}: {metric.get('target', '')}")
            if len(metrics) > 3:
                message_parts.append(f"  ... and {len(metrics) - 3} more")

        if stakeholders:
            message_parts.append(f"\n**Stakeholders** ({len(stakeholders)}):")
            for sh in stakeholders[:5]:
                sh_type = sh.get("stakeholder_type", "")
                message_parts.append(f"  • {sh.get('name', '')} ({sh_type})")
            if len(stakeholders) > 5:
                message_parts.append(f"  ... and {len(stakeholders) - 5} more")

        return {
            "success": True,
            "exists": True,
            "context": context,
            "stakeholders": stakeholders,
            "message": "\n".join(message_parts),
        }

    except Exception as e:
        logger.error(f"Error getting strategic context: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get strategic context: {str(e)}",
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


async def _add_stakeholder(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a stakeholder.

    Args:
        project_id: Project UUID
        params: Stakeholder data

    Returns:
        Creation result
    """
    try:
        from app.db.stakeholders import create_stakeholder

        name = params.get("name")
        stakeholder_type = params.get("stakeholder_type")

        if not name or not stakeholder_type:
            return {
                "success": False,
                "error": "name and stakeholder_type are required",
                "message": "Please provide stakeholder name and type (champion, sponsor, blocker, influencer, end_user)",
            }

        stakeholder = create_stakeholder(
            project_id=project_id,
            name=name,
            stakeholder_type=stakeholder_type,
            email=params.get("email"),
            role=params.get("role"),
            organization=params.get("organization"),
            influence_level=params.get("influence_level", "medium"),
            priorities=params.get("priorities", []),
            concerns=params.get("concerns", []),
            confirmation_status="ai_generated",
        )

        type_labels = {
            "champion": "Champion (internal advocate)",
            "sponsor": "Sponsor (decision maker)",
            "blocker": "Blocker (opposition)",
            "influencer": "Influencer (opinion leader)",
            "end_user": "End User",
        }
        type_label = type_labels.get(stakeholder_type, stakeholder_type)

        return {
            "success": True,
            "stakeholder": stakeholder,
            "message": f"✅ Added stakeholder: {name} as {type_label}",
        }

    except Exception as e:
        logger.error(f"Error adding stakeholder: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to add stakeholder: {str(e)}",
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


async def _list_stakeholders(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List stakeholders grouped by type.

    Args:
        project_id: Project UUID
        params: Not used

    Returns:
        Stakeholder list
    """
    try:
        from app.db.stakeholders import get_stakeholders_grouped

        grouped = get_stakeholders_grouped(project_id)

        total = sum(len(v) for v in grouped.values())

        if total == 0:
            return {
                "success": True,
                "total": 0,
                "grouped": grouped,
                "message": "No stakeholders found. Use `add_stakeholder` or `identify_stakeholders` to add them.",
            }

        # Build message
        message_parts = [f"**Stakeholders** ({total} total)"]

        type_labels = {
            "champion": "Champions (Internal Advocates)",
            "sponsor": "Sponsors (Decision Makers)",
            "blocker": "Blockers (Opposition)",
            "influencer": "Influencers (Opinion Leaders)",
            "end_user": "End Users",
        }

        for sh_type, label in type_labels.items():
            stakeholders = grouped.get(sh_type, [])
            if stakeholders:
                message_parts.append(f"\n**{label}**:")
                for sh in stakeholders:
                    influence = sh.get("influence_level", "medium")
                    role = sh.get("role", "")
                    role_str = f" ({role})" if role else ""
                    message_parts.append(f"  • {sh.get('name', 'Unknown')}{role_str} [{influence}]")

        return {
            "success": True,
            "total": total,
            "grouped": grouped,
            "message": "\n".join(message_parts),
        }

    except Exception as e:
        logger.error(f"Error listing stakeholders: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to list stakeholders: {str(e)}",
        }


async def _add_risk(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a risk to strategic context.

    Args:
        project_id: Project UUID
        params: Risk data

    Returns:
        Addition result
    """
    try:
        from app.db.strategic_context import add_risk, get_strategic_context

        category = params.get("category")
        description = params.get("description")
        severity = params.get("severity")

        if not category or not description or not severity:
            return {
                "success": False,
                "error": "category, description, and severity are required",
                "message": "Please provide risk category (business/technical/compliance/competitive), description, and severity (high/medium/low)",
            }

        # Check if context exists
        context = get_strategic_context(project_id)
        if not context:
            return {
                "success": False,
                "error": "No strategic context found",
                "message": "No strategic context exists. Generate one first with `generate_strategic_context`.",
            }

        # Add risk
        updated = add_risk(
            project_id=project_id,
            category=category,
            description=description,
            severity=severity,
            mitigation=params.get("mitigation"),
        )

        severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")

        return {
            "success": True,
            "risk_count": len(updated.get("risks", [])),
            "message": f"✅ Added {severity_emoji} {severity.upper()} {category} risk: {description[:80]}...",
        }

    except Exception as e:
        logger.error(f"Error adding risk: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to add risk: {str(e)}",
        }


async def _add_success_metric(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Add a success metric to strategic context.

    Args:
        project_id: Project UUID
        params: Metric data

    Returns:
        Addition result
    """
    try:
        from app.db.strategic_context import add_success_metric, get_strategic_context

        metric = params.get("metric")
        target = params.get("target")

        if not metric or not target:
            return {
                "success": False,
                "error": "metric and target are required",
                "message": "Please provide metric name and target value",
            }

        # Check if context exists
        context = get_strategic_context(project_id)
        if not context:
            return {
                "success": False,
                "error": "No strategic context found",
                "message": "No strategic context exists. Generate one first with `generate_strategic_context`.",
            }

        # Add metric
        updated = add_success_metric(
            project_id=project_id,
            metric=metric,
            target=target,
            current=params.get("current"),
        )

        return {
            "success": True,
            "metric_count": len(updated.get("success_metrics", [])),
            "message": f"✅ Added success metric: {metric} → Target: {target}",
        }

    except Exception as e:
        logger.error(f"Error adding success metric: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to add success metric: {str(e)}",
        }


# =============================================================================
# Entity Cascade Tool Handlers
# =============================================================================


async def _analyze_impact(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze impact of changing an entity.

    Args:
        project_id: Project UUID
        params: Entity type and ID

    Returns:
        Impact analysis result
    """
    try:
        from app.chains.impact_analysis import analyze_change_impact, format_impact_analysis

        entity_type = params.get("entity_type")
        entity_id = params.get("entity_id")

        if not entity_type or not entity_id:
            return {
                "success": False,
                "error": "entity_type and entity_id are required",
                "message": "Please specify the entity type and ID to analyze",
            }

        result = analyze_change_impact(
            project_id=project_id,
            entity_type=entity_type,
            entity_id=UUID(entity_id),
            proposed_change=params.get("proposed_change"),
        )

        return {
            "success": True,
            "entity_type": result.entity_type,
            "entity_id": result.entity_id,
            "entity_name": result.entity_name,
            "total_affected": result.total_affected,
            "recommendation": result.recommendation,
            "direct_impacts": [
                {
                    "type": i.entity_type,
                    "id": i.entity_id,
                    "name": i.entity_name,
                    "reason": i.reason,
                }
                for i in result.direct_impacts
            ],
            "indirect_impacts": [
                {
                    "type": i.entity_type,
                    "id": i.entity_id,
                    "name": i.entity_name,
                    "reason": i.reason,
                    "depth": len(i.path),
                }
                for i in result.indirect_impacts
            ],
            "message": format_impact_analysis(result),
        }

    except Exception as e:
        logger.error(f"Error analyzing impact: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to analyze impact: {str(e)}",
        }


async def _get_stale_entities(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get stale entities for the project.

    Args:
        project_id: Project UUID
        params: Optional entity type filter

    Returns:
        Stale entities grouped by type
    """
    try:
        from app.db.entity_dependencies import get_stale_entities

        result = get_stale_entities(project_id)
        entity_type_filter = params.get("entity_type", "all")

        # Filter if requested
        if entity_type_filter != "all":
            type_map = {
                "persona": "personas",
                "feature": "features",
                "vp_step": "vp_steps",
                "strategic_context": "strategic_context",
            }
            key = type_map.get(entity_type_filter)
            if key:
                filtered = {key: result.get(key, [])}
                filtered["total_stale"] = len(filtered[key])
                result = filtered

        # Format message
        lines = ["Stale entities needing refresh:"]
        if result.get("personas"):
            lines.append(f"\nPersonas ({len(result['personas'])}):")
            for p in result["personas"]:
                lines.append(f"  - {p.get('name', 'Unknown')}: {p.get('stale_reason', 'Unknown reason')}")

        if result.get("features"):
            lines.append(f"\nFeatures ({len(result['features'])}):")
            for f in result["features"]:
                lines.append(f"  - {f.get('name', 'Unknown')}: {f.get('stale_reason', 'Unknown reason')}")

        if result.get("vp_steps"):
            lines.append(f"\nVP Steps ({len(result['vp_steps'])}):")
            for s in result["vp_steps"]:
                lines.append(f"  - {s.get('label', 'Unknown')}: {s.get('stale_reason', 'Unknown reason')}")

        if result.get("strategic_context"):
            lines.append(f"\nStrategic Context ({len(result['strategic_context'])}):")
            for c in result["strategic_context"]:
                lines.append(f"  - {c.get('stale_reason', 'Unknown reason')}")

        if result.get("total_stale", 0) == 0:
            lines = ["No stale entities found. All entities are up to date."]

        return {
            "success": True,
            "stale_entities": result,
            "total_stale": result.get("total_stale", 0),
            "message": "\n".join(lines),
        }

    except Exception as e:
        logger.error(f"Error getting stale entities: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to get stale entities: {str(e)}",
        }


async def _refresh_stale_entity(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refresh a stale entity.

    Args:
        project_id: Project UUID
        params: Entity type and ID

    Returns:
        Refresh result
    """
    try:
        from app.chains.impact_analysis import refresh_stale_entity

        entity_type = params.get("entity_type")
        entity_id = params.get("entity_id")

        if not entity_type or not entity_id:
            return {
                "success": False,
                "error": "entity_type and entity_id are required",
                "message": "Please specify the entity type and ID to refresh",
            }

        result = refresh_stale_entity(
            project_id=project_id,
            entity_type=entity_type,
            entity_id=UUID(entity_id),
        )

        if result["status"] == "refreshed":
            message = f"Successfully refreshed {entity_type}"
        elif result["status"] == "no_changes":
            message = f"No changes needed for {entity_type}"
        elif result["status"] == "error":
            message = f"Failed to refresh: {result.get('error', 'Unknown error')}"
        else:
            message = f"Refresh status: {result['status']}"

        return {
            "success": result["status"] in ["refreshed", "no_changes"],
            "result": result,
            "message": message,
        }

    except Exception as e:
        logger.error(f"Error refreshing entity: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to refresh entity: {str(e)}",
        }


async def _link_strategic_context(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Link strategic context elements to entities.

    Args:
        project_id: Project UUID
        params: Section, index, and linked entity info

    Returns:
        Link result
    """
    try:
        from app.chains.strategic_context_linker import (
            link_risk_to_features,
            link_stakeholder_to_persona,
            link_success_metric_to_vp_steps,
        )

        section = params.get("section")
        index = params.get("index")
        linked_type = params.get("linked_entity_type")
        linked_ids = params.get("linked_entity_ids", [])

        if not all([section, index is not None, linked_type, linked_ids]):
            return {
                "success": False,
                "error": "Missing required parameters",
                "message": "Please provide section, index, linked_entity_type, and linked_entity_ids",
            }

        if section == "risk" and linked_type == "feature":
            link_risk_to_features(project_id, index, [UUID(fid) for fid in linked_ids])
            message = f"Linked risk {index} to {len(linked_ids)} features"

        elif section == "success_metric" and linked_type == "vp_step":
            link_success_metric_to_vp_steps(project_id, index, [UUID(sid) for sid in linked_ids])
            message = f"Linked success metric {index} to {len(linked_ids)} VP steps"

        elif section == "stakeholder" and linked_type == "persona":
            if len(linked_ids) != 1:
                return {
                    "success": False,
                    "error": "Stakeholder can only link to one persona",
                    "message": "Please provide exactly one persona ID",
                }
            # For stakeholder, index is actually the stakeholder_id
            link_stakeholder_to_persona(project_id, UUID(str(index)), UUID(linked_ids[0]))
            message = "Linked stakeholder to persona"

        else:
            return {
                "success": False,
                "error": f"Invalid combination: {section} + {linked_type}",
                "message": "Risks link to features, success metrics link to VP steps, stakeholders link to personas",
            }

        return {
            "success": True,
            "message": message,
        }

    except Exception as e:
        logger.error(f"Error linking strategic context: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to link: {str(e)}",
        }


async def _rebuild_dependencies(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rebuild the entity dependency graph.

    Args:
        project_id: Project UUID
        params: (unused)

    Returns:
        Rebuild stats
    """
    try:
        from app.db.entity_dependencies import rebuild_dependencies_for_project

        stats = rebuild_dependencies_for_project(project_id)

        message = (
            f"Rebuilt dependency graph:\n"
            f"  - Features processed: {stats['features_processed']}\n"
            f"  - VP steps processed: {stats['vp_steps_processed']}\n"
            f"  - Dependencies created: {stats['dependencies_created']}"
        )

        if stats.get("errors"):
            message += f"\n  - Errors: {len(stats['errors'])}"

        return {
            "success": True,
            "stats": stats,
            "message": message,
        }

    except Exception as e:
        logger.error(f"Error rebuilding dependencies: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to rebuild dependencies: {str(e)}",
        }


async def _process_cascades(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process pending entity cascades.

    Args:
        project_id: Project UUID
        params: Optional auto_only flag

    Returns:
        Processing stats
    """
    try:
        from app.chains.entity_cascade import process_entity_changes

        auto_only = params.get("auto_only", True)

        stats = process_entity_changes(project_id, auto_only=auto_only)

        message = (
            f"Cascade processing complete:\n"
            f"  - Changes processed: {stats['changes_processed']}\n"
            f"  - Entities marked stale: {stats['entities_marked_stale']}"
        )

        if stats.get("errors"):
            message += f"\n  - Errors: {len(stats['errors'])}"

        return {
            "success": True,
            "stats": stats,
            "message": message,
        }

    except Exception as e:
        logger.error(f"Error processing cascades: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to process cascades: {str(e)}",
        }
