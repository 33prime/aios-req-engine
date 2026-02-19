"""Temporal diff engine — what changed since the consultant's last session.

Queries belief_history, enrichment_revisions, signals, and memory_nodes
to build a list of changes. Optionally summarizes via Haiku.
"""

import time
from datetime import datetime, timezone
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_briefing import (
    BriefingWhatChanged,
    ChangeType,
    TemporalChange,
)

logger = get_logger(__name__)


def compute_temporal_diff(
    project_id: UUID,
    since: datetime | None,
) -> BriefingWhatChanged:
    """Compute what changed since the given timestamp.

    Args:
        project_id: Project UUID
        since: Timestamp of last session (None = first visit, returns empty)

    Returns:
        BriefingWhatChanged with raw changes (no LLM summary yet)
    """
    if since is None:
        return BriefingWhatChanged(
            since_label="your first visit",
            counts={},
        )

    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    since_iso = since.isoformat()
    pid = str(project_id)
    changes: list[TemporalChange] = []
    counts: dict[str, int] = {}

    # 1. Belief history changes
    try:
        result = (
            supabase.table("belief_history")
            .select("node_id, change_type, change_reason, previous_confidence, new_confidence, created_at")
            .eq("project_id", pid)
            .gt("created_at", since_iso)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        for row in result.data or []:
            ct = row.get("change_type", "")
            delta = None
            if row.get("new_confidence") is not None and row.get("previous_confidence") is not None:
                delta = row["new_confidence"] - row["previous_confidence"]

            if ct in ("confidence_increase",):
                change_type = ChangeType.BELIEF_STRENGTHENED
            elif ct in ("confidence_decrease",):
                change_type = ChangeType.BELIEF_WEAKENED
            else:
                change_type = ChangeType.BELIEF_CREATED

            changes.append(
                TemporalChange(
                    change_type=change_type,
                    summary=row.get("change_reason", "Belief updated"),
                    confidence_delta=delta,
                    timestamp=row.get("created_at"),
                )
            )
        counts["beliefs_changed"] = len(result.data or [])
    except Exception as e:
        logger.warning(f"Belief history query failed: {e}")

    # 2. New signals since last session
    try:
        result = (
            supabase.table("signals")
            .select("id, signal_type, title, created_at")
            .eq("project_id", pid)
            .gt("created_at", since_iso)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        for row in result.data or []:
            changes.append(
                TemporalChange(
                    change_type=ChangeType.SIGNAL_PROCESSED,
                    summary=f"New {row.get('signal_type', 'signal')}: {row.get('title', 'untitled')[:60]}",
                    timestamp=row.get("created_at"),
                )
            )
        counts["new_signals"] = len(result.data or [])
    except Exception as e:
        logger.warning(f"Signals query failed: {e}")

    # 3. New memory nodes (facts + insights)
    try:
        result = (
            supabase.table("memory_nodes")
            .select("id, node_type, summary, created_at")
            .eq("project_id", pid)
            .in_("node_type", ["fact", "insight"])
            .eq("is_active", True)
            .gt("created_at", since_iso)
            .order("created_at", desc=True)
            .limit(15)
            .execute()
        )
        fact_count = 0
        insight_count = 0
        for row in result.data or []:
            ntype = row.get("node_type", "fact")
            if ntype == "fact":
                change_type = ChangeType.FACT_ADDED
                fact_count += 1
            else:
                change_type = ChangeType.INSIGHT_ADDED
                insight_count += 1

            changes.append(
                TemporalChange(
                    change_type=change_type,
                    summary=row.get("summary", "New knowledge added")[:80],
                    timestamp=row.get("created_at"),
                )
            )
        counts["new_facts"] = fact_count
        counts["new_insights"] = insight_count
    except Exception as e:
        logger.warning(f"Memory nodes query failed: {e}")

    # 4. Enrichment revisions (entity updates)
    try:
        result = (
            supabase.table("enrichment_revisions")
            .select("id, entity_type, entity_id, change_summary, created_at")
            .eq("project_id", pid)
            .gt("created_at", since_iso)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        for row in result.data or []:
            changes.append(
                TemporalChange(
                    change_type=ChangeType.ENTITY_UPDATED,
                    summary=row.get("change_summary", "Entity updated")[:80],
                    entity_type=row.get("entity_type"),
                    entity_id=row.get("entity_id"),
                    timestamp=row.get("created_at"),
                )
            )
        counts["entities_updated"] = len(result.data or [])
    except Exception as e:
        logger.warning(f"Enrichment revisions query failed: {e}")

    # Build since_label
    now = datetime.now(timezone.utc)
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    delta = now - since
    if delta.days == 0:
        since_label = "earlier today"
    elif delta.days == 1:
        since_label = "yesterday"
    elif delta.days < 7:
        since_label = f"{delta.days} days ago"
    else:
        since_label = f"{delta.days // 7} week{'s' if delta.days >= 14 else ''} ago"

    # Sort all changes by timestamp descending
    changes.sort(
        key=lambda c: c.timestamp.isoformat() if c.timestamp else "",
        reverse=True,
    )

    return BriefingWhatChanged(
        since_timestamp=since,
        since_label=since_label,
        changes=changes[:20],  # cap at 20
        counts=counts,
    )


async def summarize_changes(changes: list[TemporalChange], project_id: str | None = None) -> str:
    """Summarize temporal changes via Haiku (only when changes exist).

    Returns a 1-2 sentence summary. Cost: ~$0.0002.
    """
    if not changes:
        return ""

    from anthropic import AsyncAnthropic

    from app.core.config import get_settings
    from app.core.llm_usage import log_llm_usage

    HAIKU_MODEL = "claude-haiku-4-5-20251001"

    # Build terse change list
    lines = []
    for c in changes[:15]:
        lines.append(f"- [{c.change_type.value}] {c.summary}")
    changes_text = "\n".join(lines)

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    start = time.time()
    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=200,
        temperature=0.3,
        system="Summarize what changed in a project since the consultant's last visit. "
               "Write 1-2 sentences, conversational tone, highlighting the most important changes. "
               "Reference specific things (e.g. 'belief about onboarding time strengthened'). "
               "No filler, no markdown.",
        messages=[{"role": "user", "content": f"Changes since last session:\n{changes_text}"}],
    )
    duration_ms = int((time.time() - start) * 1000)

    usage = response.usage
    log_llm_usage(
        workflow="temporal_diff_summary",
        model=HAIKU_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain="summarize_changes",
        project_id=project_id,
    )

    return response.content[0].text.strip()
