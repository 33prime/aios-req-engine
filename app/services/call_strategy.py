"""Call strategy brief generation — leverages v2.5 architecture.

Pipeline: project awareness → stakeholder intel → deal readiness → ambiguity →
          mission-critical questions → call goals (LLM) → focus areas → persist.
"""

import json
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def generate_strategy_brief(
    project_id: UUID,
    meeting_id: UUID | None = None,
    stakeholder_ids: list[UUID] | None = None,
    recording_id: UUID | None = None,
) -> dict:
    """Generate a pre-call strategy brief using v2.5 architecture.

    Returns the persisted brief dict.
    """
    from app.db.call_strategy import create_strategy_brief
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # 1. Project Awareness
    project_awareness_snapshot = await _load_awareness(project_id)

    # 2. Stakeholder Intel
    stakeholder_intel = _load_stakeholder_intel(
        project_id, meeting_id, stakeholder_ids, sb
    )

    # 3. Deal Readiness
    deal_readiness_snapshot = _compute_readiness_snapshot(project_id, stakeholder_intel, sb)

    # 4. Ambiguity Score
    ambiguity_snapshot = _compute_ambiguity_snapshot(project_id)

    # 5. Mission-Critical Questions
    mission_critical_questions = await _generate_questions(
        project_id, stakeholder_ids=stakeholder_ids
    )

    # 5.5. Critical Requirements (2.5 retrieval)
    critical_requirements = await _retrieve_critical_requirements(
        project_id, stakeholder_intel, mission_critical_questions,
        project_awareness_snapshot,
    )

    # 6. Call Goals (LLM synthesis)
    call_goals = await _generate_call_goals(
        project_awareness_snapshot, ambiguity_snapshot, mission_critical_questions
    )

    # 7. Focus Areas
    focus_areas = _derive_focus_areas(
        call_goals, ambiguity_snapshot, project_awareness_snapshot
    )

    # Persist
    brief = create_strategy_brief(
        project_id=project_id,
        meeting_id=meeting_id,
        recording_id=recording_id,
        stakeholder_intel=stakeholder_intel,
        mission_critical_questions=mission_critical_questions,
        call_goals=call_goals,
        deal_readiness_snapshot=deal_readiness_snapshot,
        ambiguity_snapshot=ambiguity_snapshot,
        focus_areas=focus_areas,
        project_awareness_snapshot=project_awareness_snapshot,
        critical_requirements=critical_requirements,
        generated_by="system",
    )

    logger.info(
        f"Strategy brief generated: project={project_id}, brief={brief.get('id')}"
    )
    return brief


# ============================================================================
# Pipeline steps
# ============================================================================


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
            "whats_working": awareness.whats_working[:3] if awareness.whats_working else [],
            "whats_next": awareness.whats_next[:5] if awareness.whats_next else [],
            "whats_discovered": (
                awareness.whats_discovered[:3] if awareness.whats_discovered else []
            ),
        }
    except Exception as e:
        logger.warning(f"Failed to load project awareness: {e}")
        return {"phase": "unknown", "flow_summary": "", "whats_next": []}


def _load_stakeholder_intel(
    project_id: UUID,
    meeting_id: UUID | None,
    stakeholder_ids: list[UUID] | None,
    sb,
) -> list[dict]:
    """Load stakeholder intelligence."""
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

        query = (
            sb.table("stakeholders")
            .select("id, name, role, influence_level, stakeholder_type")
            .eq("project_id", str(project_id))
        )

        if stakeholder_ids:
            query = query.in_("id", [str(sid) for sid in stakeholder_ids])

        result = query.limit(20).execute()
        stakeholders = result.data or []

        intel = []
        for s in stakeholders:
            # Load any linked beliefs/memory about this stakeholder
            key_concerns = []
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
                key_concerns = [b["summary"] for b in beliefs]
            except Exception:
                pass

            intel.append(
                {
                    "name": s.get("name", ""),
                    "role": s.get("role"),
                    "influence": s.get("influence_level", "unknown"),
                    "stakeholder_type": s.get("stakeholder_type", "user"),
                    "key_concerns": key_concerns,
                    "approach_notes": _stakeholder_approach(s),
                }
            )

        return intel
    except Exception as e:
        logger.warning(f"Failed to load stakeholder intel: {e}")
        return []


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
            from app.core.briefing_engine import _detect_gap_clusters

            gap_clusters = _detect_gap_clusters(project_id)
        except Exception:
            pass

        scores = score_ambiguity(project_id, categorized, gap_clusters)

        # Compute composite score
        if scores:
            composite = sum(s.composite for s in scores.values()) / len(scores)
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
                    "confidence_gap": round(s.confidence_gap, 2),
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


async def _retrieve_critical_requirements(
    project_id: UUID,
    stakeholder_intel: list[dict],
    questions: list[dict],
    awareness: dict,
) -> list[dict]:
    """Retrieve top 3 critical unresolved requirements via 2.5 retrieval."""
    try:
        from app.core.retrieval import retrieve

        # Build query from context
        parts = []
        for s in stakeholder_intel[:3]:
            parts.append(s.get("name", ""))
        for q in questions[:3]:
            parts.append(q.get("question", "")[:60])
        flow = awareness.get("flow_summary", "")
        if flow:
            parts.append(flow)

        query = "Critical unresolved requirements: " + "; ".join(
            p for p in parts if p
        )

        result = await retrieve(
            project_id=project_id,
            query=query,
            entity_types=["feature", "vp_step", "persona"],
            max_rounds=1,
            skip_evaluation=True,
        )

        # Collect entities, boost unconfirmed
        scored = []
        for ent in result.entities:
            score = ent.get("similarity", 0.5)
            status = ent.get("confirmation_status", "ai_generated")
            if status in ("ai_generated", "needs_confirmation"):
                score += 0.2
            scored.append((score, ent))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            {
                "name": ent.get("name", "Unknown"),
                "entity_type": ent.get("entity_type", "feature"),
                "status": ent.get("confirmation_status", "unknown"),
                "context": (
                    ent.get("overview") or ent.get("description") or ""
                )[:120],
            }
            for _, ent in scored[:3]
        ]
    except Exception as e:
        logger.warning(f"Failed to retrieve critical requirements: {e}")
        return []


async def _generate_questions(
    project_id: UUID, stakeholder_ids: list[UUID] | None = None
) -> list[dict]:
    """Generate mission-critical questions via the question agent."""
    try:
        from app.agents.discovery_prep.question_agent import generate_prep_questions

        output = await generate_prep_questions(
            project_id, participant_ids=stakeholder_ids
        )
        return [
            {
                "question": q.question,
                "why_important": q.why_important or "",
                "target_stakeholder": q.best_answered_by or "",
                "gap_ids": [],
            }
            for q in output.questions
        ]
    except Exception as e:
        logger.warning(f"Failed to generate mission-critical questions: {e}")
        return []


async def _generate_call_goals(
    awareness: dict,
    ambiguity: dict,
    questions: list[dict],
) -> list[dict]:
    """Synthesize 2-4 concrete call goals using LLM (Haiku, fast + cheap)."""
    try:
        from anthropic import Anthropic

        settings = get_settings()
        if not settings.ANTHROPIC_API_KEY:
            return _fallback_goals(awareness, questions)

        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        prompt = f"""Based on this project context, generate 2-4 concrete call goals.

## Project State
- Phase: {awareness.get('phase', 'unknown')}
- Flow: {awareness.get('flow_summary', 'N/A')}
- What's next: {json.dumps(awareness.get('whats_next', []))}

## Ambiguity Score: {ambiguity.get('score', 0)}
Top ambiguous beliefs: {json.dumps(ambiguity.get('top_ambiguous_beliefs', [])[:3])}

## Key Questions to Answer
{json.dumps(questions[:5])}

Return a JSON array of objects, each with:
- "goal": string (concrete, actionable goal)
- "success_criteria": string (how to know if achieved)
- "linked_gap_ids": [] (empty for now)

Return ONLY valid JSON — no markdown fences."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]

        goals = json.loads(text.strip())
        return goals if isinstance(goals, list) else []

    except Exception as e:
        logger.warning(f"Failed to generate call goals via LLM: {e}")
        return _fallback_goals(awareness, questions)


def _fallback_goals(awareness: dict, questions: list[dict]) -> list[dict]:
    """Generate basic goals without LLM."""
    goals = []
    for q in questions[:3]:
        goals.append(
            {
                "goal": f"Answer: {q.get('question', 'unknown')}",
                "success_criteria": "Clear answer obtained from stakeholder",
                "linked_gap_ids": q.get("gap_ids", []),
            }
        )
    return goals


def _derive_focus_areas(
    goals: list[dict],
    ambiguity: dict,
    awareness: dict,
) -> list[dict]:
    """Derive prioritized focus areas from goals + project state."""
    areas = []

    # From goals
    for i, goal in enumerate(goals[:3]):
        areas.append(
            {
                "area": goal.get("goal", ""),
                "priority": "high" if i == 0 else "medium",
                "context": goal.get("success_criteria", ""),
            }
        )

    # From ambiguity
    if ambiguity.get("score", 0) > 0.5:
        top_belief = (ambiguity.get("top_ambiguous_beliefs") or [{}])[0] if ambiguity.get("top_ambiguous_beliefs") else {}
        if top_belief:
            areas.append(
                {
                    "area": f"Clarify: {top_belief.get('summary', 'ambiguous assumption')[:80]}",
                    "priority": "high",
                    "context": f"Ambiguity score {ambiguity['score']:.0%} — needs validation",
                }
            )

    # From whats_next
    for item in (awareness.get("whats_next") or [])[:2]:
        if isinstance(item, str) and item not in [a["area"] for a in areas]:
            areas.append(
                {
                    "area": item,
                    "priority": "low",
                    "context": "Next step from project roadmap",
                }
            )

    return areas
