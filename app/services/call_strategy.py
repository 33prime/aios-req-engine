"""Call strategy brief generation — full 2.5 retrieval pipeline.

Pipeline: parallel data load → parallel intelligence → 2.5 retrieval → Sonnet synthesis → mission themes.
"""

import asyncio
import json
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Phase string → CollaborationPhase enum mapping
_PHASE_MAP = {
    "pre_discovery": "PRE_DISCOVERY",
    "discovery": "DISCOVERY",
    "validation": "VALIDATION",
    "prototype": "PROTOTYPE",
    "proposal": "PROPOSAL",
    "build": "BUILD",
    "delivery": "DELIVERY",
}


async def generate_strategy_brief(
    project_id: UUID,
    meeting_id: UUID | None = None,
    stakeholder_ids: list[UUID] | None = None,
    recording_id: UUID | None = None,
) -> dict:
    """Generate a pre-call strategy brief using full 2.5 architecture.

    4-phase pipeline:
      1. Parallel data load (state_snapshot, awareness, stakeholders, confidence, horizon)
      2. Parallel intelligence (tensions, gap clusters, hypotheses, prep config, readiness, ambiguity)
      3. Full 2.5 retrieval (composite query from intelligence signals)
      4. Single Sonnet synthesis → mission themes

    Returns the persisted brief dict.
    """
    from app.db.call_strategy import create_strategy_brief
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # =========================================================================
    # Phase 1: Parallel Data Load
    # =========================================================================
    (
        state_snapshot,
        awareness,
        stakeholder_intel,
        confidence_state,
        horizon_state,
        workflow_pairs,
        flow_overview,
    ) = await asyncio.gather(
        _load_state_snapshot(project_id),
        _load_awareness(project_id),
        asyncio.to_thread(
            _load_stakeholder_intel, project_id, meeting_id, stakeholder_ids, sb
        ),
        _load_confidence_state(project_id),
        _load_horizon_state(project_id),
        asyncio.to_thread(_load_workflow_pairs_safe, project_id),
        asyncio.to_thread(_load_flow_overview_safe, project_id),
    )

    # =========================================================================
    # Phase 2: Parallel Intelligence
    # =========================================================================
    phase_str = awareness.get("phase", "discovery")
    phase_enum = _resolve_phase(phase_str)

    tensions, gap_clusters, hypotheses, prep_config, readiness, ambiguity = (
        await asyncio.gather(
            asyncio.to_thread(_detect_tensions_safe, project_id),
            asyncio.to_thread(_detect_gap_clusters_safe, project_id),
            asyncio.to_thread(_get_hypotheses_safe, project_id),
            asyncio.to_thread(_get_prep_config_safe, phase_enum),
            asyncio.to_thread(
                _compute_readiness_snapshot, project_id, stakeholder_intel, sb
            ),
            asyncio.to_thread(_compute_ambiguity_snapshot, project_id),
        )
    )

    # =========================================================================
    # Phase 3: Full 2.5 Retrieval
    # =========================================================================
    query = _build_retrieval_query(
        tensions, gap_clusters, hypotheses, stakeholder_intel, prep_config,
        workflow_pairs, flow_overview,
    )

    retrieval_result, retrieval_context = await _run_retrieval(
        query, project_id, phase_str
    )

    # =========================================================================
    # Phase 4: Single Sonnet Synthesis → Mission Themes
    # =========================================================================
    mission_themes = await _synthesize_mission_themes(
        state_snapshot=state_snapshot,
        stakeholder_intel=stakeholder_intel,
        tensions=tensions,
        gap_clusters=gap_clusters,
        hypotheses=hypotheses,
        confidence_state=confidence_state,
        retrieval_context=retrieval_context,
        phase_str=phase_str,
        prep_config=prep_config,
        workflow_pairs=workflow_pairs,
        flow_overview=flow_overview,
    )

    # =========================================================================
    # Persist
    # =========================================================================
    retrieval_metadata = _build_retrieval_metadata(
        query, retrieval_result, tensions, gap_clusters
    )
    meeting_frame = _build_meeting_frame(phase_str, prep_config)

    brief = create_strategy_brief(
        project_id=project_id,
        meeting_id=meeting_id,
        recording_id=recording_id,
        stakeholder_intel=stakeholder_intel,
        mission_themes=mission_themes,
        deal_readiness_snapshot=readiness,
        ambiguity_snapshot=ambiguity,
        meeting_frame=meeting_frame,
        retrieval_metadata=retrieval_metadata,
        project_awareness_snapshot=awareness,
        generated_by="system",
        model="claude-sonnet-4-6",
        # Keep old fields empty for backward compat
        call_goals=[],
        mission_critical_questions=[],
        focus_areas=[],
        critical_requirements=[],
    )

    logger.info(
        f"Strategy brief generated: project={project_id}, brief={brief.get('id')}, "
        f"themes={len(mission_themes)}"
    )
    return brief


# ============================================================================
# Phase 1: Data loaders
# ============================================================================


async def _load_state_snapshot(project_id: UUID) -> str:
    """Load state snapshot (~500-750 tokens of named entities)."""
    try:
        from app.core.state_snapshot import get_state_snapshot

        return await asyncio.to_thread(get_state_snapshot, project_id)
    except Exception as e:
        logger.warning(f"Failed to load state snapshot: {e}")
        return ""


async def _load_awareness(project_id: UUID) -> dict:
    """Load project awareness snapshot."""
    try:
        from app.context.project_awareness import load_project_awareness

        awareness = await load_project_awareness(project_id)
        return {
            "phase": awareness.active_phase,
            "flow_summary": (
                awareness.flows[0].summary if awareness.flows else "No active flows"
            ),
            "whats_working": (
                awareness.whats_working[:3] if awareness.whats_working else []
            ),
            "whats_next": awareness.whats_next[:5] if awareness.whats_next else [],
            "whats_discovered": (
                awareness.whats_discovered[:3] if awareness.whats_discovered else []
            ),
        }
    except Exception as e:
        logger.warning(f"Failed to load project awareness: {e}")
        return {"phase": "unknown", "flow_summary": "", "whats_next": []}


async def _load_confidence_state(project_id: UUID) -> dict:
    """Load confidence state (low-confidence beliefs, active domains)."""
    try:
        from app.context.intelligence_signals import load_confidence_state

        return await load_confidence_state(project_id)
    except Exception as e:
        logger.warning(f"Failed to load confidence state: {e}")
        return {"low_confidence_beliefs": [], "active_domains": 0, "recent_insights": []}


async def _load_horizon_state(project_id: UUID) -> dict:
    """Load horizon state (H1/H2/H3 readiness)."""
    try:
        from app.context.intelligence_signals import load_horizon_state

        return await load_horizon_state(project_id)
    except Exception as e:
        logger.warning(f"Failed to load horizon state: {e}")
        return {
            "is_crystallized": False,
            "blocking_outcomes": 0,
            "blocking_details": [],
            "compound_decisions": 0,
        }


def _load_stakeholder_intel(
    project_id: UUID,
    meeting_id: UUID | None,
    stakeholder_ids: list[UUID] | None,
    sb,
) -> list[dict]:
    """Load rich stakeholder intelligence — enrichment fields + assignments + beliefs."""
    try:
        # If meeting_id provided but no explicit stakeholder_ids, look up participants
        if meeting_id and not stakeholder_ids:
            try:
                meeting = (
                    sb.table("meetings")
                    .select("stakeholder_ids")
                    .eq("id", str(meeting_id))
                    .single()
                    .execute()
                )
                if meeting.data and meeting.data.get("stakeholder_ids"):
                    stakeholder_ids = [
                        UUID(sid) for sid in meeting.data["stakeholder_ids"]
                    ]
            except Exception:
                pass

        # Pull enrichment fields — not just the 5 basics
        select_fields = (
            "id, name, role, influence_level, stakeholder_type, "
            "priorities, concerns, domain_expertise, "
            "engagement_level, engagement_strategy, risk_if_disengaged, "
            "decision_authority, approval_required_for, veto_power_over, "
            "win_conditions, key_concerns, "
            "communication_preferences, preferred_channel, "
            "linked_persona_id, profile_completeness, "
            "topic_mentions, notes"
        )

        query = (
            sb.table("stakeholders")
            .select(select_fields)
            .eq("project_id", str(project_id))
        )

        if stakeholder_ids:
            query = query.in_("id", [str(sid) for sid in stakeholder_ids])

        result = query.limit(20).execute()
        stakeholders = result.data or []

        # Batch-load stakeholder assignments (what entities they own/review)
        stakeholder_id_strs = [s["id"] for s in stakeholders if s.get("id")]
        assignments_by_sh: dict[str, list[dict]] = {}
        if stakeholder_id_strs:
            try:
                assignments = (
                    sb.table("stakeholder_assignments")
                    .select("stakeholder_id, entity_type, assignment_type, status")
                    .in_("stakeholder_id", stakeholder_id_strs)
                    .limit(100)
                    .execute()
                ).data or []
                for a in assignments:
                    sid = a.get("stakeholder_id", "")
                    assignments_by_sh.setdefault(sid, []).append(a)
            except Exception:
                pass

        intel = []
        for s in stakeholders:
            # Beliefs from memory (keep existing approach)
            belief_concerns: list[str] = []
            try:
                beliefs = (
                    sb.table("memory_nodes")
                    .select("summary")
                    .eq("project_id", str(project_id))
                    .eq("node_type", "belief")
                    .ilike("summary", f"%{s.get('name', '')}%")
                    .limit(3)
                    .execute()
                ).data or []
                belief_concerns = [b["summary"] for b in beliefs]
            except Exception:
                pass

            # Merge key_concerns: DB enrichment + belief summaries
            db_concerns = s.get("key_concerns") or []
            merged_concerns = list(dict.fromkeys(db_concerns + belief_concerns))

            # Assignments summary
            sh_assignments = assignments_by_sh.get(s.get("id", ""), [])
            owns_entities = [
                a["entity_type"]
                for a in sh_assignments
                if a.get("assignment_type") in ("knowledge_owner", "validate")
            ]

            intel.append(
                {
                    "name": s.get("name", ""),
                    "role": s.get("role"),
                    "influence": s.get("influence_level", "unknown"),
                    "stakeholder_type": s.get("stakeholder_type", "user"),
                    "key_concerns": merged_concerns,
                    "approach_notes": s.get("engagement_strategy") or _stakeholder_approach(s),
                    # Enrichment fields
                    "priorities": s.get("priorities") or [],
                    "domain_expertise": s.get("domain_expertise") or [],
                    "engagement_level": s.get("engagement_level"),
                    "decision_authority": s.get("decision_authority"),
                    "approval_required_for": s.get("approval_required_for") or [],
                    "veto_power_over": s.get("veto_power_over") or [],
                    "win_conditions": s.get("win_conditions") or [],
                    "risk_if_disengaged": s.get("risk_if_disengaged"),
                    "preferred_channel": s.get("preferred_channel"),
                    "profile_completeness": s.get("profile_completeness", 0),
                    "topic_mentions": s.get("topic_mentions") or {},
                    "owns_entities": owns_entities,
                }
            )

        return intel
    except Exception as e:
        logger.warning(f"Failed to load stakeholder intel: {e}")
        return []


def _load_workflow_pairs_safe(project_id: UUID) -> list:
    """Load workflow current/future pairs, return empty list on failure."""
    try:
        from app.db.workflows import get_workflow_pairs

        return get_workflow_pairs(project_id)
    except Exception as e:
        logger.warning(f"Failed to load workflow pairs: {e}")
        return []


def _load_flow_overview_safe(project_id: UUID) -> dict | None:
    """Load solution flow overview, return None on failure."""
    try:
        from app.db.solution_flow import get_flow_overview

        return get_flow_overview(project_id)
    except Exception as e:
        logger.warning(f"Failed to load flow overview: {e}")
        return None


def _stakeholder_approach(s: dict) -> str:
    """Generate approach notes based on stakeholder type."""
    st = s.get("stakeholder_type", "")
    name = s.get("name", "this person")
    if st == "champion":
        return f"Leverage {name} as an internal advocate — align on shared vision."
    if st == "sponsor":
        return f"Focus on ROI and strategic value for {name}."
    if st == "blocker":
        return f"Address {name}'s concerns directly — understand objections."
    if st == "influencer":
        return f"Gather {name}'s input early — their opinion carries weight."
    return f"Build rapport with {name} — understand their perspective."


# ============================================================================
# Phase 2: Intelligence loaders (safe wrappers)
# ============================================================================


def _resolve_phase(phase_str: str):
    """Map phase string to CollaborationPhase enum."""
    try:
        from app.core.schemas_collaboration import CollaborationPhase

        mapped = _PHASE_MAP.get(phase_str, "DISCOVERY")
        return CollaborationPhase[mapped]
    except Exception:
        from app.core.schemas_collaboration import CollaborationPhase

        return CollaborationPhase.DISCOVERY


def _detect_tensions_safe(project_id: UUID) -> list:
    """Detect tensions, return empty list on failure."""
    try:
        from app.core.tension_detector import detect_tensions

        return detect_tensions(project_id)
    except Exception as e:
        logger.warning(f"Failed to detect tensions: {e}")
        return []


def _detect_gap_clusters_safe(project_id: UUID) -> list:
    """Detect gap clusters via intelligence loop, return empty list on failure."""
    try:
        import asyncio as _aio

        from app.core.gap_detector import detect_gaps
        from app.core.intelligence_loop import run_intelligence_loop

        gaps = _aio.run(detect_gaps(project_id))
        return run_intelligence_loop(gaps, project_id)
    except Exception as e:
        logger.warning(f"Failed to detect gap clusters: {e}")
        return []


def _get_hypotheses_safe(project_id: UUID) -> list:
    """Get active hypotheses, return empty list on failure."""
    try:
        from app.core.hypothesis_engine import get_active_hypotheses

        return get_active_hypotheses(project_id)
    except Exception as e:
        logger.warning(f"Failed to get hypotheses: {e}")
        return []


def _get_prep_config_safe(phase_enum):
    """Get stage-aware prep config, return fallback on failure."""
    try:
        from app.agents.prep_system.prep_config import get_prep_config

        return get_prep_config(phase_enum)
    except Exception as e:
        logger.warning(f"Failed to get prep config: {e}")
        return None


def _compute_readiness_snapshot(
    project_id: UUID, stakeholder_intel: list[dict], sb
) -> dict:
    """Compute deal readiness snapshot for the brief."""
    try:
        from app.core.deal_readiness import compute_deal_readiness, compute_gaps_and_risks
        from app.db.memory_graph import get_graph_stats

        stats = get_graph_stats(project_id)

        # Load client data
        client_data = {}
        try:
            client = (
                sb.table("client_profiles")
                .select("*")
                .eq("project_id", str(project_id))
                .limit(1)
                .execute()
            )
            if client.data:
                client_data = client.data[0]
        except Exception:
            pass

        # Load vision
        vision = None
        try:
            proj = (
                sb.table("projects")
                .select("vision")
                .eq("id", str(project_id))
                .single()
                .execute()
            )
            vision = proj.data.get("vision") if proj.data else None
        except Exception:
            pass

        # Load stakeholders in the format the function expects
        stakeholders_raw = []
        try:
            sh = (
                sb.table("stakeholders")
                .select("id, name, stakeholder_type, influence_level, role")
                .eq("project_id", str(project_id))
                .execute()
            )
            stakeholders_raw = sh.data or []
        except Exception:
            pass

        components, total_score = compute_deal_readiness(
            project_id, stakeholders_raw, stats, vision, client_data, sb
        )
        gaps = compute_gaps_and_risks(
            stakeholders_raw, stats, vision, client_data, project_id, sb
        )

        return {
            "score": round(total_score, 1),
            "components": [
                {
                    "name": c.name,
                    "score": c.score,
                    "max": 100,
                    "details": c.details,
                }
                for c in components
            ],
            "gaps_and_risks": [
                {
                    "title": g.message,
                    "severity": g.severity,
                    "description": g.message,
                }
                for g in gaps
            ],
        }
    except Exception as e:
        logger.warning(f"Failed to compute readiness snapshot: {e}")
        return {"score": 0, "components": [], "gaps_and_risks": []}


def _compute_ambiguity_snapshot(project_id: UUID) -> dict:
    """Compute ambiguity snapshot for the brief."""
    try:
        from app.core.discovery_protocol import categorize_beliefs, score_ambiguity

        categorized = categorize_beliefs(project_id)

        # score_ambiguity needs gap_clusters — load or use empty
        gap_clusters = []
        try:
            gap_clusters = _detect_gap_clusters_safe(project_id)
        except Exception:
            pass

        scores = score_ambiguity(project_id, categorized, gap_clusters)

        # Compute composite score
        if scores:
            composite = sum(s.score for s in scores.values()) / len(scores)
        else:
            composite = 0.0

        # Get top ambiguous beliefs (lowest confidence)
        top_beliefs = []
        try:
            from app.db.supabase_client import get_supabase

            sb = get_supabase()
            beliefs = (
                sb.table("memory_nodes")
                .select("summary, confidence, belief_domain")
                .eq("project_id", str(project_id))
                .eq("node_type", "belief")
                .eq("status", "active")
                .order("confidence")
                .limit(5)
                .execute()
            ).data or []
            top_beliefs = [
                {
                    "summary": b["summary"],
                    "confidence": b.get("confidence", 0.5),
                    "domain": b.get("belief_domain", "unknown"),
                }
                for b in beliefs
            ]
        except Exception:
            pass

        return {
            "score": round(composite, 2),
            "factors": {
                cat: {
                    "avg_confidence": round(s.avg_confidence, 2),
                    "contradiction_rate": round(s.contradiction_rate, 2),
                    "coverage_sparsity": round(s.coverage_sparsity, 2),
                    "gap_density": round(s.gap_density, 2),
                }
                for cat, s in scores.items()
            },
            "top_ambiguous_beliefs": top_beliefs,
        }
    except Exception as e:
        logger.warning(f"Failed to compute ambiguity snapshot: {e}")
        return {"score": 0, "factors": {}, "top_ambiguous_beliefs": []}


# ============================================================================
# Phase 3: Full 2.5 Retrieval
# ============================================================================


def _build_retrieval_query(
    tensions: list,
    gap_clusters: list,
    hypotheses: list,
    stakeholder_intel: list[dict],
    prep_config,
    workflow_pairs: list | None = None,
    flow_overview: dict | None = None,
) -> str:
    """Build composite retrieval query — workflow-first, then gaps, then concerns."""
    query_parts = []

    # Primary: Workflow pair names + pain points + linked features
    for wp in (workflow_pairs or [])[:3]:
        name = wp.get("name", "")
        if name:
            query_parts.append(name)
        for step in (wp.get("current_steps") or [])[:2]:
            pain = step.get("pain_description", "")
            if pain:
                query_parts.append(pain)
        for step in (wp.get("future_steps") or [])[:2]:
            benefit = step.get("benefit_description", "")
            if benefit:
                query_parts.append(benefit)
            for fn in (step.get("feature_names") or [])[:2]:
                if fn:
                    query_parts.append(fn)

    # Secondary: Solution flow step goals
    if flow_overview:
        for step in (flow_overview.get("steps") or [])[:3]:
            goal = step.get("goal", "")
            if goal:
                query_parts.append(goal)

    # Tertiary: Gap cluster themes (knowledge holes worth exploring)
    for gc in gap_clusters[:2]:
        theme = getattr(gc, "theme", "") or ""
        if theme:
            query_parts.append(theme)

    # Minimal: Stakeholder concerns
    for s in stakeholder_intel[:2]:
        for c in s.get("key_concerns", [])[:1]:
            if c:
                query_parts.append(c)

    goal = ""
    if prep_config:
        goal = getattr(prep_config, "question_goal", "") or ""

    if query_parts:
        query = f"Workflows and user journeys for {goal}: " + "; ".join(query_parts)
    else:
        query = f"Workflows and user journeys for {goal or 'upcoming meeting'}"

    return query


async def _run_retrieval(
    query: str, project_id: UUID, phase_str: str
) -> tuple:
    """Run full 2.5 retrieval. Returns (retrieval_result, formatted_context)."""
    try:
        from app.core.retrieval import retrieve
        from app.core.retrieval_format import format_retrieval_for_context

        retrieval_result = await retrieve(
            query=query,
            project_id=str(project_id),
            graph_depth=2,
            apply_recency=True,
            apply_confidence=True,
            max_rounds=2,
            top_k=15,
            include_graph_expansion=True,
            include_beliefs=True,
            include_entities=True,
            context_hint=f"Stage: {phase_str}. Preparing strategy brief for upcoming meeting.",
        )

        retrieval_context = format_retrieval_for_context(
            retrieval_result, max_tokens=4000, style="analysis"
        )

        return retrieval_result, retrieval_context
    except Exception as e:
        logger.warning(f"Failed to run 2.5 retrieval: {e}")
        # Return a stub result
        return _stub_retrieval_result(), ""


def _stub_retrieval_result():
    """Return a minimal stub when retrieval fails."""

    class _Stub:
        chunks = []
        entities = []
        beliefs = []
        source_queries = []

    return _Stub()


# ============================================================================
# Phase 4: Sonnet Synthesis
# ============================================================================


async def _synthesize_mission_themes(
    *,
    state_snapshot: str,
    stakeholder_intel: list[dict],
    tensions: list,
    gap_clusters: list,
    hypotheses: list,
    confidence_state: dict,
    retrieval_context: str,
    phase_str: str,
    prep_config,
    workflow_pairs: list | None = None,
    flow_overview: dict | None = None,
) -> list[dict]:
    """Synthesize discovery-first mission themes via a single Sonnet call."""
    try:
        from anthropic import Anthropic

        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            return _fallback_themes(
                tensions, gap_clusters, stakeholder_intel, prep_config, workflow_pairs
            )

        question_goal = ""
        categories = []
        if prep_config:
            question_goal = getattr(prep_config, "question_goal", "") or ""
            categories = getattr(prep_config, "question_categories", []) or []

        prompt = f"""You are an elite discovery consultant preparing a strategy playbook for an upcoming {phase_str} meeting. Your goal is to UNCOVER how people work — map their workflows, understand where pain lives, and let the solution emerge from real understanding.

## PROJECT STATE SNAPSHOT
{state_snapshot or "No state snapshot available."}

## MEETING PARTICIPANTS
{_format_stakeholders(stakeholder_intel)}

## WORKFLOWS & USER JOURNEYS (PRIMARY INTELLIGENCE)
### Current/Future Workflow Pairs
{_format_workflow_pairs(workflow_pairs or [])}

### Solution Flow Overview
{_format_solution_flow(flow_overview)}

## SUPPORTING INTELLIGENCE
### Knowledge Gaps
{_format_gap_clusters(gap_clusters)}

### Confidence State
{_format_confidence(confidence_state)}

### Background — Tensions
{_format_tensions(tensions) if tensions else "None detected."}

### Active Hypotheses
{_format_hypotheses(hypotheses)}

## EVIDENCE FROM PROJECT DATA
{retrieval_context or "No retrieval data available."}

## STAGE CONTEXT
Phase: {phase_str}
Goal: {question_goal}
Categories: {', '.join(categories) if categories else 'N/A'}

## YOUR TASK
Generate 3-5 Discovery Themes for this meeting. Each theme is a DISCOVERY MISSION — uncovering how people work, where pain lives, and what the ideal future looks like.

Each theme bundles:
1. **theme**: A crisp 5-10 word mission name — frame as "Map X", "Uncover X", "Explore X" (NEVER "Validate X" or "Confirm X")
2. **context**: 1-2 sentences on WHY this matters NOW — reference specific workflows, pain points, or knowledge gaps
3. **question**: A discovery-style question addressing a SPECIFIC participant BY NAME, referencing a SPECIFIC workflow/feature BY NAME. Use "Walk me through...", "Tell me about...", "How does your team currently...", "What happens when..."
4. **explores**: What workflow, feature, or user journey this question maps (workflow name, feature name, journey step)
5. **evidence**: Array of 1-3 specific data points from the project that inform this theme (entity names, workflow steps, pain points)
6. **confidence**: float 0-1 representing how well we understand this area (low = high priority to explore)
7. **priority**: "critical" | "high" | "medium" based on workflow understanding gaps and business impact

RULES:
- Frame as DISCOVERY — we're mapping territory, not auditing answers
- Prioritize where current-state pain is HIGH and workflow understanding is LOW
- Each question MUST name a specific participant and a specific workflow/feature
- Questions should invite storytelling: "Walk me through...", "Tell me about a time when...", "How does your team handle..."
- Reference actual workflows, pain points, and features from the data — no generic filler
- If a workflow pair shows high pain in current state, make it a theme
- If a solution flow step has low confidence, make it a theme

Return ONLY valid JSON array of theme objects."""

        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]

        themes = json.loads(text.strip())
        if not isinstance(themes, list):
            return _fallback_themes(
                tensions, gap_clusters, stakeholder_intel, prep_config, workflow_pairs
            )

        # Validate and normalize each theme — NO truncation
        validated = []
        for t in themes[:5]:
            if not isinstance(t, dict):
                continue
            validated.append({
                "theme": str(t.get("theme", "")),
                "context": str(t.get("context", "")),
                "question": str(t.get("question", "")),
                "explores": str(t.get("explores", "")),
                "evidence": [str(e) for e in (t.get("evidence") or [])[:3]],
                "confidence": min(1.0, max(0.0, float(t.get("confidence", 0.5)))),
                "priority": t.get("priority", "medium")
                if t.get("priority") in ("critical", "high", "medium")
                else "medium",
            })

        return validated if validated else _fallback_themes(
            tensions, gap_clusters, stakeholder_intel, prep_config, workflow_pairs
        )

    except Exception as e:
        logger.warning(f"Failed to synthesize mission themes via Sonnet: {e}")
        return _fallback_themes(
            tensions, gap_clusters, stakeholder_intel, prep_config, workflow_pairs
        )


def _fallback_themes(
    tensions: list,
    gap_clusters: list,
    stakeholder_intel: list[dict],
    prep_config,
    workflow_pairs: list | None = None,
) -> list[dict]:
    """Generate basic themes from intelligence data without LLM — workflow-first."""
    themes = []
    default_name = (
        stakeholder_intel[0]["name"] if stakeholder_intel else "the team"
    )

    # Primary: From workflow pairs
    for wp in (workflow_pairs or [])[:3]:
        name = wp.get("name", "Unknown workflow")
        pain_points = []
        features = []
        for step in wp.get("current_steps") or []:
            pain = step.get("pain_description", "")
            if pain:
                pain_points.append(pain)
            for fn in step.get("feature_names") or []:
                if fn and fn not in features:
                    features.append(fn)

        context = f"Current-state workflow '{name}' has pain points that need mapping."
        if pain_points:
            context = f"'{name}' has {len(pain_points)} pain point(s) to explore in the current workflow."

        themes.append({
            "theme": f"Map: {name}",
            "context": context,
            "question": f"Walk me through how {default_name}'s team currently handles {name}",
            "explores": name,
            "evidence": (pain_points[:2] + features[:1])[:3],
            "confidence": 0.2,
            "priority": "critical",
        })

    # Secondary: From gap clusters
    for gc in gap_clusters[:2]:
        theme_text = getattr(gc, "theme", "") or "Knowledge gap"
        total = getattr(gc, "total_gaps", 0)
        themes.append({
            "theme": f"Explore: {theme_text}",
            "context": f"{total} knowledge gaps clustered around '{theme_text}'.",
            "question": f"Tell me about how {default_name}'s team approaches {theme_text}",
            "explores": theme_text,
            "evidence": [],
            "confidence": 0.2,
            "priority": "high",
        })

    # Tertiary: From tensions (background, only if few themes so far)
    if len(themes) < 3:
        for t in tensions[:2]:
            summary = getattr(t, "summary", "") or "Unknown tension"
            involved = getattr(t, "involved_entities", []) or []
            entity_names = [e.get("name", "") for e in involved if e.get("name")]

            themes.append({
                "theme": f"Uncover: {summary}",
                "context": f"Tension detected that needs deeper understanding.",
                "question": f"How does {default_name}'s team handle {summary}?",
                "explores": entity_names[0] if entity_names else summary,
                "evidence": entity_names[:3],
                "confidence": getattr(t, "confidence", 0.3),
                "priority": "high",
            })

    return themes[:5]


# ============================================================================
# Formatters for Sonnet prompt
# ============================================================================


def _format_workflow_pairs(pairs: list) -> str:
    """Format workflow current/future pairs for the Sonnet prompt."""
    if not pairs:
        return "No workflow pairs mapped yet."
    lines = []
    for i, wp in enumerate(pairs[:5], 1):
        name = wp.get("name", "Unnamed")
        desc = wp.get("description", "")
        status = wp.get("confirmation_status", "ai_generated")
        lines.append(f"{i}. **{name}** (status: {status})")
        if desc:
            lines.append(f"   {desc}")

        # Current state steps
        current = wp.get("current_steps") or []
        if current:
            lines.append("   **Current State:**")
            for s in current[:4]:
                label = s.get("label", "Step")
                pain = s.get("pain_description", "")
                actor = s.get("actor_persona_name", "")
                auto = s.get("automation_level", "")
                line = f"   - {label}"
                if actor:
                    line += f" (actor: {actor})"
                if auto:
                    line += f" [{auto}]"
                lines.append(line)
                if pain:
                    lines.append(f"     Pain: {pain}")

        # Future state steps
        future = wp.get("future_steps") or []
        if future:
            lines.append("   **Future State:**")
            for s in future[:4]:
                label = s.get("label", "Step")
                benefit = s.get("benefit_description", "")
                features = s.get("feature_names") or []
                auto = s.get("automation_level", "")
                line = f"   - {label}"
                if auto:
                    line += f" [{auto}]"
                lines.append(line)
                if benefit:
                    lines.append(f"     Benefit: {benefit}")
                if features:
                    lines.append(f"     Features: {', '.join(features[:3])}")

        # ROI
        roi = wp.get("roi")
        if roi:
            saved = roi.get("time_saved_percent", 0)
            cost_yr = roi.get("cost_saved_per_year", 0)
            automated = roi.get("steps_automated", 0)
            total = roi.get("steps_total", 0)
            lines.append(
                f"   ROI: {saved}% time saved, ${cost_yr}/yr, "
                f"{automated}/{total} steps automated"
            )

    return "\n".join(lines)


def _format_solution_flow(flow: dict | None) -> str:
    """Format solution flow overview for the Sonnet prompt."""
    if not flow:
        return "No solution flow generated yet."
    lines = [f"**{flow.get('title', 'Solution Flow')}** (status: {flow.get('confirmation_status', 'unknown')})"]
    summary = flow.get("summary", "")
    if summary:
        lines.append(summary)
    for step in (flow.get("steps") or [])[:8]:
        idx = step.get("step_index", "?")
        title = step.get("title", "Step")
        goal = step.get("goal", "")
        actors = step.get("actors", [])
        status = step.get("confirmation_status", "")
        line = f"  {idx}. **{title}**"
        if actors:
            line += f" (actors: {', '.join(actors[:3])})"
        if status:
            line += f" [{status}]"
        lines.append(line)
        if goal:
            lines.append(f"     Goal: {goal}")
    return "\n".join(lines)


def _format_stakeholders(intel: list[dict]) -> str:
    """Format rich stakeholder intel as markdown for Sonnet prompt."""
    if not intel:
        return "No participant data available."
    lines = []
    for s in intel:
        name = s.get("name", "Unknown")
        role = s.get("role") or "No role specified"
        influence = s.get("influence", "unknown")
        stype = s.get("stakeholder_type", "")
        completeness = s.get("profile_completeness", 0)

        header = f"- **{name}** — {role} (influence: {influence}, type: {stype})"
        if completeness:
            header += f" [profile: {completeness}%]"
        lines.append(header)

        # Decision authority & power
        authority = s.get("decision_authority")
        if authority:
            lines.append(f"  Decision authority: {authority}")
        approvals = s.get("approval_required_for") or []
        if approvals:
            lines.append(f"  Approvals: {', '.join(approvals[:4])}")
        veto = s.get("veto_power_over") or []
        if veto:
            lines.append(f"  Veto power: {', '.join(veto[:3])}")

        # Engagement context
        engagement = s.get("engagement_level")
        if engagement:
            lines.append(f"  Engagement: {engagement}")
        risk = s.get("risk_if_disengaged")
        if risk:
            lines.append(f"  Risk if disengaged: {risk}")

        # Win conditions (what success looks like for them)
        wins = s.get("win_conditions") or []
        if wins:
            lines.append(f"  Win conditions: {'; '.join(wins[:3])}")

        # Concerns & priorities
        concerns = s.get("key_concerns") or []
        if concerns:
            for c in concerns[:3]:
                lines.append(f"  - Concern: {c}")
        priorities = s.get("priorities") or []
        if priorities:
            lines.append(f"  Priorities: {', '.join(str(p) for p in priorities[:4])}")

        # Domain expertise & topics
        expertise = s.get("domain_expertise") or []
        if expertise:
            lines.append(f"  Expertise: {', '.join(expertise[:5])}")
        topics = s.get("topic_mentions") or {}
        if topics:
            top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:4]
            lines.append(f"  Top topics: {', '.join(f'{t}({c})' for t, c in top_topics)}")

        # Entity ownership
        owns = s.get("owns_entities") or []
        if owns:
            lines.append(f"  Owns/validates: {', '.join(owns[:5])}")

        # Approach
        approach = s.get("approach_notes")
        if approach:
            lines.append(f"  Approach: {approach}")

    return "\n".join(lines)


def _format_tensions(tensions: list) -> str:
    """Format tensions as numbered list."""
    if not tensions:
        return "No tensions detected."
    lines = []
    for i, t in enumerate(tensions[:5], 1):
        summary = getattr(t, "summary", "Unknown")
        side_a = getattr(t, "side_a", "?")
        side_b = getattr(t, "side_b", "?")
        conf = getattr(t, "confidence", 0.0)
        lines.append(
            f"{i}. {summary} — '{side_a}' vs '{side_b}' (confidence: {conf:.1%})"
        )
    return "\n".join(lines)


def _format_gap_clusters(clusters: list) -> str:
    """Format gap clusters as list with top gaps."""
    if not clusters:
        return "No knowledge gaps detected."
    lines = []
    for i, gc in enumerate(clusters[:4], 1):
        theme = getattr(gc, "theme", "Unknown")
        total = getattr(gc, "total_gaps", 0)
        priority = getattr(gc, "priority_score", 0.0)
        gaps = getattr(gc, "gaps", [])
        lines.append(f"{i}. **{theme}** — {total} gaps (priority: {priority:.2f})")
        for g in gaps[:2]:
            desc = getattr(g, "description", "") or getattr(g, "gap_description", "")
            if desc:
                lines.append(f"   - {desc[:100]}")
    return "\n".join(lines)


def _format_hypotheses(hypotheses: list) -> str:
    """Format hypotheses as list."""
    if not hypotheses:
        return "No active hypotheses."
    lines = []
    for i, h in enumerate(hypotheses[:5], 1):
        statement = getattr(h, "statement", "Unknown")
        confidence = getattr(h, "confidence", 0.0)
        ev_for = getattr(h, "evidence_for", 0)
        ev_against = getattr(h, "evidence_against", 0)
        lines.append(
            f"{i}. {statement} (confidence: {confidence:.0%}, "
            f"+{ev_for}/-{ev_against} evidence)"
        )
    return "\n".join(lines)


def _format_confidence(state: dict) -> str:
    """Format confidence state as bullet list."""
    beliefs = state.get("low_confidence_beliefs", [])
    if not beliefs:
        return "No low-confidence beliefs flagged."
    lines = [f"Active domains: {state.get('active_domains', 0)}"]
    for b in beliefs[:5]:
        summary = b.get("summary", "Unknown")
        conf = b.get("confidence", 0.0)
        domain = b.get("domain", "?")
        lines.append(f"- [{domain}] {summary[:80]} (confidence: {conf:.0%})")
    return "\n".join(lines)


# ============================================================================
# Metadata builders
# ============================================================================


def _build_retrieval_metadata(
    query: str, retrieval_result, tensions: list, gap_clusters: list
) -> dict:
    """Build debug metadata for the retrieval step."""
    return {
        "query": query[:500],
        "chunk_count": len(getattr(retrieval_result, "chunks", [])),
        "entity_count": len(getattr(retrieval_result, "entities", [])),
        "belief_count": len(getattr(retrieval_result, "beliefs", [])),
        "graph_depth": 2,
        "tensions_count": len(tensions),
        "gap_clusters_count": len(gap_clusters),
    }


def _build_meeting_frame(phase_str: str, prep_config) -> dict:
    """Build meeting frame from phase and prep config."""
    frame = {"phase": phase_str}
    if prep_config:
        frame["question_goal"] = getattr(prep_config, "question_goal", "") or ""
        frame["categories"] = getattr(prep_config, "question_categories", []) or []
    return frame
