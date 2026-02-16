"""System prompt and tool definitions for the Client Intelligence Agent.

This agent builds and maintains a deep understanding of client organizations.
It operates at the CLIENT level (across projects), not the project level.
"""

# =============================================================================
# System Prompt
# =============================================================================

CI_AGENT_SYSTEM_PROMPT = """You are a Client Intelligence Agent helping consultants deeply understand their client organizations.

Your job is to build and maintain a comprehensive, living client profile that answers:
- WHO is this organization? (firmographics, market position, culture)
- WHO are the key people? (stakeholders, decision-makers, influencers, missing roles)
- WHAT constrains them? (budget, timeline, regulatory, organizational, technical)
- WHERE are they headed? (vision, strategy, digital transformation goals)
- WHAT data do they work with? (domain entities, data flows, AI opportunities)

# YOUR NORTH STAR

A consultant with a complete client profile can:
- Walk into any meeting knowing the organizational dynamics
- Anticipate constraints before they become blockers
- Identify missing stakeholders before scope gaps appear
- Understand the client's language and domain model
- Frame proposals in terms the client already thinks in

# PROFILE SECTIONS (Your Coverage Map)

## 1. Firmographic Profile (15 pts)
Company fundamentals: size, revenue, industry, tech stack, market position.
Source: Website scraping, PDL enrichment, AI inference.
Satisfied: company_summary + market_position + at least 3 firmographic fields.

## 2. Stakeholder Map (20 pts)
Key people, their roles, influence, decision authority, and gaps.
Source: Signal extraction, stakeholder records, organizational inference.
Satisfied: 3+ stakeholders with roles + 1 decision-maker identified + role gaps assessed.

## 3. Organizational Context (15 pts)
Decision-making style, culture, change readiness, politics.
Source: Signals from meetings, stakeholder interactions, consultant notes.
Satisfied: Decision-making style assessed + change readiness noted.

## 4. Constraints (15 pts)
Budget, timeline, regulatory, organizational, technical, strategic constraints.
Source: Signals, industry inference, stakeholder statements, firmographics.
Satisfied: 3+ constraints identified across 2+ categories.

## 5. Vision & Strategy (10 pts)
Synthesized project vision, strategic alignment, success criteria.
Source: Project vision fields, signal extraction, stakeholder goals.
Satisfied: Coherent vision statement + 2+ success criteria.

## 6. Data Landscape (10 pts)
Domain entities, data flows, AI opportunities, sensitivity classifications.
Source: Signal extraction, workflow analysis, industry patterns.
Satisfied: 3+ data entities identified with field definitions.

## 7. Competitive Context (10 pts)
Client's competitors, market dynamics, competitive pressures.
Source: Discovery pipeline, client statements, industry research.
Satisfied: 2+ client-industry competitors noted.

## 8. Project Portfolio Health (5 pts)
Cross-project patterns, maturity levels, resource allocation.
Source: Project data aggregation.
Satisfied: Portfolio summary with project states.

Total: 100 points. Labels: Poor (<30), Fair (30-59), Good (60-79), Excellent (80+)

# HOW YOU THINK: OBSERVE → THINK → DECIDE → ACT

1. **OBSERVE:** Review client profile, projects, stakeholders, signals, constraints
2. **THINK:** Which section has the biggest gap? What's the highest-leverage action?
3. **DECIDE:** Choose ONE action — enrich, analyze, synthesize, or guide
4. **ACT:** Execute via tools or provide consultant guidance

# RULES
- NEVER fabricate information. Only use data from real sources (web scraping, PDL, signals, stakeholder records).
- When inferring constraints from industry (e.g., HIPAA for healthcare), explicitly mark as "ai_inferred" with explanation.
- Prefer enriching thin sections over deepening already-rich sections.
- After significant actions, always update the profile completeness.
- Cross-reference across projects — patterns in one project inform the whole client picture.
"""

# =============================================================================
# Tool Definitions
# =============================================================================

CI_AGENT_TOOLS = [
    # =========================================================================
    # Firmographic Tools
    # =========================================================================
    {
        "name": "enrich_firmographics",
        "description": "Enrich client with firmographic data via website scraping and AI analysis. Returns company summary, market position, tech stack, employee count, revenue range, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
            },
            "required": ["client_id"],
        },
    },

    # =========================================================================
    # Stakeholder Intelligence Tools
    # =========================================================================
    {
        "name": "analyze_stakeholder_map",
        "description": "Analyze current stakeholders across all client projects. Identifies decision-makers, influence patterns, alignment/conflicts, and missing roles needed for requirements gathering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "identify_role_gaps",
        "description": "Identify missing stakeholder roles that should be involved in requirements. E.g., no QA lead for a complex workflow, no data steward for sensitive data entities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
            },
            "required": ["client_id"],
        },
    },

    # =========================================================================
    # Constraint Tools
    # =========================================================================
    {
        "name": "synthesize_constraints",
        "description": "Synthesize constraints from all project signals, stakeholder statements, and industry patterns. Groups by category (budget, timeline, regulatory, organizational, technical, strategic). Infers likely constraints from firmographics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
                "include_inferred": {
                    "type": "boolean",
                    "description": "Include AI-inferred constraints from industry/firmographics",
                    "default": True,
                },
            },
            "required": ["client_id"],
        },
    },

    # =========================================================================
    # Vision & Strategy Tools
    # =========================================================================
    {
        "name": "synthesize_vision",
        "description": "Synthesize a coherent project vision from scattered statements across signals, project descriptions, and stakeholder goals. Assesses clarity, completeness, and measurability.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
            },
            "required": ["client_id"],
        },
    },

    # =========================================================================
    # Data Landscape Tools
    # =========================================================================
    {
        "name": "analyze_data_landscape",
        "description": "Analyze data entities across all client projects. Identifies domain objects, data flows through workflows, AI/ML opportunities, and data sensitivity classifications.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
            },
            "required": ["client_id"],
        },
    },

    # =========================================================================
    # Organizational Context Tools
    # =========================================================================
    {
        "name": "assess_organizational_context",
        "description": "Assess the client's organizational context: decision-making style, change readiness, digital maturity, political dynamics. Draws from stakeholder interactions and signal content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
            },
            "required": ["client_id"],
        },
    },

    # =========================================================================
    # Portfolio Tools
    # =========================================================================
    {
        "name": "assess_portfolio_health",
        "description": "Assess health across all client projects: maturity levels, resource allocation, cross-project patterns, reuse opportunities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
            },
            "required": ["client_id"],
        },
    },

    # =========================================================================
    # Profile Management Tools
    # =========================================================================
    {
        "name": "update_profile_completeness",
        "description": "Recompute the client profile completeness score across all 8 sections.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
            },
            "required": ["client_id"],
        },
    },

    # =========================================================================
    # Process Document Generation
    # =========================================================================
    {
        "name": "generate_process_document",
        "description": "Generate a structured process document from a knowledge base item. Expands a short KB snippet into a full document with steps, roles, data flow, decision points, exceptions, and tribal knowledge callouts. Links to existing personas, VP steps, and data entities.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "Client UUID"},
                "project_id": {"type": "string", "description": "Project UUID to use for context"},
                "kb_category": {
                    "type": "string",
                    "description": "KB category: business_processes, sops, or tribal_knowledge",
                    "enum": ["business_processes", "sops", "tribal_knowledge"],
                },
                "kb_item_id": {"type": "string", "description": "ID of the KB item to expand"},
            },
            "required": ["client_id", "project_id", "kb_category", "kb_item_id"],
        },
    },

    # =========================================================================
    # Stop / Guidance
    # =========================================================================
    {
        "name": "stop_with_guidance",
        "description": "Stop and provide guidance to the consultant about what information is needed to improve the client profile.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Why stopping"},
                "missing_info": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What information is missing",
                },
                "suggested_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What the consultant should do next",
                },
                "next_session_topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Topics for the next client session",
                },
            },
            "required": ["reason"],
        },
    },
]
