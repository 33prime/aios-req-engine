"""Database operations for project memory system.

Provides persistent memory for the Design Intelligence Agent:
- Semantic memory: Project understanding document
- Episodic memory: Decision log with rationale
- Procedural memory: Learnings and patterns
"""

from datetime import datetime
from typing import Any, Literal, Optional
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# =============================================================================
# Project Memory Document (Semantic Memory)
# =============================================================================


def get_project_memory(project_id: UUID) -> dict | None:
    """
    Get the project memory document.

    Returns the full memory including the markdown content
    and structured sections.
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("project_memory")
            .select("*")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        )
        # maybe_single() returns None for response.data if no row exists
        # Also handle case where response itself is None (edge case)
        if response is None:
            logger.debug(f"No response from project_memory query for {project_id}")
            return None
        if not hasattr(response, 'data'):
            logger.debug(f"Response has no data attribute for {project_id}")
            return None
        return response.data
    except Exception as e:
        # Table might not exist yet, or other DB error
        logger.warning(f"Failed to get project memory for {project_id}: {e}")
        return None


def get_or_create_project_memory(project_id: UUID) -> dict:
    """
    Get project memory, creating it if it doesn't exist.

    Returns the memory document, initializing with a template if new.
    """
    existing = get_project_memory(project_id)
    if existing:
        return existing

    # Create with initial template
    return create_project_memory(project_id)


def create_project_memory(project_id: UUID) -> dict:
    """
    Create a new project memory document with initial template.
    """
    supabase = get_supabase()

    initial_content = f"""# Project Memory
Last Updated: {datetime.utcnow().isoformat()}Z

## Project Understanding
*No understanding documented yet. The DI Agent will update this section as it learns about the project.*

## Client Profile
*Client preferences and patterns will be documented here as interactions occur.*

## Key Decisions & Rationale
*No decisions logged yet.*

## Current Strategy
*Strategy will be documented once initial analysis is complete.*

## Learning Journal
*Learnings will be recorded as the project progresses.*

## Open Questions
*Questions will be added as gaps are identified.*

## Milestones Achieved
*Milestones will be recorded as gates are satisfied.*
"""

    try:
        response = (
            supabase.table("project_memory")
            .insert({
                "project_id": str(project_id),
                "content": initial_content,
                "project_understanding": "",
                "client_profile": {},
                "current_strategy": {},
                "open_questions": [],
            })
            .execute()
        )
        logger.info(f"Created project memory for {project_id}")
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to create project memory for {project_id}: {e}")
        raise


def update_project_memory(
    project_id: UUID,
    content: str | None = None,
    project_understanding: str | None = None,
    client_profile: dict | None = None,
    current_strategy: dict | None = None,
    open_questions: list | None = None,
    updated_by: str = "di_agent",
) -> dict:
    """
    Update the project memory document.

    Only updates fields that are provided (not None).
    """
    supabase = get_supabase()

    # Ensure memory exists
    get_or_create_project_memory(project_id)

    # Build update payload
    payload: dict[str, Any] = {"last_updated_by": updated_by}

    if content is not None:
        payload["content"] = content
        # Estimate tokens (rough: 4 chars per token)
        payload["tokens_estimate"] = len(content) // 4

    if project_understanding is not None:
        payload["project_understanding"] = project_understanding

    if client_profile is not None:
        payload["client_profile"] = client_profile

    if current_strategy is not None:
        payload["current_strategy"] = current_strategy

    if open_questions is not None:
        payload["open_questions"] = open_questions

    try:
        response = (
            supabase.table("project_memory")
            .update(payload)
            .eq("project_id", str(project_id))
            .execute()
        )
        logger.info(f"Updated project memory for {project_id}")
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to update project memory for {project_id}: {e}")
        raise


def get_memory_for_context(project_id: UUID, max_tokens: int = 2000) -> str:
    """
    Get a token-limited version of memory for agent context.

    Prioritizes recent decisions, active learnings, and open questions.
    Truncates if necessary to fit token budget.
    """
    memory = get_project_memory(project_id)
    if not memory:
        return "No project memory exists yet."

    content = memory.get("content", "")

    # If within budget, return full content
    estimated_tokens = len(content) // 4
    if estimated_tokens <= max_tokens:
        return content

    # Otherwise, truncate intelligently
    # Keep the first part (understanding) and last part (recent decisions)
    lines = content.split("\n")
    truncated_lines = []
    current_tokens = 0
    max_chars = max_tokens * 4

    # Always include header and understanding
    for line in lines:
        if current_tokens * 4 + len(line) > max_chars * 0.7:
            break
        truncated_lines.append(line)
        current_tokens += len(line) // 4

    truncated_lines.append("\n... [Memory truncated for context window] ...\n")

    # Add most recent section from the end
    remaining_budget = max_chars - (current_tokens * 4)
    end_section = "\n".join(lines[-20:])  # Last 20 lines
    if len(end_section) < remaining_budget:
        truncated_lines.append(end_section)

    return "\n".join(truncated_lines)


# =============================================================================
# Decision Log (Episodic Memory)
# =============================================================================


def add_decision(
    project_id: UUID,
    title: str,
    decision: str,
    rationale: str,
    alternatives_considered: list[dict] | None = None,
    evidence_signal_ids: list[UUID] | None = None,
    evidence_entity_ids: list[UUID] | None = None,
    decided_by: str = "di_agent",
    confidence: float = 0.8,
    decision_type: str = "feature",
    affects_gates: list[str] | None = None,
) -> dict:
    """
    Log a decision with full rationale.

    This creates episodic memory of WHY something was done.
    """
    supabase = get_supabase()

    payload = {
        "project_id": str(project_id),
        "title": title,
        "decision": decision,
        "rationale": rationale,
        "alternatives_considered": alternatives_considered or [],
        "evidence_signal_ids": [str(s) for s in (evidence_signal_ids or [])],
        "evidence_entity_ids": [str(e) for e in (evidence_entity_ids or [])],
        "decided_by": decided_by,
        "confidence": confidence,
        "decision_type": decision_type,
        "affects_gates": affects_gates or [],
    }

    try:
        response = supabase.table("project_decisions").insert(payload).execute()
        logger.info(f"Added decision for {project_id}: {title}")

        # Trigger compaction check (background)
        trigger_compaction_check(project_id)

        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to add decision for {project_id}: {e}")
        raise


def get_recent_decisions(
    project_id: UUID,
    limit: int = 10,
    decision_type: str | None = None,
    active_only: bool = True,
) -> list[dict]:
    """
    Get recent decisions for a project.
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("project_decisions")
            .select("*")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(limit)
        )

        if active_only:
            query = query.eq("is_active", True)

        if decision_type:
            query = query.eq("decision_type", decision_type)

        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get decisions for {project_id}: {e}")
        return []


def supersede_decision(
    decision_id: UUID,
    new_decision_id: UUID,
    reason: str,
) -> dict:
    """
    Mark a decision as superseded by a newer one.

    This preserves history while indicating which decision is current.
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("project_decisions")
            .update({
                "is_active": False,
                "superseded_by": str(new_decision_id),
                "superseded_at": datetime.utcnow().isoformat(),
                "supersede_reason": reason,
            })
            .eq("id", str(decision_id))
            .execute()
        )
        logger.info(f"Superseded decision {decision_id} with {new_decision_id}")
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to supersede decision {decision_id}: {e}")
        raise


# =============================================================================
# Learning Journal (Procedural Memory)
# =============================================================================


def add_learning(
    project_id: UUID,
    title: str,
    context: str,
    learning: str,
    learning_type: Literal["insight", "mistake", "pattern", "terminology"] = "insight",
    domain: str | None = None,
    source_signal_id: UUID | None = None,
    source_action_log_id: UUID | None = None,
) -> dict:
    """
    Record a learning in the project memory.

    Learnings help the agent avoid repeating mistakes and
    apply successful patterns.
    """
    supabase = get_supabase()

    payload = {
        "project_id": str(project_id),
        "title": title,
        "context": context,
        "learning": learning,
        "learning_type": learning_type,
        "domain": domain,
        "source_signal_id": str(source_signal_id) if source_signal_id else None,
        "source_action_log_id": str(source_action_log_id) if source_action_log_id else None,
    }

    try:
        response = supabase.table("project_learnings").insert(payload).execute()
        logger.info(f"Added learning for {project_id}: {title}")

        # Trigger compaction check (background)
        trigger_compaction_check(project_id)

        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to add learning for {project_id}: {e}")
        raise


def get_learnings(
    project_id: UUID,
    limit: int = 20,
    learning_type: str | None = None,
    domain: str | None = None,
) -> list[dict]:
    """
    Get learnings for a project.

    Prioritizes frequently applied learnings.
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("project_learnings")
            .select("*")
            .eq("project_id", str(project_id))
            .order("times_applied", desc=True)
            .order("created_at", desc=True)
            .limit(limit)
        )

        if learning_type:
            query = query.eq("learning_type", learning_type)

        if domain:
            query = query.eq("domain", domain)

        response = query.execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to get learnings for {project_id}: {e}")
        return []


def apply_learning(learning_id: UUID) -> dict:
    """
    Record that a learning was applied (reinforcement).

    Increases times_applied counter and updates last_applied_at.
    """
    supabase = get_supabase()

    try:
        # First get current count
        current = (
            supabase.table("project_learnings")
            .select("times_applied")
            .eq("id", str(learning_id))
            .single()
            .execute()
        )

        times_applied = (current.data.get("times_applied") or 0) + 1

        response = (
            supabase.table("project_learnings")
            .update({
                "times_applied": times_applied,
                "last_applied_at": datetime.utcnow().isoformat(),
            })
            .eq("id", str(learning_id))
            .execute()
        )
        return response.data[0] if response.data else {}
    except Exception as e:
        logger.error(f"Failed to apply learning {learning_id}: {e}")
        raise


def get_mistakes_to_avoid(project_id: UUID, limit: int = 5) -> list[dict]:
    """
    Get recent mistakes to help agent avoid repeating them.
    """
    return get_learnings(
        project_id=project_id,
        learning_type="mistake",
        limit=limit,
    )


# =============================================================================
# Memory Access Tracking (Reinforcement/Decay)
# =============================================================================


def log_memory_access(
    project_id: UUID,
    memory_type: str,
    memory_id: UUID,
    accessed_by: str = "di_agent",
    access_context: str | None = None,
) -> None:
    """
    Log that a memory was accessed.

    Used for decay calculations and reinforcement.
    """
    supabase = get_supabase()

    try:
        supabase.table("memory_access_log").insert({
            "project_id": str(project_id),
            "memory_type": memory_type,
            "memory_id": str(memory_id),
            "accessed_by": accessed_by,
            "access_context": access_context,
        }).execute()
    except Exception as e:
        # Don't fail on access logging - it's not critical
        logger.warning(f"Failed to log memory access: {e}")


# =============================================================================
# Memory Synthesis (for updating the document)
# =============================================================================


def synthesize_memory_document(
    project_id: UUID,
    project_name: str = "Unknown Project",
) -> str:
    """
    Synthesize a complete memory document from structured data.

    Combines decisions, learnings, and questions into a coherent narrative.
    """
    memory = get_project_memory(project_id)
    decisions = get_recent_decisions(project_id, limit=20)
    learnings = get_learnings(project_id, limit=15)

    # Build the document
    now = datetime.utcnow().isoformat()

    sections = [
        f"# Project Memory: {project_name}",
        f"Last Updated: {now}Z",
        "",
        "## Project Understanding",
        memory.get("project_understanding", "*Not yet documented*") if memory else "*Not yet documented*",
        "",
        "## Client Profile",
    ]

    if memory and memory.get("client_profile"):
        profile = memory["client_profile"]
        for key, value in profile.items():
            sections.append(f"- **{key.replace('_', ' ').title()}**: {value}")
    else:
        sections.append("*Not yet documented*")

    sections.extend(["", "## Key Decisions & Rationale", ""])

    if decisions:
        for d in decisions[:10]:  # Limit to 10 most recent
            created = d.get("created_at", "")[:10]
            sections.append(f"### {created}: {d.get('title', 'Untitled')}")
            sections.append(f"- **Decision**: {d.get('decision', '')}")
            sections.append(f"- **Rationale**: {d.get('rationale', '')}")
            if d.get("decided_by"):
                sections.append(f"- **Decided by**: {d.get('decided_by')}")
            sections.append("")
    else:
        sections.append("*No decisions logged yet.*")

    sections.extend(["", "## Current Strategy", ""])

    if memory and memory.get("current_strategy"):
        strategy = memory["current_strategy"]
        if strategy.get("focus"):
            sections.append(f"**Active Focus**: {strategy['focus']}")
        if strategy.get("hypotheses"):
            sections.append("**Working Hypotheses**:")
            for h in strategy["hypotheses"]:
                sections.append(f"- {h}")
    else:
        sections.append("*Strategy not yet documented*")

    sections.extend(["", "## Learning Journal", ""])

    if learnings:
        for l in learnings[:10]:
            emoji = {"insight": "💡", "mistake": "⚠️", "pattern": "🔄", "terminology": "📝"}.get(
                l.get("learning_type", "insight"), "📌"
            )
            sections.append(f"### {emoji} {l.get('title', 'Untitled')}")
            sections.append(f"- **Context**: {l.get('context', '')}")
            sections.append(f"- **Learning**: {l.get('learning', '')}")
            if l.get("times_applied", 0) > 0:
                sections.append(f"- *Applied {l['times_applied']} times*")
            sections.append("")
    else:
        sections.append("*No learnings recorded yet.*")

    sections.extend(["", "## Open Questions", ""])

    if memory and memory.get("open_questions"):
        for i, q in enumerate(memory["open_questions"], 1):
            status = "☑️" if q.get("resolved") else "☐"
            sections.append(f"{i}. {status} {q.get('question', q) if isinstance(q, dict) else q}")
    else:
        sections.append("*No open questions.*")

    sections.extend(["", "## Milestones Achieved", ""])
    sections.append("*Milestones will be added as gates are satisfied.*")

    return "\n".join(sections)


def regenerate_memory_document(project_id: UUID, project_name: str = "Project") -> dict:
    """
    Regenerate the memory document from structured data and save it.
    """
    content = synthesize_memory_document(project_id, project_name)
    result = update_project_memory(project_id, content=content, updated_by="system")

    # Check if compaction needed after regeneration
    trigger_compaction_check(project_id)

    return result


# =============================================================================
# Auto-Compaction
# =============================================================================


def trigger_compaction_check(project_id: UUID) -> None:
    """
    Check if memory needs compaction and trigger it if so.

    This is called after memory-growing operations to keep memory lean.
    Runs in a background thread to avoid blocking the main operation.
    """
    import threading

    def _check_and_compact():
        try:
            from app.chains.compact_memory import maybe_compact_memory

            result = maybe_compact_memory(project_id)
            if result and result.get("compacted"):
                logger.info(
                    f"Auto-compacted memory for {project_id}: "
                    f"{result.get('before_tokens')} → {result.get('after_tokens')} tokens"
                )
        except Exception as e:
            logger.warning(f"Auto-compaction check failed for {project_id}: {e}")

    # Run in background to avoid blocking
    thread = threading.Thread(target=_check_and_compact, daemon=True)
    thread.start()
