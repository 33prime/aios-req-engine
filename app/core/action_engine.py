"""Relationship-aware action engine v2.

Layer 1: Graph-walking skeleton builder — deterministic, no LLM, instant.
Walks: workflows → steps → drivers → personas → cross-refs
Produces 5 ActionSkeletons with rich relationship context.

Layer 2 (generate_action_narratives.py) wraps skeletons with Haiku narratives.
"""

import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID

from app.core.schemas_actions import (
    ActionCategory,
    ActionEngineResult,
    ActionSkeleton,
    GapDomain,
    QuestionTarget,
    SkeletonRelationship,
    UnifiedAction,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Phase multipliers
# ============================================================================

# (gap_domain, phase) → multiplier. Missing combos default to 1.0.
PHASE_MULTIPLIERS: dict[tuple[str, str], float] = {
    # Workflows are always important, but peak in definition
    ("workflow", "discovery"): 1.0,
    ("workflow", "definition"): 1.3,
    ("workflow", "validation"): 1.1,
    ("workflow", "build_ready"): 0.8,
    # Drivers matter most in discovery/definition
    ("driver", "discovery"): 1.2,
    ("driver", "definition"): 1.1,
    ("driver", "validation"): 0.9,
    ("driver", "build_ready"): 0.7,
    # Personas matter in discovery, less later
    ("persona", "discovery"): 1.1,
    ("persona", "definition"): 1.0,
    ("persona", "validation"): 0.8,
    ("persona", "build_ready"): 0.6,
    # Cross-refs and intelligence matter more in validation
    ("cross_ref", "discovery"): 0.8,
    ("cross_ref", "definition"): 1.0,
    ("cross_ref", "validation"): 1.2,
    ("cross_ref", "build_ready"): 1.3,
}


def _phase_mult(domain: str, phase: str) -> float:
    return PHASE_MULTIPLIERS.get((domain, phase), 1.0)


def _temporal_mod(days_stale: int | None) -> float:
    if not days_stale or days_stale < 7:
        return 1.0
    if days_stale < 14:
        return 1.1
    if days_stale < 30:
        return 1.2
    return 1.3


def _urgency(score: float) -> str:
    if score >= 90:
        return "critical"
    if score >= 80:
        return "high"
    if score >= 65:
        return "normal"
    return "low"


def _skeleton_id(gap_type: str, entity_id: str) -> str:
    """Deterministic hash for caching."""
    raw = f"{gap_type}:{entity_id}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ============================================================================
# Data loading
# ============================================================================


async def _load_project_data(project_id: UUID) -> dict:
    """Load all project data needed for skeleton generation.

    Single async boundary — everything below is sync graph walking.
    """
    from app.db.business_drivers import list_business_drivers
    from app.db.entity_dependencies import get_dependency_graph
    from app.db.features import list_features
    from app.db.open_questions import list_open_questions
    from app.db.personas import list_personas
    from app.db.workflows import get_workflow_pairs

    # Phase — v3 re-detects via _detect_context_phase(); this is a v2 fallback
    phase = "discovery"
    phase_progress = 0.0

    # Core data — all sync calls
    workflow_pairs = get_workflow_pairs(project_id)
    drivers = list_business_drivers(project_id, limit=200)
    personas = list_personas(project_id)
    features = list_features(project_id)
    dep_graph = get_dependency_graph(project_id)
    questions = list_open_questions(project_id, status="open", limit=50)

    # Stakeholder names for question routing
    stakeholder_names: list[str] = []
    try:
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        result = (
            sb.table("stakeholders")
            .select("id, first_name, last_name, name, role, stakeholder_type")
            .eq("project_id", str(project_id))
            .execute()
        )
        stakeholder_names = [
            f"{s.get('first_name', '')} {s.get('last_name', '')}".strip()
            or s.get("name", "")
            for s in (result.data or [])
        ]
    except Exception as e:
        logger.warning(f"Stakeholder load failed: {e}")

    return {
        "phase": phase,
        "phase_progress": phase_progress,
        "workflow_pairs": workflow_pairs,
        "drivers": drivers,
        "personas": personas,
        "features": features,
        "dep_graph": dep_graph,
        "questions": questions,
        "stakeholder_names": stakeholder_names,
    }


# ============================================================================
# Step 1: Walk Workflows (highest priority)
# ============================================================================


def _walk_workflows(
    workflow_pairs: list[dict],
    personas: list[dict],
    dep_graph: dict,
    phase: str,
) -> list[ActionSkeleton]:
    """Walk each workflow → each step, looking for structural gaps."""
    skeletons: list[ActionSkeleton] = []
    persona_map = {str(p["id"]): p for p in personas}

    # Build a lookup: persona_id → list of workflow names they own
    persona_workflow_count: dict[str, int] = {}

    for pair in workflow_pairs:
        wf_name = pair.get("name", "Unnamed Workflow")
        wf_id = pair.get("id", "")

        # Check current vs future state completeness
        current_steps = pair.get("current_steps") or []
        future_steps = pair.get("future_steps") or []

        # Track persona ownership
        owner = pair.get("owner", "")
        if owner:
            # Find persona by name match
            for p in personas:
                if p.get("name", "").lower() == owner.lower():
                    pid = str(p["id"])
                    persona_workflow_count[pid] = (
                        persona_workflow_count.get(pid, 0) + 1
                    )

        # Walk current state steps
        for step in current_steps:
            step_id = str(step.get("id", ""))
            step_label = step.get("label", "step")

            # Gap: step has no actor
            if not step.get("actor_persona_id"):
                base = 82
                skeletons.append(
                    ActionSkeleton(
                        skeleton_id=_skeleton_id("step_no_actor", step_id),
                        category=ActionCategory.GAP,
                        gap_domain=GapDomain.WORKFLOW,
                        gap_type="step_no_actor",
                        gap_description=f"Step '{step_label}' in '{wf_name}' has no assigned actor — we don't know who does this today",
                        primary_entity_type="vp_step",
                        primary_entity_id=step_id,
                        primary_entity_name=step_label,
                        related_entities=[
                            SkeletonRelationship(
                                entity_type="workflow",
                                entity_id=wf_id,
                                entity_name=wf_name,
                                relationship="belongs_to",
                            )
                        ],
                        base_score=base,
                        phase_multiplier=_phase_mult("workflow", phase),
                        final_score=min(
                            100, round(base * _phase_mult("workflow", phase), 1)
                        ),
                        suggested_question_target=QuestionTarget.CONSULTANT,
                    )
                )

            # Gap: step has no pain description (current state)
            if not step.get("pain_description"):
                base = 78
                actor_name = step.get("actor_persona_name") or "someone"
                skeletons.append(
                    ActionSkeleton(
                        skeleton_id=_skeleton_id("step_no_pain", step_id),
                        category=ActionCategory.GAP,
                        gap_domain=GapDomain.WORKFLOW,
                        gap_type="step_no_pain",
                        gap_description=f"Step '{step_label}' in '{wf_name}' has no pain description — what's broken for {actor_name} here?",
                        primary_entity_type="vp_step",
                        primary_entity_id=step_id,
                        primary_entity_name=step_label,
                        related_entities=[
                            SkeletonRelationship(
                                entity_type="workflow",
                                entity_id=wf_id,
                                entity_name=wf_name,
                                relationship="belongs_to",
                            )
                        ],
                        base_score=base,
                        phase_multiplier=_phase_mult("workflow", phase),
                        final_score=min(
                            100, round(base * _phase_mult("workflow", phase), 1)
                        ),
                        suggested_question_target=QuestionTarget.CONSULTANT,
                    )
                )

            # Gap: step has no time estimate
            if not step.get("time_minutes"):
                base = 65
                skeletons.append(
                    ActionSkeleton(
                        skeleton_id=_skeleton_id("step_no_time", step_id),
                        category=ActionCategory.GAP,
                        gap_domain=GapDomain.WORKFLOW,
                        gap_type="step_no_time",
                        gap_description=f"Step '{step_label}' in '{wf_name}' has no time estimate — needed for ROI calculation",
                        primary_entity_type="vp_step",
                        primary_entity_id=step_id,
                        primary_entity_name=step_label,
                        related_entities=[
                            SkeletonRelationship(
                                entity_type="workflow",
                                entity_id=wf_id,
                                entity_name=wf_name,
                                relationship="belongs_to",
                            )
                        ],
                        base_score=base,
                        phase_multiplier=_phase_mult("workflow", phase),
                        final_score=min(
                            100, round(base * _phase_mult("workflow", phase), 1)
                        ),
                        suggested_question_target=QuestionTarget.CONSULTANT,
                    )
                )

        # Walk future state steps
        for step in future_steps:
            step_id = str(step.get("id", ""))
            step_label = step.get("label", "step")

            # Gap: future step has no benefit description
            if not step.get("benefit_description"):
                base = 75
                skeletons.append(
                    ActionSkeleton(
                        skeleton_id=_skeleton_id("step_no_benefit", step_id),
                        category=ActionCategory.GAP,
                        gap_domain=GapDomain.WORKFLOW,
                        gap_type="step_no_benefit",
                        gap_description=f"Future step '{step_label}' in '{wf_name}' has no benefit description — what improves here?",
                        primary_entity_type="vp_step",
                        primary_entity_id=step_id,
                        primary_entity_name=step_label,
                        related_entities=[
                            SkeletonRelationship(
                                entity_type="workflow",
                                entity_id=wf_id,
                                entity_name=wf_name,
                                relationship="belongs_to",
                            )
                        ],
                        base_score=base,
                        phase_multiplier=_phase_mult("workflow", phase),
                        final_score=min(
                            100, round(base * _phase_mult("workflow", phase), 1)
                        ),
                        suggested_question_target=QuestionTarget.CONSULTANT,
                    )
                )

        # Cross-step: current steps with pains but no corresponding future improvement
        steps_with_pains = [
            s for s in current_steps if s.get("pain_description")
        ]
        future_labels = {(s.get("label") or "").lower() for s in future_steps}

        if steps_with_pains and not future_steps:
            # Entire workflow has no future state
            base = 88
            skeletons.append(
                ActionSkeleton(
                    skeleton_id=_skeleton_id("wf_no_future", wf_id),
                    category=ActionCategory.GAP,
                    gap_domain=GapDomain.WORKFLOW,
                    gap_type="workflow_no_future_state",
                    gap_description=f"Workflow '{wf_name}' has {len(steps_with_pains)} current pain points but no future state defined — what does the improved process look like?",
                    primary_entity_type="workflow",
                    primary_entity_id=wf_id,
                    primary_entity_name=wf_name,
                    downstream_entity_count=len(steps_with_pains),
                    base_score=base,
                    phase_multiplier=_phase_mult("workflow", phase),
                    final_score=min(
                        100, round(base * _phase_mult("workflow", phase), 1)
                    ),
                    suggested_question_target=QuestionTarget.CONSULTANT,
                )
            )

        # Check if workflow has no linked drivers via entity deps
        wf_dep_key = f"workflow:{wf_id}"
        wf_deps = dep_graph.get("by_source", {}).get(wf_dep_key, [])
        driver_deps = [
            d
            for d in wf_deps
            if d.get("target_entity_type") == "business_driver"
        ]
        if not driver_deps and (current_steps or future_steps):
            base = 72
            skeletons.append(
                ActionSkeleton(
                    skeleton_id=_skeleton_id("wf_no_drivers", wf_id),
                    category=ActionCategory.GAP,
                    gap_domain=GapDomain.WORKFLOW,
                    gap_type="workflow_no_drivers",
                    gap_description=f"Workflow '{wf_name}' isn't linked to any business drivers — why are we changing this process?",
                    primary_entity_type="workflow",
                    primary_entity_id=wf_id,
                    primary_entity_name=wf_name,
                    base_score=base,
                    phase_multiplier=_phase_mult("workflow", phase),
                    final_score=min(
                        100, round(base * _phase_mult("workflow", phase), 1)
                    ),
                    suggested_question_target=QuestionTarget.CONSULTANT,
                )
            )

    return skeletons


# ============================================================================
# Step 2: Walk Business Drivers
# ============================================================================


def _walk_drivers(
    drivers: list[dict],
    dep_graph: dict,
    phase: str,
) -> list[ActionSkeleton]:
    """Walk drivers looking for orphans, missing data, weak evidence."""
    skeletons: list[ActionSkeleton] = []

    for d in drivers:
        d_id = str(d.get("id", ""))
        d_type = d.get("driver_type", "")
        d_desc = d.get("description", "")[:80]
        d_dep_key = f"business_driver:{d_id}"

        # How many things depend on / are linked to this driver
        inbound = dep_graph.get("by_target", {}).get(d_dep_key, [])
        outbound = dep_graph.get("by_source", {}).get(d_dep_key, [])
        all_links = inbound + outbound

        # Linked workflow steps
        step_links = [
            l
            for l in all_links
            if l.get("source_entity_type") == "vp_step"
            or l.get("target_entity_type") == "vp_step"
        ]

        # Pain with no linked workflow step
        if d_type == "pain" and not step_links:
            base = 76
            skeletons.append(
                ActionSkeleton(
                    skeleton_id=_skeleton_id("pain_orphan", d_id),
                    category=ActionCategory.GAP,
                    gap_domain=GapDomain.DRIVER,
                    gap_type="pain_no_workflow",
                    gap_description=f"Pain '{d_desc}' isn't linked to any workflow step — where does this hurt in the process?",
                    primary_entity_type="business_driver",
                    primary_entity_id=d_id,
                    primary_entity_name=d_desc,
                    existing_evidence_count=len(d.get("evidence") or []),
                    base_score=base,
                    phase_multiplier=_phase_mult("driver", phase),
                    final_score=min(
                        100, round(base * _phase_mult("driver", phase), 1)
                    ),
                    suggested_question_target=QuestionTarget.CONSULTANT,
                )
            )

        # Goal with no linked features (via linked_feature_ids)
        if d_type == "goal" and not d.get("linked_feature_ids"):
            base = 70
            skeletons.append(
                ActionSkeleton(
                    skeleton_id=_skeleton_id("goal_no_feature", d_id),
                    category=ActionCategory.GAP,
                    gap_domain=GapDomain.DRIVER,
                    gap_type="goal_no_feature",
                    gap_description=f"Goal '{d_desc}' has no features addressing it — how do we achieve this?",
                    primary_entity_type="business_driver",
                    primary_entity_id=d_id,
                    primary_entity_name=d_desc,
                    base_score=base,
                    phase_multiplier=_phase_mult("driver", phase),
                    final_score=min(
                        100, round(base * _phase_mult("driver", phase), 1)
                    ),
                    suggested_question_target=QuestionTarget.CONSULTANT,
                )
            )

        # KPI with no baseline or target
        if d_type == "kpi":
            has_baseline = bool(d.get("baseline_value"))
            has_target = bool(d.get("target_value"))
            if not has_baseline or not has_target:
                missing = []
                if not has_baseline:
                    missing.append("baseline")
                if not has_target:
                    missing.append("target")
                base = 80
                skeletons.append(
                    ActionSkeleton(
                        skeleton_id=_skeleton_id("kpi_no_numbers", d_id),
                        category=ActionCategory.GAP,
                        gap_domain=GapDomain.DRIVER,
                        gap_type="kpi_no_numbers",
                        gap_description=f"KPI '{d_desc}' is missing {' and '.join(missing)} — can't measure success without numbers",
                        primary_entity_type="business_driver",
                        primary_entity_id=d_id,
                        primary_entity_name=d_desc,
                        base_score=base,
                        phase_multiplier=_phase_mult("driver", phase),
                        final_score=min(
                            100, round(base * _phase_mult("driver", phase), 1)
                        ),
                        suggested_question_target=QuestionTarget.CLIENT,
                        suggested_contact_name=d.get("owner"),
                    )
                )

        # Single-source evidence
        evidence = d.get("evidence") or []
        source_signals = d.get("source_signal_ids") or []
        total_sources = max(len(evidence), len(source_signals))
        if total_sources == 1 and d.get("confirmation_status") != "confirmed_client":
            base = 62
            skeletons.append(
                ActionSkeleton(
                    skeleton_id=_skeleton_id("driver_single_source", d_id),
                    category=ActionCategory.GAP,
                    gap_domain=GapDomain.DRIVER,
                    gap_type="driver_single_source",
                    gap_description=f"{d_type.title()} '{d_desc}' has only 1 evidence source — needs corroboration",
                    primary_entity_type="business_driver",
                    primary_entity_id=d_id,
                    primary_entity_name=d_desc,
                    existing_evidence_count=1,
                    base_score=base,
                    phase_multiplier=_phase_mult("driver", phase),
                    final_score=min(
                        100, round(base * _phase_mult("driver", phase), 1)
                    ),
                    suggested_question_target=QuestionTarget.CONSULTANT,
                )
            )

    return skeletons


# ============================================================================
# Step 3: Walk Personas (as actors)
# ============================================================================


def _walk_personas(
    personas: list[dict],
    workflow_pairs: list[dict],
    phase: str,
) -> list[ActionSkeleton]:
    """Walk personas looking for ownership gaps and unaddressed goals."""
    skeletons: list[ActionSkeleton] = []

    # Build persona → workflow ownership map
    persona_workflows: dict[str, list[str]] = {}
    for pair in workflow_pairs:
        owner = (pair.get("owner") or "").lower()
        for p in personas:
            if p.get("name", "").lower() == owner:
                pid = str(p["id"])
                if pid not in persona_workflows:
                    persona_workflows[pid] = []
                persona_workflows[pid].append(pair.get("name", "workflow"))

    for p in personas:
        pid = str(p["id"])
        p_name = p.get("name", "Persona")
        is_primary = p.get("is_primary") or p.get("canvas_role") == "primary"

        # Primary persona owns 0 workflows
        if is_primary and pid not in persona_workflows:
            base = 84
            skeletons.append(
                ActionSkeleton(
                    skeleton_id=_skeleton_id("persona_no_workflow", pid),
                    category=ActionCategory.GAP,
                    gap_domain=GapDomain.PERSONA,
                    gap_type="persona_no_workflow",
                    gap_description=f"Primary persona '{p_name}' doesn't own any workflows — what do they actually do day-to-day?",
                    primary_entity_type="persona",
                    primary_entity_id=pid,
                    primary_entity_name=p_name,
                    base_score=base,
                    phase_multiplier=_phase_mult("persona", phase),
                    final_score=min(
                        100, round(base * _phase_mult("persona", phase), 1)
                    ),
                    suggested_question_target=QuestionTarget.CONSULTANT,
                )
            )

        # Pain points not tracked as business drivers
        pain_points = p.get("pain_points") or []
        if pain_points and len(pain_points) > 2:
            # This is a softer signal — just note it
            base = 55
            skeletons.append(
                ActionSkeleton(
                    skeleton_id=_skeleton_id("persona_pains_informal", pid),
                    category=ActionCategory.GAP,
                    gap_domain=GapDomain.PERSONA,
                    gap_type="persona_pains_not_drivers",
                    gap_description=f"'{p_name}' has {len(pain_points)} pain points that aren't formalized as business drivers",
                    primary_entity_type="persona",
                    primary_entity_id=pid,
                    primary_entity_name=p_name,
                    base_score=base,
                    phase_multiplier=_phase_mult("persona", phase),
                    final_score=min(
                        100, round(base * _phase_mult("persona", phase), 1)
                    ),
                    suggested_question_target=QuestionTarget.CONSULTANT,
                )
            )

    return skeletons


# ============================================================================
# Step 4: Cross-reference (open questions, low-confidence beliefs)
# ============================================================================


def _walk_cross_refs(
    questions: list[dict],
    phase: str,
) -> list[ActionSkeleton]:
    """Link open questions to gaps, boost urgency for entity-linked questions."""
    skeletons: list[ActionSkeleton] = []

    for q in questions:
        priority = q.get("priority", "medium")
        if priority == "low":
            continue

        q_id = str(q.get("id", ""))
        q_text = q.get("question", "")[:80]
        target_type = q.get("target_entity_type")
        target_id = q.get("target_entity_id")

        # Calculate staleness
        days_old = None
        created = q.get("created_at")
        if created:
            try:
                if isinstance(created, str):
                    created = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    )
                days_old = (datetime.now(timezone.utc) - created).days
            except (ValueError, TypeError):
                pass

        base = {"critical": 88, "high": 80, "medium": 68}.get(priority, 68)

        # Boost if linked to an entity
        if target_type and target_id:
            base += 5

        related = []
        if target_type and target_id:
            related.append(
                SkeletonRelationship(
                    entity_type=target_type,
                    entity_id=str(target_id),
                    entity_name=f"linked {target_type}",
                    relationship="targets",
                )
            )

        pm = _phase_mult("cross_ref", phase)
        tm = _temporal_mod(days_old)

        skeletons.append(
            ActionSkeleton(
                skeleton_id=_skeleton_id("open_question", q_id),
                category=ActionCategory.GAP,
                gap_domain=GapDomain.CROSS_REF,
                gap_type="open_question",
                gap_description=q_text,
                primary_entity_type="open_question",
                primary_entity_id=q_id,
                primary_entity_name=q_text,
                related_entities=related,
                base_score=base,
                phase_multiplier=pm,
                temporal_modifier=tm,
                final_score=min(100, round(base * pm * tm, 1)),
                suggested_question_target=(
                    QuestionTarget.CLIENT
                    if q.get("suggested_owner")
                    else QuestionTarget.CONSULTANT
                ),
                suggested_contact_name=q.get("suggested_owner"),
            )
        )

    return skeletons


# ============================================================================
# Skeleton assembly + ranking
# ============================================================================


def _build_all_skeletons(data: dict) -> list[ActionSkeleton]:
    """Run all walk functions and merge into a single ranked list."""
    phase = data["phase"]

    all_skeletons: list[ActionSkeleton] = []

    # Step 1: Workflows (highest priority)
    all_skeletons.extend(
        _walk_workflows(
            data["workflow_pairs"],
            data["personas"],
            data["dep_graph"],
            phase,
        )
    )

    # Step 2: Business drivers
    all_skeletons.extend(
        _walk_drivers(data["drivers"], data["dep_graph"], phase)
    )

    # Step 3: Personas
    all_skeletons.extend(
        _walk_personas(data["personas"], data["workflow_pairs"], phase)
    )

    # Step 4: Cross-references (open questions)
    all_skeletons.extend(_walk_cross_refs(data["questions"], phase))

    # Inject stakeholder names into skeletons that need contacts
    for sk in all_skeletons:
        if not sk.known_contacts and data.get("stakeholder_names"):
            sk.known_contacts = data["stakeholder_names"][:3]

    # Sort by final_score descending
    all_skeletons.sort(key=lambda s: s.final_score, reverse=True)

    # Deduplicate: same entity shouldn't appear in multiple skeletons
    # Keep highest-scored skeleton per primary entity
    seen_entities: set[str] = set()
    deduped: list[ActionSkeleton] = []
    for sk in all_skeletons:
        key = f"{sk.primary_entity_type}:{sk.primary_entity_id}"
        if key not in seen_entities:
            seen_entities.add(key)
            deduped.append(sk)

    return deduped


# ============================================================================
# Main entry point
# ============================================================================


async def compute_actions(
    project_id: UUID,
    max_skeletons: int = 5,
    include_narratives: bool = True,
) -> ActionEngineResult:
    """Full action computation: skeletons + optional Haiku narratives.

    Args:
        project_id: Project UUID
        max_skeletons: How many skeletons to produce (show 3, buffer 5)
        include_narratives: If True, calls Haiku for narrative layer
    """
    # Load all data (single async boundary)
    data = await _load_project_data(project_id)

    # Build skeletons (sync, instant)
    all_skeletons = _build_all_skeletons(data)
    total_skeleton_count = len(all_skeletons)
    top_skeletons = all_skeletons[:max_skeletons]

    # Layer 2: Haiku narratives (optional)
    actions: list[UnifiedAction] = []
    narrative_cached = False

    if include_narratives and top_skeletons:
        try:
            from app.chains.generate_action_narratives import (
                generate_narratives,
            )
            from app.core.state_snapshot import get_state_snapshot

            snapshot = get_state_snapshot(project_id)
            actions, narrative_cached = await generate_narratives(
                skeletons=top_skeletons,
                state_snapshot=snapshot,
                project_id=str(project_id),
            )
        except ImportError:
            logger.info(
                "Narrative chain not available, returning skeleton-only actions"
            )
            actions = _skeletons_to_actions(top_skeletons)
        except Exception as e:
            logger.warning(f"Narrative generation failed, falling back: {e}")
            actions = _skeletons_to_actions(top_skeletons)
    else:
        actions = _skeletons_to_actions(top_skeletons)

    # Open questions summary
    open_questions_summary = [
        {
            "id": q.get("id"),
            "question": q.get("question"),
            "priority": q.get("priority"),
            "category": q.get("category"),
        }
        for q in data["questions"][:5]
    ]

    return ActionEngineResult(
        actions=actions,
        skeleton_count=total_skeleton_count,
        open_questions=open_questions_summary,
        phase=data["phase"],
        phase_progress=data["phase_progress"],
        narrative_cached=narrative_cached,
    )


def _skeletons_to_actions(skeletons: list[ActionSkeleton]) -> list[UnifiedAction]:
    """Fallback: convert skeletons to actions without Haiku narratives."""
    return [
        UnifiedAction(
            action_id=sk.skeleton_id,
            category=sk.category,
            gap_domain=sk.gap_domain,
            narrative=sk.gap_description,
            unlocks=f"Resolving this affects {sk.downstream_entity_count} downstream entities"
            if sk.downstream_entity_count
            else "Fills a structural gap in the project",
            questions=[],
            impact_score=sk.final_score,
            urgency=_urgency(sk.final_score),
            primary_entity_type=sk.primary_entity_type,
            primary_entity_id=sk.primary_entity_id,
            primary_entity_name=sk.primary_entity_name,
            related_entity_ids=[
                r.entity_id for r in sk.related_entities
            ],
            gates_affected=sk.gates_affected,
            gap_type=sk.gap_type,
            known_contacts=sk.known_contacts,
            evidence_count=sk.existing_evidence_count,
        )
        for sk in skeletons
    ]


# ============================================================================
# Lightweight sync entry point (for batch dashboard)
# ============================================================================


def compute_actions_from_inputs(
    inputs: dict, phase: str = "discovery"
) -> list[UnifiedAction]:
    """Lightweight sync computation from pre-aggregated SQL inputs.

    Used by batch dashboard endpoint. Returns skeleton-only actions (no Haiku).
    """
    skeletons: list[ActionSkeleton] = []

    # Workflow gaps from RPC counts
    wf_count = inputs.get("workflow_count", 0)
    if wf_count == 0:
        skeletons.append(
            ActionSkeleton(
                skeleton_id=_skeleton_id("no_workflows", "project"),
                category=ActionCategory.GAP,
                gap_domain=GapDomain.WORKFLOW,
                gap_type="no_workflows",
                gap_description="No workflows defined — workflows are the backbone of the project",
                primary_entity_type="project",
                primary_entity_id=inputs.get("project_id", ""),
                primary_entity_name="Project",
                base_score=95,
                phase_multiplier=_phase_mult("workflow", phase),
                final_score=min(
                    100, round(95 * _phase_mult("workflow", phase), 1)
                ),
            )
        )

    # KPI gaps
    kpi_count = inputs.get("kpi_count", 0)
    if kpi_count == 0:
        skeletons.append(
            ActionSkeleton(
                skeleton_id=_skeleton_id("no_kpis", "project"),
                category=ActionCategory.GAP,
                gap_domain=GapDomain.DRIVER,
                gap_type="no_kpis",
                gap_description="No KPIs defined — can't measure success without metrics",
                primary_entity_type="project",
                primary_entity_id=inputs.get("project_id", ""),
                primary_entity_name="Project",
                base_score=80,
                phase_multiplier=_phase_mult("driver", phase),
                final_score=min(
                    100, round(80 * _phase_mult("driver", phase), 1)
                ),
            )
        )

    # Critical open questions
    crit_q = inputs.get("critical_question_count", 0)
    if crit_q > 0:
        skeletons.append(
            ActionSkeleton(
                skeleton_id=_skeleton_id("crit_questions", "project"),
                category=ActionCategory.GAP,
                gap_domain=GapDomain.CROSS_REF,
                gap_type="critical_questions",
                gap_description=f"{crit_q} critical question{'s' if crit_q > 1 else ''} blocking progress",
                primary_entity_type="project",
                primary_entity_id=inputs.get("project_id", ""),
                primary_entity_name="Project",
                base_score=88,
                phase_multiplier=_phase_mult("cross_ref", phase),
                final_score=min(
                    100, round(88 * _phase_mult("cross_ref", phase), 1)
                ),
            )
        )

    # No vision
    if not inputs.get("has_vision"):
        skeletons.append(
            ActionSkeleton(
                skeleton_id=_skeleton_id("no_vision", "project"),
                category=ActionCategory.GAP,
                gap_domain=GapDomain.DRIVER,
                gap_type="no_vision",
                gap_description="No vision statement — the project needs a clear north star",
                primary_entity_type="project",
                primary_entity_id=inputs.get("project_id", ""),
                primary_entity_name="Project",
                base_score=72,
                phase_multiplier=_phase_mult("driver", phase),
                final_score=min(
                    100, round(72 * _phase_mult("driver", phase), 1)
                ),
            )
        )

    # Staleness
    days_since = inputs.get("days_since_last_signal")
    if days_since and days_since > 14 and phase != "discovery":
        tm = _temporal_mod(days_since)
        base = 73
        skeletons.append(
            ActionSkeleton(
                skeleton_id=_skeleton_id("project_stale", "project"),
                category=ActionCategory.GAP,
                gap_domain=GapDomain.CROSS_REF,
                gap_type="project_stale",
                gap_description=f"No new signals in {days_since} days — project may be stalling",
                primary_entity_type="project",
                primary_entity_id=inputs.get("project_id", ""),
                primary_entity_name="Project",
                base_score=base,
                phase_multiplier=_phase_mult("cross_ref", phase),
                temporal_modifier=tm,
                final_score=min(
                    100,
                    round(
                        base * _phase_mult("cross_ref", phase) * tm, 1
                    ),
                ),
            )
        )

    skeletons.sort(key=lambda s: s.final_score, reverse=True)
    return _skeletons_to_actions(skeletons[:3])


# ============================================================================
# State frame delegation (backward compat for chat context)
# ============================================================================


def compute_state_frame_actions(
    phase: str,
    metrics: dict,
    blockers: list,
) -> list:
    """Compute next actions for state frame (returns NextAction models).

    Bridges state_frame.py → action_engine delegation.
    Returns app.context.models.NextAction instances (not UnifiedAction).
    """
    from app.context.models import NextAction

    actions = []
    priority = 1

    for blocker in blockers:
        if blocker.type == "no_personas":
            actions.append(
                NextAction(
                    action="Add first persona to establish target users",
                    tool_hint="create_entity",
                    priority=priority,
                    rationale="Personas help focus feature development",
                )
            )
        elif blocker.type == "no_features":
            actions.append(
                NextAction(
                    action="Identify core features from client signals",
                    tool_hint="create_entity",
                    priority=priority,
                    rationale="Features are the foundation of the product",
                )
            )
        elif blocker.type == "insufficient_mvp":
            actions.append(
                NextAction(
                    action="Mark more features as MVP or propose new MVP features",
                    tool_hint="create_entity",
                    priority=priority,
                    rationale="Need 3+ MVP features for baseline",
                )
            )
        priority += 1

    if phase == "build_ready" and len(actions) < 5:
        actions.append(
            NextAction(
                action="Run final readiness assessment",
                tool_hint="assess_readiness",
                priority=5,
                rationale="Confirm all requirements for development handoff",
            )
        )

    return actions[:5]


# ============================================================================
# v3: Context Frame Engine
# ============================================================================


def _detect_context_phase(data: dict) -> tuple:
    """Detect 4-tier project phase from entity counts.

    Returns:
        (ContextPhase, progress float 0-1)
    """
    from app.core.schemas_actions import ContextPhase

    workflow_pairs = data.get("workflow_pairs") or []
    features = data.get("features") or []
    personas = data.get("personas") or []
    vp_steps_count = sum(
        len(p.get("current_steps") or []) + len(p.get("future_steps") or [])
        for p in workflow_pairs
    )

    total_entities = len(features) + len(personas) + vp_steps_count
    workflow_count = len(workflow_pairs)

    # Refining: >70% structural completeness
    if total_entities >= 15 and workflow_count >= 2:
        # Check completeness: count gaps vs total fields
        total_fields = 0
        filled_fields = 0
        for p in workflow_pairs:
            for step in p.get("current_steps") or []:
                total_fields += 3  # actor, pain, time
                if step.get("actor_persona_id"):
                    filled_fields += 1
                if step.get("pain_description"):
                    filled_fields += 1
                if step.get("time_minutes"):
                    filled_fields += 1
            for step in p.get("future_steps") or []:
                total_fields += 1  # benefit
                if step.get("benefit_description"):
                    filled_fields += 1

        completeness = filled_fields / max(total_fields, 1)
        if completeness > 0.70:
            return ContextPhase.REFINING, min(1.0, 0.75 + completeness * 0.25)

        return ContextPhase.BUILDING, 0.4 + completeness * 0.35

    # Seeding: 3-15 entities OR <2 workflows
    if total_entities >= 3 or workflow_count >= 1:
        progress = min(0.4, total_entities / 15 * 0.3 + workflow_count / 2 * 0.1)
        return ContextPhase.SEEDING, progress

    # Empty
    progress = total_entities / 3 * 0.1
    return ContextPhase.EMPTY, progress


def _build_workflow_context(workflow_pairs: list[dict]) -> str:
    """Build a terse workflow context string with IDs for chat agent (~400 tokens)."""
    if not workflow_pairs:
        return "No workflows defined yet."

    lines = []
    for p in workflow_pairs[:8]:
        name = p.get("name", "Unnamed")
        wf_id = str(p.get("id", ""))[:8]
        current = p.get("current_steps") or []
        future = p.get("future_steps") or []
        line = f"- {name} [wf:{wf_id}]"
        if current:
            step_parts = [f"{s.get('label', 'step')} [s:{str(s.get('id', ''))[:8]}]" for s in current[:6]]
            line += f" (current: {', '.join(step_parts)})"
        if future:
            step_parts = [f"{s.get('label', 'step')} [s:{str(s.get('id', ''))[:8]}]" for s in future[:6]]
            line += f" (future: {', '.join(step_parts)})"
        lines.append(line)
    if len(workflow_pairs) > 8:
        lines.append(f"  ... and {len(workflow_pairs) - 8} more workflows")
    return "\n".join(lines)


def _build_structural_gaps(
    workflow_pairs: list[dict],
    phase_str: str,
) -> list:
    """Walk workflows only, produce StructuralGap list (no drivers/personas)."""
    from app.core.schemas_actions import StructuralGap

    gaps = []

    for pair in workflow_pairs:
        wf_name = pair.get("name", "Unnamed Workflow")
        wf_id = pair.get("id", "")

        current_steps = pair.get("current_steps") or []
        future_steps = pair.get("future_steps") or []

        for step in current_steps:
            step_id = str(step.get("id", ""))
            step_label = step.get("label", "step")

            if not step.get("actor_persona_id"):
                gaps.append(
                    StructuralGap(
                        gap_id=_skeleton_id("step_no_actor", step_id),
                        gap_type="step_no_actor",
                        sentence=f"Who performs '{step_label}' in {wf_name}?",
                        entity_type="vp_step",
                        entity_id=step_id,
                        entity_name=step_label,
                        workflow_name=wf_name,
                        score=82 * _phase_mult("workflow", phase_str),
                        question_placeholder="Enter the person or role...",
                    )
                )

            if not step.get("pain_description"):
                gaps.append(
                    StructuralGap(
                        gap_id=_skeleton_id("step_no_pain", step_id),
                        gap_type="step_no_pain",
                        sentence=f"What's the pain point at '{step_label}' in {wf_name}?",
                        entity_type="vp_step",
                        entity_id=step_id,
                        entity_name=step_label,
                        workflow_name=wf_name,
                        score=78 * _phase_mult("workflow", phase_str),
                        question_placeholder="Describe the current frustration...",
                    )
                )

            if not step.get("time_minutes"):
                gaps.append(
                    StructuralGap(
                        gap_id=_skeleton_id("step_no_time", step_id),
                        gap_type="step_no_time",
                        sentence=f"How long does '{step_label}' take in {wf_name}?",
                        entity_type="vp_step",
                        entity_id=step_id,
                        entity_name=step_label,
                        workflow_name=wf_name,
                        score=65 * _phase_mult("workflow", phase_str),
                        question_placeholder="Estimated minutes...",
                    )
                )

        for step in future_steps:
            step_id = str(step.get("id", ""))
            step_label = step.get("label", "step")

            if not step.get("benefit_description"):
                gaps.append(
                    StructuralGap(
                        gap_id=_skeleton_id("step_no_benefit", step_id),
                        gap_type="step_no_benefit",
                        sentence=f"What improves at '{step_label}' in {wf_name}?",
                        entity_type="vp_step",
                        entity_id=step_id,
                        entity_name=step_label,
                        workflow_name=wf_name,
                        score=75 * _phase_mult("workflow", phase_str),
                        question_placeholder="Describe the improvement...",
                    )
                )

        # Workflow has current pains but no future state
        steps_with_pains = [s for s in current_steps if s.get("pain_description")]
        if steps_with_pains and not future_steps:
            gaps.append(
                StructuralGap(
                    gap_id=_skeleton_id("wf_no_future", wf_id),
                    gap_type="workflow_no_future_state",
                    sentence=f"'{wf_name}' has {len(steps_with_pains)} pain points but no future state — what does the improved process look like?",
                    entity_type="workflow",
                    entity_id=wf_id,
                    entity_name=wf_name,
                    workflow_name=wf_name,
                    score=88 * _phase_mult("workflow", phase_str),
                )
            )

    # Sort by score descending, deduplicate by entity
    gaps.sort(key=lambda g: g.score, reverse=True)
    seen = set()
    deduped = []
    for g in gaps:
        key = f"{g.entity_type}:{g.entity_id}"
        if key not in seen:
            seen.add(key)
            deduped.append(g)

    return deduped


def _load_memory_hints(project_id: UUID) -> list[str]:
    """Load low-confidence beliefs from memory_nodes."""
    try:
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        result = (
            sb.table("memory_nodes")
            .select("content, confidence")
            .eq("project_id", str(project_id))
            .lt("confidence", 0.6)
            .order("confidence")
            .limit(5)
            .execute()
        )
        return [
            f"{r['content']} (confidence: {r.get('confidence', 0):.0%})"
            for r in (result.data or [])
            if r.get("content")
        ]
    except Exception as e:
        logger.debug(f"Memory hints load failed: {e}")
        return []


def _count_entities(data: dict) -> dict:
    """Count entities by type for the context frame."""
    workflow_pairs = data.get("workflow_pairs") or []
    current_steps = sum(len(p.get("current_steps") or []) for p in workflow_pairs)
    future_steps = sum(len(p.get("future_steps") or []) for p in workflow_pairs)
    return {
        "workflows": len(workflow_pairs),
        "current_steps": current_steps,
        "future_steps": future_steps,
        "features": len(data.get("features") or []),
        "personas": len(data.get("personas") or []),
        "stakeholders": len(data.get("stakeholder_names") or []),
    }


def _build_entity_inventory(data: dict) -> dict[str, list[dict]]:
    """Build entity inventory from loaded project data.

    Plucks {id, name, confirmation_status, is_stale} per entity type.
    Used by the extraction pipeline for context-aware extraction.
    """
    inventory: dict[str, list[dict]] = {}

    # Features
    inventory["feature"] = [
        {
            "id": str(f.get("id", "")),
            "name": f.get("name", ""),
            "confirmation_status": f.get("confirmation_status", "ai_generated"),
            "is_stale": f.get("is_stale", False),
        }
        for f in (data.get("features") or [])
    ]

    # Personas
    inventory["persona"] = [
        {
            "id": str(p.get("id", "")),
            "name": p.get("name", ""),
            "confirmation_status": p.get("confirmation_status", "ai_generated"),
            "is_stale": p.get("is_stale", False),
        }
        for p in (data.get("personas") or [])
    ]

    # Workflows + steps
    workflows = []
    workflow_steps = []
    for pair in (data.get("workflow_pairs") or []):
        wf_id = str(pair.get("id", ""))
        wf_name = pair.get("name", "Unnamed")
        workflows.append(
            {
                "id": wf_id,
                "name": wf_name,
                "confirmation_status": pair.get("confirmation_status", "ai_generated"),
                "is_stale": pair.get("is_stale", False),
            }
        )
        for step in (pair.get("current_steps") or []) + (pair.get("future_steps") or []):
            workflow_steps.append(
                {
                    "id": str(step.get("id", "")),
                    "name": step.get("label", ""),
                    "confirmation_status": step.get("confirmation_status", "ai_generated"),
                    "is_stale": step.get("is_stale", False),
                    "workflow_name": wf_name,
                }
            )

    inventory["workflow"] = workflows
    inventory["workflow_step"] = workflow_steps

    # Business drivers
    inventory["business_driver"] = [
        {
            "id": str(d.get("id", "")),
            "name": d.get("description", "")[:80],
            "driver_type": d.get("driver_type", ""),
            "confirmation_status": d.get("confirmation_status", "ai_generated"),
            "is_stale": d.get("is_stale", False),
        }
        for d in (data.get("drivers") or [])
    ]

    return inventory


async def compute_context_frame(
    project_id: UUID,
    max_actions: int = 5,
) -> "ProjectContextFrame":
    """Compute the ProjectContextFrame — v3 universal context engine.

    Three-layer approach:
    1. Deterministic structural gaps (instant, no LLM)
    2. Haiku signal + knowledge gaps (fast, ~200ms)
    3. Merge + rank into terse actions

    Args:
        project_id: Project UUID
        max_actions: Max terse actions to return
    """
    from app.core.schemas_actions import (
        CTAType,
        ProjectContextFrame,
        TerseAction,
    )

    # Load project data (single async boundary)
    data = await _load_project_data(project_id)

    # Phase detection (new 4-tier system)
    phase, phase_progress = _detect_context_phase(data)

    # Workflow context for Haiku
    workflow_context = _build_workflow_context(data["workflow_pairs"])

    # State snapshot (cached)
    try:
        from app.core.state_snapshot import get_state_snapshot
        state_snapshot = get_state_snapshot(project_id)
    except Exception:
        state_snapshot = ""

    # Layer 1: Structural gaps (deterministic, instant)
    structural_gaps = _build_structural_gaps(
        data["workflow_pairs"], phase.value
    )

    # Layer 2: Signal + knowledge gaps (Haiku)
    signal_gaps = []
    knowledge_gaps = []
    try:
        from app.chains.generate_gap_intelligence import generate_gap_intelligence
        signal_gaps, knowledge_gaps = await generate_gap_intelligence(
            phase=phase,
            workflow_context=workflow_context,
            state_snapshot=state_snapshot,
            entity_counts=_count_entities(data),
            project_id=str(project_id),
        )
    except ImportError:
        logger.info("Gap intelligence chain not available")
    except Exception as e:
        logger.warning(f"Gap intelligence failed: {e}")

    # Memory hints
    memory_hints = _load_memory_hints(project_id)

    # Merge all gaps into terse actions, ranked
    actions: list[TerseAction] = []

    # Structural gaps → inline answer actions
    for g in structural_gaps:
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
            )
        )

    # Signal gaps → upload doc or discuss
    for g in signal_gaps:
        actions.append(
            TerseAction(
                action_id=g.gap_id,
                sentence=g.sentence,
                cta_type=g.cta_type,
                cta_label="Upload document" if g.cta_type == CTAType.UPLOAD_DOC else "Discuss in chat",
                gap_source="signal",
                gap_type="signal_gap",
                impact_score=85.0,  # signal gaps are high priority
            )
        )

    # Knowledge gaps → discuss
    for g in knowledge_gaps:
        actions.append(
            TerseAction(
                action_id=g.gap_id,
                sentence=g.sentence,
                cta_type=CTAType.DISCUSS,
                cta_label="Discuss in chat",
                gap_source="knowledge",
                gap_type="knowledge_gap",
                impact_score=80.0,
            )
        )

    # Sort by impact score, assign priority ranks
    actions.sort(key=lambda a: a.impact_score, reverse=True)
    for i, a in enumerate(actions[:max_actions]):
        a.priority = i + 1
    actions = actions[:max_actions]

    # Open questions
    open_questions_summary = [
        {
            "id": q.get("id"),
            "question": q.get("question"),
            "priority": q.get("priority"),
            "category": q.get("category"),
        }
        for q in data.get("questions", [])[:5]
    ]

    total_gaps = len(structural_gaps) + len(signal_gaps) + len(knowledge_gaps)

    return ProjectContextFrame(
        phase=phase,
        phase_progress=phase_progress,
        structural_gaps=structural_gaps[:10],
        signal_gaps=signal_gaps,
        knowledge_gaps=knowledge_gaps,
        actions=actions,
        state_snapshot=state_snapshot,
        workflow_context=workflow_context,
        memory_hints=memory_hints,
        entity_counts=_count_entities(data),
        entity_inventory=_build_entity_inventory(data),
        total_gap_count=total_gaps,
        open_questions=open_questions_summary,
    )
