"""
Memory Hooks - Automatic memory updates after significant actions.

This module provides a centralized way to update project memory
after important events like:
- Signal processing completion
- DI Agent tool execution
- Entity creation/updates
- Strategic foundation runs

The goal is to ensure the DI Agent always has up-to-date context.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.project_memory import (
    add_decision,
    add_learning,
    update_project_memory,
    get_or_create_project_memory,
)
from app.db.di_cache import invalidate_cache

logger = get_logger(__name__)


async def log_signal_processed(
    project_id: UUID,
    signal_id: UUID,
    signal_type: str,
    pipeline_type: str,
    results: dict,
) -> None:
    """
    Log memory update after signal processing completes.

    Records what was extracted from the signal and updates project understanding.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID that was processed
        signal_type: Type of signal (email, transcript, document, etc.)
        pipeline_type: Which pipeline was used (standard or bulk)
        results: Processing results with entity counts
    """
    try:
        # Extract counts from results
        features = results.get("features_created", 0) + results.get("features_found", 0)
        personas = results.get("personas_created", 0) + results.get("personas_found", 0)
        vp_steps = results.get("vp_steps_created", 0)
        drivers = results.get("business_drivers_created", 0)
        stakeholders = results.get("stakeholders_created", 0) + results.get("stakeholders_found", 0)

        total_entities = features + personas + vp_steps + drivers + stakeholders

        if total_entities == 0:
            # No entities extracted, skip memory update
            logger.debug(f"No entities extracted from signal {signal_id}, skipping memory update")
            return

        # Build entity summary
        entity_parts = []
        if features > 0:
            entity_parts.append(f"{features} feature{'s' if features > 1 else ''}")
        if personas > 0:
            entity_parts.append(f"{personas} persona{'s' if personas > 1 else ''}")
        if vp_steps > 0:
            entity_parts.append(f"{vp_steps} value path step{'s' if vp_steps > 1 else ''}")
        if drivers > 0:
            entity_parts.append(f"{drivers} business driver{'s' if drivers > 1 else ''}")
        if stakeholders > 0:
            entity_parts.append(f"{stakeholders} stakeholder{'s' if stakeholders > 1 else ''}")

        entity_summary = ", ".join(entity_parts)

        # Log as a decision (what was extracted)
        add_decision(
            project_id=project_id,
            title=f"Processed {signal_type} signal",
            decision=f"Extracted {entity_summary} from {signal_type} signal via {pipeline_type} pipeline",
            rationale=f"Automated signal processing identified {total_entities} total entities",
            evidence_signal_ids=[str(signal_id)],
            decision_type="signal_processing",
            decided_by="system",
            confidence=0.9 if pipeline_type == "bulk" else 0.8,
        )

        # Invalidate DI cache so agent knows to re-analyze
        invalidate_cache(project_id, reason=f"New signal processed: {signal_type}")

        logger.info(
            f"Logged memory update for signal {signal_id}",
            extra={
                "project_id": str(project_id),
                "signal_id": str(signal_id),
                "entities_extracted": total_entities,
            },
        )

    except Exception as e:
        # Non-fatal - don't break signal processing if memory update fails
        logger.warning(f"Failed to log signal processing to memory: {e}")


async def log_tool_execution_batch(
    project_id: UUID,
    tools_executed: list[dict],
) -> None:
    """
    Log memory update after DI Agent tool execution batch.

    Called after the DI Agent finishes executing one or more tools.
    Batches multiple tool executions into a single memory update.

    Args:
        project_id: Project UUID
        tools_executed: List of tool execution results, each with:
            - name: Tool name
            - success: Whether it succeeded
            - result: Tool result data
    """
    if not tools_executed:
        return

    try:
        # Filter successful executions
        successful = [t for t in tools_executed if t.get("success", False)]
        failed = [t for t in tools_executed if not t.get("success", False)]

        if not successful and not failed:
            return

        # Build summary
        tool_names = [t["name"] for t in successful]

        # Skip pure read operations
        read_only_tools = {"read_project_memory", "analyze_gaps", "analyze_requirements_gaps"}
        action_tools = [t for t in tool_names if t not in read_only_tools]

        if not action_tools and not failed:
            # Only read operations, no need to log
            return

        if action_tools:
            # Log what actions were taken
            action_summary = ", ".join(action_tools)
            add_decision(
                project_id=project_id,
                title="DI Agent actions",
                decision=f"Executed: {action_summary}",
                rationale="DI Agent autonomous analysis and action",
                decision_type="agent_action",
                decided_by="di_agent",
                confidence=0.85,
            )

        if failed:
            # Log failures as learnings to avoid repeating
            for tool in failed:
                error = tool.get("error", "Unknown error")
                add_learning(
                    project_id=project_id,
                    title=f"Tool failure: {tool['name']}",
                    context=f"DI Agent attempted to run {tool['name']}",
                    learning=f"Tool failed with: {error}. Avoid retrying without addressing the issue.",
                    learning_type="mistake",
                    domain="agent",
                )

        # Invalidate cache after actions
        if action_tools:
            invalidate_cache(project_id, reason=f"DI Agent executed: {', '.join(action_tools)}")

        logger.info(
            f"Logged DI Agent tool batch to memory",
            extra={
                "project_id": str(project_id),
                "successful_tools": len(successful),
                "failed_tools": len(failed),
            },
        )

    except Exception as e:
        logger.warning(f"Failed to log tool execution batch to memory: {e}")


async def log_entity_change(
    project_id: UUID,
    entity_type: str,
    entity_id: str,
    entity_name: str,
    action: str,
    source: str = "user",
    signal_ids: list[str] | None = None,
) -> None:
    """
    Log memory update when an entity is created, updated, or deleted.

    Args:
        project_id: Project UUID
        entity_type: Type of entity (feature, persona, vp_step, etc.)
        entity_id: Entity UUID
        entity_name: Human-readable name
        action: What happened (created, updated, deleted, enriched)
        source: Who made the change (user, system, di_agent, enrichment)
        signal_ids: Related signal IDs if any
    """
    try:
        # Only log significant changes (not minor updates)
        significant_actions = {"created", "deleted", "enriched", "merged"}
        if action not in significant_actions:
            return

        add_decision(
            project_id=project_id,
            title=f"{entity_type.title()} {action}: {entity_name[:50]}",
            decision=f"{action.title()} {entity_type} '{entity_name}'",
            rationale=f"Entity change by {source}",
            evidence_signal_ids=signal_ids,
            evidence_entity_ids=[entity_id],
            decision_type="entity_change",
            decided_by=source,
            confidence=0.95 if source == "user" else 0.8,
        )

        # Invalidate cache
        invalidate_cache(project_id, reason=f"Entity {action}: {entity_type}")

        logger.debug(f"Logged entity change to memory: {entity_type} {action}")

    except Exception as e:
        logger.warning(f"Failed to log entity change to memory: {e}")


async def log_foundation_run(
    project_id: UUID,
    results: dict,
) -> None:
    """
    Log memory update after strategic foundation run.

    Args:
        project_id: Project UUID
        results: Foundation run results
    """
    try:
        # Summarize what was extracted
        parts = []
        if results.get("company_info_extracted"):
            parts.append("company info")
        if results.get("business_drivers_count", 0) > 0:
            parts.append(f"{results['business_drivers_count']} business drivers")
        if results.get("competitors_count", 0) > 0:
            parts.append(f"{results['competitors_count']} competitors")
        if results.get("stakeholders_count", 0) > 0:
            parts.append(f"{results['stakeholders_count']} stakeholders")

        if not parts:
            return

        summary = ", ".join(parts)

        add_decision(
            project_id=project_id,
            title="Strategic foundation analysis",
            decision=f"Extracted {summary} from project signals",
            rationale="Ran strategic foundation to build project context",
            decision_type="foundation",
            decided_by="system",
            confidence=0.9,
        )

        # Update project understanding with high-level summary
        if results.get("company_info_extracted"):
            company_info = results.get("company_info", {})
            understanding = f"Client: {company_info.get('name', 'Unknown')}. "
            if company_info.get("industry"):
                understanding += f"Industry: {company_info['industry']}. "
            if company_info.get("description"):
                understanding += company_info["description"][:200]

            update_project_memory(
                project_id=project_id,
                project_understanding=understanding,
                updated_by="foundation_analysis",
            )

        invalidate_cache(project_id, reason="Strategic foundation completed")

        logger.info(f"Logged foundation run to memory: {summary}")

    except Exception as e:
        logger.warning(f"Failed to log foundation run to memory: {e}")


async def ensure_memory_initialized(project_id: UUID) -> None:
    """
    Ensure project memory exists, creating it if needed.

    Call this early in any flow that needs memory.
    """
    try:
        get_or_create_project_memory(project_id)
    except Exception as e:
        logger.warning(f"Failed to ensure memory initialized: {e}")


def get_full_project_context(project_id: UUID) -> dict:
    """
    Get comprehensive project context for DI Agent.

    Returns all available context without token limits.
    The caller can truncate if needed.

    Returns:
        Dict with:
        - memory: Full project memory
        - decisions: Recent decisions (last 20)
        - learnings: All learnings
        - mistakes: Mistakes to avoid
        - state_summary: Current project state
    """
    from app.db.project_memory import (
        get_project_memory,
        get_recent_decisions,
        get_learnings,
        get_mistakes_to_avoid,
    )
    from app.core.state_snapshot import get_state_snapshot

    try:
        memory = get_project_memory(project_id)
        decisions = get_recent_decisions(project_id, limit=20)
        learnings = get_learnings(project_id, limit=50)
        mistakes = get_mistakes_to_avoid(project_id, limit=10)
        state = get_state_snapshot(project_id, max_chars=5000)  # More generous limit

        return {
            "memory": memory,
            "decisions": decisions,
            "learnings": learnings,
            "mistakes": mistakes,
            "state_summary": state,
            "has_content": bool(memory or decisions or learnings),
        }
    except Exception as e:
        logger.warning(f"Failed to get full project context: {e}")
        return {
            "memory": None,
            "decisions": [],
            "learnings": [],
            "mistakes": [],
            "state_summary": "",
            "has_content": False,
        }
