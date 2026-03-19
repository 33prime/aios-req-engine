"""Execute Agent Demo — Haiku chain for interactive agent Try It panel.

Single Haiku call with tool_use for forced structured output.
6 prompt templates, one per agent type. Each produces type-specific
structured data that the frontend renders as styled cards.

Follows the synthesize_intelligence.py pattern: tool dict + forced tool_choice.
"""
# ruff: noqa: E501 — tool schema definitions have natural line lengths

from anthropic import Anthropic

from app.core.logging import get_logger

logger = get_logger(__name__)

_MODEL = "claude-haiku-4-5-20251001"
_MAX_TOKENS = 1200

# ── Tool schemas (one per agent type) ───────────────────────────

_TOOLS: dict[str, dict] = {
    "classifier": {
        "name": "classification_output",
        "description": "Output classified entities with confidence and evidence",
        "input_schema": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Entity name"},
                            "category": {"type": "string", "description": "Classification category"},
                            "confidence": {"type": "number", "description": "0-1 confidence score"},
                            "evidence": {"type": "string", "description": "Quote from input supporting this"},
                            "reasoning": {"type": "string", "description": "Why this classification"},
                        },
                        "required": ["name", "category", "confidence", "evidence", "reasoning"],
                    },
                    "minItems": 1,
                    "maxItems": 8,
                },
                "summary": {"type": "string", "description": "1-2 sentence overall summary"},
            },
            "required": ["entities", "summary"],
        },
    },
    "matcher": {
        "name": "matching_output",
        "description": "Output matched connections with similarity scores",
        "input_schema": {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "Source item"},
                            "target": {"type": "string", "description": "Matched target"},
                            "similarity": {"type": "number", "description": "0-1 similarity score"},
                            "match_type": {"type": "string", "description": "Type of match (exact, semantic, inferred)"},
                            "reasoning": {"type": "string", "description": "Why these match"},
                        },
                        "required": ["source", "target", "similarity", "match_type", "reasoning"],
                    },
                    "minItems": 1,
                    "maxItems": 8,
                },
                "unmatched": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Items that found no match",
                },
                "summary": {"type": "string", "description": "1-2 sentence overall summary"},
            },
            "required": ["matches", "unmatched", "summary"],
        },
    },
    "predictor": {
        "name": "prediction_output",
        "description": "Output forecasts with confidence intervals and risks",
        "input_schema": {
            "type": "object",
            "properties": {
                "predictions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "prediction": {"type": "string", "description": "The forecast"},
                            "confidence": {"type": "number", "description": "0-1 confidence"},
                            "timeframe": {"type": "string", "description": "When this applies"},
                            "risk_factors": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Risks that could invalidate this",
                            },
                            "evidence_basis": {"type": "string", "description": "What supports this prediction"},
                        },
                        "required": ["prediction", "confidence", "timeframe", "risk_factors", "evidence_basis"],
                    },
                    "minItems": 1,
                    "maxItems": 5,
                },
                "overall_outlook": {"type": "string", "description": "1-2 sentence outlook"},
            },
            "required": ["predictions", "overall_outlook"],
        },
    },
    "watcher": {
        "name": "alert_output",
        "description": "Output risk alerts with severity levels and actions",
        "input_schema": {
            "type": "object",
            "properties": {
                "alerts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Alert title"},
                            "severity": {
                                "type": "string",
                                "enum": ["critical", "warning", "advisory"],
                                "description": "Severity level",
                            },
                            "description": {"type": "string", "description": "What was detected"},
                            "recommended_action": {"type": "string", "description": "What to do"},
                            "evidence": {"type": "string", "description": "Supporting evidence from input"},
                        },
                        "required": ["title", "severity", "description", "recommended_action", "evidence"],
                    },
                    "minItems": 1,
                    "maxItems": 6,
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Overall risk assessment",
                },
                "summary": {"type": "string", "description": "1-2 sentence risk summary"},
            },
            "required": ["alerts", "risk_level", "summary"],
        },
    },
    "generator": {
        "name": "generation_output",
        "description": "Output generated content sections with narrative",
        "input_schema": {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "heading": {"type": "string", "description": "Section heading"},
                            "content": {"type": "string", "description": "Generated content"},
                            "source_basis": {"type": "string", "description": "What input informed this"},
                            "confidence": {"type": "number", "description": "0-1 confidence in accuracy"},
                        },
                        "required": ["heading", "content", "source_basis", "confidence"],
                    },
                    "minItems": 1,
                    "maxItems": 6,
                },
                "narrative": {"type": "string", "description": "Connecting narrative across sections"},
            },
            "required": ["sections", "narrative"],
        },
    },
    "processor": {
        "name": "processing_output",
        "description": "Output extracted entities and discovery probes",
        "input_schema": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Entity name"},
                            "type": {"type": "string", "description": "Entity type (feature, persona, constraint, etc.)"},
                            "confidence": {"type": "number", "description": "0-1 extraction confidence"},
                            "evidence": {"type": "string", "description": "Source quote"},
                        },
                        "required": ["name", "type", "confidence", "evidence"],
                    },
                    "minItems": 1,
                    "maxItems": 10,
                },
                "probes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "Discovery question"},
                            "rationale": {"type": "string", "description": "Why this matters"},
                            "target": {"type": "string", "description": "Who to ask"},
                        },
                        "required": ["question", "rationale", "target"],
                    },
                    "maxItems": 4,
                },
                "summary": {"type": "string", "description": "1-2 sentence extraction summary"},
            },
            "required": ["entities", "probes", "summary"],
        },
    },
}

# ── System prompts per agent type ────────────────────────────────

_SYSTEM_PROMPTS: dict[str, str] = {
    "classifier": (
        "You are an AI classification agent for a requirements engineering platform. "
        "Given input text (meeting notes, emails, research), extract and classify entities. "
        "Categories: feature, persona, constraint, risk, opportunity, dependency, assumption. "
        "Assign confidence based on evidence strength. Quote the exact source text."
    ),
    "matcher": (
        "You are an AI matching agent for a requirements engineering platform. "
        "Given input text, identify connections, recommendations, and relationships. "
        "Find semantic matches between mentioned items — features to personas, "
        "requirements to constraints, stakeholders to concerns. Score similarity 0-1."
    ),
    "predictor": (
        "You are an AI prediction agent for a requirements engineering platform. "
        "Given input text about a project, generate forecasts about outcomes, risks, "
        "timelines, and stakeholder reactions. Each prediction needs a confidence score, "
        "timeframe, risk factors, and evidence basis."
    ),
    "watcher": (
        "You are an AI monitoring agent for a requirements engineering platform. "
        "Given input text, detect risks, conflicts, gaps, and concerns. "
        "Assign severity (critical/warning/advisory). Each alert needs evidence "
        "from the input and a recommended action."
    ),
    "generator": (
        "You are an AI content generation agent for a requirements engineering platform. "
        "Given input text, generate structured content sections — summaries, analyses, "
        "recommendations, or documentation. Each section should cite its source basis "
        "and include a confidence score."
    ),
    "processor": (
        "You are an AI signal processing agent for a requirements engineering platform. "
        "Given raw input (meeting transcript, email, research doc), extract structured "
        "entities (features, personas, constraints, etc.) with confidence scores. "
        "Also generate discovery probes — questions that would deepen understanding."
    ),
}

# ── Example inputs per agent type ────────────────────────────────

EXAMPLE_INPUTS: dict[str, tuple[str, str]] = {
    "classifier": (
        "Paste a meeting transcript, email, or requirements document and watch the "
        "classifier extract and categorize entities with confidence scores.",
        "Meeting Notes - Product Review (March 15)\n\n"
        "Sarah (Product Lead): We need the dashboard to support real-time updates. "
        "The current 30-second refresh is frustrating users, especially the operations team "
        "who monitor live shipments.\n\n"
        "James (Engineering): Real-time would require WebSocket infrastructure. "
        "We'd need to consider our current load balancer config — it doesn't handle "
        "persistent connections well.\n\n"
        "Maria (Design): The mobile experience also needs attention. 60% of our "
        "field workers access the dashboard on tablets, but the layout breaks below 1024px.\n\n"
        "Sarah: Good point. Let's also think about role-based views. Managers want "
        "high-level metrics while operators need granular shipment data.",
    ),
    "matcher": (
        "Provide a list of features, requirements, or stakeholder concerns and see "
        "how the matcher identifies connections and relationships.",
        "Project Requirements:\n"
        "- Feature: Real-time dashboard with WebSocket support\n"
        "- Feature: Role-based access control with custom views\n"
        "- Feature: Mobile-responsive layout for tablets\n"
        "- Persona: Operations Manager — monitors KPIs, makes staffing decisions\n"
        "- Persona: Field Worker — checks shipment status, updates delivery\n"
        "- Constraint: Load balancer doesn't support persistent connections\n"
        "- Constraint: Must support offline mode for field workers\n"
        "- Risk: WebSocket infrastructure may increase hosting costs 3x",
    ),
    "predictor": (
        "Share project context and watch the predictor generate forecasts "
        "about outcomes, risks, and timeline implications.",
        "Project Status Update:\n\n"
        "We're 6 weeks into a 16-week engagement. Discovery phase is 80% complete "
        "with 12 stakeholder interviews done (3 remaining). Key findings:\n"
        "- The client's current system handles 10K transactions/day but they're "
        "projecting 50K within 18 months\n"
        "- Two competing internal teams have different visions for the platform\n"
        "- Budget was approved for Phase 1 only ($450K), Phase 2 needs re-approval\n"
        "- The technical lead is leaving the company in 4 weeks\n"
        "- Integration with legacy ERP is more complex than initially scoped",
    ),
    "watcher": (
        "Input project data and see the watcher detect risks, conflicts, "
        "and gaps that need attention.",
        "Sprint Review Notes:\n\n"
        "Velocity has dropped 30% over the last 3 sprints. The team attributes this "
        "to increasing tech debt from the rapid prototyping phase.\n\n"
        "The client requested 4 new features last week that weren't in the original scope. "
        "Two of them conflict with architectural decisions we made in Sprint 2.\n\n"
        "QA found that the authentication module fails under concurrent load > 100 users. "
        "Production currently has 85 active users.\n\n"
        "The data migration script hasn't been tested against production-scale data. "
        "Go-live is in 3 weeks.\n\n"
        "Three team members haven't updated their tasks in Jira for 5+ days.",
    ),
    "generator": (
        "Provide raw requirements data and watch the generator create "
        "structured documentation sections.",
        "Raw Interview Notes — CTO Interview:\n\n"
        "\"Our biggest challenge is that every department has built their own tools. "
        "Sales uses three different CRMs. Marketing has custom analytics. "
        "Operations runs on spreadsheets. We need a unified platform but we can't "
        "just rip and replace — too much institutional knowledge is embedded in "
        "these tools.\"\n\n"
        "\"The board wants to see ROI within 6 months. I need to show at least "
        "one department fully migrated and reporting 20% efficiency gains.\"\n\n"
        "\"Security is non-negotiable. We're in fintech. SOC 2 Type II, data "
        "residency in US/EU, and we need audit trails on everything.\"",
    ),
    "processor": (
        "Paste any raw signal — meeting notes, an email, or research — and see "
        "the processor extract structured entities and generate discovery probes.",
        "Email from Client (March 12):\n\n"
        "Hi team,\n\n"
        "Following up on yesterday's demo. The board was impressed with the prototype "
        "but had several concerns:\n\n"
        "1. The approval workflow needs to support multi-level sign-off. Currently "
        "it's one-level and that won't work for transactions over $50K.\n\n"
        "2. Linda from Compliance mentioned we need to integrate with their existing "
        "KYC provider (Jumio). She's the gatekeeper on this.\n\n"
        "3. Can the reporting module generate PDF exports? The CFO specifically "
        "asked about this for board presentations.\n\n"
        "4. Timeline is tight — we need this live before Q3 earnings (July 15).\n\n"
        "Let me know if you need access to anyone on our side.\n\n"
        "Best,\nDavid Chen\nVP Product, Meridian Financial",
    ),
}


# ── Main execution function ──────────────────────────────────────


async def execute_agent_demo(
    agent_type: str,
    agent_name: str,
    input_text: str,
    project_context: str | None = None,
) -> dict | None:
    """Execute a demo agent using Haiku with forced tool_use output.

    Returns structured dict matching the agent type's tool schema, or None on failure.
    """
    if agent_type not in _TOOLS:
        logger.warning("Unknown agent type: %s", agent_type)
        return None

    tool = _TOOLS[agent_type]
    system_prompt = _SYSTEM_PROMPTS[agent_type]

    # Add agent name context
    system_prompt += f"\n\nYou are called '{agent_name}'. Respond as this specific agent."

    # Add optional project context
    if project_context:
        system_prompt += f"\n\nProject context:\n{project_context}"

    # Build user message
    user_content = f"Process the following input:\n\n{input_text}"

    try:
        client = Anthropic()
        response = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[{"role": "user", "content": user_content}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool["name"]},
        )

        # Extract tool result
        for block in response.content:
            if block.type == "tool_use" and block.name == tool["name"]:
                result = block.input

                # Log usage
                try:
                    from app.core.llm_usage import log_llm_usage

                    log_llm_usage(
                        model=_MODEL,
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                        operation=f"agent_demo_{agent_type}",
                        metadata={
                            "agent_name": agent_name,
                            "cache_read": getattr(
                                response.usage, "cache_read_input_tokens", 0
                            ),
                            "cache_create": getattr(
                                response.usage, "cache_creation_input_tokens", 0
                            ),
                        },
                    )
                except Exception:
                    pass

                return result

        logger.warning("No tool_use block in agent demo response for %s", agent_type)
        return None

    except Exception:
        logger.exception("Agent demo execution failed for %s", agent_type)
        return None
