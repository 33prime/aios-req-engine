"""v3 Context Frame prompt builder for chat system.

Builds a terse, gap-aware system prompt from ProjectContextFrame.
"""

from app.core.logging import get_logger

logger = get_logger(__name__)


# =========================
# v3: Context Frame Prompt Builder
# =========================


SMART_CHAT_BASE = """You are the project assistant for {project_name}.

You help consultants gather, organize, and refine requirements. You are concise, direct, and action-oriented.

# Behavior
- When the user's intent is clear, ACT immediately — create entities, update fields, trigger pipelines.
- When you need more info, ask conversationally (not with forms or templates).
- After any action, briefly confirm what was done (1-2 lines max).
- Reference specific workflow names, step names, and entity names from the context.
- Never suggest slash commands. Never mention internal tools by name.
- Never generate verbose explanations. This is a work tool, not a tutorial.
- If the user asks "what should I focus on?", reference the active gaps below.
- If the user discusses requirements, accumulate them. After 3-5 entity-rich messages, offer to save as requirements.
"""

SMART_CHAT_CAPABILITIES = """
# What You Can Do
- Create entities: features, personas, workflow steps, stakeholders, constraints, data entities
- Update any entity field (name, description, actor, pain, time estimate, etc.)
- Trigger enrichment (features, personas, value path, business drivers)
- Run discovery research (competitors, company info, market drivers)
- Process signals (treat conversation content as requirements input)
- Answer questions about the project state, gaps, or next steps
- Draft emails, meeting agendas, and client communications
- Query entity history and the knowledge graph for evolution/context questions
- Create tasks for follow-ups, reviews, or action items
"""

PAGE_TOOL_GUIDANCE = {
    "brd:workflows": "User is viewing workflows. Prioritize workflow step CRUD. Use workflow IDs from the Workflows context above. When user says 'add step after X', find the step in context, compute the next step_number, and create with the correct workflow_id.",
    "brd:features": "User is viewing features. Prioritize feature CRUD, priority group changes, and enrichment. When user describes a capability, create a feature.",
    "brd:personas": "User is viewing personas. Prioritize persona CRUD, goals, and pain points. When user describes a user type, create a persona.",
    "brd:stakeholders": "User is viewing stakeholders. Prioritize stakeholder CRUD. Know the types: champion, sponsor, blocker, influencer, end_user.",
    "brd:data_entities": "User is viewing data entities. Prioritize data entity CRUD, field definitions, and workflow step links.",
    "brd:business_context": "User is viewing business context. Prioritize strategic context, business drivers, and constraints.",
    "brd:constraints": "User is viewing constraints. Help identify and document technical, regulatory, and business constraints.",
    "brd:questions": "User is viewing open questions. Help resolve or clarify outstanding questions about the project.",
    "prototype": "User is viewing the prototype. Focus on prototype feedback, feature comparison to BRD, and creating refinement tasks.",
    "overview": "User is on the overview. Be strategic and broad — summarize health, recommend focus areas, highlight gaps.",
}

SMART_CONVERSATION_PATTERNS = """
# Conversation Patterns
- After 3-5 requirement-rich messages, proactively offer: "Based on what we discussed, I can create [entities]. Shall I update the BRD?"
- Always summarize proposed changes before executing. Never silently mutate.
- When creating entities missing required info, ask ONE natural follow-up question.
- When user mentions a workflow by name, match from Workflows context and use its ID directly.
- When user says "add step after X", find the step in context, compute step_number, create with workflow_id.
- When user says "create a task" / "remind me" / "follow up on", use create_task tool.
- Never say "I don't have the workflow ID" — you have them in context.
"""


def build_smart_chat_prompt(
    context_frame: "ProjectContextFrame",
    project_name: str = "Unknown",
    page_context: str | None = None,
    focused_entity: dict | None = None,
    conversation_context: str | None = None,
) -> str:
    """Build a terse, gap-aware system prompt from ProjectContextFrame.

    Args:
        context_frame: ProjectContextFrame from compute_context_frame()
        project_name: Project display name
        page_context: Current page (e.g., "brd:workflows", "canvas", "prototype")
        focused_entity: Entity the user is currently viewing
        conversation_context: Optional context from a conversation starter

    Returns:
        Complete system prompt string (~2-3K tokens)
    """
    sections = []

    # 1. Base identity
    sections.append(SMART_CHAT_BASE.format(project_name=project_name))

    # 2. Current state (from state_snapshot — already ~500 tokens)
    if context_frame.state_snapshot:
        sections.append(f"# Current Project State\n{context_frame.state_snapshot}")

    # 3. Phase + progress
    phase_label = {
        "empty": "Getting Started — project needs initial context",
        "seeding": "Seeding — gathering core requirements and artifacts",
        "building": "Building — filling in structural details",
        "refining": "Refining — confirming and polishing for handoff",
    }.get(context_frame.phase.value, context_frame.phase.value)

    sections.append(
        f"# Phase\n{phase_label} ({int(context_frame.phase_progress * 100)}% complete)"
    )

    # 4. Active gaps (top 5, terse)
    gap_lines = []
    for action in context_frame.actions[:5]:
        source_tag = {"structural": "GAP", "signal": "NEED", "knowledge": "UNKNOWN"}.get(
            action.gap_source, "GAP"
        )
        gap_lines.append(f"- [{source_tag}] {action.sentence}")

    if gap_lines:
        sections.append(
            f"# Active Gaps ({context_frame.total_gap_count} total)\n"
            + "\n".join(gap_lines)
        )

    # 5. Workflow context (for domain reasoning)
    if context_frame.workflow_context and context_frame.workflow_context != "No workflows defined yet.":
        sections.append(f"# Workflows\n{context_frame.workflow_context}")

    # 6. Memory hints (low-confidence beliefs, contradictions)
    if context_frame.memory_hints:
        hints = "\n".join(f"- {h}" for h in context_frame.memory_hints[:3])
        sections.append(f"# Memory (low confidence — verify before citing)\n{hints}")

    # 7. Page awareness
    if page_context:
        page_labels = {
            "brd": "BRD View (all sections)",
            "brd:workflows": "BRD — Workflows section",
            "brd:features": "BRD — Features section",
            "brd:personas": "BRD — Personas section",
            "brd:stakeholders": "BRD — Stakeholders section",
            "brd:data_entities": "BRD — Data Entities section",
            "brd:business_context": "BRD — Business Context section",
            "brd:constraints": "BRD — Constraints section",
            "brd:questions": "BRD — Open Questions section",
            "canvas": "Canvas View (drag-and-drop)",
            "prototype": "Prototype Review",
            "overview": "Project Overview",
        }
        label = page_labels.get(page_context, page_context)
        sections.append(f"# Page\nUser is on: {label}")

        # 7b. Per-page tool guidance
        guidance = PAGE_TOOL_GUIDANCE.get(page_context)
        if guidance:
            sections.append(f"# Page-Specific Guidance\n{guidance}")

    # 8. Focused entity
    if focused_entity:
        etype = focused_entity.get("type", "entity")
        edata = focused_entity.get("data", {})
        ename = edata.get("title") or edata.get("name") or edata.get("question", "")
        if ename:
            sections.append(
                f"# Currently Viewing\n{etype}: \"{ename}\"\nPrioritize this entity in your responses."
            )

    # 9. Conversation starter context
    if conversation_context:
        sections.append(
            "# Active Discussion Context\n"
            "The consultant opened chat from a conversation starter. Here's what prompted this:\n"
            f"{conversation_context}\n"
            "Use this to give specific, informed responses. Reference the same evidence."
        )

    # 10. Capabilities
    sections.append(SMART_CHAT_CAPABILITIES)

    # 10. Smart conversation patterns
    sections.append(SMART_CONVERSATION_PATTERNS)

    # 11. Entity counts summary
    counts = context_frame.entity_counts
    if counts:
        count_parts = [f"{v} {k}" for k, v in counts.items() if v]
        if count_parts:
            sections.append(f"# Entity Counts\n{', '.join(count_parts)}")

    return "\n\n".join(sections)
