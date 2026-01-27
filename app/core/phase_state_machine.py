"""
Phase State Machine for Collaboration System

Handles phase transitions, gate checking, and readiness calculation.
Integrates with the existing Overview readiness system.

Linear phase flow:
  PRE_DISCOVERY → DISCOVERY → VALIDATION → PROTOTYPE → PROPOSAL → BUILD → DELIVERY
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.core.schemas_collaboration import (
    CollaborationPhase,
    PhaseGate,
    PhaseProgressConfig,
    PhaseStep,
    PhaseStepStatus,
)


# ============================================================================
# Phase Definitions
# ============================================================================

@dataclass
class PhaseDefinition:
    """Definition of a collaboration phase with its steps and gates."""
    phase: CollaborationPhase
    display_name: str
    steps: list[dict]  # {id, label, unlock_gate}
    completion_gates: list[dict]  # {id, label, condition}
    portal_content_type: str  # What client sees


PHASE_DEFINITIONS: dict[CollaborationPhase, PhaseDefinition] = {
    CollaborationPhase.PRE_DISCOVERY: PhaseDefinition(
        phase=CollaborationPhase.PRE_DISCOVERY,
        display_name="Pre-Discovery",
        steps=[
            {"id": "generate", "label": "Generate Prep", "unlock_gate": None},
            {"id": "confirm", "label": "Confirm Items", "unlock_gate": "items_generated"},
            {"id": "invite", "label": "Invite Clients", "unlock_gate": "items_confirmed"},
            {"id": "send", "label": "Send to Portal", "unlock_gate": "clients_invited"},
            {"id": "responses", "label": "Responses", "unlock_gate": "items_sent"},
        ],
        completion_gates=[
            {"id": "items_generated", "label": "Items generated", "condition": "items_generated >= 1"},
            {"id": "items_confirmed", "label": "At least 1 item confirmed", "condition": "items_confirmed >= 1"},
            {"id": "clients_invited", "label": "At least 1 client invited", "condition": "clients_invited >= 1"},
            {"id": "items_sent", "label": "Items sent to portal", "condition": "items_sent == True"},
            {"id": "responses_received", "label": "Responses received", "condition": "responses_received == True"},
        ],
        portal_content_type="questions_and_documents",
    ),
    CollaborationPhase.DISCOVERY: PhaseDefinition(
        phase=CollaborationPhase.DISCOVERY,
        display_name="Discovery",
        steps=[
            {"id": "prepare", "label": "Prepare", "unlock_gate": None},
            {"id": "conduct", "label": "Conduct Call", "unlock_gate": "prep_complete"},
            {"id": "process", "label": "Process Notes", "unlock_gate": "call_completed"},
        ],
        completion_gates=[
            {"id": "prep_complete", "label": "Prep materials ready", "condition": "prep_complete == True"},
            {"id": "call_completed", "label": "Call completed", "condition": "call_completed == True"},
            {"id": "notes_processed", "label": "Notes processed", "condition": "notes_processed == True"},
        ],
        portal_content_type="agenda_readonly",
    ),
    CollaborationPhase.VALIDATION: PhaseDefinition(
        phase=CollaborationPhase.VALIDATION,
        display_name="Validation",
        steps=[
            {"id": "extract", "label": "Extract", "unlock_gate": None},
            {"id": "generate", "label": "Generate Reqs", "unlock_gate": "extraction_complete"},
            {"id": "review", "label": "Review", "unlock_gate": "items_generated"},
            {"id": "send", "label": "Send", "unlock_gate": "items_validated"},
            {"id": "confirm", "label": "Client Confirms", "unlock_gate": "items_sent"},
        ],
        completion_gates=[
            {"id": "extraction_complete", "label": "Insights extracted", "condition": "extraction_complete == True"},
            {"id": "items_generated", "label": "Requirements generated", "condition": "requirements_count >= 1"},
            {"id": "items_validated", "label": "Items validated internally", "condition": "items_validated >= 1"},
            {"id": "items_sent", "label": "Items sent to client", "condition": "items_sent == True"},
            {"id": "client_confirmed", "label": "80%+ confirmed", "condition": "confirmation_rate >= 80"},
        ],
        portal_content_type="requirements_confirmation",
    ),
    CollaborationPhase.PROTOTYPE: PhaseDefinition(
        phase=CollaborationPhase.PROTOTYPE,
        display_name="Prototype",
        steps=[
            {"id": "build", "label": "Build", "unlock_gate": None},
            {"id": "review", "label": "Review", "unlock_gate": "build_ready"},
            {"id": "send", "label": "Send Link", "unlock_gate": "internal_approved"},
            {"id": "feedback", "label": "Feedback", "unlock_gate": "link_sent"},
            {"id": "iterate", "label": "Iterate", "unlock_gate": "feedback_received"},
        ],
        completion_gates=[
            {"id": "build_ready", "label": "Prototype built", "condition": "build_ready == True"},
            {"id": "internal_approved", "label": "Internal review passed", "condition": "internal_approved == True"},
            {"id": "link_sent", "label": "Link sent to client", "condition": "link_sent == True"},
            {"id": "feedback_received", "label": "Feedback received", "condition": "feedback_received == True"},
            {"id": "prototype_approved", "label": "Prototype approved", "condition": "prototype_approved == True"},
        ],
        portal_content_type="prototype_feedback",
    ),
    CollaborationPhase.PROPOSAL: PhaseDefinition(
        phase=CollaborationPhase.PROPOSAL,
        display_name="Proposal",
        steps=[
            {"id": "generate", "label": "Generate", "unlock_gate": None},
            {"id": "review", "label": "Review", "unlock_gate": "proposal_generated"},
            {"id": "send", "label": "Send", "unlock_gate": "internally_approved"},
            {"id": "negotiate", "label": "Negotiate", "unlock_gate": "proposal_sent"},
            {"id": "signoff", "label": "Sign-off", "unlock_gate": "negotiations_complete"},
        ],
        completion_gates=[
            {"id": "proposal_generated", "label": "Proposal generated", "condition": "proposal_generated == True"},
            {"id": "internally_approved", "label": "Internally approved", "condition": "internally_approved == True"},
            {"id": "proposal_sent", "label": "Proposal sent", "condition": "proposal_sent == True"},
            {"id": "negotiations_complete", "label": "Negotiations complete", "condition": "negotiations_complete == True"},
            {"id": "proposal_signed", "label": "Proposal signed", "condition": "proposal_signed == True"},
        ],
        portal_content_type="proposal_negotiation",
    ),
    CollaborationPhase.BUILD: PhaseDefinition(
        phase=CollaborationPhase.BUILD,
        display_name="Build",
        steps=[
            {"id": "build", "label": "Build", "unlock_gate": None},
            {"id": "review", "label": "Review", "unlock_gate": "build_checkpoint"},
            {"id": "send", "label": "Send Update", "unlock_gate": "internal_approved"},
            {"id": "feedback", "label": "Feedback", "unlock_gate": "update_sent"},
            {"id": "test", "label": "Test", "unlock_gate": "feedback_incorporated"},
        ],
        completion_gates=[
            {"id": "build_checkpoint", "label": "Build checkpoint reached", "condition": "build_checkpoint == True"},
            {"id": "internal_approved", "label": "Internal review passed", "condition": "internal_approved == True"},
            {"id": "update_sent", "label": "Update sent", "condition": "update_sent == True"},
            {"id": "feedback_incorporated", "label": "Feedback incorporated", "condition": "feedback_incorporated == True"},
            {"id": "tests_pass", "label": "All tests pass", "condition": "tests_pass == True"},
            {"id": "client_approved", "label": "Client approved", "condition": "client_approved == True"},
        ],
        portal_content_type="build_updates",
    ),
    CollaborationPhase.DELIVERY: PhaseDefinition(
        phase=CollaborationPhase.DELIVERY,
        display_name="Delivery",
        steps=[
            {"id": "package", "label": "Package", "unlock_gate": None},
            {"id": "qa", "label": "QA", "unlock_gate": "packaged"},
            {"id": "handoff", "label": "Handoff", "unlock_gate": "qa_passed"},
            {"id": "signoff", "label": "Sign-off", "unlock_gate": "delivered"},
        ],
        completion_gates=[
            {"id": "packaged", "label": "Deliverables packaged", "condition": "packaged == True"},
            {"id": "qa_passed", "label": "QA passed", "condition": "qa_passed == True"},
            {"id": "delivered", "label": "Delivered to client", "condition": "delivered == True"},
            {"id": "signed_off", "label": "Client signed off", "condition": "signed_off == True"},
        ],
        portal_content_type="deliverables",
    ),
}


# Phase order for linear progression
PHASE_ORDER = [
    CollaborationPhase.PRE_DISCOVERY,
    CollaborationPhase.DISCOVERY,
    CollaborationPhase.VALIDATION,
    CollaborationPhase.PROTOTYPE,
    CollaborationPhase.PROPOSAL,
    CollaborationPhase.BUILD,
    CollaborationPhase.DELIVERY,
]


# ============================================================================
# Gate Evaluation
# ============================================================================


def evaluate_gate(gate: dict, state: dict) -> tuple[bool, Any]:
    """
    Evaluate a gate condition against the current state.

    Returns:
        (met, current_value) - whether gate is met and the current value
    """
    condition = gate.get("condition", "")

    # Parse simple conditions
    # Format: "field >= value" or "field == value" or "field == True"
    if ">=" in condition:
        field, value = condition.split(">=")
        field = field.strip()
        value = int(value.strip())
        current = state.get(field, 0)
        return current >= value, current
    elif "==" in condition:
        field, value = condition.split("==")
        field = field.strip()
        value = value.strip()
        current = state.get(field)
        if value == "True":
            return current == True, current
        elif value == "False":
            return current == False, current
        else:
            return current == int(value), current

    return False, None


def get_phase_readiness(phase: CollaborationPhase, state: dict) -> tuple[int, list[PhaseGate]]:
    """
    Calculate readiness score for a phase based on its gates.

    Returns:
        (readiness_score, gates) - 0-100% readiness and evaluated gates
    """
    definition = PHASE_DEFINITIONS.get(phase)
    if not definition:
        return 0, []

    gates = []
    met_count = 0

    for gate_def in definition.completion_gates:
        met, current_value = evaluate_gate(gate_def, state)
        gates.append(PhaseGate(
            id=gate_def["id"],
            label=gate_def["label"],
            condition=gate_def["condition"],
            met=met,
            current_value=current_value,
            required_for_completion=True,
        ))
        if met:
            met_count += 1

    total = len(definition.completion_gates)
    readiness = int((met_count / total) * 100) if total > 0 else 0

    return readiness, gates


def get_step_status(step_def: dict, gates: list[PhaseGate], state: dict) -> PhaseStepStatus:
    """Determine the status of a step based on gate states."""
    unlock_gate = step_def.get("unlock_gate")

    # First step is always available
    if unlock_gate is None:
        # Check if step is completed
        step_id = step_def["id"]
        if state.get(f"{step_id}_complete"):
            return PhaseStepStatus.COMPLETED
        elif state.get(f"{step_id}_in_progress"):
            return PhaseStepStatus.IN_PROGRESS
        return PhaseStepStatus.AVAILABLE

    # Find the unlock gate
    gate = next((g for g in gates if g.id == unlock_gate), None)
    if gate and gate.met:
        step_id = step_def["id"]
        if state.get(f"{step_id}_complete"):
            return PhaseStepStatus.COMPLETED
        elif state.get(f"{step_id}_in_progress"):
            return PhaseStepStatus.IN_PROGRESS
        return PhaseStepStatus.AVAILABLE

    return PhaseStepStatus.LOCKED


def get_unlock_message(step_def: dict, gates: list[PhaseGate]) -> Optional[str]:
    """Get unlock message for a locked step."""
    unlock_gate = step_def.get("unlock_gate")
    if not unlock_gate:
        return None

    gate = next((g for g in gates if g.id == unlock_gate), None)
    if gate and not gate.met:
        return f"Requires: {gate.label}"

    return None


# ============================================================================
# Phase Configuration Builder
# ============================================================================


def build_phase_config(phase: CollaborationPhase, state: dict) -> PhaseProgressConfig:
    """
    Build the full phase configuration with evaluated gates and step statuses.

    Args:
        phase: Current collaboration phase
        state: Current state values for gate evaluation

    Returns:
        PhaseProgressConfig with steps, gates, and readiness
    """
    definition = PHASE_DEFINITIONS.get(phase)
    if not definition:
        return PhaseProgressConfig(
            phase=phase,
            steps=[],
            gates=[],
            readiness_score=0,
        )

    # Evaluate gates
    readiness, gates = get_phase_readiness(phase, state)

    # Build steps with statuses
    steps = []
    for step_def in definition.steps:
        status = get_step_status(step_def, gates, state)
        unlock_message = get_unlock_message(step_def, gates) if status == PhaseStepStatus.LOCKED else None

        # Get progress if applicable
        progress = None
        step_id = step_def["id"]
        if f"{step_id}_current" in state and f"{step_id}_total" in state:
            progress = {
                "current": state[f"{step_id}_current"],
                "total": state[f"{step_id}_total"],
            }

        steps.append(PhaseStep(
            id=step_id,
            label=step_def["label"],
            status=status,
            progress=progress,
            unlock_message=unlock_message,
        ))

    return PhaseProgressConfig(
        phase=phase,
        steps=steps,
        gates=gates,
        readiness_score=readiness,
    )


# ============================================================================
# Phase Transitions
# ============================================================================


def can_advance_phase(current_phase: CollaborationPhase, state: dict) -> bool:
    """Check if we can advance to the next phase."""
    readiness, gates = get_phase_readiness(current_phase, state)

    # All required gates must be met
    required_gates = [g for g in gates if g.required_for_completion]
    return all(g.met for g in required_gates)


def get_next_phase(current_phase: CollaborationPhase) -> Optional[CollaborationPhase]:
    """Get the next phase in the linear progression."""
    try:
        current_index = PHASE_ORDER.index(current_phase)
        if current_index < len(PHASE_ORDER) - 1:
            return PHASE_ORDER[current_index + 1]
    except ValueError:
        pass
    return None


def get_previous_phase(current_phase: CollaborationPhase) -> Optional[CollaborationPhase]:
    """Get the previous phase (for loops like validation rounds)."""
    try:
        current_index = PHASE_ORDER.index(current_phase)
        if current_index > 0:
            return PHASE_ORDER[current_index - 1]
    except ValueError:
        pass
    return None


def get_phase_index(phase: CollaborationPhase) -> int:
    """Get the index of a phase in the linear progression."""
    try:
        return PHASE_ORDER.index(phase)
    except ValueError:
        return -1


def get_all_phases_status(current_phase: CollaborationPhase) -> list[dict]:
    """Get status of all phases for the overview display."""
    current_index = get_phase_index(current_phase)

    phases = []
    for i, phase in enumerate(PHASE_ORDER):
        if i < current_index:
            status = "completed"
        elif i == current_index:
            status = "active"
        else:
            status = "locked"

        phases.append({
            "phase": phase.value,
            "display_name": PHASE_DEFINITIONS[phase].display_name,
            "status": status,
            "index": i,
        })

    return phases


# ============================================================================
# State Building Helpers
# ============================================================================


async def build_pre_discovery_state(project_id: UUID) -> dict:
    """Build state dict for pre-discovery phase from database."""
    from app.db.supabase_client import get_supabase

    client = get_supabase()

    # Get discovery prep bundle status
    bundle_result = client.table("discovery_prep_bundles").select("*").eq(
        "project_id", str(project_id)
    ).order("updated_at", desc=True).limit(1).execute()

    bundle = bundle_result.data[0] if bundle_result.data else None

    # Get question/doc counts
    questions_total = 0
    questions_confirmed = 0
    docs_total = 0
    docs_confirmed = 0

    if bundle:
        questions = bundle.get("questions", [])
        docs = bundle.get("documents", [])
        questions_total = len(questions)
        questions_confirmed = sum(1 for q in questions if q.get("confirmed"))
        docs_total = len(docs)
        docs_confirmed = sum(1 for d in docs if d.get("confirmed"))

    # Get client count
    members_result = client.table("project_members").select("*").eq(
        "project_id", str(project_id)
    ).eq("role", "client").execute()

    clients_invited = len(members_result.data)

    # Check if items sent
    items_sent = bundle.get("sent_to_portal_at") is not None if bundle else False

    # Check for responses (simplified - would check info_requests in real impl)
    responses_received = False  # TODO: Check actual responses

    return {
        "items_generated": questions_total + docs_total,
        "items_confirmed": questions_confirmed + docs_confirmed,
        "clients_invited": clients_invited,
        "items_sent": items_sent,
        "responses_received": responses_received,
        # Step progress
        "confirm_current": questions_confirmed + docs_confirmed,
        "confirm_total": questions_total + docs_total,
    }


async def build_validation_state(project_id: UUID) -> dict:
    """Build state dict for validation phase from database."""
    from app.db.supabase_client import get_supabase

    client = get_supabase()

    # Get features needing confirmation
    features_result = client.table("features").select("id, confirmation_status").eq(
        "project_id", str(project_id)
    ).execute()

    total_features = len(features_result.data)
    confirmed_features = sum(
        1 for f in features_result.data
        if f.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")
    )

    confirmation_rate = int((confirmed_features / total_features) * 100) if total_features > 0 else 0

    return {
        "extraction_complete": True,  # Simplified
        "requirements_count": total_features,
        "items_validated": confirmed_features,
        "items_sent": False,  # TODO: Check client packages
        "confirmation_rate": confirmation_rate,
    }


async def build_phase_state(project_id: UUID, phase: CollaborationPhase) -> dict:
    """Build state dict for a given phase."""
    if phase == CollaborationPhase.PRE_DISCOVERY:
        return await build_pre_discovery_state(project_id)
    elif phase == CollaborationPhase.VALIDATION:
        return await build_validation_state(project_id)
    # Add other phases as needed
    return {}
