"""Surgical update graph for maintenance mode entity updates.

Phase 2: Extended for all entity types (features, personas, VP steps)
"""

from typing import Any, Annotated
from uuid import UUID
import operator

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.schemas_claims import (
    Claim,
    ScopedPatch,
    Escalation,
    SurgicalUpdateResult,
    CanonicalIndex,
)
from app.chains.extract_claims import extract_claims_from_signal
from app.core.claim_router import route_claims
from app.chains.generate_scoped_patch import generate_scoped_patch
from app.chains.generate_persona_patch import generate_persona_patch
from app.core.canonical_index import build_canonical_index
from app.db.features import get_feature, update_feature
from app.db.personas import get_persona, update_persona
from app.db.vp import get_vp_step, update_vp_step

logger = get_logger(__name__)

MAX_STEPS = 20  # Safety cap for linear pipeline (7 nodes + margin)


# =========================
# State Definition
# =========================


class SurgicalUpdateState(BaseModel):
    """State for surgical update graph."""

    # Input
    signal_id: UUID
    project_id: UUID
    run_id: UUID
    prd_mode: str = "maintenance"  # Should be maintenance mode

    # Loaded data
    signal: dict[str, Any] | None = None
    canonical_index: CanonicalIndex | None = None

    # Processing
    claims: Annotated[list[Claim], operator.add] = Field(default_factory=list)
    grouped_claims: dict[str, Any] = Field(default_factory=dict)
    new_proposals: Annotated[list[Claim], operator.add] = Field(default_factory=list)
    patches: Annotated[list[ScopedPatch], operator.add] = Field(default_factory=list)
    applied_patches: Annotated[list[ScopedPatch], operator.add] = Field(default_factory=list)
    escalations: Annotated[list[Escalation], operator.add] = Field(default_factory=list)

    # Results
    applied_count: int = 0
    escalated_count: int = 0
    step_count: int = 0
    success: bool = False
    error: str | None = None

    class Config:
        arbitrary_types_allowed = True


# =========================
# Node Functions
# =========================


def _check_max_steps(state: SurgicalUpdateState) -> SurgicalUpdateState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def check_mode(state: SurgicalUpdateState) -> SurgicalUpdateState:
    """Check if project is in maintenance mode."""
    state = _check_max_steps(state)
    logger.info(
        f"Checking PRD mode for project {state.project_id}",
        extra={"run_id": str(state.run_id)},
    )

    # In real implementation, would query projects table
    # For now, assuming maintenance mode if this graph is called
    if state.prd_mode != "maintenance":
        logger.warning(
            f"Project {state.project_id} not in maintenance mode, should use build_state instead",
            extra={"run_id": str(state.run_id), "prd_mode": state.prd_mode},
        )
        state.error = "Project not in maintenance mode"
        state.success = False
        return state

    state.success = True
    return state


def load_signal(state: SurgicalUpdateState) -> SurgicalUpdateState:
    """Load signal data."""
    from app.db.phase0 import get_supabase

    logger.info(
        f"Loading signal {state.signal_id}",
        extra={"run_id": str(state.run_id)},
    )

    supabase = get_supabase()
    response = supabase.table("signals").select("*").eq("id", str(state.signal_id)).single().execute()

    if not response.data:
        state.error = f"Signal {state.signal_id} not found"
        state.success = False
        return state

    state.signal = response.data
    return state


def load_canonical_index(state: SurgicalUpdateState) -> SurgicalUpdateState:
    """Load all entities for claim routing."""
    logger.info(
        f"Building canonical index for project {state.project_id}",
        extra={"run_id": str(state.run_id)},
    )

    # Use dedicated canonical index builder
    state.canonical_index = build_canonical_index(state.project_id)

    logger.info(
        f"Canonical index built: {len(state.canonical_index.features)} features, "
        f"{len(state.canonical_index.personas)} personas, "
        f"{len(state.canonical_index.vp_steps)} VP steps",
        extra={"run_id": str(state.run_id)},
    )

    return state


def extract_claims_node(state: SurgicalUpdateState) -> SurgicalUpdateState:
    """Extract claims from signal."""
    if not state.signal or not state.canonical_index:
        state.error = "Missing signal or canonical index"
        return state

    logger.info(
        f"Extracting claims from signal {state.signal_id}",
        extra={"run_id": str(state.run_id)},
    )

    claims = extract_claims_from_signal(
        signal=state.signal,
        canonical_index=state.canonical_index,
        run_id=state.run_id,
    )

    state.claims = claims
    return state


def route_claims_node(state: SurgicalUpdateState) -> SurgicalUpdateState:
    """Route claims to entities."""
    logger.info(
        f"Routing {len(state.claims)} claims",
        extra={"run_id": str(state.run_id)},
    )

    grouped, proposals = route_claims(state.claims)

    # Convert tuple keys to strings for JSON serialization
    state.grouped_claims = {
        f"{entity_type}:{entity_id}": claims
        for (entity_type, entity_id), claims in grouped.items()
    }
    state.new_proposals = proposals

    return state


def generate_patches_node(state: SurgicalUpdateState) -> SurgicalUpdateState:
    """Generate scoped patches for each entity using entity-specific generators."""
    logger.info(
        f"Generating patches for {len(state.grouped_claims)} entities",
        extra={"run_id": str(state.run_id)},
    )

    patches = []

    for key, claims in state.grouped_claims.items():
        entity_type, entity_id_str = key.split(":", 1)
        entity_id = UUID(entity_id_str)

        # Load entity
        entity = _load_entity(entity_type, entity_id)
        if not entity:
            logger.warning(f"Entity {entity_type}:{entity_id} not found, skipping")
            continue

        # Generate patch using entity-specific generator
        try:
            if entity_type == "feature":
                # Features use generic scoped patch generator
                allowed_fields = ["description", "acceptance_criteria", "dependencies", "risks", "notes"]
                patch = generate_scoped_patch(
                    entity_type=entity_type,
                    entity=entity,
                    claims=claims,
                    allowed_fields=allowed_fields,
                    run_id=state.run_id,
                )
            elif entity_type == "persona":
                # Personas use persona-specific generator
                patch = generate_persona_patch(
                    persona=entity,
                    claims=claims,
                    run_id=state.run_id,
                )
            elif entity_type == "vp_step":
                # VP steps use generic scoped patch generator
                allowed_fields = ["description", "user_benefit_pain", "notes"]
                patch = generate_scoped_patch(
                    entity_type=entity_type,
                    entity=entity,
                    claims=claims,
                    allowed_fields=allowed_fields,
                    run_id=state.run_id,
                )
            else:
                logger.warning(f"Unknown entity type {entity_type}, skipping")
                continue

            patches.append(patch)
        except Exception as e:
            logger.error(f"Failed to generate patch for {entity_type}:{entity_id}: {e}")
            continue

    state.patches = patches
    return state


def apply_or_escalate_node(state: SurgicalUpdateState) -> SurgicalUpdateState:
    """Apply safe patches or escalate risky ones."""
    logger.info(
        f"Classifying {len(state.patches)} patches",
        extra={"run_id": str(state.run_id)},
    )

    for patch in state.patches:
        if patch.classification.auto_apply_ok:
            # Auto-apply
            try:
                _apply_patch(patch)
                state.applied_count += 1
                state.applied_patches.append(patch)  # Track for enrichment
                logger.info(
                    f"Auto-applied patch to {patch.entity_type} '{patch.entity_name}'",
                    extra={"run_id": str(state.run_id)},
                )
            except Exception as e:
                logger.error(f"Failed to apply patch: {e}")
                # Escalate on error
                state.escalations.append(
                    Escalation(
                        patch=patch,
                        escalation_reason=f"Auto-apply failed: {str(e)}",
                        recommended_action="review",
                        created_at="",  # Will be set by serialization
                    )
                )
                state.escalated_count += 1
        else:
            # Escalate
            state.escalations.append(
                Escalation(
                    patch=patch,
                    escalation_reason=patch.classification.rationale,
                    recommended_action="review",
                    created_at="",
                )
            )
            state.escalated_count += 1
            logger.info(
                f"Escalated patch for {patch.entity_type} '{patch.entity_name}': {patch.classification.rationale}",
                extra={"run_id": str(state.run_id)},
            )

    # Also escalate new object proposals
    for proposal in state.new_proposals:
        state.escalations.append(
            Escalation(
                patch=ScopedPatch(
                    entity_type=proposal.target.type,
                    entity_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
                    entity_name=f"New {proposal.target.type}",
                    allowed_fields=[],
                    changes={},
                    change_summary=proposal.claim,
                    evidence=[proposal.evidence],
                    classification=None,  # type: ignore
                    claims=[proposal],
                ),
                escalation_reason=f"Proposes creating new {proposal.target.type}",
                recommended_action="review",
                created_at="",
            )
        )
        state.escalated_count += 1

    state.success = True
    return state


# =========================
# Helper Functions
# =========================


def _load_entity(entity_type: str, entity_id: UUID) -> dict[str, Any] | None:
    """Load entity from database."""
    try:
        if entity_type == "feature":
            return get_feature(entity_id)
        elif entity_type == "persona":
            return get_persona(entity_id)
        elif entity_type == "vp_step":
            return get_vp_step(entity_id)
        else:
            return None
    except Exception as e:
        logger.error(f"Failed to load {entity_type} {entity_id}: {e}")
        return None


def _get_allowed_fields(entity_type: str) -> list[str]:
    """Get allowed fields for surgical updates by entity type."""
    if entity_type == "feature":
        return ["description", "acceptance_criteria", "dependencies", "risks", "notes"]
    elif entity_type == "persona":
        return ["demographics", "psychographics", "goals", "pain_points", "description"]
    elif entity_type == "vp_step":
        return ["description", "user_benefit_pain", "notes"]
    else:
        return []


def _apply_patch(patch: ScopedPatch) -> None:
    """Apply a patch to an entity."""
    entity_id = patch.entity_id
    changes = patch.changes

    if patch.entity_type == "feature":
        # Get feature details dict
        feature = get_feature(entity_id)
        if not feature:
            raise ValueError(f"Feature {entity_id} not found")

        details = feature.get("details", {})
        for field, value in changes.items():
            details[field] = value

        update_feature(entity_id, {"details": details})

    elif patch.entity_type == "persona":
        update_persona(entity_id, changes)

    elif patch.entity_type == "vp_step":
        update_vp_step(entity_id, changes)


# =========================
# Build Graph
# =========================


def build_surgical_update_graph() -> StateGraph:
    """Build the surgical update graph."""
    graph = StateGraph(SurgicalUpdateState)

    # Add nodes
    graph.add_node("check_mode", check_mode)
    graph.add_node("load_signal", load_signal)
    graph.add_node("load_canonical_index", load_canonical_index)
    graph.add_node("extract_claims", extract_claims_node)
    graph.add_node("route_claims", route_claims_node)
    graph.add_node("generate_patches", generate_patches_node)
    graph.add_node("apply_or_escalate", apply_or_escalate_node)

    # Add edges
    graph.set_entry_point("check_mode")
    graph.add_edge("check_mode", "load_signal")
    graph.add_edge("load_signal", "load_canonical_index")
    graph.add_edge("load_canonical_index", "extract_claims")
    graph.add_edge("extract_claims", "route_claims")
    graph.add_edge("route_claims", "generate_patches")
    graph.add_edge("generate_patches", "apply_or_escalate")
    graph.add_edge("apply_or_escalate", END)

    return graph.compile(checkpointer=MemorySaver())


# =========================
# Main Entry Point
# =========================


def run_surgical_update(
    signal_id: UUID,
    project_id: UUID,
    run_id: UUID,
) -> SurgicalUpdateResult:
    """Run surgical update pipeline for a signal.

    Args:
        signal_id: Signal UUID
        project_id: Project UUID
        run_id: Run tracking UUID

    Returns:
        SurgicalUpdateResult with patches applied and escalations

    Raises:
        Exception: If pipeline fails
    """
    logger.info(
        f"Starting surgical update for signal {signal_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    graph = build_surgical_update_graph()

    initial_state = SurgicalUpdateState(
        signal_id=signal_id,
        project_id=project_id,
        run_id=run_id,
    )

    # Run graph with checkpointer config
    config = {"configurable": {"thread_id": str(run_id)}}
    fs = graph.invoke(initial_state, config=config)

    # LangGraph StateGraph.invoke() returns a dict in v1.0+
    _g = fs.get if isinstance(fs, dict) else lambda k, d=None: getattr(fs, k, d)

    # Build result
    result = SurgicalUpdateResult(
        signal_id=signal_id,
        project_id=project_id,
        claims_extracted=len(_g("claims", [])),
        patches_generated=len(_g("patches", [])),
        patches_applied=_g("applied_count", 0),
        patches_escalated=_g("escalated_count", 0),
        applied_patches=_g("applied_patches", []),
        escalations=_g("escalations", []),
        new_proposals=_g("new_proposals", []),
        success=_g("success", False),
        error=_g("error", None),
    )

    logger.info(
        f"Surgical update complete: {result.patches_applied} applied, {result.patches_escalated} escalated",
        extra={"run_id": str(run_id), "result": result.model_dump()},
    )

    return result
