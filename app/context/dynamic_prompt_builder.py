"""Dynamic system prompt builder for phase-aware context.

Builds a compact, phase-aware system prompt that:
- Includes base identity and guidelines (~2K tokens)
- Injects the project state frame (~800 tokens)
- Adds phase-specific instructions (~500 tokens)
- Only includes relevant tool documentation based on intent (~1.5K tokens)
- Total target: ~4-5K tokens (vs ~5K static)
"""

from typing import Any

from app.context.models import IntentClassification, ProjectPhase, ProjectStateFrame
from app.context.token_budget import TokenBudgetManager
from app.core.logging import get_logger

logger = get_logger(__name__)


# =========================
# Base Identity (always included)
# =========================

BASE_IDENTITY = """You are a **Project Command Center** - an AI helping consultants manage client-approved data and project evolution.

# Philosophy
- **Signal-driven updates**: Client signals (transcripts, emails, documents) are the source of truth
- **Proposals, not patches**: Changes come as reviewable proposals for bulk apply/discard
- **Client-approved data**: Focus on capturing what clients say, not generating content

# Behavior: Act First, Recap After
- **Just do it** - Process signals, create proposals, execute actions. Don't ask clarifying questions.
- **Recap what you did** - After actions, give a brief summary of exactly what changed
- **One response** - Complete the full task in a single turn when possible
- **Stay focused** - Only execute the specific tool/action requested. Do NOT automatically chain to other enrichment tools (enrich_features, enrich_personas, generate_value_path) unless explicitly asked.

# Output Format
After completing actions, provide a brief recap:
- ✅ What was extracted/updated
- 📋 Proposal created (if any) - tell user to review in Overview tab
- 📊 Key findings (if research was done)

Keep recaps to 2-4 bullet points max. No verbose explanations.

# Constraints
- Value Path: Always say "Value Path" or "VP" (not "value proposition")
- NEVER auto-apply proposals - always leave them pending for user review in the UI
- NEVER use deprecated tools: list_insights, apply_patch, bulk_apply_patches, assess_readiness
"""


# =========================
# Phase-Specific Instructions
# =========================

PHASE_INSTRUCTIONS: dict[ProjectPhase, str] = {
    ProjectPhase.DISCOVERY: """
# Phase: Discovery (baseline < 25%)
Actions: Process client signals via `add_signal`. Review and apply proposals from Overview tab.
""",
    ProjectPhase.DEFINITION: """
# Phase: Definition (baseline 25-75%)
Actions: Complete features/personas. Use `analyze_gaps` to find missing pieces. Enrich entities when ready.
""",
    ProjectPhase.VALIDATION: """
# Phase: Validation (baseline 75-100%)
Actions: Run research, get confirmations, review pending proposals. Use `list_pending_proposals` to check queue.
""",
    ProjectPhase.BUILD_READY: """
# Phase: Build-Ready ✓
Actions: Final checks, address warnings, verify MVP evidence. Ready for handoff.
""",
}


# =========================
# Tool Documentation by Category
# =========================

TOOL_DOCS = {
    "signal": """
## Signal Processing (PRIMARY WORKFLOW)
`add_signal`: Add client content (transcripts, emails, documents)
- Automatically extracts: features, personas, stakeholders, constraints
- Auto-updates creative brief with client info
- Creates a **proposal** for review if changes detected
- User reviews proposals in Overview tab

Example: When user shares a transcript, use add_signal with signal_type="transcript"
""",
    "creative_brief": """
## Creative Brief
`get_creative_brief`: Check client info status
- Returns client_name, industry, website, competitors
- Check this before running research

`update_creative_brief`: Save client information
- Updates client_name, industry, website
- Appends to competitors, focus_areas
""",
    "proposal": """
## Proposal Management
`list_pending_proposals`: Show proposals awaiting review
- Returns all pending proposals with summary
- Each proposal shows what will change

`preview_proposal`: View detailed before/after for a proposal
`apply_proposal`: Execute a proposal after user confirms

`propose_features`: Manually suggest features with evidence
- Creates a proposal for user review
""",
    "analysis": """
## Analysis
`analyze_gaps`: Identify what's missing
- Evidence gaps, persona gaps, feature gaps
- VP gaps, confirmation gaps
- Suggests specific actions
""",
    "research": """
## Research & Evidence
`search_research`: Keyword search through research chunks
`semantic_search_research`: Similarity-based evidence search
`find_evidence_gaps`: Identify entities missing research backing
`attach_evidence`: Link research to features/PRD/VP
""",
    "enrichment": """
## Enrichment
`enrich_features`: Add detailed mini-spec info to features
- Adds target personas, user actions, system behaviors, UI requirements

`enrich_personas`: Add detailed profiles and key workflows
- Adds overview, key workflows showing feature interactions
""",
    "status": """
## Project Status
`get_project_status`: Current state summary with counts
- Features, personas, VP steps, open confirmations
- Highlights items needing attention

`list_pending_confirmations`: Questions needing client input
`generate_client_email`: Draft client outreach emails
`generate_meeting_agenda`: Structure client meetings
""",
    "documents": """
## Document Clarification
`check_document_clarifications`: Check for documents needing type clarification
- Returns pending questions about ambiguous uploads
- Use after document processing completes

`respond_to_document_clarification`: Update a document's classification
- Called after user identifies the document type
""",
}

# Map intents to tool categories
INTENT_TO_TOOLS: dict[str, list[str]] = {
    "proposal": ["proposal", "signal", "analysis"],
    "analysis": ["analysis", "status"],
    "research": ["research", "analysis", "creative_brief"],
    "status": ["status", "proposal"],
    "features": ["proposal", "enrichment", "signal"],
    "value_path": ["proposal", "analysis"],
    "personas": ["proposal", "enrichment", "signal"],
    "prd": ["proposal", "status"],
    "confirmation": ["status", "proposal"],
    "query": ["status", "proposal"],
    "signal": ["signal", "proposal", "creative_brief", "documents"],
    "enrichment": ["enrichment", "analysis"],
}


# =========================
# Research Onboarding Instructions
# =========================

RESEARCH_ONBOARDING_PROMPT = """
# Research: Just Do It

When user asks about research:
1. Check creative brief - if missing info, use what's available from project context or signals
2. Run the research immediately with whatever context exists
3. Recap findings briefly

Don't ask for client name/industry - extract from existing signals or project name if needed.
"""


def build_dynamic_prompt(
    context: dict[str, Any],
    state_frame: ProjectStateFrame,
    intent: IntentClassification | None = None,
    budget_manager: TokenBudgetManager | None = None,
) -> str:
    """
    Build a dynamic, phase-aware system prompt.

    Args:
        context: Project context from build_smart_context
        state_frame: Current project state frame
        intent: Classified user intent
        budget_manager: Token budget manager for size checking

    Returns:
        Complete system prompt string
    """
    sections = []

    # 1. Base identity (always included)
    sections.append(BASE_IDENTITY)

    # 2. Project state frame
    sections.append(_build_state_section(context, state_frame))

    # 3. Phase-specific instructions
    phase_instructions = PHASE_INSTRUCTIONS.get(state_frame.current_phase, "")
    if phase_instructions:
        sections.append(phase_instructions)

    # 4. Tool documentation (based on intent)
    tool_docs = _get_relevant_tool_docs(intent)
    if tool_docs:
        sections.append("\n# Your Tools\n" + tool_docs)

    # 5. Research onboarding (if intent is research-related)
    if intent and intent.primary == "research":
        sections.append(RESEARCH_ONBOARDING_PROMPT)

    # 6. Focused entity section (if viewing specific item)
    focused_section = _build_focused_section(context)
    if focused_section:
        sections.append(focused_section)

    # 7. Proactive suggestions (if any)
    suggestions = context.get("suggestions", [])
    if suggestions:
        sections.append(_build_suggestions_section(suggestions))

    prompt = "\n".join(sections)

    # Log token usage if budget manager provided
    if budget_manager:
        token_count = budget_manager.count_tokens(prompt)
        logger.debug(f"System prompt tokens: {token_count}")

    return prompt


def _build_state_section(context: dict, state_frame: ProjectStateFrame) -> str:
    """Build the project state section with state frame."""
    project = context.get("project", {})

    mode_description = (
        "Maintenance Mode (surgical updates via patches)"
        if project.get("prd_mode") == "maintenance"
        else "Initial Mode (generative baseline building)"
    )

    baseline_status = (
        "Finalized - research available"
        if project.get("baseline_ready")
        else "In progress - research not yet available"
    )

    # Include state frame XML
    state_frame_xml = state_frame.to_xml()

    return f"""
# Project Context
Project: {project.get('name', 'Unknown')}
Mode: {mode_description}
Baseline: {baseline_status}

# Project State
{state_frame_xml}

Use the state frame above to understand:
- Current phase and progress toward next phase
- Blocking issues that need resolution
- Recommended next actions with tool hints
"""


def _get_relevant_tool_docs(intent: IntentClassification | None) -> str:
    """Get tool documentation relevant to the detected intent."""
    if not intent:
        # Include all core tools if no intent
        return "\n".join([
            TOOL_DOCS["proposal"],
            TOOL_DOCS["analysis"],
            TOOL_DOCS["status"],
        ])

    # Get tool categories for this intent
    categories = INTENT_TO_TOOLS.get(intent.primary, ["status"])

    # Always include status tools as baseline
    if "status" not in categories:
        categories.append("status")

    # Build combined documentation
    docs = []
    seen = set()
    for category in categories:
        if category in TOOL_DOCS and category not in seen:
            docs.append(TOOL_DOCS[category])
            seen.add(category)

    return "\n".join(docs)


def _build_focused_section(context: dict) -> str:
    """Build focused entity section if user is viewing a specific item."""
    focused_entity = context.get("focused_entity")
    if not focused_entity:
        return ""

    entity_type = focused_entity.get("type", "entity")
    entity_data = focused_entity.get("data", {})
    entity_title = (
        entity_data.get("title")
        or entity_data.get("name")
        or entity_data.get("question", "Untitled")
    )

    return f"""
# Currently Viewing
The consultant is viewing: **{entity_type}** - "{entity_title}"

Prioritize information relevant to this entity in your responses.
"""


def _build_suggestions_section(suggestions: list[str]) -> str:
    """Build proactive suggestions section."""
    section = "\n# Proactive Suggestions\n"
    section += "Consider mentioning when appropriate:\n"
    for suggestion in suggestions[:5]:  # Max 5 suggestions
        section += f"- {suggestion}\n"
    return section


def estimate_prompt_tokens(
    context: dict[str, Any],
    state_frame: ProjectStateFrame,
    intent: IntentClassification | None = None,
) -> dict[str, int]:
    """
    Estimate token usage for each prompt section.

    Returns breakdown for debugging/optimization.
    """
    from app.context.token_budget import get_budget_manager

    budget_manager = get_budget_manager()

    # Calculate each section
    base_tokens = budget_manager.count_tokens(BASE_IDENTITY)
    state_tokens = budget_manager.count_tokens(state_frame.to_xml())
    phase_tokens = budget_manager.count_tokens(
        PHASE_INSTRUCTIONS.get(state_frame.current_phase, "")
    )
    tool_tokens = budget_manager.count_tokens(_get_relevant_tool_docs(intent))

    focused_section = _build_focused_section(context)
    focused_tokens = budget_manager.count_tokens(focused_section) if focused_section else 0

    suggestions = context.get("suggestions", [])
    suggestions_tokens = (
        budget_manager.count_tokens(_build_suggestions_section(suggestions))
        if suggestions else 0
    )

    total = (
        base_tokens + state_tokens + phase_tokens +
        tool_tokens + focused_tokens + suggestions_tokens
    )

    return {
        "base_identity": base_tokens,
        "state_frame": state_tokens,
        "phase_instructions": phase_tokens,
        "tool_docs": tool_tokens,
        "focused_entity": focused_tokens,
        "suggestions": suggestions_tokens,
        "total": total,
    }
