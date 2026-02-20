"""Intelligence Briefing Engine — the main orchestrator.

Composes deterministic engines + LLM chains into a single IntelligenceBriefing.
5-phase parallel execution:
  Phase 1: Data loading (reuses _load_project_data from action_engine)
  Phase 2: Deterministic (tensions, hypotheses, gaps, heartbeat)
  Phase 3: Temporal diff (DB queries + optional Haiku summary)
  Phase 4: Narrative (Sonnet, only if cache stale)
  Phase 5: Assembly
"""

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core.schemas_actions import ContextPhase, TerseAction
from app.core.schemas_briefing import (
    ActiveTension,
    BriefingSituation,
    BriefingWhatChanged,
    ConversationStarter,
    Hypothesis,
    IntelligenceBriefing,
    ProjectHeartbeat,
    WhatYouShouldKnow,
)

logger = logging.getLogger(__name__)


async def compute_intelligence_briefing(
    project_id: UUID,
    user_id: UUID | None = None,
    max_actions: int = 5,
    force_refresh: bool = False,
) -> IntelligenceBriefing:
    """Compute the full intelligence briefing.

    Parallel execution of deterministic + LLM phases.
    Narrative is cached in synthesized_memory_cache.briefing_sections.
    """
    from app.core.action_engine import (
        _build_structural_gaps,
        _build_workflow_context,
        _build_workflow_context_display,
        _count_entities,
        _detect_context_phase,
        _load_project_data,
    )

    # ── Phase 1: Data Loading ──
    data = await _load_project_data(project_id)
    phase, phase_progress = _detect_context_phase(data)
    workflow_context = _build_workflow_context(data["workflow_pairs"])
    workflow_context_display = _build_workflow_context_display(data["workflow_pairs"])
    entity_counts = _count_entities(data)

    # Load project name
    project_name = _get_project_name(project_id)

    # Load session data for temporal diff
    session = None
    since_timestamp = None
    if user_id:
        from app.db.consultant_sessions import get_session
        session = get_session(project_id, user_id)
        if session:
            ts = session.get("last_briefing_at")
            if ts:
                since_timestamp = _parse_timestamp(ts)

    # Load memory data
    beliefs = _load_beliefs(project_id)
    insights = _load_insights(project_id)

    # Check briefing cache
    cached_sections = _get_cached_briefing(project_id)
    cache_stale = force_refresh or not cached_sections or _is_cache_stale(project_id)

    # ── Phase 2: Deterministic (parallel-safe, <50ms) ──
    from app.core.hypothesis_engine import get_active_hypotheses, scan_for_hypotheses
    from app.core.temporal_diff import compute_temporal_diff
    from app.core.tension_detector import detect_tensions

    tensions = detect_tensions(project_id)
    hypotheses = _merge_hypotheses(
        scan_for_hypotheses(project_id),
        get_active_hypotheses(project_id),
    )
    structural_gaps = _build_structural_gaps(data["workflow_pairs"], phase.value)
    heartbeat = _build_heartbeat(project_id, data, entity_counts)
    temporal_diff = compute_temporal_diff(project_id, since_timestamp)

    # ── Phase 3: Temporal diff summary (Haiku, conditional) ──
    if temporal_diff.changes:
        try:
            from app.core.temporal_diff import summarize_changes
            temporal_diff.change_summary = await summarize_changes(
                temporal_diff.changes,
                project_id=str(project_id),
            )
        except Exception as e:
            logger.warning(f"Change summary failed (non-fatal): {e}")

    # ── Phase 4: Narrative (Sonnet, only if cache stale) ──
    situation_narrative = ""
    what_you_should_know = WhatYouShouldKnow()
    narrative_cached = False

    if cache_stale:
        try:
            from app.chains.generate_briefing_narrative import generate_briefing_narrative

            tension_dicts = [t.model_dump() for t in tensions]
            temporal_data = {
                "since_label": temporal_diff.since_label,
                "change_summary": temporal_diff.change_summary,
                "counts": temporal_diff.counts,
                "changes": [c.model_dump(mode="json") for c in temporal_diff.changes[:5]],
            } if temporal_diff.changes else None
            result = await generate_briefing_narrative(
                project_name=project_name,
                beliefs=beliefs,
                insights=insights,
                tensions=tension_dicts,
                entity_summary=entity_counts,
                workflow_context=workflow_context_display,
                stakeholder_names=data.get("stakeholder_names", []),
                phase=phase.value,
                phase_progress=phase_progress,
                project_id=str(project_id),
                temporal_changes=temporal_data,
            )
            situation_narrative = result.get("situation_narrative", "")
            what_you_should_know = WhatYouShouldKnow(
                narrative=result.get("what_you_should_know_narrative", ""),
                bullets=result.get("what_you_should_know_bullets", []),
            )

            # Cache the narrative
            _cache_briefing_sections(project_id, {
                "situation_narrative": situation_narrative,
                "what_you_should_know": what_you_should_know.model_dump(),
            })
        except Exception as e:
            logger.warning(f"Narrative generation failed (non-fatal): {e}")
    else:
        # Use cached narrative
        narrative_cached = True
        situation_narrative = cached_sections.get("situation_narrative", "")
        wysk_data = cached_sections.get("what_you_should_know", {})
        what_you_should_know = WhatYouShouldKnow(
            narrative=wysk_data.get("narrative", ""),
            bullets=wysk_data.get("bullets", []),
        )

    # ── Phase 4b: Hypothesis test suggestions (Haiku, conditional) ──
    new_hypotheses = [h for h in hypotheses if h.status.value == "proposed" and not h.test_suggestion]
    if new_hypotheses:
        try:
            from app.core.hypothesis_engine import generate_test_suggestions
            suggestions = await generate_test_suggestions(
                new_hypotheses,
                project_id=str(project_id),
            )
            # Merge suggestions back
            suggestion_map = {s["hypothesis_id"]: s["test_suggestion"] for s in suggestions}
            for h in hypotheses:
                if h.hypothesis_id in suggestion_map:
                    h.test_suggestion = suggestion_map[h.hypothesis_id]
        except Exception as e:
            logger.warning(f"Test suggestions failed (non-fatal): {e}")

    # ── Phase 4c: Conversation Starters (Sonnet, conditional) ──
    conversation_starters: list[ConversationStarter] = []
    starter_situation_summary = ""
    if cache_stale or not cached_sections or not cached_sections.get("conversation_starters"):
        try:
            from app.chains.generate_conversation_starter import generate_conversation_starters

            signal_evidence = _load_signal_evidence(project_id)
            cs_result = await generate_conversation_starters(
                phase=phase.value,
                phase_progress=phase_progress,
                signal_evidence=signal_evidence,
                workflow_context=workflow_context_display,
                entity_counts=entity_counts,
                beliefs=beliefs[:3],
                open_questions=data.get("questions", [])[:3],
                project_id=str(project_id),
                project_name=project_name,
            )
            starter_situation_summary = cs_result.get("situation_summary", "")
            conversation_starters = cs_result.get("starters", [])
            # Cache alongside narrative
            existing_cache = cached_sections or {}
            _cache_briefing_sections(project_id, {
                **existing_cache,
                "conversation_starters": [s.model_dump(mode="json") for s in conversation_starters],
                "starter_situation_summary": starter_situation_summary,
            })
        except Exception as e:
            logger.warning(f"Conversation starters failed (non-fatal): {e}")
    else:
        # Load from cache
        cs_list = cached_sections.get("conversation_starters", [])
        for cs_data in cs_list:
            try:
                conversation_starters.append(ConversationStarter(**cs_data))
            except Exception:
                pass
        starter_situation_summary = cached_sections.get("starter_situation_summary", "")

    # ── Phase 5: Actions (reuse v3 context frame) ──
    actions = _build_terse_actions(structural_gaps, max_actions)

    # ── Phase 6: Assembly ──
    # Use starter situation summary as the primary narrative (2 sentences)
    # Fall back to the longer narrative if starters didn't produce one
    final_narrative = starter_situation_summary or situation_narrative

    situation = BriefingSituation(
        narrative=final_narrative,
        project_name=project_name,
        phase=phase,
        phase_progress=phase_progress,
        key_stakeholders=data.get("stakeholder_names", [])[:5],
        entity_summary=entity_counts,
    )

    briefing = IntelligenceBriefing(
        situation=situation,
        what_changed=temporal_diff,
        what_you_should_know=what_you_should_know,
        tensions=tensions,
        hypotheses=hypotheses,
        heartbeat=heartbeat,
        actions=actions,
        conversation_starters=conversation_starters,
        computed_at=datetime.now(timezone.utc),
        narrative_cached=narrative_cached,
        phase=phase,
    )

    # Record session timestamp
    if user_id:
        try:
            from app.db.consultant_sessions import upsert_session
            upsert_session(project_id, user_id)
        except Exception as e:
            logger.warning(f"Session upsert failed (non-fatal): {e}")

    return briefing


def compute_heartbeat_only(project_id: UUID) -> ProjectHeartbeat:
    """Instant heartbeat — no LLM, always fresh. <100ms."""
    from app.core.action_engine import _count_entities

    data = _load_sync_data(project_id)
    entity_counts = _count_entities(data) if data else {}
    return _build_heartbeat(project_id, data or {}, entity_counts)


# =============================================================================
# Internal helpers
# =============================================================================


def _get_project_name(project_id: UUID) -> str:
    """Load project name from DB."""
    try:
        from app.db.supabase_client import get_supabase
        sb = get_supabase()
        result = sb.table("projects").select("name").eq("id", str(project_id)).maybe_single().execute()
        return (result.data or {}).get("name", "Project")
    except Exception:
        return "Project"


def _load_beliefs(project_id: UUID) -> list[dict]:
    """Load active beliefs for narrative generation."""
    try:
        from app.db.memory_graph import get_active_beliefs
        return get_active_beliefs(project_id, limit=15)
    except Exception:
        return []


def _load_insights(project_id: UUID) -> list[dict]:
    """Load insights for narrative generation."""
    try:
        from app.db.memory_graph import get_insights
        return get_insights(project_id, limit=10)
    except Exception:
        return []


def _parse_timestamp(ts) -> datetime | None:
    """Parse a timestamp from DB (string or datetime)."""
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt
        except (ValueError, TypeError):
            return None
    return None


def _get_cached_briefing(project_id: UUID) -> dict | None:
    """Load cached briefing sections from synthesized_memory_cache."""
    try:
        from app.db.supabase_client import get_supabase
        sb = get_supabase()
        result = (
            sb.table("synthesized_memory_cache")
            .select("briefing_sections, is_stale")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        )
        if result.data and not result.data.get("is_stale"):
            sections = result.data.get("briefing_sections")
            if sections and isinstance(sections, dict) and sections.get("situation_narrative"):
                return sections
        return None
    except Exception:
        return None


def _is_cache_stale(project_id: UUID) -> bool:
    """Check if briefing cache is stale."""
    try:
        from app.db.supabase_client import get_supabase
        sb = get_supabase()
        result = (
            sb.table("synthesized_memory_cache")
            .select("is_stale")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        )
        if result.data:
            return result.data.get("is_stale", True)
        return True  # No cache = stale
    except Exception:
        return True


def _cache_briefing_sections(project_id: UUID, sections: dict) -> None:
    """Upsert briefing sections into synthesized_memory_cache."""
    try:
        from app.db.supabase_client import get_supabase
        sb = get_supabase()

        # Try update first
        result = (
            sb.table("synthesized_memory_cache")
            .update({
                "briefing_sections": json.dumps(sections),
                "narrative_version": 1,  # Will increment on subsequent updates
            })
            .eq("project_id", str(project_id))
            .execute()
        )

        if not result.data:
            # No row exists, insert
            sb.table("synthesized_memory_cache").insert({
                "project_id": str(project_id),
                "content": "",  # Required NOT NULL
                "briefing_sections": json.dumps(sections),
                "narrative_version": 1,
            }).execute()
    except Exception as e:
        logger.warning(f"Failed to cache briefing sections: {e}")


def _build_heartbeat(
    project_id: UUID,
    data: dict,
    entity_counts: dict,
) -> ProjectHeartbeat:
    """Build instant heartbeat from loaded data."""
    from app.db.supabase_client import get_supabase

    # Completeness: structural field fill rate
    completeness = _compute_field_completeness(data)

    # Confirmation percentage
    confirmation_pct = _compute_confirmation_pct(data)

    # Days since last signal
    days_since = None
    try:
        sb = get_supabase()
        result = (
            sb.table("signals")
            .select("created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            last_signal_ts = _parse_timestamp(result.data[0].get("created_at"))
            if last_signal_ts:
                days_since = (datetime.now(timezone.utc) - last_signal_ts).days
    except Exception:
        pass

    # Memory depth
    memory_depth = 0
    try:
        from app.db.memory_graph import get_graph_stats
        stats = get_graph_stats(project_id)
        memory_depth = stats.get("total_nodes", 0)
    except Exception:
        pass

    # Stale entities
    stale_count = 0
    try:
        sb = get_supabase()
        for table in ["features", "personas", "vp_steps"]:
            result = (
                sb.table(table)
                .select("id", count="exact")
                .eq("project_id", str(project_id))
                .eq("is_stale", True)
                .execute()
            )
            stale_count += result.count or 0
    except Exception:
        pass

    # Scope alerts (same heuristics as health endpoint)
    scope_alerts = []
    features = data.get("features") or []
    workflow_pairs = data.get("workflow_pairs") or []

    # Scope creep: >=50% features low priority
    if features:
        low_prio = sum(
            1 for f in features
            if f.get("priority_group") in ("could_have", "out_of_scope")
        )
        if low_prio >= len(features) * 0.5 and len(features) > 3:
            scope_alerts.append("scope_creep")

    # Workflow complexity: >15 total steps
    total_steps = sum(
        len(p.get("current_steps") or []) + len(p.get("future_steps") or [])
        for p in workflow_pairs
    )
    if total_steps > 15:
        scope_alerts.append("workflow_complexity")

    return ProjectHeartbeat(
        completeness_pct=round(completeness, 1),
        confirmation_pct=round(confirmation_pct, 1),
        days_since_last_signal=days_since,
        memory_depth=memory_depth,
        stale_entity_count=stale_count,
        scope_alerts=scope_alerts,
        entity_counts=entity_counts,
    )


def _compute_field_completeness(data: dict) -> float:
    """Compute structural field fill rate across workflow steps."""
    total_fields = 0
    filled_fields = 0

    for pair in data.get("workflow_pairs") or []:
        for step in pair.get("current_steps") or []:
            total_fields += 3  # actor, pain, time
            if step.get("actor_persona_id"):
                filled_fields += 1
            if step.get("pain_description"):
                filled_fields += 1
            if step.get("time_minutes"):
                filled_fields += 1
        for step in pair.get("future_steps") or []:
            total_fields += 1  # benefit
            if step.get("benefit_description"):
                filled_fields += 1

    if total_fields == 0:
        return 0.0
    return (filled_fields / total_fields) * 100


def _compute_confirmation_pct(data: dict) -> float:
    """Compute % of entities confirmed by consultant or client."""
    confirmed_statuses = {"confirmed_consultant", "confirmed_client"}
    total = 0
    confirmed = 0

    for f in data.get("features") or []:
        total += 1
        if f.get("confirmation_status") in confirmed_statuses:
            confirmed += 1

    for p in data.get("personas") or []:
        total += 1
        if p.get("confirmation_status") in confirmed_statuses:
            confirmed += 1

    for pair in data.get("workflow_pairs") or []:
        for step in (pair.get("current_steps") or []) + (pair.get("future_steps") or []):
            total += 1
            if step.get("confirmation_status") in confirmed_statuses:
                confirmed += 1

    if total == 0:
        return 0.0
    return (confirmed / total) * 100


def _merge_hypotheses(scanned: list[Hypothesis], active: list[Hypothesis]) -> list[Hypothesis]:
    """Merge scanned candidates with already-active hypotheses, deduplicate."""
    seen_ids = set()
    merged = []

    # Active first (they have status already)
    for h in active:
        if h.hypothesis_id not in seen_ids:
            seen_ids.add(h.hypothesis_id)
            merged.append(h)

    # Then scanned candidates
    for h in scanned:
        if h.hypothesis_id not in seen_ids:
            seen_ids.add(h.hypothesis_id)
            merged.append(h)

    return merged[:10]


def _build_terse_actions(structural_gaps: list, max_actions: int) -> list[TerseAction]:
    """Convert structural gaps to terse actions (same as v3 context frame)."""
    from app.core.schemas_actions import CTAType

    actions = []
    for g in structural_gaps[:max_actions]:
        actions.append(
            TerseAction(
                action_id=g.gap_id,
                sentence=g.sentence,
                cta_type=CTAType.INLINE_ANSWER,
                cta_label="Answer",
                gap_source="structural",
                gap_type=g.gap_type,
                entity_type=g.entity_type,
                entity_id=g.entity_id,
                entity_name=g.entity_name,
                question_placeholder=g.question_placeholder,
                impact_score=g.score,
                priority=len(actions) + 1,
            )
        )

    return actions


def _load_signal_evidence(project_id: UUID) -> dict:
    """Load recent signal previews and entity evidence for conversation starter.

    Returns:
        {signal_previews: [...], evidence_excerpts: [...]}
    """
    from app.db.supabase_client import get_supabase

    signal_previews = []
    evidence_excerpts = []

    try:
        sb = get_supabase()

        # Last 5 signals with raw_text preview
        result = (
            sb.table("signals")
            .select("id, source_label, signal_type, raw_text, created_at")
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        for sig in result.data or []:
            raw = sig.get("raw_text") or ""
            signal_previews.append({
                "source_label": sig.get("source_label") or sig.get("source", ""),
                "signal_type": sig.get("signal_type", ""),
                "raw_text_preview": raw[:500],
            })

        # Entity evidence: pluck first evidence item from entities
        for table, name_col in [
            ("features", "name"),
            ("personas", "name"),
            ("vp_steps", "title"),
            ("business_drivers", "description"),
        ]:
            try:
                ent_result = (
                    sb.table(table)
                    .select(f"id, {name_col}, evidence")
                    .eq("project_id", str(project_id))
                    .limit(5)
                    .execute()
                )
                for ent in ent_result.data or []:
                    evidence = ent.get("evidence") or []
                    if isinstance(evidence, list) and evidence:
                        ev = evidence[0]
                        excerpt = ev.get("excerpt", "")
                        if excerpt and len(evidence_excerpts) < 15:
                            evidence_excerpts.append({
                                "entity_name": ent.get(name_col, ""),
                                "excerpt": excerpt[:280],
                                "source_label": ev.get("source_type", "signal"),
                            })
            except Exception:
                continue

    except Exception as e:
        logger.warning(f"Signal evidence load failed (non-fatal): {e}")

    return {
        "signal_previews": signal_previews,
        "evidence_excerpts": evidence_excerpts,
    }


def _load_sync_data(project_id: UUID) -> dict | None:
    """Minimal sync data load for heartbeat (no async boundary)."""
    try:
        from app.db.features import list_features
        from app.db.personas import list_personas
        from app.db.workflows import get_workflow_pairs

        return {
            "workflow_pairs": get_workflow_pairs(project_id),
            "features": list_features(project_id),
            "personas": list_personas(project_id),
            "drivers": [],
            "questions": [],
            "stakeholder_names": [],
        }
    except Exception as e:
        logger.warning(f"Sync data load failed: {e}")
        return None
